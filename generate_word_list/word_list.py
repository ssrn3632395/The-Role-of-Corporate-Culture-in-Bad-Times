"""find covid-19 related keywords using w2v models
"""

import csv
import re
import shutil
from pathlib import Path

import file_util
import gensim
import global_options
import pandas as pd
from gensim.models import word2vec

from generate_word_list import prep_coreNLP_inputs


def generate_list_single(model_path, outfile, word_dict, **kwargs):
    # used to tally freq of words
    w2v_mod = gensim.models.Word2Vec.load(str(model_path))
    word_list_details(
        word_dict=word_dict, w2v_mod=w2v_mod, topn=1000, outfile=outfile, **kwargs
    )


def word_list_details(word_dict, w2v_mod, topn, outfile, seed_words=["covid-19"]):
    all_words = []
    for word, sim in w2v_mod.wv.most_similar(seed_words, topn=topn):
        word_info = {}
        word_info["word"] = word
        word_info["sim"] = round(sim, 3)
        word_info["n_sentence"] = word_dict.dfs.get(word_dict.token2id.get(word))
        all_words.append(word_info)

    all_words_df = pd.DataFrame(all_words)
    all_words_df["n_sentence"].fillna(0, inplace=True)
    all_words_df["n_sentence"] = all_words_df["n_sentence"].astype(int)
    all_words_df.to_csv(outfile, index=False)


def consolidate_csvs():
    """merge parsed text with raw text and meta-data and output for fitting topic models"""
    all_transcripts = prep_coreNLP_inputs.prep_inputs()
    documents = file_util.file_to_list(
        Path(
            global_options.DATA_PATH,
            "text_corpra",
            "processed",
            "trigram",
            "documents.txt",
        )
    )
    document_sent_ids = file_util.file_to_list(
        Path(
            global_options.DATA_PATH,
            "text_corpra",
            "parsed",
            "document_sent_ids.txt",
        )
    )
    assert len(documents) == len(document_sent_ids)

    parsed_doc_metas = []
    for doc_sent_id in document_sent_ids:
        doc_meta = {}
        id_pattern = re.compile("(.+?)(\-\-)(Presentation|QA)(--)(\d+)_(\d+)")
        id_fields = re.split(id_pattern, doc_sent_id)
        doc_meta["call_title_date"] = id_fields[1]
        doc_meta["ROUND"] = id_fields[3]
        doc_meta["Paragraph"] = id_fields[5]
        parsed_doc_metas.append(doc_meta)
    parsed_doc_metas = pd.DataFrame(parsed_doc_metas)
    parsed_doc_metas["text_parsed"] = documents
    parsed_doc_metas = parsed_doc_metas.groupby(
        ["call_title_date", "ROUND", "Paragraph"], as_index=False
    ).agg({"text_parsed": " ".join})
    parsed_doc_metas["Paragraph"] = parsed_doc_metas["Paragraph"].astype("int64")

    all_transcripts = all_transcripts.merge(
        parsed_doc_metas, how="left", on=["call_title_date", "ROUND", "Paragraph"]
    )
    all_transcripts.drop("Paragraph_ID", axis=1, inplace=True)

    all_transcripts.to_csv(
        Path(global_options.DATA_PATH, "text_corpra", "all_transcripts_parsed.csv.gz"),
        index=False,
        quoting=csv.QUOTE_ALL,
    )


if __name__ == "__main__":
    MAIN_CORPUS = Path(
        global_options.DATA_PATH, "text_corpra", "processed", "trigram", "documents.txt"
    )

    consolidate_csvs()

    word_dict = gensim.corpora.dictionary.Dictionary(
        documents=word2vec.LineSentence(str(MAIN_CORPUS)), prune_at=20000000
    )

    generate_list_single(
        model_path=Path(global_options.MODEL_PATH, "w2v.mod"),
        outfile=Path(global_options.DATA_PATH, "word_list.csv"),
        word_dict=word_dict,
        seed_words=["covid-19"],
    )

    shutil.copy(
        Path(global_options.DATA_PATH, "word_list.csv"),
        Path(global_options.DATA_PATH, "word_list_filtered.csv"),
    )
