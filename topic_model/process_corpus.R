############################################################
# ' Process corpus for stm experiments (source from stm_experiment)
# '
############################################################
library(tidyverse)
library(stringr)
library(tidytext)
library(stm)
library(stopwords)
setwd(here::here())

seed <- 1

process_corpus <- function(stop_words_source,
                           vocab_lower,
                           K,
                           score_threshold) {
  vocab_upper <- 1
  all_transcripts_covid_related <-
    read_csv("data/text_corpra/all_transcripts_covid_related.csv.gz")
  all_transcripts_covid_related$text_parsed <-
    str_replace_all(all_transcripts_covid_related$text_parsed,
                    "\\[ner.*?\\]",
                    "") # remove ners
  
  all_transcripts_covid_related <-
    all_transcripts_covid_related %>% mutate(id = row_number())
  all_transcripts_covid_related_tidytext <-
    all_transcripts_covid_related %>% dplyr::select(id, text_parsed) %>% unnest_tokens(word, text_parsed, token = "regex", pattern = " ")
  
  all_transcripts_covid_related_tidytext$word <-
    str_replace_all(all_transcripts_covid_related_tidytext$word,
                    "_\\b|\\b_",
                    "") # replace phrases starts with or end with _
  
  all_transcripts_covid_related_tidytext <-
    all_transcripts_covid_related_tidytext %>% filter(!word %in% stopwords(source = stop_words_source)) # stopwords
  stop_words_extra <-
    read_table("data/text_corpra/extra_stopwords.txt", col_names = F) %>% deframe() %>% tolower()
  
  all_transcripts_covid_related_tidytext <-
    all_transcripts_covid_related_tidytext %>% filter(!word %in% stop_words_extra)
  
  text_parsed_filtered <-
    all_transcripts_covid_related_tidytext %>% group_by(id) %>% summarise(text_parsed = str_c(word, collapse = " ")) %>% ungroup()
  all_transcripts_covid_related$text_parsed <-
    NULL # remove unfiltered text
  all_transcripts_covid_related <-
    all_transcripts_covid_related %>% left_join(text_parsed_filtered, by = 'id') # join filtered text back
  
  meta <-
    all_transcripts_covid_related %>% dplyr::select(call_title_date,
                                                    ROUND,
                                                    Paragraph,
                                                    speaker,
                                                    speaker_title,
                                                    speaker_role)
  processed <-
    textProcessor(
      all_transcripts_covid_related$text_parsed,
      metadata = meta,
      removestopwords = F,
      removepunctuation = F,
      stem = F,
      wordLengths = c(2, Inf),
      removenumbers = F
    )
  
  out <-
    prepDocuments(processed$documents,
                  processed$vocab,
                  lower.thresh = vocab_lower)
  return(
    list(
      "processed" = processed,
      "out" = out,
      "all_transcripts_covid_related" = all_transcripts_covid_related
    )
  )
}
