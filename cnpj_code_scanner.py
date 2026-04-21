#!/usr/bin/env python3
"""Scanner de código-fonte para identificar impactos da migração de CNPJ alfanumérico.

Compatível com Windows e Linux.
Saídas: CSV, TXT e HTML.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SUPPORTED_EXTENSIONS = {
    ".cs", ".vb", ".java", ".php", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".rb", ".html", ".htm", ".sql", ".ktr", ".kjb", ".xml", ".json", ".yml",
    ".yaml", ".config", ".properties", ".txt", ".md",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "dist", "build", "target", "bin", "obj",
    ".idea", ".vscode", "coverage", "vendor", "__pycache__", ".venv", "venv",
}

PROJECT_MARKERS = {
    ".git", ".sln", "pom.xml", "build.gradle", "settings.gradle", "settings.gradle.kts",
    "package.json", "angular.json", "composer.json", "Gemfile", "pyproject.toml",
    "setup.py", "requirements.txt", ".project",
}


@dataclass(frozen=True)
class PatternDef:
    nome: str
    regex: re.Pattern[str]
    categoria: str
    criticidade: str
    apenas_indicios: bool = False


@dataclass
class Finding:
    projeto: str
    arquivo: str
    arquivo_absoluto: str
    linha: int
    nome_padrao: str
    categoria: str
    criticidade: str
    trecho: str
    contexto: str
    acao_sugerida: str


PATTERNS: tuple[PatternDef, ...] = (
    # REFERENCIA DIRETA
    PatternDef("CNPJ", re.compile(r"(?i)\bcnpj\b"), "Referencia Direta", "Alta"),
    PatternDef("CPF/CNPJ combinado", re.compile(r"(?i)\bcpf\s*/\s*cnpj\b|\bcpfcnpj\b|\bcnpjcpf\b"), "Referencia Direta", "Alta"),
    PatternDef("Nome completo", re.compile(r"(?i)cadastro nacional (da |de )?pessoa jur[ií]dica"), "Referencia Direta", "Alta"),

    # MASCARA
    PatternDef("Mascara 99.999.999", re.compile(r"99\.999\.999/9999-99|00\.000\.000/0000-00|##\.###\.###/####-##|__\.___.___/____-__"), "Mascara", "Alta"),
    PatternDef("Mask/placeholder CNPJ", re.compile(r"(?i)(mask|mascara|format|pattern|placeholder)[^\n]{0,60}cnpj|cnpj[^\n]{0,60}(mask|mascara|format|pattern)"), "Mascara", "Media"),

    # VALIDACAO
    PatternDef("Regex 14 dígitos", re.compile(r"\\d\{14\}|\[0-9\]\{14\}"), "Validacao", "Alta"),
    PatternDef("Regex CNPJ formatado", re.compile(r"\\d\{2\}\\\.\\d\{3\}\\\.\\d\{3\}[/\\/]\\d\{4\}-\\d\{2\}"), "Validacao", "Alta"),
    PatternDef("Metodo ValidarCnpj", re.compile(r"(?i)\bvalid\w*cnpj\b|\bcnpj\w*valid\b|\bisValidCnpj\b|\bcnpjValido\b|\bcheckCnpj\b|\bvalidaCnpj\b"), "Validacao", "Alta"),
    PatternDef("Dígito verificador", re.compile(r"(?i)d[ií]gito\s+verificador|m[oó]dulo\s*11"), "Validacao", "Alta"),
    PatternDef("Pesos CNPJ 1o dígito", re.compile(r"5\s*,\s*4\s*,\s*3\s*,\s*2\s*,\s*9\s*,\s*8\s*,\s*7\s*,\s*6\s*,\s*5\s*,\s*4\s*,\s*3\s*,\s*2"), "Validacao", "Alta"),
    PatternDef("Pesos CNPJ 2o dígito", re.compile(r"6\s*,\s*5\s*,\s*4\s*,\s*3\s*,\s*2\s*,\s*9\s*,\s*8\s*,\s*7\s*,\s*6\s*,\s*5\s*,\s*4\s*,\s*3\s*,\s*2"), "Validacao", "Alta"),

    # NORMALIZACAO
    PatternDef("Replace ponto/barra", re.compile(r"Replace\(\s*['\"][./\-]['\"]\s*,\s*['\"]['\"]\s*\)"), "Normalizacao", "Media"),
    PatternDef("Remove nao-numericos", re.compile(r"(?i)(Regex\.Replace\(.+\[\^\\d\]|\.replace\s*\(/\\D/g|re\.sub\s*\(.+\\D)"), "Normalizacao", "Media"),
    PatternDef("Funcao ApenasNumeros", re.compile(r"(?i)\b(apenasnumeros|somentenumeros|removemascara|removerformatacao|stripnonnumeric|onlynumbers)\b"), "Normalizacao", "Media"),

    # BANCO
    PatternDef("Coluna CHAR/VARCHAR(14/18)", re.compile(r"(?i)\b(n?var)?char\s*\(\s*(14|18)\s*\)"), "Banco", "Alta"),
    PatternDef("DDL CREATE/ALTER TABLE", re.compile(r"(?i)(create|alter)\s+table[^\n]{0,120}cnpj"), "Banco", "Alta"),
    PatternDef("Nomes de coluna CNPJ", re.compile(r"(?i)\b(nr_cnpj|num_cnpj|cd_cnpj|cnpj_nr|cnpj_num|ds_cnpj|tx_cnpj)\b"), "Banco", "Alta"),
    PatternDef("Index/constraint CNPJ", re.compile(r"(?i)(create\s+(unique\s+)?index|constraint)[^\n]{0,80}cnpj"), "Banco", "Alta"),

    # FRONT-END
    PatternDef("Atributo HTML com CNPJ", re.compile(r"(?i)(id|name|for|placeholder)\s*=\s*['\"][^'\"]*cnpj[^'\"]*['\"]"), "Front-end", "Media"),
    PatternDef("InputMask CNPJ", re.compile(r"(?i)\bmask\b[^\n]{0,40}cnpj|\bcnpj\b[^\n]{0,40}\bmask\b|\binputmask\b"), "Front-end", "Alta"),
    PatternDef("Label/caption CNPJ", re.compile(r"(?i)(label|caption|title|hint|tooltip|aria-label)[^\n]{0,60}cnpj"), "Front-end", "Media"),

    # INTEGRACAO
    PatternDef("Receita Federal/SPED/NF-e", re.compile(r"(?i)(receita\s*federal|sped|nfe|nota\s*fiscal|sintegra)[^\n]{0,80}cnpj|cnpj[^\n]{0,80}(receita|sped|nfe)"), "Integracao", "Alta"),
    PatternDef("Rota API com CNPJ", re.compile(r"(?i)(route|endpoint|url|uri|path)\s*[=:][^\n]{0,60}cnpj"), "Integracao", "Media"),

    # MENSAGEM
    PatternDef("Mensagem erro CNPJ", re.compile(r"(?i)(message|mensagem|erro|error|msg)[^\n]{0,60}cnpj|cnpj[^\n]{0,60}(invalido|inválido|invalid|obrigat)"), "Mensagem", "Media"),

    # INDICIOS
    PatternDef("Razão Social", re.compile(r"(?i)\b(razao\s+social|nome\s+fantasia|matriz|filial|cnpj\s+matriz)\b"), "Indicio Correlato", "Baixa", True),
    PatternDef("Documento fiscal", re.compile(r"(?i)\b(nr_?documento|num_?documento|pessoajuridica|pessoa_juridica)\b"), "Indicio Correlato", "Baixa", True),
)

SUGGESTION_BY_CATEGORY = {
    "Referencia Direta": "Mapear usos para priorizar revisão de regras de negócio e contratos.",
    "Mascara": "Atualizar máscaras/formatadores para permitir caracteres alfanuméricos nas 12 primeiras posições.",
    "Validacao": "Revisar regex e algoritmo de validação (DV/módulo 11) para CNPJ alfanumérico.",
    "Normalizacao": "Evitar sanitização que preserve apenas dígitos quando o campo for CNPJ novo.",
    "Banco": "Revisar tipo/tamanho de coluna, índices e constraints para cenário alfanumérico.",
    "Front-end": "Ajustar UX de inputs/labels e bibliotecas de máscara/validação.",
    "Integracao": "Conferir payloads, endpoints e integrações fiscais com novo padrão.",
    "Mensagem": "Atualizar mensagens de validação e documentação exibida ao usuário.",
    "Indicio Correlato": "Validar se o ponto correlato também deve entrar no backlog de migração.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scanner de referências CNPJ em bases de código.")
    parser.add_argument("root", nargs="?", default=".", help="Diretório raiz para varredura.")
    parser.add_argument("--out-dir", default="./resultado_cnpj_scan", help="Diretório de saída dos relatórios.")
    parser.add_argument("--encoding", default="utf-8", help="Encoding primário para leitura de arquivos.")
    parser.add_argument("--max-file-size-kb", type=int, default=1024, help="Ignora arquivos maiores que este limite.")
    parser.add_argument("--include-ext", nargs="*", help="Extensões adicionais (ex.: .scala .go).")
    parser.add_argument("--exclude-dir", nargs="*", help="Diretórios adicionais para exclusão.")
    parser.add_argument("--incluir-indicios", action="store_true", help="Inclui padrões de indícios correlatos (criticidade baixa).")
    parser.add_argument(
        "--project-group-mode",
        choices=("auto", "topdir", "none"),
        default="auto",
        help="Modo de agrupamento por projeto: auto (marcadores), topdir (1o nível), none (sem agrupamento).",
    )
    return parser.parse_args()


def iter_source_files(root: Path, extensions: set[str], excluded_dirs: set[str], max_size_kb: int) -> Iterable[Path]:
    max_size_bytes = max_size_kb * 1024
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in excluded_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue
        try:
            if path.stat().st_size > max_size_bytes:
                continue
        except OSError:
            continue
        yield path


def safe_read_lines(path: Path, encoding: str) -> Sequence[str]:
    for enc in (encoding, "utf-8", "latin-1"):
        try:
            with path.open("r", encoding=enc, errors="strict") as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
        except OSError:
            return []
    return []


def active_patterns(include_indicios: bool) -> tuple[PatternDef, ...]:
    if include_indicios:
        return PATTERNS
    return tuple(p for p in PATTERNS if not p.apenas_indicios)


def detect_project(path: Path, root: Path, mode: str) -> str:
    rel = path.relative_to(root)

    if mode == "none":
        return "SEM_GRUPO"

    if mode == "topdir":
        return rel.parts[0] if len(rel.parts) > 1 else "RAIZ"

    # auto: procura marcador de projeto subindo diretórios até a raiz informada.
    current = path.parent
    while True:
        for marker in PROJECT_MARKERS:
            if (current / marker).exists():
                if current == root:
                    return "RAIZ"
                return current.name
        if current == root:
            break
        current = current.parent

    return rel.parts[0] if len(rel.parts) > 1 else "RAIZ"


def scan_file(path: Path, root: Path, encoding: str, patterns: Sequence[PatternDef], project_group_mode: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = safe_read_lines(path, encoding)
    rel = path.relative_to(root).as_posix()
    projeto = detect_project(path, root, project_group_mode)
    absoluto = str(path.resolve())

    for idx, line in enumerate(lines, start=1):
        line_clean = line.rstrip("\n")
        for pattern in patterns:
            if not pattern.regex.search(line_clean):
                continue

            context = ""
            if idx > 1:
                context += lines[idx - 2].strip() + " | "
            context += line_clean.strip()
            if idx < len(lines):
                context += " | " + lines[idx].strip()

            suggestion = SUGGESTION_BY_CATEGORY.get(pattern.categoria, "Revisar ponto identificado.")
            findings.append(
                Finding(
                    projeto=projeto,
                    arquivo=rel,
                    arquivo_absoluto=absoluto,
                    linha=idx,
                    nome_padrao=pattern.nome,
                    categoria=pattern.categoria,
                    criticidade=pattern.criticidade,
                    trecho=line_clean.strip()[:220],
                    contexto=context[:500],
                    acao_sugerida=suggestion,
                )
            )
    return findings


def write_csv(findings: list[Finding], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["projeto", "arquivo", "arquivo_absoluto", "linha", "nome_padrao", "categoria", "criticidade", "trecho", "contexto", "acao_sugerida"])
        for item in findings:
            writer.writerow([
                item.projeto,
                item.arquivo,
                item.arquivo_absoluto,
                item.linha,
                item.nome_padrao,
                item.categoria,
                item.criticidade,
                item.trecho,
                item.contexto,
                item.acao_sugerida,
            ])


def write_txt(findings: list[Finding], output: Path) -> None:
    grouped: dict[str, list[Finding]] = {}
    for item in findings:
        grouped.setdefault(item.projeto, []).append(item)

    with output.open("w", encoding="utf-8") as f:
        f.write("Relatório de varredura CNPJ\n")
        f.write("=" * 100 + "\n")
        f.write(f"Total de ocorrências: {len(findings)}\n\n")
        for projeto in sorted(grouped):
            f.write(f"Projeto: {projeto} | Ocorrências: {len(grouped[projeto])}\n")
            f.write("-" * 100 + "\n")
            for item in grouped[projeto]:
                f.write(f"Arquivo: {item.arquivo}\n")
                f.write(f"Arquivo absoluto: {item.arquivo_absoluto}\n")
                f.write(f"Linha: {item.linha}\n")
                f.write(f"Padrão: {item.nome_padrao}\n")
                f.write(f"Categoria: {item.categoria}\n")
                f.write(f"Criticidade: {item.criticidade}\n")
                f.write(f"Trecho: {item.trecho}\n")
                f.write(f"Ação: {item.acao_sugerida}\n")
                f.write("-" * 100 + "\n")


def write_html(findings: list[Finding], output: Path) -> None:
    rows = []
    for item in findings:
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.projeto)}</td>"
            f"<td>{html.escape(item.arquivo)}</td>"
            f"<td>{html.escape(item.arquivo_absoluto)}</td>"
            f"<td>{item.linha}</td>"
            f"<td>{html.escape(item.nome_padrao)}</td>"
            f"<td>{html.escape(item.categoria)}</td>"
            f"<td>{html.escape(item.criticidade)}</td>"
            f"<td>{html.escape(item.trecho)}</td>"
            f"<td>{html.escape(item.acao_sugerida)}</td>"
            "</tr>"
        )

    html_doc = f"""<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Relatório CNPJ</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f2f2f2; }}
    tr:nth-child(even) {{ background: #fbfbfb; }}
    .Alta {{ background: #ffe9e9; }}
    .Media {{ background: #fff7df; }}
    .Baixa {{ background: #eaf7ea; }}
  </style>
</head>
<body>
  <h1>Relatório de varredura CNPJ</h1>
  <p>Total de ocorrências: <strong>{len(findings)}</strong></p>
  <table>
    <thead>
      <tr>
        <th>Projeto</th><th>Arquivo</th><th>Arquivo absoluto</th><th>Linha</th><th>Padrão</th><th>Categoria</th><th>Criticidade</th><th>Trecho</th><th>Ação sugerida</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    output.write_text(html_doc, encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve()

    extensions = set(SUPPORTED_EXTENSIONS)
    if args.include_ext:
        extensions.update(ext if ext.startswith(".") else f".{ext}" for ext in args.include_ext)

    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    if args.exclude_dir:
        excluded_dirs.update(args.exclude_dir)

    patterns = active_patterns(args.incluir_indicios)
    files = list(iter_source_files(root, extensions, excluded_dirs, args.max_file_size_kb))

    findings: list[Finding] = []
    for file_path in files:
        findings.extend(scan_file(file_path, root, args.encoding, patterns, args.project_group_mode))
    findings.sort(key=lambda i: (i.projeto, i.arquivo, i.linha, i.nome_padrao))

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(findings, out_dir / "relatorio_cnpj.csv")
    write_txt(findings, out_dir / "relatorio_cnpj.txt")
    write_html(findings, out_dir / "relatorio_cnpj.html")

    print(f"Arquivos analisados: {len(files)}")
    print(f"Padrões ativos: {len(patterns)}")
    print(f"Ocorrências encontradas: {len(findings)}")
    print(f"Relatórios gerados em: {out_dir}")


if __name__ == "__main__":
    main()
