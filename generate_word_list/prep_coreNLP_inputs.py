"""prep calls text to be parsed using CoreNLP
"""
from pathlib import Path

import file_util
import global_options
import pandas as pd
from tqdm.auto import tqdm


def prep_inputs():
    """prep inputs documents (paragraphs) and IDs for CORENLP processing"""
    # read all csv_files
    csv_files = file_util.get_csv_files()
    # create list of QA and presentation dfs
    all_QA = []
    all_Presentation = []
    for call in tqdm(csv_files):
        call_df = pd.read_csv(call, index_col=0)
        # create call primary id as call_title_date
        call_df.insert(0, "call_title_date", call.stem)
        call_df.drop("Title", axis=1, inplace=True)
        if call_df.ROUND[0] == "QA":
            all_QA.append(call_df)
        else:
            all_Presentation.append(call_df)
    all_Presentation = pd.concat(all_Presentation, axis=0, ignore_index=True)
    all_QA = pd.concat(all_QA, axis=0, ignore_index=True)

    all_transcripts = pd.concat([all_QA, all_Presentation], axis=0, ignore_index=True)
    all_transcripts = all_transcripts.sort_values(
        ["call_title_date", "ROUND", "Paragraph"]
    )
    all_transcripts["Paragraph_ID"] = (
        all_transcripts["call_title_date"].astype(str)
        + "--"
        + all_transcripts["ROUND"].astype(str)
        + "--"
        + all_transcripts["Paragraph"].astype(str)
    )

    # only use US earnings calls (hand-collected and checked)
    cleaned_meta = pd.read_csv(Path(global_options.DATA_PATH, "meta_data_cleaned.csv"))
    cleaned_meta["call_title_date"] = (
        cleaned_meta["call_title"]
        + " "
        + pd.to_datetime(cleaned_meta["date_EST"]).dt.strftime("%Y-%m-%d")
    )
    cleaned_meta = cleaned_meta.drop_duplicates(
        subset=["call_title_date"]
    )  # make sure call_title_date is unique
    cleaned_meta["include_sample"] = 1
    cleaned_meta = cleaned_meta[["call_title_date", "include_sample"]]
    all_transcripts = all_transcripts.merge(cleaned_meta, on="call_title_date")
    return all_transcripts


def output_input(all_transcripts):
    Path(global_options.DATA_PATH, "text_corpra", "input").mkdir(
        parents=True, exist_ok=True
    )
    file_util.list_to_file(
        all_transcripts["Paragraph_ID"].tolist(),
        Path(global_options.DATA_PATH, "text_corpra", "input", "document_ids.txt"),
    )
    file_util.list_to_file(
        all_transcripts["text"].tolist(),
        Path(global_options.DATA_PATH, "text_corpra", "input", "documents.txt"),
    )


if __name__ == "__main__":
    all_transcripts = prep_inputs()
    output_input(all_transcripts)
