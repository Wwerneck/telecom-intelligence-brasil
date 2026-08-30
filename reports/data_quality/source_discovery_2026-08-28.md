# Relatório de descoberta de fontes — 2026-08-28

## Escopo

Validação inicial, sem transformação, dos recursos prioritários da ANATEL e do IBGE.

## IBGE — localidades municipais

- Instituição: Instituto Brasileiro de Geografia e Estatística.
- Documentação: `https://servicodados.ibge.gov.br/api/docs/localidades`.
- Recurso: `https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome`.
- Resposta observada: HTTP 200; `application/json; charset=utf-8`.
- Volume observado: 5.571 objetos; 2.470.036 bytes.
- Amostra inspecionada: código 5200050, Abadia de Goiás/GO, Centro-Oeste.
- Campos de primeiro nível: `id`, `nome`, `microrregiao`, `regiao-imediata`.
- Hierarquias presentes: UF, macrorregião, regiões imediata/intermediária e legado
  micro/mesorregional.
- Chave candidata: `id` (código IBGE municipal de 7 dígitos).
- Riscos: alteração territorial, objetos aninhados, coexistência de duas divisões regionais.
- Decisão: recurso habilitado para a futura ingestão RAW.

## ANATEL — banda larga fixa

- Catálogo confirmado no Portal Brasileiro de Dados Abertos.
- Descrição: acessos em serviço do Serviço de Comunicação Multimídia.
- Formato catalogado: ZIP; frequência mensal; licença CC BY.
- Metadados citam ano, mês de referência, empresa e tecnologia.
- Última alteração de arquivo exibida pelo catálogo consultado: 29/11/2025.
- Bloqueio: URL direta do recurso ainda não comprovada; API pública de metadados testada
  respondeu HTTP 401.
- Decisão: manter desabilitado; não usar URL inferida.

## ANATEL — estações licenciadas

- Catálogo confirmado no Portal Brasileiro de Dados Abertos.
- Formato catalogado: CSV; atualização sob demanda; licença CC BY.
- Recursos distintos incluem estações gerais, terrenas, SMP e radiodifusão.
- Risco de modelagem: “estações licenciadas” não possui um único escopo; ERBs exigem seleção
  explícita do recurso SMP e validação do grain.
- Decisão: manter desabilitado até validar o recurso SMP direto e seu schema.

## ANATEL — reclamações

- Catálogo confirmado no Portal Brasileiro de Dados Abertos.
- Formato catalogado: ZIP (CSV); licença CC BY.
- O catálogo descreve reclamações, denúncias, pedidos de informação e sugestões; portanto o
  pipeline deverá filtrar/classificar tipos antes de chamar todos os registros de reclamações.
- Última alteração de arquivo exibida pelo catálogo consultado: 13/11/2025.
- Decisão: manter desabilitado até validar download, grain e taxonomia.

## Limitações

As datas de atualização acima são as exibidas pelo catálogo no momento da pesquisa, não a
competência máxima interna dos arquivos. Nenhuma conclusão de negócio foi produzida.

