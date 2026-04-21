# Levantamento de Impacto — Adequação ao CNPJ Alfanumérico

Ferramenta para análise técnica de impacto da migração do CNPJ numérico para o padrão alfanumérico.

## Diretrizes atendidas

- Terminologia interna e externa em português técnico.
- Lista única consolidada de ocorrências (sem segmentação por múltiplos arquivos auxiliares).
- Artefato principal único:
  - `levantamento_impacto_cnpj.xlsx`
- Artefato opcional:
  - `levantamento_impacto_cnpj.html`
- Nenhuma geração de TXT.
- Exclusão automática do diretório de saída da varredura.
- Filtro de pipeline/infra e descarte de metadados operacionais de CI/CD sem evidência funcional forte de CNPJ.
- XLSX pronto para análise com cabeçalho congelado, autofiltro, ajuste de largura, quebra de linha em colunas textuais e destaque visual por `classificacao_resultado`.
- Priorização legível em `prioridade_tratamento`: `critica`, `alta`, `media`, `baixa` e `descartada` (para ocorrências descartadas).

## Parâmetros

- `raiz` (posicional): diretório raiz de análise.
- `--diretorio-saida`: diretório de saída.
- `--encoding`: encoding preferencial.
- `--tamanho-maximo-kb`: tamanho máximo de arquivo.
- `--extensoes-adicionais`: extensões extras.
- `--diretorios-excluidos`: nomes de diretórios excluídos.
- `--modo-agrupamento-projeto`: `auto`, `topdir`, `none`.
- `--janela-contexto`: janela contextual (±N linhas).
- `--desabilitar-html`: desabilita geração do HTML.

## Colunas da saída (XLSX e HTML)

- `projeto`
- `arquivo`
- `arquivo_absoluto`
- `extensao`
- `camada`
- `linha_inicial`
- `padrao_identificado`
- `categoria_tecnica`
- `trecho`
- `contexto`
- `pontuacao`
- `origem_artefato`
- `artefato_gerado`
- `artefato_terceiro`
- `evidencia_contextual`
- `prioridade_tratamento`
- `identificador_consolidacao`
- `natureza_intervencao`
- `classificacao_resultado`

## Como interpretar o resultado

As colunas abaixo devem ser utilizadas como eixo principal de interpretação:

- `classificacao_resultado`
- `natureza_intervencao`
- `prioridade_tratamento`

### classificacao_resultado

- `adequacao_obrigatoria`: ocorrência com evidência de regra legada que tende a exigir intervenção.
- `adequacao_potencial`: ocorrência que demanda análise técnica para confirmar necessidade de ajuste.
- `evidencia_contextual`: referência de contexto, sem indicação direta de quebra funcional.
- `ocorrencia_descartada`: ocorrência sem relevância técnica para adequação, passível de desconsideração.

### natureza_intervencao

Principais categorias de impacto técnico:

- `validacao_numerica_restritiva`: validações que presumem conteúdo estritamente numérico.
- `comprimento_fixo_legado`: uso de tamanho fixo associado ao padrão anterior.
- `mascara_legada`: máscara de entrada/saída aderente ao formato antigo.
- `validacao_estrutural_legada`: algoritmo/estrutura de validação vinculada ao modelo numérico legado.
- `restricao_persistencia`: restrição de banco/campo com potencial incompatibilidade.
- `contrato_integracao`: contrato de integração que pode depender do formato antigo.

### prioridade_tratamento

- `critica`: intervenção urgente.
- `alta`: intervenção relevante.
- `media`: revisão recomendada.
- `baixa`: impacto baixo.
- `descartada`: ocorrência a ignorar no ciclo inicial.

## Como utilizar o arquivo XLSX

No Excel, recomenda-se aplicar filtros inicialmente nas colunas:

- `classificacao_resultado`
- `prioridade_tratamento`
- `natureza_intervencao`
- `origem_artefato`

Fluxo inicial sugerido de exploração:

1. filtrar `prioridade_tratamento = critica`;
2. em seguida, filtrar `classificacao_resultado = adequacao_obrigatoria`.

Observações operacionais:

- o arquivo já é gerado com ordenação por prioridade;
- o cabeçalho já possui autofiltro;
- os dados podem ser refinados progressivamente por filtros adicionais no Excel.

## Como priorizar a correção

Fluxo recomendado de priorização técnica:

1. tratar registros com `prioridade_tratamento = critica`;
2. na sequência, focar em `classificacao_resultado = adequacao_obrigatoria`;
3. posteriormente, analisar `adequacao_potencial`;
4. manter `ocorrencia_descartada` fora da frente inicial de tratamento.

## Limitações da análise

- A ferramenta executa análise estática de código/artefatos.
- O resultado não substitui avaliação técnica do time responsável.
- Nem toda ocorrência implica mudança obrigatória.
- Proximidade textual com `cnpj` pode produzir falsos positivos residuais.
- Recomenda-se validação manual antes da formalização de backlog.

## Uso recomendado

Uso indicado para:

- levantamento inicial de impacto;
- apoio à identificação de pontos críticos;
- priorização de análise técnica.

Uso não recomendado para:

- tomada automática de decisão sem revisão humana;
- geração direta de backlog sem validação técnica.
