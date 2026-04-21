# Scanner de CNPJ em código-fonte

Script em Python para varrer diretórios no **Windows e Linux** e identificar pontos de código que podem precisar de ajustes para o **CNPJ alfanumérico** (novos CNPJs a partir de **julho de 2026**).

## O que foi ampliado

Além dos padrões iniciais, o scanner agora inclui blocos por categoria:

- **Referência Direta**: CNPJ, CPF/CNPJ, nome completo da entidade.
- **Máscara**: padrões clássicos (`99.999.999/9999-99`, etc.), `mask`, `placeholder`, `format`.
- **Validação**: regex de 14 dígitos, CNPJ formatado, métodos como `validaCnpj`, dígito verificador/módulo 11 e arrays de pesos.
- **Normalização**: remoção de máscara e não numéricos (`Regex.Replace`, `/\D/g`, `re.sub`).
- **Banco**: `CHAR/VARCHAR(14|18)`, `CREATE/ALTER TABLE` com CNPJ, índices e constraints.
- **Front-end**: atributos HTML com CNPJ, `inputmask`, labels/tooltips.
- **Integração**: Receita/SPED/NF-e/Sintegra, rotas e endpoints com CNPJ.
- **Mensagem**: mensagens de erro/validação envolvendo CNPJ.
- **Indícios correlatos (opcional)**: razão social, matriz/filial, pessoa jurídica.

## Linguagens e tipos cobertos por extensão

`.NET`, `JAVA`, `PHP`, `PYTHON`, `NODEJS`, `RUBY`, `HTML`, `JAVASCRIPT`, `ANGULAR` (TS/HTML), `SQL`, `ETL/PDI` (`.ktr`, `.kjb`) e arquivos de configuração/texto comuns.

## Requisitos

- Python 3.9+

## Uso rápido

```bash
python cnpj_code_scanner.py /caminho/do/sistema --out-dir ./saida
```

No Windows (PowerShell):

```powershell
python .\cnpj_code_scanner.py C:\repos\meu-sistema --out-dir .\saida
```

Com indícios correlatos ativados:

```bash
python cnpj_code_scanner.py /caminho/do/sistema --out-dir ./saida --incluir-indicios
```

Com agrupamento por projeto/produto (detecção automática por marcador de projeto):

```bash
python cnpj_code_scanner.py /caminho/do/sistema --out-dir ./saida --project-group-mode auto
```

Modos de agrupamento:

- `auto` (padrão): detecta projeto pelo diretório mais próximo que contenha marcador como `.git`, `.sln`, `pom.xml`, `package.json`, `pyproject.toml`, etc.
- `topdir`: usa a primeira pasta abaixo da raiz informada.
- `none`: não agrupa (usa `SEM_GRUPO`).

## Saídas geradas

No diretório de saída:

- `relatorio_cnpj.csv`
- `relatorio_cnpj.txt`
- `relatorio_cnpj.html`

Campos principais do relatório:

- `projeto`
- `nome_padrao`
- `categoria`
- `criticidade` (Alta, Media, Baixa)
- `trecho`, `contexto` e `acao_sugerida`
- `arquivo_absoluto` (caminho completo do arquivo analisado)

## Observações importantes

- O scanner faz detecção por padrão textual/regex (heurística), portanto pode gerar falso positivo.
- Recomenda-se revisão manual dos pontos críticos antes de alterar produção.

## Referência oficial

- Receita Federal: https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2024/outubro/cnpj-tera-letras-e-numeros-a-partir-de-julho-de-2026
