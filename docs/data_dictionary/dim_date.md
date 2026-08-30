# Data dictionary — dim_date

**Grain:** uma linha por data de referência evidenciada pelos datasets processados.

| Coluna | Tipo | Descrição | Nullable |
|---|---|---|---|
| date_key | integer | Data em `YYYYMMDD` | Não |
| date | date | Data calendário | Não |
| year | integer | Ano | Não |
| quarter | integer | Trimestre de 1 a 4 | Não |
| month | integer | Mês de 1 a 12 | Não |
| month_name | text | Nome do mês em português | Não |
| year_month | text | Competência `YYYY-MM` | Não |

