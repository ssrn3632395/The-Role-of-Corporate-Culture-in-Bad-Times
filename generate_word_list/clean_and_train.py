import datetime
import functools
import logging
import sys
from pathlib import Path

import file_util
import gensim
import global_options

from generate_word_list import parse
from generate_word_list.nlp_process import nlp_models, preprocess

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def clean_file(in_file, out_file, lower_case=False, lemma_only=False):
    """clean the entire corpus (output from CoreNLP)

    Arguments:
        in_file {str or Path} -- input corpus, each line is a sentence
        out_file {str or Path} -- output corpus
        lower_case {bool} -- whether transform to lowercase
        lemma_only {bool} -- whether return lemma
    """
    a_text_clearner = preprocess.text_cleaner(lower_case)
    if lemma_only:
        parse.process_largefile(
            input_file=in_file,
            output_file=out_file,
            input_file_ids=[
                str(i) for i in range(file_util.line_counter(in_file))
            ],  # fake IDs (do not need IDs for this function).
            output_index_file=None,
            function_name=functools.partial(a_text_clearner.return_lemmas),
            chunk_size=200000,
        )
    else:
        parse.process_largefile(
            input_file=in_file,
            output_file=out_file,
            input_file_ids=[
                str(i) for i in range(file_util.line_counter(in_file))
            ],  # fake IDs (do not need IDs for this function).
            output_index_file=None,
            function_name=functools.partial(a_text_clearner.clean),
            chunk_size=200000,
        )


def remove_low_freq_compounds_line(line, id, word_freq_dict):
    """Remove phrases with freq fewer than threshold"""
    tokens = line.strip().split(" ")
    filtered_tokens = []
    for t in tokens:
        if "_" in t:
            freq = word_freq_dict.dfs.get(word_freq_dict.token2id.get(t))
            if freq is not None:
                if freq >= global_options.PHRASE_MIN_COUNT:
                    filtered_tokens.append(t)
                else:
                    filtered_tokens.append(" ".join(t.split("_")))
        else:
            if any(c.isalpha() for c in t):
                filtered_tokens.append(t)
    return " ".join(filtered_tokens), "0"  # fake id


def remove_low_freq_compounds_file(in_file, out_file):
    """Remove phrases with freq fewer than threshold"""
    word_dict = gensim.corpora.dictionary.Dictionary(
        documents=gensim.models.word2vec.LineSentence(in_file), prune_at=20000000
    )
    parse.process_largefile(
        input_file=in_file,
        output_file=out_file,
        input_file_ids=[
            str(i) for i in range(file_util.line_counter(in_file))
        ],  # fake IDs (do not need IDs for this function).
        output_index_file=None,
        function_name=functools.partial(
            remove_low_freq_compounds_line, word_freq_dict=word_dict
        ),
        chunk_size=200000,
    )


if __name__ == "__main__":
    Path(global_options.DATA_PATH, "text_corpra", "processed", "unigram").mkdir(
        parents=True, exist_ok=True
    )
    Path(global_options.DATA_PATH, "text_corpra", "processed", "bigram").mkdir(
        parents=True, exist_ok=True
    )
    Path(global_options.DATA_PATH, "text_corpra", "processed", "trigram").mkdir(
        parents=True, exist_ok=True
    )

    # get lemmas
    clean_file(
        in_file=Path(
            global_options.DATA_PATH, "text_corpra", "parsed", "documents.txt"
        ),
        out_file=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_lemmas.txt",
        ),
        lemma_only=True,
    )

    # remove low freq phrases
    remove_low_freq_compounds_file(
        in_file=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_lemmas.txt",
        ),
        out_file=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_temp.txt",
        ),
    )

    # trainsform to lower case
    clean_file(
        in_file=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_temp.txt",
        ),
        out_file=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_clean_phrases.txt",
        ),
        lower_case=True,
    )

    # train and apply a phrase model to detect 2-word phrases ----------------
    nlp_models.train_bigram_model(
        input_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_clean_phrases.txt",
        ),
        model_path=Path(global_options.MODEL_PATH, "bigram.mod"),
    )
    nlp_models.file_bigramer(
        input_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "unigram",
            "documents_clean_phrases.txt",
        ),
        output_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "bigram",
            "documents.txt",
        ),
        model_path=Path(global_options.MODEL_PATH, "bigram.mod"),
        scoring="original_scorer",
        threshold=global_options.PHRASE_THRESHOLD,
    )

    # train and apply a phrase model to detect 3-word phrases ----------------
    nlp_models.train_bigram_model(
        input_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "bigram",
            "documents.txt",
        ),
        model_path=Path(global_options.MODEL_PATH, "trigram.mod"),
    )
    nlp_models.file_bigramer(
        input_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "bigram",
            "documents.txt",
        ),
        output_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "trigram",
            "documents.txt",
        ),
        model_path=Path(global_options.MODEL_PATH, "trigram.mod"),
        scoring="original_scorer",
        threshold=global_options.PHRASE_THRESHOLD,
    )

    # train a word2vec model ----------------
    print(datetime.datetime.now())
    print("Training w2v model...")
    nlp_models.train_w2v_model(
        input_path=Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "trigram",
            "documents.txt",
        ),
        model_path=Path(global_options.MODEL_PATH, "w2v.mod"),
        size=global_options.W2V_DIM,
        window=global_options.W2V_WINDOW,
        workers=global_options.N_CORES,
        iter=global_options.W2V_ITER,
    )
