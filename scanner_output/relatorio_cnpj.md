# Relatório de Impacto - CNPJ Alfanumérico

## Resumo Executivo
```
Resumo Executivo - Scanner CNPJ Alfanumérico
Data: 2026-04-29T17:58:01.018290Z
Arquivos varridos: 2
Total de ocorrências: 10
Ocorrências ALTA: 3
Projetos mais impactados: sample_project(10)
Principais riscos: Campos/tipos numéricos para CNPJ, Regex/máscaras apenas numéricas, Sanitização que remove letras
Recomendações gerais: tratar CNPJ como texto, revisar regex/máscaras/validações, alinhar contratos de integração e testes.
Próximos passos: priorizar ALTA, abrir backlog técnico, executar testes de regressão com massa alfanumérica.
```

## Ocorrências

|Projeto|Arquivo|Linha|Regra|Categoria|Severidade|Trecho|
|---|---|---:|---|---|---|---|
|sample_project|src/cliente.cs|2|TIPO_NUMERICO_CNPJ|BACKEND|ALTA|public long Cnpj { get; set; }|
|sample_project|src/cliente.cs|2|IDENTIFICADOR_CNPJ|POSSIVEL_FALSO_POSITIVO|BAIXA|public long Cnpj { get; set; }|
|sample_project|src/cliente.cs|3|IDENTIFICADOR_CNPJ|POSSIVEL_FALSO_POSITIVO|BAIXA|public string Validar(string cnpj){|
|sample_project|src/cliente.cs|4|SOMENTE_DIGITOS|VALIDACAO|ALTA|var digits = Regex.Replace(cnpj, @"\D", "");|
|sample_project|src/cliente.cs|4|IDENTIFICADOR_CNPJ|POSSIVEL_FALSO_POSITIVO|BAIXA|var digits = Regex.Replace(cnpj, @"\D", "");|
|sample_project|src/cliente.cs|6|MENSAGEM_SOMENTE_NUMEROS|FRONTEND|MEDIA|return "CNPJ aceita somente numeros";|
|sample_project|src/cliente.cs|6|IDENTIFICADOR_CNPJ|POSSIVEL_FALSO_POSITIVO|BAIXA|return "CNPJ aceita somente numeros";|
|sample_project|sql/migration.sql|2|BANCO_COLUNA_NUMERICA|BANCO_DE_DADOS|ALTA|cnpj numeric(14,0)|
|sample_project|sql/migration.sql|2|IDENTIFICADOR_CNPJ|POSSIVEL_FALSO_POSITIVO|BAIXA|cnpj numeric(14,0)|
|sample_project|sql/migration.sql|4|IDENTIFICADOR_CNPJ|POSSIVEL_FALSO_POSITIVO|BAIXA|ALTER TABLE cliente ADD CONSTRAINT ck_cnpj CHECK (length(cnpj)=14);|
