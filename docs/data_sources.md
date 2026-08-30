# Inventário de fontes oficiais

> Descoberta iniciada em 28/08/2026. Campos ainda não comprovados permanecem explicitamente
> como “A verificar”; uma página de catálogo não é tratada como um recurso de ingestão.

| Nome | Instituição | Descrição | Granularidade | Formato | Periodicidade | Período disponível | Chave candidata | Registros aprox. | Última atualização | Obtenção | Campos importantes | Riscos de qualidade | Licença |
|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|
| Acessos de banda larga fixa | ANATEL | Acessos em serviço das prestadoras do SCM | A verificar | ZIP | Mensal | A verificar | competência + município + prestadora + tecnologia | A verificar | arquivo catalogado em 29/11/2025 | Catálogo dados.gov.br; recurso direto pendente | ano, mês, empresa, tecnologia, acessos | schema drift, nomes e códigos | CC BY |
| Acessos móveis | ANATEL | Acessos do Serviço Móvel Pessoal | A verificar | A verificar | Mensal | A verificar | competência + geografia + prestadora + tecnologia | A verificar | A verificar | Portal/API oficial | tecnologia, prestadora, acessos | granularidade e categorias históricas | A verificar |
| Estações licenciadas | ANATEL | Estações de diversos serviços, incluindo recurso específico do SMP | A verificar | CSV | Sob demanda | A verificar | identificador oficial da estação | A verificar | recursos catalogados em novembro/2025 | Catálogo dados.gov.br; recurso direto pendente | município, coordenadas, serviço, frequência | coordenadas, duplicidades e escopo por serviço | CC BY |
| Reclamações | ANATEL | Solicitações registradas em relação às operadoras e à Agência | A verificar | ZIP (CSV) | A verificar | ao menos desde 2019, a confirmar no arquivo | competência + prestadora + assunto + geografia | A verificar | arquivo catalogado em 13/11/2025 | Catálogo dados.gov.br; recurso direto pendente | tipo, serviço, prestadora, assunto, quantidade | mudança de taxonomia e grain | CC BY |
| Índice Brasileiro de Conectividade | ANATEL | Indicadores municipais de conectividade | Município/período, a verificar | A verificar | A verificar | A verificar | código IBGE + período | A verificar | A verificar | Portal oficial | código IBGE, componentes, índice | metodologia e versões | A verificar |
| Localidades municipais | IBGE | Referência oficial de municípios, UFs e regiões | Município atual | JSON | Sem periodicidade declarada na API | Estado territorial corrente | código IBGE de 7 dígitos | 5.571 em 28/08/2026 | consultado em 28/08/2026 | API Localidades v1 | id, nome, UF, região imediata/intermediária | mudanças territoriais; API não fornece população | API pública oficial; termos a verificar |
| População municipal | IBGE | População residente estimada | Município/ano | JSON | Anual | 2025 validado; histórico a verificar | código IBGE + ano | 5.571 em 2025 | consultado em 28/08/2026 | API SIDRA, tabela 6579, variável 9324 | código, município, valor, unidade, ano | cabeçalho como primeira linha; valores especiais; revisões | API pública oficial; termos a verificar |

## Evidências e decisões da descoberta

- O endpoint `GET /api/v1/localidades/municipios?orderBy=nome` respondeu HTTP 200, JSON UTF-8,
  2.470.036 bytes e 5.571 objetos em 28/08/2026.
- O objeto municipal contém `id`, `nome`, microrregião/mesorregião, região imediata,
  região intermediária, UF e macrorregião. Não contém população.
- O catálogo ANATEL confirmou banda larga fixa mensal em ZIP, estações em CSV e reclamações
  em ZIP/CSV. O endpoint programático de metadados testado retornou HTTP 401; por isso os
  recursos continuam desativados até que URLs oficiais diretas sejam validadas.
- O ZIP oficial de banda larga fixa foi posteriormente validado com 1.029.180.610 bytes e 27
  membros. A primeira carga usará seletivamente o CSV 2026 (67.253.578 bytes comprimidos), sem
  transferir os anos históricos fora do escopo.
- O total atual de 5.571 localidades não deve ser codificado como regra fixa: alterações
  territoriais são esperadas e devem produzir relatório de mudança, não falha automática.
- A consulta SIDRA da tabela 6579, variável 9324 e período 2025 respondeu HTTP 200 com 5.571
  linhas de dados. A primeira posição do JSON é um cabeçalho descritivo e não um município.

O relatório técnico detalhado está em `reports/data_quality/source_discovery_2026-08-28.md`.
