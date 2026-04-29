#!/usr/bin/env python3
"""
Scanner de impactos da migração de CNPJ numérico para alfanumérico.
Uso: python scanner_cnpj_alfanumerico.py <diretorio_ou_lista>
Aceita apenas UM parâmetro; para múltiplos diretórios use separador ';' ou ','.
"""
from __future__ import annotations
import csv
import html
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Pattern, Tuple

RULES_VERSION = "1.0.0"
SEVERITY_ORDER = {"ALTA": 3, "MEDIA": 2, "BAIXA": 1}
DEFAULT_IGNORED_DIRS = {
    ".git", "node_modules", "bin", "obj", "dist", "build", "target",
    "packages", ".vs", ".idea", ".vscode", "vendor", "coverage", "__pycache__"
}
DEFAULT_EXTENSIONS = {
    ".cs", ".java", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".sql",
    ".php", ".py", ".rb", ".sh", ".ps1", ".xml", ".json", ".yml", ".yaml", ".ini",
    ".cfg", ".conf", ".properties", ".md", ".txt", ".pdi", ".ktr", ".kjb"
}

LANG_BY_EXT = {
    ".cs": "C#", ".java": "Java", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sql": "SQL",
    ".php": "PHP", ".py": "Python", ".rb": "Ruby", ".sh": "Shell", ".ps1": "PowerShell",
    ".xml": "XML", ".json": "JSON", ".yml": "YAML", ".yaml": "YAML", ".ini": "Config",
    ".cfg": "Config", ".conf": "Config", ".properties": "Config", ".md": "Markdown", ".txt": "Text",
    ".pdi": "ETL/PDI", ".ktr": "ETL/PDI", ".kjb": "ETL/PDI"
}

@dataclass
class Occurrence:
    produto: str
    arquivo: str
    linguagem: str
    linha: int
    trecho: str
    regra: str
    categoria: str
    severidade: str
    risco: str
    sugestao: str
    exemplo_correcao: str

@dataclass
class Rule:
    id: str
    pattern: Pattern[str]
    categoria: str
    severidade: str
    risco: str
    sugestao: str
    exemplo: str


def load_config(base_dir: Path) -> Dict:
    config = {
        "ignored_dirs": sorted(DEFAULT_IGNORED_DIRS),
        "extensions": sorted(DEFAULT_EXTENSIONS),
        "ignored_extensions": [],
        "custom_rules": [],
        "product_names": {},
        "max_file_size_bytes": 2_000_000,
        "min_severity": "BAIXA",
    }
    candidates = [Path.cwd() / "scanner-config.json", Path.cwd() / "scanner-config.yml", base_dir / "scanner-config.json", base_dir / "scanner-config.yml"]
    for cfg in candidates:
        if not cfg.exists():
            continue
        try:
            if cfg.suffix == ".json":
                loaded = json.loads(cfg.read_text(encoding="utf-8"))
            else:
                loaded = parse_simple_yaml(cfg.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config.update(loaded)
        except Exception as exc:
            print(f"[WARN] Falha ao ler config {cfg}: {exc}")
        break
    config["ignored_dirs"] = set(config.get("ignored_dirs", []))
    config["extensions"] = set(config.get("extensions", [])) or DEFAULT_EXTENSIONS
    config["ignored_extensions"] = set(config.get("ignored_extensions", []))
    return config


def parse_simple_yaml(content: str) -> Dict:
    """Parser YAML simplificado (chave: valor, listas com '-')."""
    out: Dict = {}
    key = None
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("-"):
            k, v = [x.strip() for x in line.split(":", 1)]
            if not v:
                out[k] = []
                key = k
            else:
                out[k] = yaml_scalar(v)
                key = None
        elif line.startswith("-") and key:
            out.setdefault(key, []).append(yaml_scalar(line[1:].strip()))
    return out


def yaml_scalar(v: str):
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    if v.isdigit():
        return int(v)
    return v.strip('"\'')


def build_rules(custom_rules: List[Dict]) -> List[Rule]:
    base_rules = [
        Rule("REGEX_CNPJ_NUMERICO", re.compile(r"cnpj.*(\\d\{14\}|\[0-9\]\{14\}|\^\\d\+\$|\[0-9\]\+)", re.I), "VALIDACAO", "ALTA", "Regex limita CNPJ a dígitos.", "Permitir A-Z e 0-9 nas 12 primeiras posições úteis.", r"^[A-Z0-9]{12}[0-9]{2}$"),
        Rule("MASCARA_CNPJ_FIXA", re.compile(r"(00\.000\.000/0000-00|##\.###\.###/####-##|99\.999\.999/9999-99)"), "MASCARA_FORMATACAO", "ALTA", "Máscara fixa pode bloquear alfanuméricos.", "Trocar máscara por componente flexível ou máscara alfanumérica.", "AAAAAA00/AAAA-00 (exemplo conceitual)"),
        Rule("SOMENTE_DIGITOS", re.compile(r"(onlyNumbers|somenteNumeros|removeNonDigits|Regex\.Replace\(.*\\D|replace\(/\\D\+/g|[^a-z]replace\([^)]*[^0-9])", re.I), "VALIDACAO", "ALTA", "Remoção forçada elimina letras válidas do novo CNPJ.", "Preservar letras e números; normalizar apenas separadores.", "value.replace(/[\.\/-]/g, '')"),
        Rule("TIPO_NUMERICO_CNPJ", re.compile(r"(cnpj\w*\s*[:=]\s*(int|long|decimal|number|numeric|bigint)|\b(int|long|decimal|numeric|bigint)\b\s+\w*cnpj\w*)", re.I), "BACKEND", "ALTA", "Tipo numérico perde zeros e não suporta letras.", "Migrar para string/char/varchar.", "cnpj VARCHAR(14)"),
        Rule("VALIDACAO_TAMANHO_NUMERICO", re.compile(r"(cnpj.*(len\(|length\(|\.Length|size\()\s*[^\n]*14[^\n]*(digit|numeric|\d))", re.I), "VALIDACAO", "MEDIA", "Validação de tamanho pode manter regra somente numérica.", "Manter tamanho 14, mas aceitar alfanumérico nas 12 primeiras posições.", "len(cnpj)==14 and re.match(r'^[A-Z0-9]{12}[0-9]{2}$',cnpj)"),
        Rule("CALCULO_DV_NUMERICO", re.compile(r"(cnpj.*(int\(|parseInt|Convert\.ToInt|Character\.getNumericValue|\-\s*48))", re.I), "VALIDACAO", "MEDIA", "Cálculo DV pode pressupor caracteres apenas numéricos.", "Adaptar algoritmo oficial para base alfanumérica quando aplicável.", "mapear A-Z para valores conforme norma oficial"),
        Rule("BANCO_COLUNA_NUMERICA", re.compile(r"(cnpj\w*\s+(int|bigint|numeric|decimal|number))", re.I), "BANCO_DE_DADOS", "ALTA", "Coluna numérica de banco não suporta CNPJ alfanumérico.", "Migrar coluna para VARCHAR(14) e revisar índices.", "ALTER TABLE cliente ALTER COLUMN cnpj TYPE VARCHAR(14);"),
        Rule("CHECK_CONSTRAINT_NUMERICA", re.compile(r"(check\s*\(.*cnpj.*(only|digit|\d|0-9).*(14|len|length).*)", re.I), "BANCO_DE_DADOS", "ALTA", "Constraint restringe CNPJ a número.", "Atualizar check para padrão alfanumérico oficial.", "CHECK (cnpj ~ '^[A-Z0-9]{12}[0-9]{2}$')"),
        Rule("MENSAGEM_SOMENTE_NUMEROS", re.compile(r"(cnpj.*(somente numeros|apenas numeros|only numbers))", re.I), "FRONTEND", "MEDIA", "Mensagem de UX orienta regra desatualizada.", "Atualizar mensagem para formato alfanumérico.", "'Informe CNPJ com 14 posições (alfanumérico)'."),
        Rule("TESTE_CNPJ_NUMERICO", re.compile(r"(assert.*cnpj.*\d{14}|cnpj.*(11\.111\.111/1111-11|\d{14}))", re.I), "TESTE", "MEDIA", "Teste automatizado cobre apenas cenário numérico.", "Adicionar casos com letras válidas.", "CNPJ exemplo: AB12CD34EF5601"),
        Rule("IDENTIFICADOR_CNPJ", re.compile(r"\b(cnpj|cnpj_raiz|cnpjBase|companyDocument)\b", re.I), "POSSIVEL_FALSO_POSITIVO", "BAIXA", "Referência a CNPJ pode exigir revisão contextual.", "Revisar manualmente o uso semântica e contrato.", "Tipo textual + validação nova"),
    ]
    for cr in custom_rules or []:
        try:
            base_rules.append(Rule(cr["id"], re.compile(cr["pattern"], re.I), cr.get("categoria", "POSSIVEL_FALSO_POSITIVO"), cr.get("severidade", "BAIXA"), cr.get("risco", "Regra customizada."), cr.get("sugestao", "Revisar."), cr.get("exemplo", "")))
        except Exception:
            pass
    return base_rules


def parse_roots(single_argument: str) -> List[Path]:
    parts = [p.strip() for p in re.split(r"[;,]", single_argument) if p.strip()]
    roots = [Path(p).resolve() for p in parts]
    return [r for r in roots if r.exists() and r.is_dir()]


def detect_language(path: Path) -> str:
    return LANG_BY_EXT.get(path.suffix.lower(), "Outro")


def should_scan(path: Path, cfg: Dict) -> bool:
    ext = path.suffix.lower()
    if ext in cfg["ignored_extensions"]:
        return False
    if cfg["extensions"] and ext not in cfg["extensions"]:
        return False
    try:
        if path.stat().st_size > int(cfg.get("max_file_size_bytes", 2_000_000)):
            return False
    except OSError:
        return False
    return True


def scan_file(path: Path, root: Path, produto: str, rules: List[Rule]) -> List[Occurrence]:
    occs: List[Occurrence] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return occs
    lines = text.splitlines()
    lang = detect_language(path)
    for idx, line in enumerate(lines, start=1):
        if "cnpj" not in line.lower() and not re.search(r"\d{14}|00\.000\.000/0000-00", line):
            continue
        for rule in rules:
            if rule.pattern.search(line):
                occs.append(Occurrence(produto, str(path.relative_to(root)), lang, idx, line.strip()[:300], rule.id, rule.categoria, rule.severidade, rule.risco, rule.sugestao, rule.exemplo))
    return occs


def severity_allowed(sev: str, min_sev: str) -> bool:
    return SEVERITY_ORDER.get(sev, 0) >= SEVERITY_ORDER.get(min_sev, 1)


def write_reports(out_dir: Path, occs: List[Occurrence], scanned_files: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = [asdict(o) for o in occs]
    (out_dir / "relatorio_cnpj.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    with (out_dir / "relatorio_cnpj.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()) if data else list(asdict(Occurrence("", "", "", 0, "", "", "", "", "", "", "")).keys()))
        w.writeheader(); [w.writerow(r) for r in data]

    summary = build_summary(occs, scanned_files)
    (out_dir / "resumo_executivo.txt").write_text(summary, encoding="utf-8")
    (out_dir / "relatorio_cnpj.md").write_text(build_markdown(occs, summary), encoding="utf-8")
    (out_dir / "relatorio_cnpj.html").write_text(build_html(occs, summary), encoding="utf-8")


def counter(occs: List[Occurrence], attr: str) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for o in occs:
        k = getattr(o, attr)
        d[k] = d.get(k, 0) + 1
    return dict(sorted(d.items(), key=lambda x: (-x[1], x[0])))


def build_summary(occs: List[Occurrence], scanned_files: int) -> str:
    by_project = counter(occs, "produto")
    top = ", ".join([f"{k}({v})" for k, v in list(by_project.items())[:5]]) or "Nenhum"
    high = [o for o in occs if o.severidade == "ALTA"]
    risks = ["Campos/tipos numéricos para CNPJ", "Regex/máscaras apenas numéricas", "Sanitização que remove letras"]
    return (
        f"Resumo Executivo - Scanner CNPJ Alfanumérico\n"
        f"Data: {datetime.utcnow().isoformat()}Z\n"
        f"Arquivos varridos: {scanned_files}\n"
        f"Total de ocorrências: {len(occs)}\n"
        f"Ocorrências ALTA: {len(high)}\n"
        f"Projetos mais impactados: {top}\n"
        f"Principais riscos: {', '.join(risks)}\n"
        f"Recomendações gerais: tratar CNPJ como texto, revisar regex/máscaras/validações, alinhar contratos de integração e testes.\n"
        f"Próximos passos: priorizar ALTA, abrir backlog técnico, executar testes de regressão com massa alfanumérica.\n"
    )


def build_markdown(occs: List[Occurrence], summary: str) -> str:
    lines = ["# Relatório de Impacto - CNPJ Alfanumérico", "", "## Resumo Executivo", "```", summary.strip(), "```", "", "## Ocorrências", "", "|Projeto|Arquivo|Linha|Regra|Categoria|Severidade|Trecho|", "|---|---|---:|---|---|---|---|"]
    for o in occs:
        lines.append(f"|{o.produto}|{o.arquivo}|{o.linha}|{o.regra}|{o.categoria}|{o.severidade}|{o.trecho.replace('|','/')}|")
    return "\n".join(lines) + "\n"


def build_html(occs: List[Occurrence], summary: str) -> str:
    by_lang, by_cat, by_sev, by_proj = counter(occs, "linguagem"), counter(occs, "categoria"), counter(occs, "severidade"), counter(occs, "produto")
    def lis(d): return "".join([f"<li><b>{html.escape(k)}</b>: {v}</li>" for k, v in d.items()])
    rows = []
    for o in occs:
        cls = "high" if o.severidade == "ALTA" else ""
        rows.append(f"<tr class='{cls}'><td>{o.produto}</td><td>{html.escape(o.arquivo)}</td><td>{o.linha}</td><td>{o.linguagem}</td><td>{o.regra}</td><td>{o.categoria}</td><td>{o.severidade}</td><td>{html.escape(o.trecho)}</td></tr>")
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Relatório CNPJ</title>
<style>body{{font-family:Arial;margin:20px}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .card{{border:1px solid #ddd;padding:10px;border-radius:8px}} table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:6px}} .high{{background:#ffe5e5}} #f{{margin:10px 0}}</style>
<script>function filtrar(){{const v=document.getElementById('f').value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(v)?'':'none');}}</script></head>
<body><h1>Relatório de Impacto - CNPJ Alfanumérico</h1><pre>{html.escape(summary)}</pre>
<div class='grid'><div class='card'><h3>Por projeto</h3><ul>{lis(by_proj)}</ul></div><div class='card'><h3>Por linguagem</h3><ul>{lis(by_lang)}</ul></div><div class='card'><h3>Por categoria</h3><ul>{lis(by_cat)}</ul></div><div class='card'><h3>Por severidade</h3><ul>{lis(by_sev)}</ul></div></div>
<input id='f' onkeyup='filtrar()' placeholder='Filtrar tabela'>
<table><thead><tr><th>Projeto</th><th>Arquivo</th><th>Linha</th><th>Linguagem</th><th>Regra</th><th>Categoria</th><th>Severidade</th><th>Trecho</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""


def scan_roots(roots: List[Path], config: Dict) -> Tuple[List[Occurrence], int]:
    rules = build_rules(config.get("custom_rules", []))
    min_sev = config.get("min_severity", "BAIXA")
    occs: List[Occurrence] = []
    scanned = 0
    for root in roots:
        produto = config.get("product_names", {}).get(str(root), root.name)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in config["ignored_dirs"]]
            for name in filenames:
                p = Path(dirpath) / name
                if not should_scan(p, config):
                    continue
                scanned += 1
                for o in scan_file(p, root, produto, rules):
                    if severity_allowed(o.severidade, min_sev):
                        occs.append(o)
    return occs, scanned


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scanner_cnpj_alfanumerico.py <pasta_raiz_ou_lista_sep_por_;_ou_,>")
        return 2
    roots = parse_roots(sys.argv[1])
    if not roots:
        print("Nenhum diretório válido informado.")
        return 2
    config = load_config(roots[0])
    occs, scanned = scan_roots(roots, config)
    output = Path.cwd() / "scanner_output"
    write_reports(output, occs, scanned)
    print("=" * 72)
    print("Scanner CNPJ Alfanumérico concluído")
    print(f"Diretórios analisados: {', '.join(str(r) for r in roots)}")
    print(f"Arquivos varridos: {scanned}")
    print(f"Ocorrências encontradas: {len(occs)}")
    print(f"Relatórios: {output}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrompido pelo usuário.")
        raise SystemExit(130)
