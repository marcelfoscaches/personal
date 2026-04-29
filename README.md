# Scanner CNPJ Alfanumérico

Ferramenta CLI **multiplataforma (Windows/Linux)** em Python para varredura estática e mapeamento de impactos da transição de CNPJ numérico para alfanumérico.

## Justificativa da tecnologia
Python foi escolhido por ser multiplataforma, ter ótima portabilidade para scripts CLI, facilitar regex/análise textual e permitir empacotamento para executável único (PyInstaller).

## Arquivo principal
- `scanner_cnpj_alfanumerico.py` (arquivo único com scanner, regras, classificação e relatórios).

## Uso
> Restrição: **apenas um parâmetro**.

```bash
python scanner_cnpj_alfanumerico.py /caminho/raiz
```

Para múltiplas raízes, ainda com 1 parâmetro:
```bash
python scanner_cnpj_alfanumerico.py "/repo1;/repo2"
# ou
python scanner_cnpj_alfanumerico.py "/repo1,/repo2"
```

## Exemplos por shell
### Linux Bash
```bash
python3 scanner_cnpj_alfanumerico.py "/home/user/sistema"
```

### Windows PowerShell
```powershell
python .\scanner_cnpj_alfanumerico.py "C:\Projetos\ERP;C:\Projetos\Portal"
```

### Windows CMD
```cmd
python scanner_cnpj_alfanumerico.py "C:\Projetos\ERP"
```

## Configuração externa
Arquivo opcional `scanner-config.json` ou `scanner-config.yml` no diretório atual ou raiz analisada.
Veja `scanner-config.json` deste repositório.

## Saídas geradas
No diretório `scanner_output/`:
- `relatorio_cnpj.csv`
- `relatorio_cnpj.json`
- `relatorio_cnpj.html`
- `relatorio_cnpj.md`
- `resumo_executivo.txt`

## Build/publicação
### Execução direta
```bash
python scanner_cnpj_alfanumerico.py ./examples/sample_project
```

### Empacotar executável
```bash
pip install pyinstaller
pyinstaller --onefile scanner_cnpj_alfanumerico.py
```
Executável gerado em `dist/`.

## Testes básicos
```bash
python -m unittest -v test_scanner_cnpj_alfanumerico.py
```
