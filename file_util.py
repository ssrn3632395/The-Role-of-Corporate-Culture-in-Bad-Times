from pathlib import Path
from string import punctuation

import gensim
import pandas as pd
from gensim.parsing.preprocessing import *
from tqdm import tqdm

import global_options


def line_counter(a_file):
    """Count the number of lines in a text file
    
    Arguments:
        a_file {str or Path} -- input text file
    
    Returns:
        int -- number of lines in the file
    """
    n_lines = 0
    with open(a_file, "r") as f:
        n_lines = sum(1 for _ in f)
    return n_lines


def file_to_list(a_file):
    """Read a text file to a list, each line is an element
    
    Arguments:
        a_file {str or path} -- path to the file
    
    Returns:
        [str] -- list of lines in the input file, can be empty
    """
    doc_ids = []
    with open(a_file) as f:
        for l in f:
            doc_ids.append(l.strip())
    return doc_ids


def list_to_file(a_list, a_file, validate=True):
    """Write a list to a file, each element in a line
    The strings needs to have no "\n"
    
    Keyword Arguments:
        validate {bool} -- check if number of lines in the file
            equals to the length of the list (default: {True})
    """
    with open(a_file, "w", 8192000) as f:
        for e in a_list:
            f.write("{}\n".format(e))
    if validate:
        assert line_counter(a_file) == len(a_list)


def read_large_file(a_file, block_size=10000):
    """A generator to read text files into blocks
    Usage: 
    for block in read_large_file(filename):
        do_something(block)
    
    Arguments:
        a_file {str or path} -- path to the file
    
    Keyword Arguments:
        block_size {int} -- [number of lines in a block] (default: {10000})
    """
    block = []
    with open(a_file) as file_handler:
        for line in file_handler:
            block.append(line)
            if len(block) == block_size:
                yield block
                block = []
    # yield the last block
    if block:
        yield block


def preprocess_string(s: str) -> "[tokens (str)]":
    """preporcessing str

    Args:
        s (str): string to preprocess

    Returns:
        [str]: strip end and begining punctuation marks, lower case, and remove stopwords
    """
    tokens_processed = gensim.parsing.preprocessing.preprocess_string(
        s,
        filters=[
            lambda x: " ".join([t.strip(punctuation) for t in x.split()]),
            lambda x: x.lower(),
            remove_stopwords,
        ],
    )
    return tokens_processed


def get_csv_files(DIR=global_options.PDF_PARSED_PATH):
    """return parsed csv files from pdf

    Returns:
        [Path]: a list of csv files
    """
    parsed_csvs = Path(DIR).glob("**/*.csv")
    return list(parsed_csvs)


def get_corpus(csv_files: "[Path]"):
    """return corpus from parsed transcripts

    Returns:
        [str]: a list of paragraphs from all transcripts
    """
    csv_files = get_csv_files()
    corpus_all = []
    for csv_f in tqdm(csv_files):
        text = pd.read_csv(csv_f, index_col=0).text.to_list()
        corpus_all.extend(text)
    return corpus_all


def combine_all_csv(csv_files: "[Path]"):
    """Combine all csv files in a list
    
    Returns:
        [str]: a list of paragraphs from all transcripts
    """
    csv_all = []
    for csv_f in tqdm(csv_files):
        a_df = pd.read_csv(str(csv_f), index_col=0)
        csv_all.append(a_df)
    return pd.concat(csv_all, axis=0, ignore_index=True)


def if_contains_words(doc_list, words_set) -> "[bool]":
    """check if a list of string contains any of the words in a set
    Args:
        doc_list ([str]): input string
        words_set (set(str)): set of words
    """
    n_words_in_doc = [len(set(x.split()).intersection(words_set)) for x in doc_list]
    return [x > 0 for x in n_words_in_doc]
