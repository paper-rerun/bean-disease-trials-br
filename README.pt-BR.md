# Ensaios de manejo de doenças do feijão-comum no Brasil

English version: [README.md](README.md)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23641861.svg)](https://doi.org/10.5281/zenodo.23641861)

1.562 resultados de ensaios sobre o manejo das principais doenças do feijão-comum (*Phaseolus vulgaris*) no Brasil, tirados das tabelas de 20 publicações de acesso aberto da Embrapa: antracnose, mancha-angular, mofo-branco, ferrugem, mela e mosaico-dourado. Cada linha é um número exatamente como foi impresso, com a página e a tabela de onde saiu, e aponta para o ensaio a que pertence (local, safra, cultivar, inoculação, momento de aplicação, delineamento).

O feijão-comum é alimento básico das famílias de baixa renda no Brasil, e boa parte dos dados sobre como protegê-lo está em boletins técnicos e comunicados curtos em português. Este dataset torna 20 deles pesquisáveis e comparáveis.

Faz parte do [Paper Rerun](https://paper-rerun.github.io), na linha Open Tables. O trabalho foi feito por agentes de IA num computador doméstico e revisado por uma pessoa antes da publicação.

## O que tem

| | |
|---|---|
| Publicações | 20 (Alice e Infoteca-e, os repositórios abertos da Embrapa), de 1992 até a década de 2020; a maioria são ensaios de fungicidas da Embrapa Arroz e Feijão, além de controle biológico (Bacillus, Trichoderma), linhagens resistentes e multilinhas, manejo cultural (palhada de braquiária) e sanidade de sementes |
| Ensaios | 52 (41 de campo, 6 em casa de vegetação, 3 em laboratório, 2 em câmara de crescimento) |
| Registros | 1.562 |

Arquivos:
- `data/bean_disease_trials.csv`: o dataset, um registro por valor impresso, com `doc_id` e `trial_id`. As colunas estão descritas em `method/schema.json`.
- `data/bean_disease_trials_context.csv`: uma linha por ensaio. Junte os dois arquivos por `doc_id` + `trial_id`; um campo de contexto vazio num registro significa que vale o valor do ensaio.
- `data/sources.csv`: as 20 publicações, com autores, link do registro e aviso de licença.
- `qa/decisions.csv`: cada divergência entre as duas transcrições independentes e como ela foi resolvida conferindo o PDF (2.166 decisões, com a página).
- `method/`: o schema, o script de comparação e o script de junção.

`source_inconsistency` marca 433 registros em que a publicação se contradiz (por exemplo, uma nota de rodapé e uma tabela que discordam sobre uma dose ou uma data).

### Principais colunas

O arquivo está em UTF-8, com vírgula separando as colunas. Local, safra, cultivar, inoculação e delineamento de cada ensaio estão em `data/bean_disease_trials_context.csv`.

- `doc_id`: identificador da publicação de origem. Liga o registro a `data/sources.csv` e é também o nome do PDF, sem a extensão.
- `trial_id`: o ensaio a que o valor pertence, dentro da publicação. Com `doc_id`, liga o registro à sua linha no arquivo de contexto.
- `page`: página do PDF contada a partir de 1 (a primeira página do arquivo é 1), e não o número impresso na página. O rótulo da tabela está em `table_or_figure`, como impresso ("Tabela 3", "Quadro 1"), ou `text` quando o número está no corpo do texto.
- `treatment`: rótulo da linha ou da coluna exatamente como impresso (código, produto, cultivar, isolado, planta de cobertura, época de semeadura, "Testemunha", "Média"). Numa célula de fatorial, os níveis vêm unidos por " x ", na ordem da tabela.
- `disease`: a doença ou o vetor a que a variável se refere: `anthracnose` (antracnose), `angular_leaf_spot` (mancha-angular), `white_mold` (mofo-branco), `rust` (ferrugem), `web_blight` (mela), `golden_mosaic` (mosaico-dourado), `whitefly` (mosca-branca), `seed_fungi` (fungos em sementes), `root_rot` (podridão radicular) ou `multiple`. É `none` quando a variável não mede doença (produtividade, estande, massa de 100 grãos, palhada, custos), mesmo num ensaio sobre doença.
- `variable`: variável medida, exatamente como no cabeçalho ou na legenda, com o momento quando ele faz parte do cabeçalho ("Severidade (%)", "Nota 87 DAE", "AACPD", "M100 (g)").
- `variable_standardized`: a mesma variável numa lista fechada. Alguns exemplos: `yield_kg_ha` (produtividade de grãos em kg/ha), `severity_score` (severidade em escala de notas), `severity_pct` (severidade em % do tecido), `incidence_pct` (% de plantas, folhas ou vagens com sintoma), `control_efficacy_pct` (% de controle impresso pelos autores), `audpc` (AACPD) e `in_vitro_growth` (crescimento de colônia em cultura). A lista completa está em `method/schema.json`.
- `value_as_printed`: a célula exatamente como impressa, sem a letra de significância ("2.151", "56,25"). Nas classes de reação vem a própria classe ("MR"); nesse caso `value_kind` é `class` e `value` fica vazio.
- `value`: o mesmo número pronto para cálculo, com ponto decimal e sem separador de milhar ("2.151" vira 2151, "56,25" vira 56.25). Nada foi calculado, convertido ou arredondado.
- `unit`: unidade como impressa ou informada na legenda ("%", "kg/ha", "kg ha-1", "g/parcela", "cm"). Vazia quando não há unidade impressa, como em notas e na AACPD.
- `statistic`: o que o número é: `mean` (média do tratamento ou entre ambientes), `relative_to_check` (percentual ou razão calculada pelos autores em relação à testemunha, como eficiência de controle, produtividade relativa ou redução), `total`, `median`, `single_value` (uma parcela ou uma observação), `percentage_of_total` ou `other`.
- `significance_letter`: letra(s) do teste de médias exatamente como impressas ("a", "AB", "a A", "bc"). Vazia quando não há.

## Como foi feito

1. **Coleta.** Um agente buscou nos repositórios abertos da Embrapa publicações com tabelas de ensaios quantitativos sobre o tema, baixou 20 e registrou outras 108 candidatas que não entraram, com o motivo.
2. **Duas transcrições independentes.** Dois agentes por publicação transcreveram o contexto dos ensaios e cada célula de tabela sobre o tema num schema fixo, sem ver o trabalho um do outro, copiando os números exatamente como impressos e prestando contas de cada célula de dados de cada tabela.
3. **Comparação e arbitragem.** Um script pareou as duas transcrições, ensaio por ensaio e registro por registro, e listou cada divergência e cada valor presente em só uma delas. Cada caso foi resolvido conferindo o PDF, com a página como evidência.

## Qual a precisão

- **Números:** as duas transcrições concordaram em todos os 1.500 valores e letras de significância que ambas leram.
- **Contexto e classificação:** o contexto agora é escrito uma vez por ensaio, e não em cada linha, o que reduziu os erros de contexto de 4.813 campos na nossa rodada anterior para 14. Os rótulos de cada registro (por exemplo, se o documento diz qual estatística é o número, ou o tipo de tratamento) ainda saem errados em tabelas inteiras quando há uma transcrição só: sozinha, uma estava totalmente correta em 66% dos registros, e a outra em 79%. Cada divergência foi resolvida conferindo o PDF, então o dataset não depende de nenhuma das duas sozinha.
- **Limites conhecidos:** o trabalho recente sobre doenças do feijão nesses repositórios é, na maior parte, lançamento de cultivares, então poucos documentos são posteriores a 2013. Valores mostrados só em gráficos, sem número impresso, não foram lidos. Uma página de registro no repositório não lista autores; os autores do capítulo aparecem como impressos no PDF.

## Licença e citação

- O dataset (os arquivos CSV, o schema e os scripts) é publicado sob a licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Por favor, cite as publicações originais listadas em `data/sources.csv` e também este dataset.
- As publicações não são redistribuídas. Os repositórios da Embrapa exibem um aviso CC BY-NC-ND 4.0; os artigos de periódico mantêm as licenças das revistas, e alguns PDFs trazem "todos os direitos reservados". Aqui são usados só os números, que são fatos, e citações curtas.

Erros ou ensaios que faltam: por favor, [abra uma issue](https://github.com/paper-rerun/bean-disease-trials-br/issues).

## Como este dataset foi feito

Este dataset foi montado por agentes de IA (Claude, da Anthropic) num computador doméstico e revisado por uma pessoa antes da publicação. Nenhum valor foi estimado ou digitado à mão: cada um foi transcrito do PDF original duas vezes, de forma independente, e cada divergência foi conferida na página. O método e os scripts estão em `method/`. Como funciona o projeto como um todo (em inglês): https://github.com/paper-rerun/paper-rerun/blob/main/METHOD.md

Contato: Filipe Tessaro, pelas issues deste repositório.
