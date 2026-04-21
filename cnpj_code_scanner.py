#!/usr/bin/env python3
"""Scanner defensável de impactos do CNPJ alfanumérico."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SUPPORTED_EXTENSIONS = {
    ".cs", ".vb", ".fs", ".fsx", ".java", ".kt", ".kts", ".scala", ".go", ".rs", ".php", ".py", ".rb",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".html", ".htm", ".cshtml", ".razor",
    ".aspx", ".ascx", ".css", ".scss", ".sass", ".less", ".sql", ".ddl", ".dml", ".psql", ".hql", ".ktr", ".kjb",
    ".json", ".xml", ".yml", ".yaml", ".config", ".ini", ".properties", ".env", ".csproj", ".vbproj", ".gradle",
    ".tf", ".tfvars", ".ps1", ".bat", ".cmd", ".sh", ".bash",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "dist", "build", "target", "bin", "obj", ".idea", ".vscode", "coverage",
    "vendor", "packages", "wwwroot", "publicacoes", "__pycache__", ".venv", "venv", "docs", "documentation", "examples", "samples",
}
PROJECT_MARKERS = {
    ".git", ".sln", "pom.xml", "build.gradle", "settings.gradle", "settings.gradle.kts", "package.json", "angular.json",
    "composer.json", "Gemfile", "pyproject.toml", "setup.py", "requirements.txt", "Cargo.toml",
}

SKIP_FILENAME_RE = re.compile(r"\.(?:min\.(?:js|css)|map|lock)$", re.IGNORECASE)
SKIP_FILENAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock"}
CNPJ_ANCHOR_RE = re.compile(r"(?i)\b(cnpj|cpf\s*/\s*cnpj|cpfcnpj|cnpjcpf|nr_cnpj|num_cnpj|cd_cnpj|cnpj_nr|cnpj_num)\b")
MASK_CLASSIC_RE = re.compile(r"00\.000\.000/0000-00|99\.999\.999/9999-99|##\.###\.###/####-##")
NON_CNPJ_TARGET_RE = re.compile(
    r"(?i)\b(telefone|celular|email|e-?mail|fax|cep|endereco|endereço|inscricaoestadual|inscricao_estadual|ie\b|inscricaomunicipal|inscricao_municipal|im\b)\b"
)
POSITIVE_CNPJ_TARGET_RE = re.compile(
    r"(?i)\b(cnpj|cpfcnpj|cpf_cnpj|cpf\s*/\s*cnpj|documento(pj)?|pessoa_juridica|pessoajuridica|cnpj_matriz)\b"
)


@dataclass(frozen=True)
class PatternDef:
    nome: str
    regex: re.Pattern[str]
    categoria: str
    criticidade: str
    prioridade_backlog: str
    score: int
    requires_context: bool = True
    mode: str = "executivo"  # executivo | exploratorio


@dataclass
class Finding:
    projeto: str
    arquivo: str
    arquivo_absoluto: str
    extensao: str
    camada: str
    linha: int
    nome_padrao: str
    categoria: str
    criticidade: str
    trecho: str
    contexto: str
    score: int
    source_kind: str
    is_generated: str
    is_third_party: str
    contextual_match: str
    prioridade_backlog: str
    dedup_id: str


PATTERNS: tuple[PatternDef, ...] = (
    PatternDef("CNPJ", re.compile(r"(?i)\bcnpj\b"), "Referencia Direta", "Alta", "P0", 95, False),
    PatternDef("CPF/CNPJ combinado", re.compile(r"(?i)\bcpf\s*/\s*cnpj\b|\bcpfcnpj\b|\bcnpjcpf\b"), "Referencia Direta", "Alta", "P0", 95, False),
    PatternDef("Nome completo cadastro", re.compile(r"(?i)cadastro nacional (da |de )?pessoa jur[ií]dica"), "Referencia Direta", "Alta", "P1", 85, False),
    PatternDef("Máscara clássica CNPJ", re.compile(r"00\.000\.000/0000-00|99\.999\.999/9999-99|##\.###\.###/####-##|__\.___.___/____-__"), "Mascara", "Alta", "P0", 95, False),
    PatternDef("Mask/Inputmask contextual", re.compile(r"(?i)\b(mask|mascara|inputmask|placeholder|pattern)\b"), "Mascara", "Alta", "P1", 80, True),
    PatternDef("Regex 14 dígitos", re.compile(r"\\d\{14\}|\[0-9\]\{14\}|\b\d\{14\}\b"), "Validacao", "Alta", "P0", 95, True),
    PatternDef("Regex CNPJ formatado", re.compile(r"\\d\{2\}\\\.\\d\{3\}\\\.\\d\{3\}[/\\/]\\d\{4\}-\\d\{2\}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"), "Validacao", "Alta", "P0", 95, True),
    PatternDef("Metodo validar CNPJ", re.compile(r"(?i)\bvalid\w*cnpj\b|\bcnpj\w*valid\b|\bisValidCnpj\b|\bcnpjValido\b|\bcheckCnpj\b|\bvalidaCnpj\b"), "Validacao", "Alta", "P0", 100, False),
    PatternDef("Dígito verificador contextual", re.compile(r"(?i)d[ií]gito\s+verificador|m[oó]dulo\s*11|calcula[_-]?digito|primeiro[_-]?digito|segundo[_-]?digito"), "Validacao", "Alta", "P1", 80, True),
    PatternDef("Pesos CNPJ 1o dígito", re.compile(r"5\s*,\s*4\s*,\s*3\s*,\s*2\s*,\s*9\s*,\s*8\s*,\s*7\s*,\s*6\s*,\s*5\s*,\s*4\s*,\s*3\s*,\s*2"), "Validacao", "Alta", "P0", 98, False),
    PatternDef("Pesos CNPJ 2o dígito", re.compile(r"6\s*,\s*5\s*,\s*4\s*,\s*3\s*,\s*2\s*,\s*9\s*,\s*8\s*,\s*7\s*,\s*6\s*,\s*5\s*,\s*4\s*,\s*3\s*,\s*2"), "Validacao", "Alta", "P0", 98, False),
    PatternDef("Len 14 contextual", re.compile(r"(?i)\blen\s*\(?\s*\w+\s*\)?\s*==\s*14\b|\.length\s*==\s*14\b|max_length\s*=\s*14\b|\bvarchar\s*\(\s*14\s*\)|\bnvarchar\s*\(\s*14\s*\)|\bchar\s*\(\s*14\s*\)"), "Validacao", "Alta", "P0", 90, True),
    PatternDef("IsNumeric contextual", re.compile(r"(?i)\b(isdigit|isnumeric|numeric)\b"), "Validacao", "Alta", "P1", 80, True),
    PatternDef("Nomes de coluna CNPJ", re.compile(r"(?i)\b(nr_cnpj|num_cnpj|cd_cnpj|cnpj_nr|cnpj_num|ds_cnpj|tx_cnpj)\b"), "Banco", "Alta", "P0", 95, False),
    PatternDef("Index/constraint CNPJ", re.compile(r"(?i)(create\s+(unique\s+)?index|constraint)[^\n]{0,100}cnpj"), "Banco", "Alta", "P0", 92, False),
    PatternDef("DDL com CNPJ", re.compile(r"(?i)(create|alter)\s+table[^\n]{0,120}cnpj"), "Banco", "Alta", "P1", 85, False),
    # Exploratório (fora do executivo por padrão)
    PatternDef("Mensagem erro CNPJ", re.compile(r"(?i)(message|mensagem|erro|error|msg)[^\n]{0,60}cnpj|cnpj[^\n]{0,60}(invalido|inválido|invalid|obrigat)"), "Mensagem", "Media", "P3", 50, False, "exploratorio"),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scanner defensável de impacto CNPJ.")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--out-dir", default="./resultado_cnpj_scan")
    p.add_argument("--encoding", default="utf-8")
    p.add_argument("--max-file-size-kb", type=int, default=1024)
    p.add_argument("--include-ext", nargs="*")
    p.add_argument("--exclude-dir", nargs="*")
    p.add_argument("--sem-html", action="store_true")
    p.add_argument("--sem-txt", action="store_true")
    p.add_argument("--somente-csv-html", action="store_true")
    p.add_argument("--project-group-mode", choices=("auto", "topdir", "none"), default="auto")
    p.add_argument("--modo-relatorio", choices=("executivo", "exploratorio"), default="executivo")
    p.add_argument("--context-window", type=int, default=4)
    return p.parse_args()


def detect_project(path: Path, root: Path, mode: str) -> str:
    rel = path.relative_to(root)
    if mode == "none":
        return "SEM_GRUPO"
    if mode == "topdir":
        return rel.parts[0] if len(rel.parts) > 1 else "RAIZ"
    current = path.parent
    while True:
        if any((current / m).exists() for m in PROJECT_MARKERS):
            return "RAIZ" if current == root else current.name
        if current == root:
            break
        current = current.parent
    return rel.parts[0] if len(rel.parts) > 1 else "RAIZ"


def infer_layer(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".sql", ".ddl", ".dml", ".psql", ".hql"}:
        return "Banco"
    if ext in {".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte", ".html", ".htm", ".css", ".scss", ".sass", ".less", ".cshtml", ".razor"}:
        return "Front-end"
    if ext in {".json", ".xml", ".config", ".yml", ".yaml", ".ini", ".properties", ".env", ".csproj", ".vbproj", ".gradle", ".tf", ".tfvars"}:
        return "Config"
    if ext in {".ps1", ".bat", ".cmd", ".sh", ".bash"}:
        return "Script"
    return "Back-end"


def classify_source_kind(path: Path) -> str:
    p = path.as_posix().lower()
    name = path.name.lower()
    if any(token in p for token in ("/vendor/", "/third_party/", "/third-party/", "/plugins/", "/plugin/", "/lib/", "/node_modules/", "/inputmask/")):
        return "third_party"
    if "migration" in p or "migrations" in p:
        return "migration"
    if "snapshot" in p or name.endswith("snapshot.cs"):
        return "snapshot"
    if "designer" in p or name.endswith(".designer.cs"):
        return "designer"
    if any(token in p for token in ("/generated/", "/codegen/", "/gen/")) or "autogenerated" in name or name.endswith(".g.cs"):
        return "generated"
    return "source"


def iter_source_files(root: Path, exts: set[str], excluded_dirs: set[str], max_size_kb: int) -> Iterable[Path]:
    max_size = max_size_kb * 1024
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix.lower() not in exts:
            continue
        if any(part.lower() in excluded_dirs for part in path.parts):
            continue
        if SKIP_FILENAME_RE.search(path.name) or path.name.lower() in SKIP_FILENAMES:
            continue
        try:
            if path.stat().st_size > max_size:
                continue
        except OSError:
            continue
        yield path


def safe_read_lines(path: Path, enc: str) -> Sequence[str]:
    for e in (enc, "utf-8", "latin-1"):
        try:
            return path.read_text(encoding=e).splitlines()
        except Exception:
            pass
    return []


def active_patterns(mode: str) -> tuple[PatternDef, ...]:
    if mode == "exploratorio":
        return PATTERNS
    return tuple(p for p in PATTERNS if p.mode == "executivo")


def has_anchor(context: str) -> bool:
    return bool(CNPJ_ANCHOR_RE.search(context) or MASK_CLASSIC_RE.search(context))


def should_drop_generic_mask(line: str) -> bool:
    return bool(re.search(r"(?i)\$\.fn\.inputmask|data-inputmask|\bmaskset\b|\balias(es)?\b|\binputmask\(fn\)", line))


def extract_semantic_targets(text: str) -> str:
    patterns = [
        r'(?i)\b(id|name|for|placeholder|ng-model|formControlName)\s*=\s*["\']([^"\']+)["\']',
        r'(?i)\b(const|let|var|public static|private static)\s+([A-Za-z_][\w$]*)',
        r'(?i)\b([A-Za-z_][\w$]*)\s*:\s*\{',
        r'(?i)\b([A-Za-z_][\w$]*)\s*=',
    ]
    values: list[str] = []
    for p in patterns:
        for m in re.finditer(p, text):
            if m.lastindex and m.lastindex >= 2:
                values.append((m.group(2) or "").strip())
            elif m.lastindex and m.lastindex >= 1:
                values.append((m.group(1) or "").strip())
    return " ".join(values).lower()


def semantic_target_ok(context: str, line: str) -> bool:
    targets = extract_semantic_targets(context + "\n" + line)
    if targets and NON_CNPJ_TARGET_RE.search(targets) and not POSITIVE_CNPJ_TARGET_RE.search(targets):
        return False
    if NON_CNPJ_TARGET_RE.search(line) and not POSITIVE_CNPJ_TARGET_RE.search(line):
        return False
    return True


def contextual_ok(pattern: PatternDef, lines: Sequence[str], idx: int, window: int) -> bool:
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)
    ctx = "\n".join(lines[start:end])
    line = lines[idx]
    if pattern.nome == "Mask/Inputmask contextual":
        if should_drop_generic_mask(line) and not has_anchor(ctx):
            return False
        if not has_anchor(ctx):
            return False
        return semantic_target_ok(ctx, line)
    if pattern.nome == "Dígito verificador contextual":
        if not has_anchor(ctx):
            return False
        return bool(re.search(r"(?i)pesos|\b14\b|valida", ctx) or re.search(r"5\s*,\s*4\s*,\s*3\s*,\s*2", ctx))
    if pattern.nome in {"Regex 14 dígitos", "Regex CNPJ formatado", "Len 14 contextual", "IsNumeric contextual"}:
        if not has_anchor(ctx):
            return False
        return semantic_target_ok(ctx, line)
    return True


def dedup_id_for(path: str, region: int, category: str) -> str:
    raw = f"{path}|{region}|{category}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def scan_file(path: Path, root: Path, args: argparse.Namespace, patterns: Sequence[PatternDef]) -> tuple[list[Finding], list[Finding]]:
    lines = safe_read_lines(path, args.encoding)
    if not lines:
        return [], []
    rel = path.relative_to(root).as_posix()
    src_kind = classify_source_kind(path)
    projeto = detect_project(path, root, args.project_group_mode)
    camada = infer_layer(path)

    kept: list[Finding] = []
    discarded: list[Finding] = []
    seen_region: set[tuple[int, str]] = set()

    for i, line in enumerate(lines):
        for p in patterns:
            if not p.regex.search(line):
                continue
            ok_context = contextual_ok(p, lines, i, args.context_window) if p.requires_context else True
            region = i // max(args.context_window, 1)
            if (region, p.categoria) in seen_region:
                continue
            finding = Finding(
                projeto=projeto,
                arquivo=rel,
                arquivo_absoluto=str(path.resolve()),
                extensao=path.suffix.lower(),
                camada=camada,
                linha=i + 1,
                nome_padrao=("Validação legada de CNPJ numérico" if p.categoria == "Validacao" and region in [r for r, c in seen_region if c == "Validacao"] else p.nome),
                categoria=p.categoria,
                criticidade=p.criticidade,
                trecho=line.strip()[:220],
                contexto=" | ".join(lines[max(0, i-1): min(len(lines), i+2)])[:500],
                score=p.score,
                source_kind=src_kind,
                is_generated="sim" if src_kind in {"generated", "snapshot", "designer"} else "nao",
                is_third_party="sim" if src_kind == "third_party" else "nao",
                contextual_match="sim" if ok_context else "nao",
                prioridade_backlog=p.prioridade_backlog,
                dedup_id=dedup_id_for(rel, region, p.categoria),
            )
            if not ok_context:
                discarded.append(finding)
                continue
            if args.modo_relatorio == "executivo" and src_kind in {"third_party", "generated", "snapshot", "designer"}:
                discarded.append(finding)
                continue
            seen_region.add((region, p.categoria))
            kept.append(finding)
    return kept, discarded


def write_csv(path: Path, rows: list[Finding]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "projeto", "arquivo", "arquivo_absoluto", "extensao", "camada", "linha", "nome_padrao", "categoria", "criticidade",
            "trecho", "contexto", "score", "source_kind", "is_generated", "is_third_party", "contextual_match", "prioridade_backlog", "dedup_id",
        ])
        for r in rows:
            w.writerow([
                r.projeto, r.arquivo, r.arquivo_absoluto, r.extensao, r.camada, r.linha, r.nome_padrao, r.categoria, r.criticidade,
                r.trecho, r.contexto, r.score, r.source_kind, r.is_generated, r.is_third_party, r.contextual_match, r.prioridade_backlog, r.dedup_id,
            ])


def write_html(path: Path, rows: list[Finding], title: str) -> None:
    trs = "".join(
        f"<tr><td>{html.escape(r.projeto)}</td><td>{html.escape(r.arquivo)}</td><td>{r.linha}</td><td>{html.escape(r.nome_padrao)}</td><td>{r.score}</td><td>{html.escape(r.source_kind)}</td><td>{html.escape(r.prioridade_backlog)}</td><td>{html.escape(r.trecho)}</td></tr>"
        for r in rows
    )
    path.write_text(
        f"""<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{font-family:Arial;margin:20px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:6px;font-size:12px}}</style>
<h1>{html.escape(title)}</h1><p>Total: {len(rows)}</p>
<table><thead><tr><th>Projeto</th><th>Arquivo</th><th>Linha</th><th>Padrão</th><th>Score</th><th>source_kind</th><th>Prioridade</th><th>Trecho</th></tr></thead><tbody>{trs}</tbody></table></html>""",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve()

    exts = set(SUPPORTED_EXTENSIONS)
    if args.include_ext:
        exts.update(e if e.startswith(".") else f".{e}" for e in args.include_ext)
    excluded = set(DEFAULT_EXCLUDED_DIRS)
    if args.exclude_dir:
        excluded.update(x.lower() for x in args.exclude_dir)
    patterns = active_patterns(args.modo_relatorio)

    print(f"Iniciando varredura em: {root}", flush=True)
    print(f"Modo: {args.modo_relatorio} | Janela contexto: ±{args.context_window}", flush=True)
    print("Coletando arquivos elegíveis...", flush=True)
    files = list(iter_source_files(root, exts, excluded, args.max_file_size_kb))
    print(f"Arquivos elegíveis: {len(files)}", flush=True)

    findings: list[Finding] = []
    noises: list[Finding] = []
    total = len(files)
    for i, fp in enumerate(files, start=1):
        k, d = scan_file(fp, root, args, patterns)
        findings.extend(k)
        noises.extend(d)
        if i % 200 == 0 or i == total:
            print(f"Processados {i}/{total} arquivos...", flush=True)

    findings.sort(key=lambda r: (r.prioridade_backlog, -r.score, r.projeto, r.arquivo, r.linha))
    noises.sort(key=lambda r: (r.arquivo, r.linha))

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "relatorio_cnpj.csv", findings)
    write_csv(out_dir / "impactos_priorizados.csv", findings)
    write_csv(out_dir / "ruidos_descartados.csv", noises)

    sem_txt = args.sem_txt or args.somente_csv_html
    if not sem_txt:
        (out_dir / "relatorio_cnpj.txt").write_text(
            f"Arquivos varridos: {len(files)}\nOcorrencias executivas: {len(findings)}\nRuido descartado: {len(noises)}\n",
            encoding="utf-8",
        )
    if not args.sem_html:
        write_html(out_dir / "relatorio_executivo.html", findings, "Relatório Executivo CNPJ")
        write_html(out_dir / "relatorio_cnpj.html", findings, "Relatório CNPJ")

    print(f"Ocorrências encontradas: {len(findings)}")
    print(f"Ruídos descartados: {len(noises)}")
    print(f"Relatórios gerados em: {out_dir}")


if __name__ == "__main__":
    main()
