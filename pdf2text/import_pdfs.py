""" 
Parse earnings call pdf to conversations
"""
import json
import re
from functools import partial
from io import StringIO
from multiprocessing import Pool
from pathlib import Path

import global_options
import pandas as pd
import pendulum
from bs4 import BeautifulSoup
from pdfminer import high_level
from pdfminer.layout import LAParams


class transcript:
    """a parser to transform a pdf transcript to structured conversation"""

    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.presentation_start_marker = """<span style="font-family: Verdana-Bold; font-size:24px">Presentation
<br></span></div>"""
        self.QA_start_marker = """<span style="font-family: Verdana-Bold; font-size:24px">Question and Answer
<br></span></div>"""
        self.End_marker = """<span style="font-family: Verdana; font-size:8px">These materials have been prepared solely for information purposes based upon information generally available to the public"""
        self.call_title = self.pdf_path.stem
        self.html = None
        self.firm_full_name, self.firm_name, self.ticker = [None] * 3
        (
            self.call_type,
            self.time_raw,
            self.date_EST,
            self.time_EST,
            self.call_participants,
            self.call_participants_titles,
            self.presentation_contents,
            self.QA_contents,
            self.presentation_contents_s,
            self.QA_contents_s,
        ) = [None] * 10

    def parse(self, html_dir=None, parse_contents=True):
        """the main parse function"""
        print(f"Parsing {self.call_title}")
        self.html = self.pdf_to_html(self.pdf_path, html_dir=html_dir)
        soup = BeautifulSoup(self.html, features="lxml")
        # parse firm name
        self.firm_full_name = self.soup2text(
            soup.find_all(
                "span",
                style=re.compile("font-family: Verdana-Bold; font-size:2[0|3]px"),
            )
        )
        firm_splited = self.firm_full_name.split()
        firm_name = []
        for token in firm_splited:
            if ":" in token:
                self.ticker = token
            else:
                firm_name.append(token)
        self.firm_name = " ".join(firm_name)

        self.call_type = self.soup2text(
            soup.find(
                "span",
                style=re.compile("font-family: Verdana-Bold; font-size:(25|30)px"),
            )
        )
        # parse date
        date_str = self.soup2text(
            soup.find(
                "span",
                style=re.compile("font-family: Verdana-Bold; font-size:1[7|8]px"),
            )
        )
        self.time_raw = date_str
        try:
            date_parsed = pendulum.parse(
                " ".join(date_str.split(",")[1:]), strict=False
            )
            self.time_EST = date_parsed.in_tz("EST").to_datetime_string()
            self.date_EST = date_parsed.in_tz("EST").to_date_string()
        except:
            print(f"{self.call_title}'s date: {date_str} cannot be parsed. ")
        self.parse_contents()

    def parse_contents(self):
        """parse the conversation contents"""
        # spilt the html by sections
        (
            before_presentation_html,
            presentation_html,
            QA_html,
        ) = self.seperate_presentation_QA()
        (
            self.call_participants,
            self.call_participants_titles,
        ) = self.get_call_participants(before_presentation_html)
        try:
            self.presentation_contents = self.soup2raw_content(
                BeautifulSoup(presentation_html, features="lxml")
            )
            self.presentation_contents_s = self.structure_content(
                self.presentation_contents
            )
            self.presentation_contents_s.insert(
                0, "Paragraph", range(len(self.presentation_contents_s))
            )
            self.presentation_contents_s.insert(0, "ROUND", "Presentation")
            self.presentation_contents_s.insert(0, "Title", self.call_title)
        except Exception as e:
            print(f"Unablet to parse presentation for {self.call_title}")
            print(e)
        try:
            self.QA_contents = self.soup2raw_content(
                BeautifulSoup(QA_html, features="lxml")
            )
            self.QA_contents_s = self.structure_content(self.QA_contents)
            self.QA_contents_s.insert(0, "Paragraph", range(len(self.QA_contents_s)))
            self.QA_contents_s.insert(0, "ROUND", "QA")
            self.QA_contents_s.insert(0, "Title", self.call_title)
        except Exception as e:
            print(f"Unablet to parse QA for {self.call_title}")
            print(e)

    def meta2dict(self):
        """output meta data of the call to a dict (for output csv)

        Returns:
            {str: str}
        """
        record = {
            "call_title": self.call_title,
            "firm_full_name": self.firm_full_name,
            "firm_name": self.firm_name,
            "ticker": self.ticker,
            "call_type": self.call_type,
            "date_EST": self.date_EST,
            "time_EST": self.time_EST,
            "time_raw": self.time_raw,
            "call_participants": json.dumps(self.call_participants),
            "call_participants_titles": json.dumps(self.call_participants_titles),
        }
        return record

    def seperate_presentation_QA(self) -> "str, str":
        """using the markers defined in the __init__ to sepearate html into presentation and QA sections (html)"""
        before_presentation_html, presentation_html, QA_html = "", "", ""
        if self.presentation_start_marker in self.html:
            # print("Presentation exists.")
            before_presentation_html = self.html.split(self.presentation_start_marker)[
                0
            ]
            after_presentation_html = self.html.split(self.presentation_start_marker)[1]
            if self.QA_start_marker in self.html:
                # print("QA exists.")
                presentation_html = after_presentation_html.split(self.QA_start_marker)[
                    0
                ]
                QA_html = after_presentation_html.split(self.QA_start_marker)[1].split(
                    self.End_marker
                )[0]
            else:
                print(f"!!!!! WARNING: {self.call_title} QA does not exist!")
                presentation_html = after_presentation_html.split(self.End_marker)[0]
        else:
            print(f"!!!!! WARNING: {self.call_title} presentation does not exist!")
        return before_presentation_html, presentation_html, QA_html

    def pdf_to_html(self, pdf_path, html_dir=None) -> "str (html)":
        """convert pdf file to html using pdfminer.six
        Args:
            pdf_path (str/Path): path to the pdf file
            html_dir (str, optional): where to save the html file. Defaults to "output/".

        Returns:
            str: html from pdfminer.six
        """
        output_string = StringIO()
        with open(pdf_path, "rb") as fin:
            high_level.extract_text_to_fp(
                fin,
                output_string,
                laparams=LAParams(boxes_flow=1),
                output_type="html",
                codec=None,
            )
        html_result = output_string.getvalue().strip()
        if html_dir is not None:
            Path(f"{html_dir}/{pdf_path.stem}.html").write_text(html_result)
        return html_result

    @staticmethod
    def soup2text(find_results):
        """return text from soup search results; handles None/find//find_all cases. If find_results is from find_all, then concat texts from all elements using whitespace."""
        if find_results is None:
            text = ""
        elif find_results.__class__.__name__ == "Tag":
            text = find_results.text.strip()
        else:
            text = " ".join([x.text.strip() for x in find_results])
        return text

    @staticmethod
    def soup2raw_content(a_soup) -> "[type (speaker/spearker_title/text), text]":
        """initial parse of the presentation/QA section into spearkers and content

        Returns:
            [(str, str)]: a list of tuples - (type (speaker/spearker_title/text), text)
        """
        content_spans = a_soup.find_all("span", style=re.compile(" font-size:10px"))
        contents = []
        last_span = ""
        for s in content_spans:
            if s["style"] == "font-family: Verdana-Bold; font-size:10px":
                speaker_type = "speaker"
            if s["style"] == "font-family: Verdana-Italic; font-size:10px":
                speaker_type = "speaker_title"
            if s["style"] == "font-family: Verdana; font-size:10px":
                speaker_type = "text"
            span_text = s.text.strip()
            if " | " not in span_text and span_text.upper() != span_text:
                if (
                    span_text[0].lower() == span_text[0]
                    and speaker_type == "text"
                    and span_text[0].isalnum()
                ):
                    # merge with last paragraph if starts with lower-case
                    del contents[-1]
                    contents.append((speaker_type, last_span + " " + span_text))
                else:
                    contents.append((speaker_type, span_text))
                    last_span = span_text
        return contents

    def structure_content(self, contents_raw):
        """parse text content into conversations

        Args:
            contents_raw ([(str, str)]):  Example:
            [('speaker', 'Operator'),
            ('text',
            'This concludes our question-and-answer session. I would like to turn the conference back over to Bill\nClancy for any closing remarks.'),
            ('speaker', 'William M. Clancy'),
            ('speaker_title', 'Executive VP, CFO & Corporate Secretary'),
            ('text',
            "Thank you. To summarize, for Q4, we were pleased with our book-to-bill, the performance of DSI, which\nis our newest addition to VPG, and the milestones we are achieving in our manufacturing and cost-\noptimization initiatives. I also want to note that in March, we'll be at the Sidoti Conference in New York. I\nwant to thank you for joining our call today, and we look forward to updating you on our next earnings call\nin May. Thank you very much."),
            ('speaker', 'Operator'),
            ('text',
            "The conference has now concluded. Thank you for attending today's presentation. You may now\ndisconnect.")]

        Returns:
            A DataFrame with the following cols:
                ['speaker', 'speaker_title', 'speaker_role', 'text']
        """
        contents_structured = []
        paragraph = {}
        current_speaker = ""
        current_speaker_title = ""
        for span_type, span_text in contents_raw:
            if span_type == "speaker":
                current_speaker = span_text.replace("\n", " ")
                current_speaker_title = ""
            if span_type == "speaker_title":
                current_speaker_title = span_text.replace("\n", " ")
            if span_type == "text":
                paragraph = {}
                paragraph["speaker"] = current_speaker
                paragraph["speaker_title"] = self.call_participants_titles.get(
                    current_speaker
                )
                paragraph["speaker_role"] = ""
                for role in self.call_participants.keys():
                    if current_speaker in self.call_participants[role]:
                        paragraph["speaker_role"] = role
                paragraph["text"] = span_text.replace("\n", " ")
                if "Operator Instructions" in paragraph["text"]:
                    paragraph["speaker"] = "Operator"
                    paragraph["speaker_title"] = ""
                    paragraph["speaker_role"] = ""
                contents_structured.append(paragraph)
        return pd.DataFrame.from_dict(contents_structured)

    def get_call_participants(self, before_presentation_html) -> "[str]":
        """get a list of call participants from html

        Returns : {str : [str]}, {str: str}
        (example):
            call_participants: {'EXECUTIVES': ['Alberto Zanata', 'Carlo Caroni', 'Fabio Zarpellon', 'Jacob Broberg', 'Philippe Zavattiero', 'Torsten Urban'], 'ANALYSTS': ['Björn Enarson', 'Erik Paulsson', 'Johan Eliason']}

            call_participants_titles: {'Alberto Zanata': 'Executive VP & Head of Professional Products', 'Carlo Caroni': '', 'Fabio Zarpellon': 'Chief Financial Officer of Electrolux Professional Products', 'Jacob Broberg': 'Senior VP of Investor Relations and Corporate Communication at Electrolux Professional AB', 'Philippe Zavattiero': 'Senior VP & GM for Europe - Electrolux Professional AG', 'Torsten Urban': 'Senior Vice President of Product & Marketing at Electrolux AB (publ)', 'Björn Enarson': 'Danske Bank Markets Equity Research', 'Erik Paulsson': 'Pareto Securities, Research Division', 'Johan Eliason': 'Kepler Cheuvreux, Research Division'}
        """
        # call participants
        participant_spans = BeautifulSoup(
            before_presentation_html, features="lxml"
        ).find_all("span", style=re.compile("font-size:10px"))
        call_participants_raw = []
        call_participants = {}
        call_participants_titles = {}
        PARTICIPANTS_TYPES = ["EXECUTIVES", "ANALYSTS", "ATTENDEES"]
        START_ADD_FLAG = 0
        span_text = ""
        for span in participant_spans:
            span_text = span.text.strip()
            if span_text == "EXECUTIVES":
                START_ADD_FLAG = 1
            if " | " in span_text and span_text.upper() == span_text:
                START_ADD_FLAG = 0
            if START_ADD_FLAG:
                call_participants_raw.append(span_text.replace("\n", " "))
                if span["style"] == "font-family: Verdana-Bold; font-size:10px":
                    if span_text in PARTICIPANTS_TYPES:
                        call_participants[span_text] = []
                        PARTICIPANTS_TYPES.remove(span_text)
                        TYPE = span_text
                    else:
                        name = span_text.replace("\n", " ")
                        title = ""
                        for sib in span.next_siblings:
                            if (
                                sib["style"]
                                == "font-family: Verdana-Italic; font-size:10px"
                            ):
                                title = sib.text.strip().replace("\n", " ")
                            if (
                                sib["style"]
                                == "font-family: Verdana-Bold; font-size:10px"
                            ):
                                title = ""
                                break
                        call_participants[TYPE].append(name)
                        call_participants_titles[name] = title
        return call_participants, call_participants_titles


def parse_single_pdf(pdf_path, out_dir, write_content=True, HTML_DIR=None):
    """parse single pdf and save conversation to csv file

    Args:
        pdf_path (str/path): path to the pdf file
        out_dir (str/pth): folder to save results, creates 2 sub-folders QA/presentations automatically

    Returns:
        [dict]: a list of meta data about each file
    """
    Path(out_dir, "QA").mkdir(parents=True, exist_ok=True)
    Path(out_dir, "presentation").mkdir(parents=True, exist_ok=True)

    a_transcript = transcript(pdf_path)
    a_transcript.parse(HTML_DIR)
    if write_content:
        try:
            if len(a_transcript.QA_contents_s) > 0:
                a_transcript.QA_contents_s.to_csv(
                    Path(
                        out_dir,
                        "QA",
                        f"{a_transcript.call_title} {a_transcript.date_EST}.csv",
                        index=False,
                    )
                )
        except:
            pass
        try:
            if len(a_transcript.presentation_contents_s) > 0:
                a_transcript.presentation_contents_s.to_csv(
                    Path(
                        out_dir,
                        "presentation",
                        f"{a_transcript.call_title} {a_transcript.date_EST}.csv",
                        index=False,
                    )
                )
        except:
            pass
    return a_transcript.meta2dict()


def parse_all_pdfs(**kwargs):
    INPUT_DIR = global_options.PDF_PATH
    OUT_DIR = global_options.PDF_PARSED_PATH
    pdf_files = list(Path(INPUT_DIR).glob("**/*.pdf"))
    with Pool(global_options.N_CORES) as p:
        meta_all = p.map(
            partial(parse_single_pdf, out_dir=OUT_DIR, **kwargs), pdf_files
        )
    # fix json representations
    meta_all = pd.DataFrame(meta_all)
    meta_all.call_participants = [
        json.dumps(eval(j)) for j in meta_all.call_participants
    ]
    meta_all.call_participants_titles = [
        json.dumps(eval(j)) for j in meta_all.call_participants_titles
    ]

    meta_all.to_csv(Path(global_options.DATA_PATH, "meta_data.csv"), index=False)


if __name__ == "__main__":
    parse_all_pdfs(write_content=True)
