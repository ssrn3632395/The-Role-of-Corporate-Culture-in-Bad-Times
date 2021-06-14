############################################################
# ' Fit STM
############################################################
library(tidyverse)
library(stringr)
library(tidytext)
library(stm)
library(tm)
library(stopwords)
library(here)
setwd(here())

source("topic_model/process_corpus.R")
source("topic_model/create_output_folders.R")
seed <- 1

fit_stm <-
  function(stop_words_source,
           vocab_lower,
           K) {
    processed_corpus <- process_corpus(stop_words_source,
                                       vocab_lower,
                                       K)
    
    saveRDS(processed_corpus$out,
            file = here(
              paste0(
                "output/stm/exp/out_",
                stop_words_source,
                "_K_",
                K,
                "_vocab_lower_",
                vocab_lower,
                ".rds"
              )
            )) # dump out and process to disk; use readRDS() to load the model from disk
    
    saveRDS(processed_corpus$processed,
            file = here(
              paste0(
                "output/stm/exp/processed_",
                stop_words_source,
                "_K_",
                K,
                "_vocab_lower_",
                vocab_lower,
                ".rds"
              )
            )) # dump out and process to disk; use readRDS() to load the model from disk
    
    out <- processed_corpus$out
    stm_fit <- stm(
      documents = out$documents,
      vocab = out$vocab,
      K = K,
      max.em.its = 100,
      init.type = "Spectral",
      seed = seed
    )
    
    saveRDS(stm_fit,
            file = here(
              paste0(
                "output/stm/exp/stm_",
                stop_words_source,
                "_K_",
                K,
                "_vocab_lower_",
                vocab_lower,
                ".rds"
              )
            )) # dump model to disk; use readRDS() to load the model from disk
    
    label_results <- labelTopics(stm_fit, n = 10)
    sink(here(
      paste0(
        "output/stm/exp/stm_",
        stop_words_source,
        "_K_",
        K,
        "_vocab_lower_",
        vocab_lower,
        ".txt"
      )
    ))
    print(label_results)
    sink() # save label topic results to disk
  }

fit_stm(stop_words_source = "stopwords-iso",
        vocab_lower = 10,
        K = 35)
