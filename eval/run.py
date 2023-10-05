import sys
import os
import re
import json
currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from LexLoader import LexiconLoader
from StringMatcher import StringMatcher


def get_token_offsets(txt):

    offsets2token = {}
    tokens = txt.split()
    offset = 0
    for i, t in enumerate(tokens):
        offsets2token[(offset, offset + len(t))] = i + 1  # +1 because token ids start at 1 in conllu
        offset += len(t) + 1  # +1 because of whitespace
    return offsets2token

def overlap(s1, s2):
    if s1[0] <= s2[0] and s1[1] >= s2[1]:
        return True
    elif s1[0] >= s2[0] and s1[1] <= s2[1]:
        return True

def run(xmlex, fname, lang):

    ll = LexiconLoader()
    connectives = ll.load_lexicon(xmlex)
    sm = StringMatcher(lang, connectives)
    strict = True
    lines = open(fname).readlines()

    # strip all existing annotations
    lines = [re.sub('Seg=[BI]-Conn', '_', x) for x in lines]

    ambinfo_missing = False

    for i, line in enumerate(lines):
        if re.search('^# text = ', line):
            text = re.sub('^# text = ', '', line)
            annotations, ambinfo_missing = sm.match(text, strict)
            offsets2token = get_token_offsets(text)
            mark_tokens = []
            for ann in annotations:
                for off in ann['offsets']:
                    for t in offsets2token:
                        if overlap(t, off):  # have to go with plain overlap, because tokenisation might differ
                            mark_tokens.append(offsets2token[t])
            for mt in mark_tokens:
                if mt-1 in mark_tokens:
                    lines[i+mt] = '\t'.join(lines[i+mt].split('\t')[:-1]) + '\t' + 'Seg=I-Conn\n'
                else:
                    lines[i + mt] = '\t'.join(lines[i + mt].split('\t')[:-1]) + '\t' + 'Seg=B-Conn\n'
    outname = os.path.splitext(fname)[0] + '_disco-stringmatcher-preds.conllu'
    outf = open(outname, 'w')
    for line in lines:
        outf.write(line)
    outf.close()

    if ambinfo_missing:
        sys.stderr.write('WARNING: Strict flag set to True, but one or more connectives do not have syntactic ambiguity information. Letting everything through (essentially defaulting to strict=False).\n')


def main():


    en_text = r"..\..\sharedtask2023\data\eng.pdtb.pdtb\eng.pdtb.pdtb_test.conllu"
    en_xml = r"..\tests\eng-dimlex.xml"
    run(en_xml, en_text, 'en')

  

if __name__ == '__main__':
    main()
