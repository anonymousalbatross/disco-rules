import os
import re
import sys
import spacy
import stanza
from optparse import OptionParser
from LexLoader import LexiconLoader
from StringMatcher import StringMatcher
from tqdm import tqdm

SPACY_LANG_MAP = {
    'en': 'en_core_web_sm',
    # TODO: add more langs
}

LEX_MAP = {
    'czech': os.path.join('tests', 'czedlex_connective_lex.xml'),
    # TODO: add more langs
}

STANZA_SUPPORTED = {
    'czech',
    # TODO: add more langs!
}


def dump_ptb(sentences, outfile, lang):
    # TODO: https://stanfordnlp.github.io/stanza/constituency.html (unfortunately, lang support rather limited)
    pass


def dump_depparses_with_stringmatching(sentences, outfile, lang):

    if lang in STANZA_SUPPORTED:
        pipeline = stanza.Pipeline(lang=lang, processors='tokenize,mwt,pos,lemma,depparse', tokenize_pretokenized=True)
    else:
        models_url = 'https://stanfordnlp.github.io/stanza/available_models.html'
        sys.stderr.write(
            'ERROR: Lang "%s" not supported. Supported languages&models: %s.\n' % (lang, models_url))
        sys.exit()

    conllu_lines = ['# newdoc']
    for si, s in tqdm(enumerate(sentences), desc='Getting conllu attributes'):
        conllu_lines.append('# sent_id = %s' % str(si+1))
        doc = pipeline(' '.join(s))
        assert len(doc.sentences) == 1  # input is pe-sentencized, so if this is not 1, something is off
        for token in doc.sentences[0].tokens:
            # https://github.com/korpling/pepperModules-CoNLLModules
            tdict = token.to_dict()[0]
            _id = str(tdict['id'])
            text = token.text
            lemma = tdict['lemma']
            cpostag = '-'
            postag = tdict['upos']
            feats = '-'
            if 'feats' in tdict:
                feats = tdict['feats']
            head = str(tdict['head'])
            deprel = tdict['deprel']
            phead = '-'
            pdeprel = '-'
            line = [_id, text, lemma, cpostag, postag, feats, head, deprel, phead, pdeprel]
            conllu_lines.append('\t'.join(line))
        conllu_lines.append('')

    presegmented_text = '\n'.join([' '.join(t for t in s) for s in sentences])

    ll = LexiconLoader()
    if lang in LEX_MAP:
        connectives = ll.load_lexicon(LEX_MAP[lang])
    else:
        sys.stderr.write('ERROR: Lang "%s" not supported. Please check LEX_MAP.\n')
        sys.exit()
    sm = StringMatcher(lang, connectives)
    strict = False
    annotations, ambinfo_missing = sm.match(presegmented_text, strict)

    tempfile = open(outfile, 'w')
    to = 0
    for line in conllu_lines:
        if re.search(r'^\d+\t', line):
            token = line.split('\t')[1]
            # replace 4th column with connective annotation
            # (highjacking CPOSTAG, https://github.com/korpling/pepperModules-CoNLLModules/tree/master#usage)
            ann = '_'  # TODO: this overwrites the postag for all tokens! Find a way to include as extra feature, without deleting postags for all other tokens.
            for c in annotations:  # more efficient to hash annotations (dict from offset to conn), but since this whole
                # thing is offline anyway, will leave to future work
                for o in c['offsets']:
                    # TODO: This only marks connective. Sense info is available, think how to best add this to conllu
                    #  (dumping all possible senses is highly unreadable in most cases)
                    if o[0] == to:
                        ann = 'B-connective'
                    elif to > o[0] and to + len(token) <= o[1]:
                        ann = 'I-connective'
            line = '\t'.join(line.split('\t')[:4] + [ann] + line.split('\t')[5:])
            # making sure everyone is still on the same page/token (if this goes wrong, it means udpipe tokenized
            # differently. Work-around would then be to just go with udpipe tokenization from here on, instead of what
            # is fed as input to this method.)
            assert presegmented_text[to:to + len(token)] == token
            to += len(token) + 1
        tempfile.write(line + '\n')


def get_sents(inputfile, lang, sentencized, tokenized):
    txt = open(inputfile).read()
    sentences = []
    spacy_pipeline = False
    stanza_pipeline = False
    if not sentencized or not tokenized:
        if lang in SPACY_LANG_MAP:
            nlp = spacy.load(SPACY_LANG_MAP[lang], disable=['ner'])
            nlp.max_length = 10000000
            spacy_pipeline = True
        elif lang in STANZA_SUPPORTED:
            nlp = stanza.Pipeline(lang=lang, processors='tokenize,mwt,pos,lemma,depparse')
            nlp.max_length = 10000000  # might not work for stanza
            stanza_pipeline = True
    if sentencized:
        if tokenized:
            sentences = [[t for t in s.split()] for s in txt.split('\n')]
        else:
            sentences = [[t.text for t in nlp(s)] for s in txt.split('\n')]
    else:
        tempsents = []
        if spacy_pipeline:
            tempsents = [s for s in nlp(txt).sents]
        elif stanza_pipeline:
            tempsents = [s for s in nlp(txt).sentences]
        if tokenized:
            sentences = [[t for t in s.text.split()] for s in tempsents]
        else:
            sentences = [[t.text for t in s.tokens] for s in tempsents]

    return sentences


def main():
    parser = OptionParser()
    parser.add_option("-i", "--inputfile", dest="inputfile", help="file with plain text to process")
    parser.add_option("-o", "--outputfolder", dest="outputfolder", help="folder to dump output to")
    parser.add_option("-l", "--language", dest="language", help="language of input file")
    parser.add_option("-s", "--sentencized", action="store_true", dest="sentencized", default=False,
                      help="optional boolean flag to indicate input is one sentence per line (splitting on newlines "
                           "results in sentences)")
    parser.add_option("-t", "--tokenized", action="store_true", dest="tokenized", default=False,
                      help="optional boolean flag to indicate input is pretokenized (splitting on whitespace results "
                           "in tokens)")
    options, args = parser.parse_args()

    if options.inputfile is None or options.outputfolder is None or options.language is None:
        parser.print_help()
        sys.exit(1)

    sentences = get_sents(options.inputfile, options.language, options.sentencized, options.tokenized)
    if not os.path.exists(options.outputfolder):
        os.mkdir(options.outputfolder)

    conllu_out = os.path.join(options.outputfolder, os.path.splitext(os.path.basename(options.inputfile))[0] + '.conllu')
    dump_depparses_with_stringmatching(sentences, conllu_out, options.language)
    ptb_out = os.path.join(options.outputfolder, os.path.splitext(os.path.basename(options.inputfile))[0] + '.ptb')
    # dump_ptb(sentences, ptb_out, options.language)


if __name__ == '__main__':
    main()
