# Common bean disease management trials in Brazil

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23641861.svg)](https://doi.org/10.5281/zenodo.23641861)

1,562 trial results on managing the main diseases of common bean (*Phaseolus vulgaris*, "feijão-comum") in Brazil, taken from the tables of 20 open-access Embrapa publications: anthracnose, angular leaf spot, white mold, rust, web blight and bean golden mosaic. Each row is one number exactly as printed, with the page and table it came from, and points to the trial it belongs to (place, season, cultivar, inoculation, application timing, design).

Common bean is a staple food of low-income households in Brazil, and much of the evidence on how to protect it sits in Portuguese technical bulletins and short notes. This dataset makes 20 of them searchable and comparable.

Part of [Paper Rerun](https://paper-rerun.github.io), in its Open Tables line. The work was done by AI agents on a home computer and reviewed by a human before publication.

## What is in it

| | |
|---|---|
| Publications | 20 (Alice and Infoteca-e, Embrapa's open repositories), 1992 to 2020s; most are fungicide trials from Embrapa Arroz e Feijão, plus biological control (Bacillus, Trichoderma), resistant lines and multilines, cultural management (Brachiaria straw) and seed health |
| Trials | 52 (41 field, 6 greenhouse, 3 laboratory, 2 growth chamber) |
| Records | 1,562 |

Files:
- `data/bean_disease_trials.csv`: the dataset, one record per printed value, with `doc_id` and `trial_id`. Columns are described in `method/schema.json`.
- `data/bean_disease_trials_context.csv`: one row per trial. Join on `doc_id` + `trial_id`; an empty context field in a record means the trial's value applies.
- `data/sources.csv`: the 20 publications, with authors, record link and licence notice.
- `qa/decisions.csv`: every disagreement between the two independent transcriptions and how it was settled against the PDF (2,166 decisions, with page).
- `method/`: the schema, the comparison script and the merge script.

`source_inconsistency` marks 433 records where the publication contradicts itself (for example a footnote and a table disagreeing on a dose or a date).

## How it was made

1. **Collection.** An agent searched Embrapa's open repositories for publications with quantitative trial tables on this topic, downloaded 20 and recorded 108 candidates it did not take, with the reason.
2. **Two independent transcriptions.** Two agents per publication transcribed the trial context and every table cell on the topic into a fixed schema, without seeing each other's work, copying numbers exactly as printed and accounting for every data cell of every table.
3. **Comparison and adjudication.** A script paired the two transcriptions, trial by trial and record by record, and listed every disagreement and every value present in only one of them. Each one was settled by checking the PDF, with the page as evidence.

## How accurate it is

- **Numbers:** the two transcriptions agreed on all 1,500 values and significance letters they both read.
- **Context and classification:** trial context is now written once per trial instead of on every row, which cut context errors from 4,813 fields in our previous round to 14. Per-record labels (for example whether a statistic is stated, or the treatment type) still go wrong across whole tables in a single transcription: one alone was fully correct on 66% and 79% of records. Every disagreement was settled against the PDF, so the dataset does not depend on either one alone.
- **Known limits:** recent work on bean diseases in these repositories is mostly cultivar releases, so only a few documents are from after 2013. Values shown only in charts without printed numbers were not read. One record page lists no authors; the chapter authors are given as printed in the PDF.

## Licence and citation

- The dataset (the CSV files, schema and scripts) is released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Please cite the original publications listed in `data/sources.csv` as well as this dataset.
- The publications are not redistributed. Embrapa's repositories show a CC BY-NC-ND 4.0 notice; journal articles keep their journals' licences and some PDFs print "all rights reserved". Only numbers, which are facts, and short citations are used here.

Errors or missing trials: please [open an issue](https://github.com/paper-rerun/bean-disease-trials-br/issues).

## How this dataset was made

This dataset was built by AI agents (Claude, by Anthropic) on a home computer and reviewed by a human before publication. No value was estimated or typed by hand: each one was transcribed from the source PDF twice, independently, and every disagreement was checked against the page. The method and scripts are in `method/`. How the wider project works: https://github.com/paper-rerun/paper-rerun/blob/main/METHOD.md

Contact: Filipe Tessaro, via issues on this repository.
