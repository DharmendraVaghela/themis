import numpy
import pandas

from themis import QUESTION, CORRECT, CsvFileType, IN_PURVIEW, ANSWER, CONFIDENCE, FREQUENCY

# Annotation Assist column names
QUESTION_TEXT = "Question_Text"
IS_IN_PURVIEW = "Is_In_Purview"
SYSTEM_ANSWER = "System_Answer"
ANNOTATION_SCORE = "Annotation_Score"


def roc_curve(judgements):
    """
    Plot a receiver operating characteristic (ROC) curve.

    :param judgements: data frame with confidence, in purview, correct, and frequency information
    :return: true positive rate, false positive rate, confidence thresholds
    """
    ts = confidence_thresholds(judgements, True)
    true_positive_rates = [true_positive_rate(judgements, t) for t in ts]
    false_positive_rates = [false_positive_rate(judgements, t) for t in ts]
    return true_positive_rates, false_positive_rates, ts


def true_positive_rate(judgements, t):
    correct = judgements[judgements[CORRECT]]
    true_positive = sum(correct[correct[CONFIDENCE] >= t][FREQUENCY])
    in_purview = sum(judgements[judgements[IN_PURVIEW]][FREQUENCY])
    return true_positive / float(in_purview)


def false_positive_rate(judgements, t):
    out_of_purview_questions = judgements[~judgements[IN_PURVIEW]]
    false_positive = sum(out_of_purview_questions[out_of_purview_questions[CONFIDENCE] >= t][FREQUENCY])
    out_of_purview = sum(judgements[~judgements[IN_PURVIEW]][FREQUENCY])
    return false_positive / float(out_of_purview)


def precision_curve(judgements):
    ts = confidence_thresholds(judgements, False)
    precision_values = [precision(judgements, t) for t in ts]
    attempted_values = [questions_attempted(judgements, t) for t in ts]
    return precision_values, attempted_values, ts


def precision(judgements, t):
    s = judgements[judgements[CONFIDENCE] >= t]
    correct = sum(s[s[CORRECT]][FREQUENCY])
    in_purview = sum(s[s[IN_PURVIEW]][FREQUENCY])
    return correct / float(in_purview)


def questions_attempted(judgements, t):
    s = judgements[judgements[CONFIDENCE] >= t]
    in_purview_attempted = sum(s[s[IN_PURVIEW]][FREQUENCY])
    total_in_purview = sum(judgements[judgements[IN_PURVIEW]][FREQUENCY])
    return in_purview_attempted / float(total_in_purview)


def confidence_thresholds(judgements, add_max):
    ts = judgements[CONFIDENCE].sort_values(ascending=False).unique()
    if add_max:
        ts = numpy.insert(ts, 0, numpy.Infinity)
    return ts


def collate_systems(test_set, systems, judgements):
    """
    Collate judged answers for different systems.

    :param test_set: questions and their frequencies
    :param systems: dictionary of system name to answers file
    :param judgements: human judgements of answer correctness, dataframe with (Answer, Correct) columns
    :return: collated dataframes of judged answers for all the systems
    """
    fs = []
    for name in systems:
        s = add_judgements_to_qa_pairs(systems[name], judgements)
        s.columns = pandas.MultiIndex.from_tuples([(name, c) for c in s.columns])
        fs.append(s)
    f = reduce(lambda m, f: m.join(f), fs)
    # Add frequency information from the test set.
    f = f.join(test_set.set_index(QUESTION))
    return f


def add_judgements_to_qa_pairs(system, judgements):
    # The Annotation Assist tool strips newlines, so remove them from the answer text in the system output as well.
    system[ANSWER] = system[ANSWER].str.replace("\n", "")
    system = system.set_index([QUESTION, ANSWER])
    judgements = judgements.set_index([QUESTION, ANSWER])
    system = system.join(judgements)
    return system.dropna()


class AnnotationAssistFileType(CsvFileType):
    def __init__(self):
        super(self.__class__, self).__init__([QUESTION_TEXT, IS_IN_PURVIEW, SYSTEM_ANSWER, ANNOTATION_SCORE],
                                             {QUESTION_TEXT: QUESTION, IS_IN_PURVIEW: IN_PURVIEW,
                                              SYSTEM_ANSWER: ANSWER})


def from_annotation_assist(annotation_assist_judgements, judgement_threshold):
    """
    Convert from the file format produced by
    `Annotation Assist <https://github.com/cognitive-catalyst/annotation-assist>`.

    :param annotation_assist_judgements: Annotation Assist file
    :param judgement_threshold: threshold above which an answer is deemed correct
    :return: dataframe with (Answer, Correct) columns
    """
    annotation_assist_judgements[IN_PURVIEW] = annotation_assist_judgements[IN_PURVIEW].astype("bool")
    annotation_assist_judgements[CORRECT] = annotation_assist_judgements[ANNOTATION_SCORE] >= judgement_threshold
    annotation_assist_judgements = annotation_assist_judgements.drop(ANNOTATION_SCORE, axis="columns")
    return annotation_assist_judgements[[QUESTION, ANSWER, IN_PURVIEW, CORRECT]]