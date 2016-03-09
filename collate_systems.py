#!/usr/bin/env python

"""Print the text of answers generated by different systems."""
import argparse
import os

import pandas

RESPONSE_MARKUP = "responseMarkup"
ID = "id"
ANSWER = "Answer"
ANSWER_ID = "AnswerId"
CORRECT_ANSWER_ID = "CorrectAnswerId"
QUESTION = "Question"
CORRECT = "Correct"


def collate_qa_answers(corpus_file, system_files, names, truth_file):
    corpus = pandas.read_csv(corpus_file, encoding="utf-8")
    systems = [pandas.read_csv(system_file, encoding="utf-8") for system_file in system_files]
    # Get a mapping of answer Ids to answers from the corpus.
    corpus = corpus[[RESPONSE_MARKUP, ID]]
    corpus.rename(columns={RESPONSE_MARKUP: ANSWER, ID: ANSWER_ID}, inplace=True)
    systems = [pandas.merge(system, corpus, on=ANSWER_ID) for system in systems]
    # If we have truth add a column indicating whether the answer is correct.
    if truth_file is not None:
        truth = pandas.read_csv(truth_file, encoding="utf-8")
        truth.rename(columns={ANSWER_ID: CORRECT_ANSWER_ID}, inplace=True)
        systems = [correct_answer(system, truth) for system in systems]
    # Place each system beneath its own top-level multi-index.
    systems = [system.set_index(QUESTION) for system in systems]
    fs = []
    for name, system in zip(names, systems):
        system.columns = pandas.MultiIndex.from_tuples([(name, c) for c in system.columns])
        fs.append(system)
    # Join the results from the different systems into a single data frame.
    return reduce(lambda m, f: m.join(f), fs)


def correct_answer(system, truth):
    system = pandas.merge(system, truth, on=QUESTION)
    system[CORRECT] = system[ANSWER_ID] == system[CORRECT_ANSWER_ID]
    system.drop(CORRECT_ANSWER_ID, axis="columns", inplace=True)
    return system


def filter_systems(systems, sample, correct_systems, incorrect_systems):
    for correct_system in correct_systems:
        systems = systems[systems[correct_system]['Correct']]
    for incorrect_system in incorrect_systems:
        systems = systems[systems[incorrect_system]['Correct'] != True]
    if sample is not None:
        systems = systems.sample(n=sample)
    return systems


def systems_to_html(systems):
    system_names = systems.columns.levels[0]
    html_lines = ["<table border=1>"]
    html_lines.append("<th>Question</th>" + " ".join(["<th>%s</th>" % system_name for system_name in system_names]))
    questions = systems.index
    answer_rows = zip(*[systems[n]['Answer'] for n in system_names])
    for question, answer_row in zip(questions, answer_rows):
        s = " ".join(["<td>%s</td>" % field for field in ([question] + list(answer_row))])
        html_lines.append("<tr> %s </tr>" % s)
    html_lines.append("</table>")
    return "\n".join(html_lines).encode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=argparse.FileType(), help="corpus mapping answer to answer Id")
    parser.add_argument("systems", type=argparse.FileType(), nargs="+",
                        help="Results file generated by answer_questions.py")
    parser.add_argument("--names", type=str, nargs="+", help="system names")
    parser.add_argument("--truth", type=argparse.FileType(), help="truth file with correct answers")
    parser.add_argument("--correct", type=str, nargs="+", default=[], help="filter on these systems being correct")
    parser.add_argument("--incorrect", type=str, nargs="+", default=[], help="filter on these systems being incorrect")
    parser.add_argument("--format", choices=["csv", "html"], default="csv", help="output format, default csv")
    parser.add_argument("--sample", type=int, help="number of questions to sample, default all")
    args = parser.parse_args()

    if args.names is None:
        args.names = [os.path.basename(system.name) for system in args.systems]
    elif not len(args.names) == len(args.systems):
        parser.print_usage()
        parser.error("There must be a name for each system.")
    if args.truth is None and args.correct:
        parser.print_usage()
        parser.error("Must specify a truth file to filter on correctness.")

    systems = collate_qa_answers(args.corpus, args.systems, args.names, args.truth)
    systems = filter_systems(systems, args.sample, args.correct, args.incorrect)
    if args.format == "csv":
        # Read it back in with a command like the following:
        # pandas.read_csv(filename, encoding="utf-8", header=[0,1], index_col=0)
        print(systems.to_csv(encoding="utf-8"))
    else:  # args.format == "html"
        print(systems_to_html(systems))
