# Scanner de CNPJ em código-fonte

Script em Python para varrer diretórios no **Windows e Linux** e identificar pontos que podem precisar de ajustes para o **CNPJ alfanumérico** (novos CNPJs a partir de **julho de 2026**).

## Cobertura implementada

- Busca por padrões de:
  - **Referência Direta**
  - **Máscara**
  - **Validação**
  - **Normalização**
  - **Banco**
  - **Front-end**
  - **Integração**
  - **Mensagem**
  - **Indícios correlatos** (opcional via `--incluir-indicios`)
- Agrupamento por **projeto/produto** com `--project-group-mode` (`auto`, `topdir`, `none`).
- Exportação em **CSV**, **TXT** e **HTML** (ou sem HTML com `--sem-html`).
- Exibe caminho relativo e **arquivo absoluto** para facilitar triagem entre clones locais diferentes.

## Extensões cobertas por padrão

Inclui, entre outras: `.cs`, `.vb`, `.fs`, `.java`, `.kt`, `.scala`, `.go`, `.rs`, `.php`, `.py`, `.rb`, `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs`, `.vue`, `.svelte`, `.html`, `.cshtml`, `.razor`, `.sql`, `.ddl`, `.dml`, `.psql`, `.hql`, `.ktr`, `.kjb`, `.json`, `.xml`, `.yml`, `.yaml`, `.ini`, `.env`, `.properties`, `.csproj`, `.vbproj`, `.tf`, `.tfvars`, `.ps1`, `.sh`, `.bat`, `.cmd`, `.md`, `.txt`, `.ipynb`.

Você ainda pode adicionar extensões com `--include-ext`.

## Requisitos

- Python 3.9+

## Uso rápido

```bash
python cnpj_code_scanner.py /caminho/do/sistema --out-dir ./saida
```

Windows (PowerShell):

```powershell
python .\cnpj_code_scanner.py "E:\Workspace\TCE" --out-dir "E:\Workspace\TCE\resultado_cnpj_scan"
```

Com indícios correlatos:

```bash
python cnpj_code_scanner.py /caminho/do/sistema --out-dir ./saida --incluir-indicios
```

Sem relatório HTML:

```bash
python cnpj_code_scanner.py /caminho/do/sistema --out-dir ./saida --sem-html
```

## Saídas geradas

No diretório de saída:

- `relatorio_cnpj.csv`
- `relatorio_cnpj.txt`
- `relatorio_cnpj.html` (exceto com `--sem-html`)

Campos principais:

- `projeto`
- `arquivo` e `arquivo_absoluto`
- `extensao` e `camada`
- `nome_padrao`, `categoria`, `criticidade`
- `trecho`, `contexto`, `acao_sugerida`

## Observações

- A varredura é **heurística** (texto/regex), então pode haver falsos positivos.
- Use `--incluir-indicios` apenas quando quiser ampliar cobertura com mais ruído.

## Referência oficial

- Receita Federal: https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2024/outubro/cnpj-tera-letras-e-numeros-a-partir-de-julho-de-2026
