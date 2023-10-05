"""
This assumes the PDiT (we've used the 3.0 version for our experiments) to be in this same folder.
https://ufal.mff.cuni.cz/pdit3.0 (https://lindat.mff.cuni.cz/repository/xmlui/handle/11234/1-4875)
Unzip that folder, this script assumes the following folder structure:
- PDiT_3.0
  - data
    - column
    - pml
    - resources
It's using the PDTB column format (data/column folder) for evaluation.
TODO: document all of this in a proper README.md
"""

import os
import re
import sys
import csv
import json
currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from LexLoader import LexiconLoader
from StringMatcher import StringMatcher
from tqdm import tqdm
from collections import defaultdict


def evaluate(dump_falses=False):

    column_folder = os.path.join('PDiT_3.0', 'data', 'column')
    pred_folder = os.path.join(column_folder, 'pred')
    gold_folder = os.path.join(column_folder, 'gold')
    raw_folder = os.path.join(column_folder, 'raw')
    tp = 0
    fp = 0
    fn = 0
    if dump_falses:
        mffps = defaultdict(int)
        false_positives = open('false_positives.txt', 'w', encoding='utf8')
        false_negatives = open('false_negatives.txt', 'w', encoding='utf8')
        true_positives = open('true_positives.txt', 'w', encoding='utf8')
        most_freq_fps = open('most_frequent_false_positives.txt', 'w', encoding='utf8')
    for subfolder in os.listdir(pred_folder):
        ap_pred = os.path.join(pred_folder, subfolder)
        ap_gold = os.path.join(gold_folder, subfolder)
        ap_raw = os.path.join(raw_folder, subfolder)
        for f in os.listdir(ap_gold):
            goldf = csv.reader(open(os.path.join(ap_gold, f), encoding='utf8'), delimiter='|')
            predf = json.load(open(os.path.join(ap_pred, f+'.json'), encoding='utf8'))
            rawtext = open(os.path.join(ap_raw, f), encoding='utf8').read()
            gold_offsets = []
            for row in goldf:
                if row[0] == 'Explicit':
                    offsets = []
                    for pair in row[1].split(';'):
                        if pair:  # 01/ln94204_150 contains empty row
                            offsets.append(tuple([int(i) for i in pair.split('..')]))
                    # adding discontinuous ones as separate tuples here, meaning that they don't have to occur together to be scored
                    for tu in offsets:
                        gold_offsets.append(tu)
            pred_offsets = []
            for conn in predf:
                offsets = []
                for item in conn['offsets']:
                    offsets.append(tuple(item))
                # adding discontinuous ones as separate tuples here, meaning that they don't have to occur together to be scored
                for tu in offsets:
                    pred_offsets.append(tu)
            for ann in set(pred_offsets).union(set(gold_offsets)):
                if re.match(r'\W+', rawtext[ann[0]:ann[1]]):  # skipping hyphen-only instances. Seems like this is not annotated consistently, as skipping them also increases recall...
                    continue
                elif rawtext[ann[0]:ann[1]] in ['s', 'to', 'ne']:
                    conn = rawtext[ann[0]:ann[1]]  # for debugging purposes...
                    continue
                if ann in gold_offsets:
                    if ann in pred_offsets:
                        tp += 1
                        left = re.sub('\n', '', rawtext[max(0, ann[0] - 100):ann[0]])
                        left = left.rjust(100)
                        conn = rawtext[ann[0]:ann[1]].center(10)
                        right = re.sub('\n', '', rawtext[ann[1]:min(ann[1] + 100, len(rawtext) - 1)])
                        right = right.ljust(100)
                        true_positives.write(left + ' +++ ' + conn + ' +++ ' + right + '\n')
                    else:
                        fn += 1
                        if dump_falses:
                            left = re.sub('\n', '', rawtext[max(0, ann[0] - 100):ann[0]])
                            left = left.rjust(100)
                            conn = rawtext[ann[0]:ann[1]].center(10)
                            right = re.sub('\n', '', rawtext[ann[1]:min(ann[1] + 100, len(rawtext) - 1)])
                            right = right.ljust(100)
                            false_negatives.write(left + ' +++ ' + conn + ' +++ ' + right + '\n')
                elif ann in pred_offsets:
                    fp += 1
                    if dump_falses:
                        left = re.sub('\n', '', rawtext[max(0, ann[0] - 100):ann[0]])
                        left = left.rjust(100)
                        conn = rawtext[ann[0]:ann[1]].center(10)
                        right = re.sub('\n', '', rawtext[ann[1]:min(ann[1] + 100, len(rawtext) - 1)])
                        right = right.ljust(100)
                        false_positives.write(left + ' +++ ' + conn + ' +++ ' + right + '\n')
                        mffps[rawtext[ann[0]:ann[1]]] += 1
    if dump_falses:
        for pair in sorted(mffps.items(), key=lambda x: x[1], reverse=True):
            most_freq_fps.write('%s\t%i\n' % (pair[0], pair[1]))

    p = 0
    if tp + fp > 0:
        p = tp / (tp + fp)
    r = 0
    if tp + fn > 0:
        r = tp / (tp + fn)
    f = 0
    if p + r > 0:
        f = 2 * ((p * r) / (p + r))
    print('precision:', p)
    print('   recall:', r)
    print('       f1:', f)


def predict():

    ll = LexiconLoader()
    connectives = ll.load_lexicon('czedlex1.0-basic.xml')
    sm = StringMatcher('czech', connectives, os.path.join('..', 'rules', 'cz_dummy.yaml'))
    column_folder = os.path.join('PDiT_3.0', 'data', 'column')
    pred_folder = os.path.join(column_folder, 'pred')
    if not os.path.exists(pred_folder):
        os.mkdir(pred_folder)
    raw_folder = os.path.join(column_folder, 'raw')
    for subfolder in tqdm(os.listdir(raw_folder), desc='Predicting input folders'):
        ap_subfolder = os.path.join(raw_folder, subfolder)
        if not os.path.exists(os.path.join(pred_folder, subfolder)):
            os.mkdir(os.path.join(pred_folder, subfolder))
        for infile in os.listdir(ap_subfolder):
            txt = open(os.path.join(ap_subfolder, infile), encoding='utf8').read()
            results, ambinfo_missing = sm.match(txt, False)
            json.dump(results, open(os.path.join(pred_folder, subfolder, infile+'.json'), 'w', encoding='utf8'), indent=2, ensure_ascii=False)


def main():

    predict()
    dump_falses = True
    evaluate(dump_falses)


if __name__ == '__main__':
    main()
