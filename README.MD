This repository contains data cleaning and topic model training code in _Li, K., Liu, X., Mai, F., & Zhang, T. (2021). The role of corporate culture in bad times: Evidence from the COVID-19 pandemic. Journal of Financial and Quantitative Analysis (forthcoming)_. [[SSRN]](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3632395)

The code is tested in Ubuntu 18.04 and macOS Catalina.

# Requirements

## Environments:

_Python 3.7+_  
Install required packages using `pip install -r requirements.txt`.

_R 4.0+_  
Install required libraries using `Rscript topic_model/install_req_libs.R`.

The code is tested on Ubuntu 18.04 and macOS Big Sur.

## Data

A list of conference call transcripts (in PDF format) from S&P Global Market Intelligence. The names can be found in
`data/call_list.txt`. Sample data can be found in `data/pdfs/raw/`.

# Running the code

1. Parse PDFs (Python)

`python -m pdf2text.import_pdfs` : The module transforms calls in PDFs in `data/pdfs/raw/` to individual CSV files in `data/pdfs/parsed/`. It also outputs the meta data of the calls `data/meta_data.csv`. The meta data is manually checked and matched to firms in the format in `meta_data_cleaned.csv`.

2. Train word2vec model (Python)

Please see additional requirements in `generate_word_list/w2v_README.md`

`python -m generate_word_list.prep_coreNLP_inputs`:  
The module imports a hand-collected meta-data file (with firm GVKEYs) `data/meta_data_clean.csv`. It then outputs Paragraph IDs and texts as plain text files to be parsed by Stanford CoreNLP.

`python -m generate_word_list.parse` :  The module uses Stanford CoreNLP to parse the raw texts.

`python -m generate_word_list.clean_and_train` :  The module clean the parsed raw text, identify phrases, and train a word2vec model.

`python -m generate_word_list.word_list`: The module uses the trained word2vec model to generate a word list (`data/word_list.csv`) for tagging COVID-19 related paragraphs. It also stacks all csv files to a single file `data/text_corpra/all_transcripts_parsed.csv.gz`. The word list should be manually inspected and saved as `data/word_list_filtered.csv`.

4. Train topic model (R)

`Rscript topic_model/filter_covid_paragraph.R`: Finds paragraphs with COVID-related keywords; outputs to `data/text_corpra/all_transcripts_covid_related.csv.gz`.

`Rscript topic_model/fit_stm.R`: Fits a correlated topic model using the stm package. Saves the model in `output/stm/`. 

`Rscript topic_model/stm_results.R`: Outputs topic top words, representative paragraphs, and word clouds for individual topics in `output/stm/`. After inspecting the topics, you should manually create a topic map in the format of `output/stm/exp/top_agg.csv`.

`Rscript topic_model/combine_topics.R`: Takes topic aggregation map in `output/stm/exp/top_agg.csv` and creates aggregated document level measures in `output/stm/call_measure` and word clouds in `output/stm/agg`.
