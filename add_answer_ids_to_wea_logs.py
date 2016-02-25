#!/usr/bin/env python

"""Look up answer Ids matching the top answer text and add them to the WEA logs.
The mapping from answer text to answer Id is taken from the corpus file extracted by get_paus.py.
Optionally search for PAU ids inserted into the TopAnswerText field, because XMGR sometimes does that."""
import argparse
import logging
import re

import pandas

logger = logging.getLogger(__name__)

ID = "id"
RESPONSE_MARKUP = "responseMarkup"
ANSWER_ID = "AnswerId"
TOP_ANSWER_TEXT = "TopAnswerText"


def wea_answers(wea_file, corpus_file, id_in_text, n):
    wea = pandas.read_csv(wea_file, nrows=n, encoding="utf-8")
    corpus = pandas.read_csv(corpus_file, usecols=[ID, RESPONSE_MARKUP], encoding="utf-8")
    corpus.rename(columns={ID: ANSWER_ID, RESPONSE_MARKUP: TOP_ANSWER_TEXT}, inplace=True)
    merged = pandas.merge(wea, corpus, on=TOP_ANSWER_TEXT).dropna(subset=["QuestionText"])
    # Some WEA logs have the PAU id written into the TopAnswerText column instead of the PAU text for some answers.
    if id_in_text:
        merged[ANSWER_ID] = merged[ANSWER_ID].combine_first(wea.apply(lambda row: get_answer_id_from_answer_text(row)))
    logger.info("%d questions, %d questions with answer ids" % (len(merged), merged[ANSWER_ID].count()))
    return merged


def get_answer_id_from_answer_text(row):
    answer_id = None
    # PAUId - PAU Title
    m = re.match("(\w+) - .*", row["TopAnswerText"])
    if m:
        answer_id = m.group(1)
    return answer_id


def configure_logger(level, format):
    logger.setLevel(level)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter(format))
    logger.addHandler(h)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wea_file", metavar="wea", type=argparse.FileType(), help="QuestionsData.csv from the WEA logs")
    parser.add_argument("corpus_file", metavar="corpus", type=argparse.FileType(),
                        help="corpus as generated by get_paus.py")
    parser.add_argument("--id-in-text", action="store_true", default=False, help="Read PAU ids from the TopAnswerText")
    parser.add_argument("--n", type=int, help="load first N rows, default load all")
    parser.add_argument('--log', type=str, default="ERROR", help="logging level")
    args = parser.parse_args()

    configure_logger(args.log.upper(), "%(asctime)-15s %(message)s")
    answers = wea_answers(args.wea_file, args.corpus_file, args.id_in_text, args.n)
    print(answers.to_csv(encoding="utf-8", index=False))
