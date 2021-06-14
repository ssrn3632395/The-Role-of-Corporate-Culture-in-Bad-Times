# ' ############################################
# ' Create output folders to store stm results
# ' ############################################
setwd(here::here())

dir.create(file.path("output", "stm", "exp"),
           showWarnings = F,
           recursive = T)
dir.create(file.path("output", "stm", "exp", "top_words"), showWarnings = F)
dir.create(file.path("output", "stm", "exp", "wordclouds"), showWarnings = F)
dir.create(file.path("output", "stm", "exp", "rep_docs"), showWarnings = F)
dir.create(file.path("output", "stm", "exp", "rep_sents"), showWarnings = F)
dir.create(file.path("output", "stm", "exp", "call_measure"),
           showWarnings = F)

dir.create(file.path("output", "stm", "plot"), showWarnings = F)
