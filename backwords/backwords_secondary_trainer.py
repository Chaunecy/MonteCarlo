"""
Backoff words
"""
import re
import sys
from collections import defaultdict
from typing import TextIO, Dict, Tuple, List, Union

from tqdm import tqdm

from lib4mc.FileLib import wc_l


def parse_line(line: str, splitter: str, start4words: int, step4words: int):
    line = line.strip("\r\n")
    if splitter == '':
        return list(line)
    items = re.split(splitter, line)
    words = items[start4words:len(items):step4words]
    return words


def backwords_counter(nwords_list: TextIO, splitter: str, start_chr: str, end_chr: str,
                      start4words: int, step4words: int, max_gram: int, threshold: int,
                      nwords_dict: Dict[Tuple, Dict[str, int]] = None,
                      words: Dict[str, int] = None):
    if nwords_dict is None:
        nwords_dict: Dict[Tuple, Dict[str, int]] = {}
        words: Dict[str, int] = {}
    zero = tuple()
    if isinstance(nwords_list, list):
        line_num = len(nwords_list)
    else:
        line_num = wc_l(nwords_list)
    if line_num == 0:
        print("No passwords for training, early return!", file=sys.stderr)
        return nwords_dict, words
    section_dict = defaultdict(lambda: defaultdict(int))
    actual_max_gram = 2
    for line in tqdm(nwords_list, total=line_num, desc="Reading: "):  # type: str
        line = line.strip("\r\n")
        sections = [start_chr]
        sections.extend(parse_line(line, splitter, start4words, step4words))
        sections.append(end_chr)
        for sec in sections:
            if sec not in words:
                words[sec] = 0
            words[sec] += 1
            if sec not in {start_chr}:
                if zero not in nwords_dict:
                    nwords_dict[zero] = {}
                if sec not in nwords_dict[zero]:
                    nwords_dict[zero][sec] = 0
                nwords_dict[zero][sec] += 1

        section_dict[len(sections)][tuple(sections)] += 1
        if len(sections) > actual_max_gram:
            actual_max_gram = len(sections)
    pass

    for n in tqdm(range(2, min(max_gram, actual_max_gram) + 1), desc="N-Gram: "):
        tmp_nwords_dict: Dict[Tuple, Dict[str, int]] = {}
        for sec_len, sec_len_dict in section_dict.items():
            if sec_len < n:
                continue
            order = n - 1
            for sec, cnt in sec_len_dict.items():
                for i in range(0, sec_len - order):
                    prefix = sec[i:i + order]
                    transition = sec[i + order]

                    if prefix not in tmp_nwords_dict:
                        tmp_nwords_dict[prefix] = {}
                    if transition not in tmp_nwords_dict[prefix]:
                        tmp_nwords_dict[prefix][transition] = 0
                    tmp_nwords_dict[prefix][transition] += cnt
                pass
            pass
        if len(tmp_nwords_dict) == 0:
            break
        """
        NOTION: Here I assume that we only supply the cracked passwords as secondary training file.
                According to the assumption above, the model will first remove transitions whose appearance 
                is less than threshold. Therefore, the cracked passwords will never contain the removed transitions.
                As a result, we can remove these transitions early to save memory.
        """
        for prefix, transitions in tmp_nwords_dict.items():

            if prefix not in nwords_dict:
                if any([cnt >= threshold for cnt in transitions.values()]):
                    nwords_dict[prefix] = transitions
                continue
            origin = nwords_dict[prefix]
            for trans, v in transitions.items():
                if trans not in origin:
                    origin[trans] = 0
                origin[trans] += v
        pass
    return nwords_dict, words


def freq2prob(nwords_dict: Dict[Tuple, List[Union[Dict[str, int], int]]], threshold: int) -> Dict:
    nwords_float_dict: Dict[Tuple, Dict[str, float]] = {}
    for prefix, trans_cnt in sorted(nwords_dict.items(), key=lambda x: len(x[0])):
        total = sum(trans_cnt.values())
        trans_prob = {trans: cnt / total for trans, cnt in trans_cnt.items() if cnt >= threshold}
        if len(trans_prob) == 0:
            # all transitions are ignored
            # because their frequencies are less than the threshold
            continue

        if len(trans_prob) < len(trans_cnt) and len(prefix) > 0:
            # some transitions are ignored
            # continue when prefix is empty, it occurs when the training file is too small
            missing = 1.0 - sum(trans_prob.values())
            parent_prefix = prefix[1:]
            for trans, p in nwords_float_dict[parent_prefix].items():
                trans_prob[trans] = trans_prob.get(trans, .0) + p * missing
        nwords_float_dict[prefix] = trans_prob

    return nwords_float_dict
