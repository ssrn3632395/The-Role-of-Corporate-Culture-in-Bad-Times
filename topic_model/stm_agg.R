# ' ############################################
# ' Manually aggregate topics according to stm results, output new word cloud, top docs, and measures
# ' ############################################

library(tidyverse)
library(stringr)
library(tidytext)
library(stm)
library(stopwords)
library(lubridate)
library(cowplot)
library(ggthemes)
library(janitor)
setwd(here::here())

stop_words_source <- 'stopwords-iso'
vocab_lower <-  10
K <- 35

OUTPUT_TOPDOC <- T
OUTPUT_WORDCLOUD <- T
OUTPUT_CALL_MEASURE <- T


agg_topics_map <-
  read_csv(file = "output/stm/exp/top_agg.csv") %>% mutate(topics = as.character(topics))

model_name = paste0(stop_words_source,
                    "_K_",
                    K,
                    "_vocab_lower_",
                    vocab_lower)

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
  read_csv(here::here(
    paste0("data/text_corpra/all_transcripts_covid_related",
           ".csv.gz")
  ))
if (length(processed$docs.removed) > 0) {
  all_transcripts_covid_related <-
    all_transcripts_covid_related[-processed$docs.removed, ]
}
if (length(out$docs.removed) > 0) {
  all_transcripts_covid_related <-
    all_transcripts_covid_related[-out$docs.removed, ]
}
stopifnot(nrow(all_transcripts_covid_related) == nrow(stm_model$theta))


# 1. consolidated topic representative sentences---------------------------
topic_prop <- stm_model$theta %>% as_tibble()
topic_prop %>% dim
# construct topic labels (include top 3 words)
topic_labels <- 1:K
colnames(topic_prop) <- topic_labels
topic_prop$doc_id = 1:nrow(topic_prop)
topic_prop_long <-
  topic_prop %>% pivot_longer(cols = -'doc_id',
                              names_to = 'topics',
                              values_to = 'p')
topic_prop_long <-
  topic_prop_long %>% left_join(agg_topics_map, by = 'topics')
topic_prop_long <-
  topic_prop_long %>% replace_na(list(type = 'others', name = 'others'))
topic_prop_long_agg <-
  topic_prop_long %>% group_by(doc_id, name) %>% summarise(p = sum(p))
topic_prop_agg <-
  topic_prop_long_agg %>% pivot_wider(id_cols = 'doc_id',
                                      values_from = 'p',
                                      names_from = 'name') %>% arrange(doc_id) %>% ungroup() %>% select(-doc_id)


all_transcripts_covid_related_copy <-
  bind_cols(all_transcripts_covid_related, topic_prop_agg)
all_transcripts_covid_related_copy %>% glimpse()
all_transcripts_covid_related_copy$length <-
  str_count(all_transcripts_covid_related_copy$text_parsed, " ")
all_transcripts_covid_related_f <-
  all_transcripts_covid_related_copy %>% filter(length >= 10)
all_transcripts_covid_related_f <-
  all_transcripts_covid_related_f %>% distinct(text, .keep_all = T)

new_topic_names <- colnames(topic_prop_agg)
output_df <- tibble()
num_of_examples <- 20
for (new_topic_name in new_topic_names) {
  example_topic <-
    all_transcripts_covid_related_f %>% top_n(n = num_of_examples, wt = get(new_topic_name)) %>% select(text,!!new_topic_name)
  example_topic$topic <- new_topic_name
  example_topic <-
    example_topic %>% rename(agg_prop = !!new_topic_name) %>% arrange(topic)
  example_topic$example_num <- 1:num_of_examples
  output_df <- bind_rows(output_df, example_topic)
}

dir.create(file.path("output", "stm", "exp", "agg", model_name),
           recursive = T)
dir.create(file.path("output", "stm", "exp", "agg", model_name, "plots"),
           recursive = T)

if (OUTPUT_TOPDOC) {
  output_df %>% select(topic, example_num, text, agg_prop) %>% mutate(agg_prop = round(agg_prop, 2)) %>%
    openxlsx::write.xlsx(
      file = file.path(
        "output",
        "stm",
        "exp",
        "agg",
        model_name,
        "top_docs_agg.xlsx"
      ),
      row.names = F
    )
}


# 2 aggregated topics word cloud---------------------------
# Note: P(w|T1 or T2) = [P(W and T1) + P(W and T2)] / [P(T1) + P(T2)]
topic_prob <- colMeans(stm_model$theta)
topic_prob <-
  topic_prob %>% t %>% as.tibble() %>% slice(rep(1:n(), each = length(stm_model$vocab)))
topic_prob %>% dim
word_topic <- exp(stm_model$beta$logbeta[[1]]) %>% t
P_W_and_T <- word_topic * as.matrix(topic_prob) %>% as.data.frame()

# construct topic labels
topic_labels <- 1:K
colnames(P_W_and_T) <- topic_labels
colnames(topic_prob) <- topic_labels

P_W_and_T$word_id = 1:nrow(P_W_and_T)
P_W_and_T_L <-
  P_W_and_T %>% pivot_longer(cols = -'word_id',
                             names_to = 'topics',
                             values_to = 'p')
P_W_and_T_L <-
  P_W_and_T_L %>% left_join(agg_topics_map, by = 'topics')
P_W_and_T_L <-
  P_W_and_T_L %>% replace_na(list(type = 'others', name = 'others'))
P_W_and_T_L <-
  P_W_and_T_L %>% group_by(word_id, name) %>% summarise(p = sum(p))
P_W_and_T_agg <-
  P_W_and_T_L %>% pivot_wider(id_cols = 'word_id',
                              values_from = 'p',
                              names_from = 'name') %>% arrange(word_id) %>% ungroup() %>% select(-word_id)

topic_prob$word_id = 1:nrow(topic_prob)
topic_prob_L <-
  topic_prob %>% pivot_longer(cols = -'word_id',
                              names_to = 'topics',
                              values_to = 'p')
topic_prob_L <-
  topic_prob_L %>% left_join(agg_topics_map, by = 'topics')
topic_prob_L <-
  topic_prob_L %>% replace_na(list(type = 'others', name = 'others'))
topic_prob_L <-
  topic_prob_L %>% group_by(word_id, name) %>% summarise(p = sum(p))
topic_prob_agg <-
  topic_prob_L %>% pivot_wider(id_cols = 'word_id',
                               values_from = 'p',
                               names_from = 'name') %>% arrange(word_id) %>% ungroup() %>% select(-word_id)

word_topic_agg <-
  ((as.matrix(P_W_and_T_agg) / as.matrix(topic_prob_agg)) * sum(stm_model$settings$dim$wcounts$x)) %>% as.tibble()
colnames(word_topic_agg) <- colnames(topic_prob_agg)


## 2.1 consolidated single topic (for testing only)  =====
topic <- 1
word_topic <-
  word_topic_agg[, topic] %>% pull() # pull a single cosolidated topic
vocab <- stm_model$vocab
vocab <-
  str_replace_all(vocab, "_\\b|\\b_", "") # remove phrases starting or ending _

word_df <- tibble(vocab = vocab, prop = word_topic)
word_df <-
  word_df %>% top_n(n = 40, wt = prop) %>% arrange(-prop) %>% mutate(
    angle = 90 * sample(c(0, 1), n(), replace = TRUE, prob = c(70, 30)),
    w_color = sample.int(7, n(), replace = T)
  ) # 30% of vertical


plot_wc <-
  ggplot(word_df,
         aes(
           label = vocab,
           size = prop,
           angle = angle,
           color = factor(w_color)
         )) +
  geom_text_wordcloud_area(shape = "square") + # can also be "circle"
  scale_radius(range = c(10, 24)) + # min and mox font size
  theme_minimal() + labs(x = paste0("Topic ", topic), y = NULL) +
  scale_colour_manual(values = c(
    '#458BAF',
    '#4A4E22',
    '#343331',
    '#486E5E',
    '#1E364F',
    '#9F574B',
    "#136874"
  ))
ggdraw() + draw_plot(plot_wc, scale = 1)
# ggsave("output/stm/plot/1.png", width = 12, height = 8)

## 2.2 consolidated all plots ===============

plot_topic <- function(topic,
                       max_w = 30,
                       radius = c(1.5, 6)) {
  word_topic <- word_topic_agg[, topic] %>% pull()
  topic_name <-
    str_replace_all(colnames(word_topic_agg)[topic], " ", "_")
  topic_name <- toupper(topic_name)
  vocab <- stm_model$vocab
  vocab <-
    str_replace_all(vocab, "_\\b|\\b_", "") # remove phrases starting or ending _
  
  word_df <- tibble(vocab = vocab, prop = word_topic)
  word_df <-
    word_df %>% top_n(n = max_w, wt = prop) %>% arrange(-prop) %>%
    mutate(angle = 90 * sample(c(0, 1), n(), replace = TRUE, prob = c(95, 5))) # 30% of vertical
  
  
  word_df %>% ggplot(aes(
    label = vocab,
    size = prop,
    angle = angle,
    color = factor(sample.int(7, nrow(word_df), replace = TRUE))
  )) +
    geom_text_wordcloud(shape = "square",
                        grid_margin = 1,
                        area_corr = 0.5) + # can also be "circle"
    scale_radius(range = radius) + # min and mox font size
    theme_minimal() + labs(x = paste0(topic_name), y = NULL) +
    theme(axis.title.x = element_text(size = 4)) +
    scale_colour_manual(
      values = c(
        '#458BAF',
        '#4A4E22',
        '#343331',
        '#486E5E',
        '#1E364F',
        '#9F574B',
        "#136874"
      )
    )
}

exposure_topics <-
  agg_topics_map %>% filter(type == 'exposure') %>% distinct(name) %>% pull(name) %>% sort
response_topics <-
  agg_topics_map %>% filter(type == 'response') %>% distinct(name) %>% pull(name) %>% sort

word_topic_agg <-
  word_topic_agg %>% select(exposure_topics, response_topics)

set.seed(1)
if (OUTPUT_WORDCLOUD) {
  do.call("plot_grid", c(lapply(1:3, plot_topic, 30, c(2.5, 6.5)), nrow = 1))
  ggsave(
    file.path("output", "stm", "exp", "agg", model_name, "exposure_1.png"),
    width = 8,
    height = 4
  )
  
  do.call("plot_grid", c(lapply(
    4:length(exposure_topics), plot_topic, 30, c(2.5, 6.5)
  ), nrow = 1))
  ggsave(
    file.path("output", "stm", "exp", "agg", model_name, "exposure_2.png"),
    width = 8,
    height = 4
  )
  
  
  do.call("plot_grid", c(lapply((length(exposure_topics) + 1):(length(exposure_topics) + length(response_topics)), plot_topic, 30, c(2.5, 6.5)
  ), nrow = 1))
  ggsave(
    file.path("output", "stm", "exp", "agg", model_name, "response.png"),
    width = 8,
    height = 4
  )
  
}


# 3. call level measure -------------------------
stopifnot(nrow(all_transcripts_covid_related) == nrow(topic_prop_agg))
colnames(topic_prop_agg) = paste0("agg_", colnames(topic_prop_agg))

topic_prob_agg <- clean_names(topic_prop_agg)

topic_prop <-
  bind_cols(
    all_transcripts_covid_related %>% select(
      call_title_date,
      ROUND,
      Paragraph,
      speaker,
      speaker_title,
      speaker_role,
      text,
      text_parsed
    ),
    topic_prob_agg
  )

# number of words in each paragraph
topic_prop <-
  topic_prop %>% mutate(paragraph_length = str_count(topic_prop$text_parsed, " ") + 1)

topic_prop <- topic_prop %>% dplyr::select(-text_parsed)

# Note: each paragraphs' topic's prop weighted by paragraph length
# e.g., paragraph1_topic_1 = 0.5, paragraph1_topic_2 = 0.5, paragraph2_topic_1 = 0.2, paragraph2_topic_2 = 0.8
# paragraph1_length = 2, paragraph1_length = 6
# call_level weighted measure for topic_1 = (0.5*2 + 0.2*6)/(2+6) = 0.275

all_transcripts <-
  read_csv("data/text_corpra/all_transcripts_parsed.csv.gz")
all_transcripts <-
  all_transcripts %>% mutate(paragraph_length = str_count(text_parsed, " ") + 1)

prop_weighted <- topic_prop %>% group_by(call_title_date) %>%
  summarise_at(vars(starts_with("agg_")), ~ weighted.mean(., w = paragraph_length))
length_discussion <-
  topic_prop %>% ungroup() %>%  group_by(call_title_date) %>%
  summarise_at(
    vars(starts_with("agg_")),
    ~ sum(paragraph_length, na.rm = T) * weighted.mean(., w = paragraph_length)
  )

prop_weighted %>% mutate(across(where(is.numeric), round, 4)) %>%
  write_csv("output/stm/exp/call_measure/prop_weighted.csv")
length_discussion %>% mutate(across(where(is.numeric), round, 4)) %>%
  write_csv("output/stm/exp/call_measure/length_discussion.csv")
