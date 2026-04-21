# Scanner de impacto de CNPJ alfanumérico (modo defensável)

Scanner Python para mapear impacto real da migração de CNPJ com foco em **defensabilidade técnica** (menos ruído, mais evidência contextual).

## Principais mudanças

- **Modo executivo (padrão)**: só promove achado com âncora semântica de CNPJ e validação contextual.
- **Modo exploratório**: amplia cobertura e aceita sinais mais fracos.
- Exclusão estrutural no executivo para `third_party`, `generated`, `snapshot`, `designer`.
- Janela de contexto configurável (`--context-window`, padrão `4` => ±4 linhas).
- Deduplicação por bloco/categoria (`dedup_id`).

## Requisitos

- Python 3.9+

## Uso

```bash
python cnpj_code_scanner.py /caminho/do/codigo --out-dir ./saida
```

Windows (PowerShell):

```powershell
python .\cnpj_code_scanner.py "E:\Workspace\TCE" --out-dir "E:\Workspace\TCE\resultado_cnpj_scan"
```

Modo exploratório:

```bash
python cnpj_code_scanner.py /caminho --out-dir ./saida --modo-relatorio exploratorio
```

Somente CSV + HTML:

```bash
python cnpj_code_scanner.py /caminho --out-dir ./saida --somente-csv-html
```

## Saídas

- `relatorio_cnpj.csv` (compatível com fluxo principal)
- `impactos_priorizados.csv`
- `ruidos_descartados.csv`
- `relatorio_cnpj.txt` (exceto com `--sem-txt` / `--somente-csv-html`)
- `relatorio_executivo.html` e `relatorio_cnpj.html` (exceto com `--sem-html`)

## Colunas adicionais

- `score`
- `source_kind`
- `is_generated`
- `is_third_party`
- `contextual_match`
- `prioridade_backlog`
- `dedup_id`
