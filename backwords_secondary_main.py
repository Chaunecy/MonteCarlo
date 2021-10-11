"""
This file is the portal of secondary training for backwords
"""
import argparse
import random
import sys

from backwords.backwords_secondary_trainer import backwords_counter
from backwords_secondary_simulator import BackWordsSecondaryMonteCarlo
from lib4mc.MonteCarloLib import MonteCarloLib


def secondary_cracker(backwords, words, config, guess_number_threshold, **kwargs):
    nwords_dict, _words = backwords_counter(
        nwords_list=kwargs['training'], splitter=kwargs['splitter'], start_chr=config['start_chr'],
        end_chr=config['end_chr'],
        start4words=kwargs['start4words'], step4words=kwargs['skip4words'], max_gram=kwargs['max_gram'],
        nwords_dict=backwords, words=words)
    # config['training_list'].append(kwargs['training'].name)
    # if kwargs['training']
    backword_mc = BackWordsSecondaryMonteCarlo((nwords_dict, _words, config), max_iter=kwargs['max_iter'])
    ml2p_list = backword_mc.sample(size=kwargs['size'])
    mc = MonteCarloLib(ml2p_list)
    scored_testing = backword_mc.parse_file(kwargs['testing'])
    gc = mc.ml2p_iter2gc(minus_log_prob_iter=scored_testing)
    secondary_training = []
    for pwd, _, num, gn, _, _ in gc:
        if gn <= guess_number_threshold:
            secondary_training.extend([pwd] * num)
    secondary_sample_size = kwargs['secondary_sample']
    if secondary_sample_size < len(secondary_training):
        print(f"We sample {secondary_sample_size} passwords to perform secondary training in the next round",
              file=sys.stderr)
        secondary_training = random.sample(secondary_training, kwargs['secondary_sample'])
    return nwords_dict, _words, config, secondary_training


def wrapper():
    cli = argparse.ArgumentParser('Backwords secondary main')
    cli.add_argument("-i", "--training", dest="training", type=argparse.FileType('r'), required=True,
                     help="The training file, each password a line")
    cli.add_argument("-t", "--testing", dest="testing", type=argparse.FileType('r'), required=True,
                     help="The testing file, each password a line")
    cli.add_argument("-g", "--guess-number-thresholds", dest="guess_number_thresholds", type=int, nargs="+",
                     help="Each threshold refers to a guess number threshold. "
                          "The model will crack passwords under the threshold "
                          "and use the cracked passwords as secondary training file")
    cli.add_argument("--size", dest="size", type=int, required=False, default=100000, help="sample size")
    cli.add_argument("--secondary-sample", dest="secondary_sample", type=int, required=False, default=-1,
                     help="use some of the cracked passwords for secondary training. set -1 to use all.")
    cli.add_argument("--splitter", dest="splitter", type=str, required=False, default="empty",
                     help="how to divide different columns from the input file, "
                          "set it \"empty\" to represent \'\', \"space\" for \' \', \"tab\" for \'\t\'")
    cli.add_argument("--start4word", dest="start4words", type=int, required=False, default=0,
                     help="start index for words, to fit as much as formats of input. An entry per line. "
                          "We get an array of words by splitting the entry. "
                          "\"start4word\" is the index of the first word in the array")
    cli.add_argument("--skip4word", dest="skip4words", type=int, required=False, default=1,
                     help="there may be other elements between words, such as tags. "
                          "Set skip4word larger than 1 to skip unwanted elements.")
    cli.add_argument("--max-gram", dest="max_gram", required=False, type=int, default=256, help="max gram")
    cli.add_argument("--threshold", dest="threshold", required=False, type=int, default=10,
                     help="grams whose frequencies less than the threshold will be ignored")
    cli.add_argument("--max-iter", dest="max_iter", required=False, default=10 ** 20, type=int,
                     help="max iteration when calculating the maximum probability of a password")
    args = cli.parse_args()
    splitter_map = {'empty': '', 'space': ' ', 'tab': '\t'}
    if args.splitter.lower() in splitter_map:
        args.splitter = splitter_map[args.splitter.lower()]
    start_chr, end_chr, training_list = '\x03', '\x00', []
    config = {'start_chr': start_chr, 'end_chr': end_chr, 'max_gram': args.max_gram, 'threshold': args.threshold,
              'training_list': training_list}
    backwords, words = None, None
    training = args.training
    for guess_number_threshold in args.guess_number_thresholds:
        backwords, words, config, training = secondary_cracker(
            backwords, words, config=config,
            guess_number_threshold=guess_number_threshold,
            training=training, splitter=args.splitter,
            start4words=args.start4words, skip4words=args.skip4words,
            max_gram=args.max_gram, size=args.size, max_iter=args.max_iter,
            testing=args.testing,
        )
        pass
    pass
