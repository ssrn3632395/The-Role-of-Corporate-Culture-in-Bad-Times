import os
from pathlib import Path

DATA_PATH = "Data/"
MODEL_PATH = "Data/models/"

# ==== parsing pdfs ====
PDF_PATH = "Data/pdfs/raw/"  # where to put raw pdf files
PDF_PARSED_PATH = "Data/pdfs/parsed/"  # where to put parsed pdf files (in csv format)
N_CORES = 4  # number of CPU cores to use for parsing

Path(DATA_PATH).mkdir(parents=True, exist_ok=True)
Path(PDF_PARSED_PATH).mkdir(parents=True, exist_ok=True)
Path(PDF_PATH).mkdir(parents=True, exist_ok=True)
Path(MODEL_PATH).mkdir(parents=True, exist_ok=True)


# ==== training word2vec model ====
# Hardware options
RAM_CORENLP: str = "32G"  # max RAM allocated for parsing using CoreNLP
PARSE_CHUNK_SIZE: int = 1000  # number of lines in the input file to process uing CoreNLP at once. Increase on workstations with larger RAM (e.g. to 1000 if RAM is 64G)

# CoreNLP directory location
os.environ[
    "CORENLP_HOME"
] = "/Users/mai/stanford-corenlp-full-2018-10-05"  # location of the CoreNLP models

# Parsing and analysis options
PHRASE_THRESHOLD: int = 10  # threshold of the phraser module (smaller -> more phrases)
PHRASE_MIN_COUNT: int = 20  # min number of times a bigram needs to appear in the corpus to be considered as a phrase
W2V_DIM: int = 300  # dimension of word2vec vectors
W2V_WINDOW: int = 5  # window size in word2vec
W2V_ITER: int = 40  # number of iterations in word2vec
DICT_RESTRICT_VOCAB = None  # change to a fraction number (e.g. 0.2) to restrict the dictionary vocab in the top 20% of most frequent vocab
