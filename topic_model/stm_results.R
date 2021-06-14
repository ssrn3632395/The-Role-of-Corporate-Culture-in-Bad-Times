############################################################
# ' Organize STM experiments results
# '
############################################################
library(tidyverse)
library(stm)
library(ggwordcloud)
library(cowplot)
library(gridExtra)
library(openxlsx)
library(RColorBrewer)
library(stopwords)
library(ggcharts)

setwd(here::here())

output_top_words <- function(stop_words_source,
                             vocab_lower,
                             K) {
  stm_model <- readRDS(
    paste0(
      "output/stm/exp/stm_",
      stop_words_source,
      "_K_",
      K,
      "_vocab_lower_",
      vocab_lower,
      ".rds"
    )
  )
  labels <- labelTopics(stm_model, n = 40)
  
  wb <- openxlsx::createWorkbook("top_words")
  for (score_type in names(labels)[1:4]) {
    openxlsx::addWorksheet(wb, sheetName = score_type)
    x <- as.data.frame(t(labels[[score_type]]))
    colnames(x) <- paste0("topic"," ", 1:ncol(x))
    openxlsx::writeDataTable(wb, sheet = score_type, x = x)
    setColWidths(wb, sheet = score_type, cols=1:40, widths = 12)
    
  }
  openxlsx::saveWorkbook(
    wb,
    file = paste0(
      "output/stm/exp/top_words/",
      stop_words_source,
      "_K_",
      K,
      "_vocab_lower_",
      vocab_lower,
      ".xlsx"
    ),
    overwrite = TRUE
  ) ## save to working directory
  
}


output_topdoc_wc <- function(stop_words_source,
                             vocab_lower,
                             K,
                             score_threshold) {
  # ================== representative paragraphs ================================
  stm_model <- readRDS(
    paste0(
      "output/stm/exp/stm_",
      stop_words_source,
      "_K_",
      K,
      "_vocab_lower_",
      vocab_lower,
      ".rds"
    )
  )
  
  
  out <- readRDS(file = here::here(
    paste0(
      "output/stm/exp/out_",
      stop_words_source,
      "_K_",
      K,
      "_vocab_lower_",
      vocab_lower,
      ".rds"
    )
  ))
  
  processed <- readRDS(file = here::here(
    paste0(
      "output/stm/exp/processed_",
      stop_words_source,
      "_K_",
      K,
      "_vocab_lower_",
      vocab_lower,
      ".rds"
    )
  ))
  
  all_transcripts_covid_related <-
    read_csv(
        "data/text_corpra/all_transcripts_covid_related.csv.gz",
    )
  if (length(processed$docs.removed) > 0) {
    all_transcripts_covid_related <-
      all_transcripts_covid_related[-processed$docs.removed, ]
  }
  if (length(out$docs.removed) > 0) {
    all_transcripts_covid_related <-
      all_transcripts_covid_related[-out$docs.removed, ]
  }
  stopifnot(nrow(all_transcripts_covid_related) == nrow(stm_model$theta))
  
  topic_prop <- stm_model$theta %>% as_tibble()
  
  # construct topic labels (include top words)
  topic_labels <- paste0("topic", 1:K)
  colnames(topic_prop) <- topic_labels
  
  all_transcripts_covid_related_copy <-
    bind_cols(all_transcripts_covid_related, topic_prop)
  all_transcripts_covid_related_copy$length <-
    str_count(all_transcripts_covid_related_copy$text_parsed, " ")
  all_transcripts_covid_related_f <-
    all_transcripts_covid_related_copy %>% filter(length >= 10)
  all_transcripts_covid_related_f <-
    all_transcripts_covid_related_f %>% distinct(text, .keep_all = T)
  
  new_topic_names <- colnames(all_transcripts_covid_related_f)
  new_topic_names <-
    new_topic_names[str_starts(new_topic_names, "topic")]
  
  output_df <- tibble()
  num_of_examples <- 10
  for (new_topic_name in new_topic_names) {
    example_topic <-
      all_transcripts_covid_related_f %>% top_n(n = num_of_examples, wt = get(new_topic_name)) 
    example_topic <- example_topic[1:num_of_examples,]
    example_topic$topic <- new_topic_name
    example_topic$example_num <- 1:num_of_examples
    output_df <- bind_rows(output_df, example_topic)
  }
  
  output_df %>% select(topic, example_num, text, everything()) %>%
    mutate_at(vars(starts_with("topic\\d")), round, 2) %>%
    openxlsx::write.xlsx(
      file = paste0(
        "output/stm/exp/rep_docs/",
        stop_words_source,
        "_K_",
        K,
        "_vocab_lower_",
        vocab_lower,
        ".xlsx"
      ),
      na = ""
    )
  
  # ============ Word Clouds  ============================================
  plot_topic <- function(topic, max_w = 20) {
    word_topic <-
      exp(stm_model$beta$logbeta[[1]])[topic, ] * sum(stm_model$settings$dim$wcounts$x)
    vocab <- stm_model$vocab
    vocab <-
      str_replace_all(vocab, "_\\b|\\b_", "") # remove phrases starting or ending _
    
    word_df <- tibble(vocab = vocab, prop = word_topic)
    word_df <-
      word_df %>% top_n(n = max_w, wt = prop) %>% arrange(-prop) %>%
      mutate(angle = 90 * sample(c(0, 1), n(), replace = TRUE, prob = c(80, 20))) # % of vertical
    
    word_df %>% ggplot(aes(
      label = vocab,
      size = prop,
      angle = angle
    )) +
      geom_text_wordcloud_area(shape = "square", eccentricity = 0.6,
                          grid_margin = 0,
                          grid_size = 1, 
                          perc_step = 0.005,
                          max_steps = 50,
                          area_corr_power = 1) +  
      scale_radius(range = c(1.5, 3.5), limits = c(0, NA)) + # min and max font size
      theme_minimal() + labs(x = paste0("Topic ", topic), y = NULL) +
      theme(axis.title.x = element_text(size = 4))
  }
  do.call("plot_grid", c(lapply(1:K, plot_topic), nrow = ceiling(K / 5)))
  ggsave(
    paste0(
      "output/stm/exp/wordclouds/",
      stop_words_source,
      "_K_",
      K,
      "_vocab_lower_",
      vocab_lower,
      ".png"
    ),
    width = 11.5,
    height = 8.5,
    dpi = 600,
  )
}

output_top_words(stop_words_source = "stopwords-iso",
                 vocab_lower = 10,
                 K = 35)
output_topdoc_wc(stop_words_source = "stopwords-iso",
                 vocab_lower = 10,
                 K = 35)
