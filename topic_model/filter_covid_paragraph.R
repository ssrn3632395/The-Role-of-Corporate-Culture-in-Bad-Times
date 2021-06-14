############################################################'
# ' filter covid paragraphs using a two-step procedure
############################################################'
library(tidyverse)
library(stringr)
library(tidytext)
library(stm)
setwd(here::here())

all_transcripts <-
  read_csv("data/text_corpra/all_transcripts_parsed.csv.gz")
all_transcripts <-
  all_transcripts %>% mutate(id = row_number()) # add row (paragraph) id

# filtered covid-related words
covid_related_words <- read_csv("data/word_list_filtered.csv") %>% pull(word)
original_list <- c("covid-19") # seed word

covid_related_words <-
  c(covid_related_words, original_list) %>% unique()

# Note: word counting using only parsed text sometimes miss keywords due to part of named entities. We detect if these words appear in the original unparsed text.
covid_related_words_single <-
  covid_related_words[!str_detect(covid_related_words, "_")]
covid_related_words_single <-
  c(original_list, covid_related_words_single)

# score using expanded list
# decompose each word/phrase to own record using tidytext
all_transcripts_tidy <-
  all_transcripts %>% dplyr::select(id, text_parsed) %>% unnest_tokens(word, text_parsed, token = "regex", pattern = " ")
all_transcripts_tidy <-
  all_transcripts_tidy %>% dplyr::filter(word %in% covid_related_words)

all_transcripts_tidy2 <-
  all_transcripts %>% dplyr::select(id, text) %>% unnest_tokens(word, text) # find undetected words from parsed_text in the original text
all_transcripts_tidy2 <-
  all_transcripts_tidy2 %>% dplyr::filter(word %in% covid_related_words_single)
  
undetected <-
  all_transcripts_tidy2 %>% anti_join(all_transcripts_tidy, by = c('id')) # only count the missing words

all_transcripts_tidy <- bind_rows(all_transcripts_tidy, undetected)
all_transcripts_tidy <-
  all_transcripts_tidy %>% group_by(id) %>% count() # count hits per paragraph

all_transcripts <-
  all_transcripts %>% left_join(all_transcripts_tidy, by = 'id') # n is the number of keywords match
all_transcripts <-
  all_transcripts %>% rename(expanded_n = n)

all_transcripts_covid_related <-
  all_transcripts %>% filter(expanded_n > 0)  # paragraphs with keywords

all_transcripts_covid_related %>% write_csv(
  paste0(
    "data/text_corpra/all_transcripts_covid_related",
    ".csv.gz"
  ),
  na = ""
)

