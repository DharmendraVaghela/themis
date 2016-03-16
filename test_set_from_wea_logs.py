#!/usr/bin/env python

"""Extract a test set from the augmented WEA logs generated by process_wea_logs.py.
This returns a CSV with two columns: Question and Frequency, where the latter counts the number of times a question
appears in a test set.
The test set may optionally be restricted to just those questions that elicited an answer from the WEA Q&A system.
The test set may also be sampled to any size.
The distribution of questions in a sample will match that in the full set extracted from the logs.
"""
import argparse
import logging

import pandas

logger = logging.getLogger(__name__)

QUESTION = "Question"
QUESTION_TEXT = "QuestionText"
ANSWER_ID = "AnswerId"
FREQUENCY = "Frequency"


def create_test_set(questions_data_file, answer_id_required, sample, seed, limit):
    test_set = pandas.read_csv(questions_data_file, usecols=[QUESTION_TEXT, ANSWER_ID], encoding="utf-8", nrows=limit)
    logger.info("%d questions" % len(test_set))
    test_set.rename(columns={QUESTION_TEXT: QUESTION}, inplace=True)
    # Optionally only retain questions that were mapped to an answer ID.
    if answer_id_required:
        test_set = test_set[test_set[ANSWER_ID].notnull()]
        logger.info("%d questions with answers" % len(test_set))
    # Optionally sample. Questions may be duplicated in the logs, so random sampling with replacement returns questions
    # with the same distribution.
    if sample is not None:
        test_set = test_set.sample(n=sample, replace=True, random_state=seed)
    # Write the frequency with which each question appears in a Frequency column while making all the values in the
    # Question column unique.
    test_set = pandas.merge(test_set.drop_duplicates(QUESTION),
                            test_set.groupby(QUESTION).size().to_frame(FREQUENCY).reset_index())
    test_set.sort([FREQUENCY, QUESTION], ascending=[False, True], inplace=True)
    logger.info("%d unique questions" % len(test_set))
    return test_set[[QUESTION, FREQUENCY]]


def configure_logger(level, format):
    logger.setLevel(level)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter(format))
    logger.addHandler(h)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wea_logs", metavar="wea", type=argparse.FileType(), help="WEA logs with answer ID column")
    parser.add_argument("--answer-id-required", action="store_true", default=False,
                        help="Only retain questions that have an answer id")
    parser.add_argument("--sample", type=int, help="sample size")
    parser.add_argument("--seed", type=int, help="sample random seed")
    parser.add_argument("--limit", metavar="N", type=int, help="only load first N questions from the logs")
    parser.add_argument("--log", type=str, default="ERROR", help="logging level")
    args = parser.parse_args()

    if args.sample is None and args.seed is not None:
        parser.print_usage()
        parser.error("Random seed is only used with sampling")

    configure_logger(args.log.upper(), "%(asctime)-15s %(message)s")
    questions = create_test_set(args.wea_logs, args.answer_id_required, args.sample, args.seed, args.limit)
    print(questions.to_csv(encoding="utf-8", index=False))
