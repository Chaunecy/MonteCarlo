import re
import sys
from collections import defaultdict
from math import log2
from typing import TextIO, List, Tuple, Dict, Any, Set

from tqdm import tqdm

from bpcX.modelreader import read_bpe
from lib4mc.MonteCarloLIb import MonteCarloLib
from lib4mc.MonteCarloParent import MonteCarlo
from lib4mc.ProbLib import expand_2d, pick_expand, expand_1d

re_digits = re.compile(r"\d+")


def luds(pwd: str):
    struct = []
    prev_tag = ""
    t_len = 0
    cur_tag = " "
    for c in pwd:
        if c.isalpha():
            if c.isupper():
                cur_tag = "U"
            else:
                cur_tag = "L"
        elif c.isdigit():
            cur_tag = "D"
        else:
            cur_tag = "S"
        if cur_tag == prev_tag:
            t_len += 1
        else:
            if len(prev_tag) > 0:
                struct.append((prev_tag, t_len))
            prev_tag = cur_tag
            t_len = 1
    struct.append((cur_tag, t_len))
    return tuple(struct)

    pass


def count_luds(structures: Dict[str, float]) -> Dict[Any, Set]:
    skipped_list = []
    converts = defaultdict(set)
    for structure in structures:
        parsed_structure = []
        skip = False
        for tag, t_len in structure:
            parsed_structure.append((tag, t_len))
            if 'M' in tag:
                skip = True
        parsed_structure = tuple(parsed_structure)
        if skip:
            skipped_list.append(parsed_structure)
            continue
        converts[parsed_structure].add(parsed_structure)
    novels = defaultdict(set)
    print("Preprocess done!")
    for k in converts.keys():
        novels[len(k)].add(k)

    def the_same(struct_a, struct_b) -> bool:
        if sum([_len for _, _len in struct_a]) != sum([_len for _, _len in struct_b]):
            return False
        n_struct_a, n_struct_b = [], []
        for _tag, _len in struct_a:
            n_struct_a.extend([_tag] * _len)
        for _tag, _len in struct_b:
            n_struct_b.extend([_tag] * _len)
        for s_a, s_b in zip(n_struct_a, n_struct_b):
            if s_a != s_b and 'M' not in s_a and 'M' not in s_b:
                return False
        return True

    for skipped in tqdm(skipped_list[:100], desc="Refining: "):
        candidates = novels[len(skipped)]
        for candidate in candidates:
            if the_same(candidate, skipped):
                converts[candidate].add(skipped)
    return converts


class BpePcfgSim(MonteCarlo):
    def sample_one(self) -> (float, str):
        pwd = ""
        prob = .0
        p, struct = pick_expand(self.__grammars)
        prob += p
        for tag_len in struct:
            target_terminal = self.__terminals[tag_len]
            p, replacement = pick_expand(target_terminal)
            prob += p
            pwd += replacement
        return prob, pwd

    def sample(self, size: int = 100000) -> List[float]:
        results = []
        for _ in tqdm(iterable=range(size), desc="Sampling: "):
            prob, _ = self.sample_one()
            results.append(prob)
        return results

    def parse_file(self, testing_set: TextIO) -> List[Tuple[str, int, float]]:
        # for line in testing_set:
        #     pwd = line.strip("\r\n")
        #     prob = self.calc_minus_log_prob(pwd)
        #
        #     pass
        pass

    def calc_minus_log_prob(self, pwd: str) -> float:
        label = luds(pwd)
        candidate_structures = self.__converted.get(label, set())
        log_max = log2(sys.float_info.max)
        if len(candidate_structures) == 0:
            return log_max
        grammars, _, _ = self.__grammars
        results = []
        for candidate in candidate_structures:
            p = grammars.get(candidate)
            start = 0
            for tag, t_len in candidate:
                terminal, _, _ = self.__terminals.get((tag, t_len))
                replacement = pwd[start:start + t_len]
                start += t_len
                if replacement not in terminal:
                    p = log_max
                    break
                else:
                    p += terminal[replacement]
            results.append((candidate, p))
        min_minus_log_prob = min(results, key=lambda x: x[1])
        print(min_minus_log_prob[0], 2 ** (-min_minus_log_prob[1]))
        return min_minus_log_prob[1]

    def __init__(self, model_path: str):
        grammars, terminals = read_bpe(model_path=model_path)
        self.__grammars = expand_1d(grammars, minus_log_based=True)
        self.__terminals = expand_2d(terminals, minus_log_based=True)
        self.__converted = count_luds(grammars)
        pass


def test():
    bpePcfg = BpePcfgSim("/home/cw/Documents/tmp/model")
    samples = bpePcfg.sample()
    monte_carlo = MonteCarloLib(minus_log_prob_list=samples)
    mlp = bpePcfg.calc_minus_log_prob("12345678z")
    rank = monte_carlo.minus_log_prob2rank(mlp)
    print(rank)
    pass


if __name__ == '__main__':
    test()
