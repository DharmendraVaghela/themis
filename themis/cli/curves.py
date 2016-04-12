"""
Generate and optionally draw precision and ROC curves.
"""
from themis import CsvFileType
from themis.annotate import add_judgments_and_frequencies_to_qa_pairs


def curves_command(parser, subparsers):
    curves_parser = subparsers.add_parser("curves", help="generate performance curves")
    curves_parser.add_argument("type", choices=["roc", "precision"], help="type of curve to create")
    curves_parser.add_argument("answers", type=CsvFileType(), nargs="+",
                               help="answers generated by one of the 'qa' commands")
    curves_parser.add_argument("judgments", type=CsvFileType(),
                               help="Q&A pair judgments generated by the 'judge interpret' command")
    curves_parser.add_argument("--labels", nargs="+", help="names of the Q&A systems")
    curves_parser.add_argument("--output", default=".", help="output directory")
    curves_parser.set_defaults(func=CurvesHandlerClosure(parser))


def curves_handler(parser, args):
    if args.labels is None:
        args.labels = [answers.filename for answers in args.answers]
    elif not len(args.answers) == len(args.labels):
        parser.print_usage()
        parser.error("There must be a name for each plot.")

    for label, answers in zip(args.labels, args.answers):
        data = add_judgments_and_frequencies_to_qa_pairs(answers, args.judgments, args.test_set)
        if args.type == "roc":
            pass
        else:
            pass


class CurvesHandlerClosure(object):
    def __init__(self, parser):
        self.parser = parser

    def __call__(self, args):
        curves_handler(self.parser, args)