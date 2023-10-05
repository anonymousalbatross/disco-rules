import LexLoader
import itertools
import stanza
import spacy
import yaml
import re

SPACY_LANGMAP = {
    'en': 'en_core_web_sm',
    'de': 'de_core_news_sm',
    'zh': 'zh_core_web_sm',
    'nl': 'nl_core_news_sm',
    'fr': 'fr_core_news_sm',
    'it': 'it_core_news_sm',
    'pt': 'pt_core_news_sm',
    'ru': 'ru_core_news_sm',
    'es': 'es_core_news_sm',
    'uk': 'uk_core_news_sm',
    'xx': 'xx_sent_ud_sm'
}

STANZA_SUPPORTED = {
    'czech',
    # TODO: add more langs!
}


class StringMatcher:

    def __init__(self, lang, connectives, rules=False):
        self.connectives = connectives
        self.spacy_pipeline = False
        self.stanza_pipeline = False
        self.rules = {}
        self.offsets2tokeninfo = {}
        if lang in SPACY_LANGMAP:
            self.nlp = spacy.load(SPACY_LANGMAP[lang], disable=['ner'])
            self.nlp.max_length = 10000000
            self.spacy_pipeline = True
        elif lang in STANZA_SUPPORTED:
            self.nlp = stanza.Pipeline(lang=lang, processors='tokenize,mwt,pos,lemma,depparse')
            self.stanza_pipeline = True
        else:
            self.nlp = spacy.load(SPACY_LANGMAP['xx'], disable=['ner'])
            self.nlp.max_length = 10000000
            self.spacy_pipeline = True
        self.max_sent_dist = 3  # discontinuous connectives can have this as their max sentence distance

        if rules:
            self.rules = yaml.safe_load(open(rules))

    def match(self, input_text, strict=False):
        self.offsets2tokeninfo = {}
        if self.spacy_pipeline:
            t2sid = {}
            doc = self.nlp(input_text)
            for sid, sent in enumerate(doc.sents):
                for token in sent:
                    t2sid[token] = sid
            for stoken in doc:
                lemma = stoken.lemma_
                deprel = stoken.dep_
                upos = stoken.pos_
                self.offsets2tokeninfo[(stoken.idx, stoken.idx + len(stoken.text))] = {'id': stoken.i,
                                                                                       'text': stoken.text,
                                                                                       'sid': t2sid[stoken],
                                                                                       'lemma': lemma,
                                                                                       'deprel': deprel,
                                                                                       'upostag': upos,
                                                                                       'head': stoken.head,
                                                                                       'feats': stoken.morph.to_dict()}

        elif self.stanza_pipeline:
            doc = self.nlp(input_text)
            offsets2sid = {}
            stokens = []
            for sid, sent in enumerate(doc.sentences):
                for token in sent.tokens:
                    offsets2sid[(token.start_char, token.end_char)] = sid
                    stokens.append(token)
            for stoken in stokens:
                stoken_dict = stoken.to_dict()[0]
                lemma = stoken_dict['lemma'] if 'lemma' in stoken_dict else stoken.text
                deprel = stoken_dict['deprel'] if 'deprel' in stoken_dict else 'UNK'
                upos = stoken_dict['upos'] if 'upos' in stoken_dict else 'UNK'
                head = stoken_dict['head'] if 'head' in stoken_dict else stoken.id
                feats_str = stoken_dict['feats'] if 'feats' in stoken_dict else 'UNK'
                feats = {x.split('=')[0]: x.split('=')[1] for x in feats_str.split('|') if feats_str != 'UNK'}
                self.offsets2tokeninfo[(stoken.start_char, stoken.end_char)] = {'id': stoken.id,
                                                                                'text': stoken.text,
                                                                                'sid': offsets2sid[(stoken.start_char, stoken.end_char)],
                                                                                'lemma': lemma,
                                                                                'deprel': deprel,
                                                                                'upostag': upos,
                                                                                'head': head,
                                                                                'feats': feats}

        # making sure this is sorted by character offset
        self.offsets2tokeninfo = {k: v for k, v in sorted(self.offsets2tokeninfo.items(), key=lambda x: x[0][0])}

        ambinfo_missing_warning = False
        annotations = []
        for c in self.connectives:
            if strict and not c.has_ambinfo():
                ambinfo_missing_warning = True
            for orth in c.get_orths():
                if not c.is_discontinuous() and orth[0] and len(orth[0].split()) == 1:  # single token
                    matches = []
                    if re.search(r'\w', orth[0]):
                        matches = re.finditer(r'\b%s\b' % orth[0], input_text, re.IGNORECASE)
                    else:  # for Czech for example, a plain hyphen (-) is a connective. The regex with word boundaries doesn't work then, so skipping word boundaries for such cases.
                        matches = re.finditer(r'%s' % orth[0], input_text, re.IGNORECASE)
                    for m in matches:
                        d = {
                            'canonical_connective': c.canonical,
                            'surface_form': input_text[m.start():m.end()],
                            'offsets': [(m.start(), m.end())],
                            'senses': c.get_senses()
                        }
                        if c.canonical in self.rules:
                            # TODO: test valid_match for spacy pipeline (only tested for stanza for now)
                            if not self.valid_match(c.canonical, (m.start(), m.end())):
                                continue
                        if strict and c.has_ambinfo():
                            if not c.is_ambiguous():
                                annotations.append(d)
                        else:
                            annotations.append(d)
                else:
                    # note that this assumes that all lexicons whitespace-split phrasal connectives.
                    # also, it only works for discontinuous connectives if they have max 2 parts. Are there lexicons/languages that
                    # have discontinuous connectives with three or more parts?
                    tokens = []#orth[0].split()
                    for o in orth:
                        if o:
                            tokens.extend(o.split())
                    discont = c.is_discontinuous()
                    candidates = StringMatcher.get_consecutive_token_matches(tokens, input_text, discont)
                    if candidates:
                        prefinal_matches = []
                        if discont:
                            for cand in candidates:
                                if self.within_bounds(cand):
                                    prefinal_matches.append(cand)
                        else:
                            prefinal_matches = candidates
                        if prefinal_matches:
                            # final check: if multiple matches at this point, take the one of which the items are closest together
                            final = StringMatcher.filter_verified_matches(prefinal_matches)
                            if discont:
                                offsets = [(x.start(), x.end()) for x in final]
                                # TODO: nicer to get consecutive blocks here
                            else:
                                offsets = [(final[0].start(), final[-1].end())]
                            d = {
                                'canonical_connective': c.canonical,
                                'surface_form': input_text[offsets[0][0]:offsets[0][1]],
                                'offsets': offsets,
                                'senses': c.get_senses()
                            }
                            if strict:
                                if not c.is_ambiguous():
                                    annotations.append(d)
                            else:
                                annotations.append(d)

        #if ambinfo_missing_warning:
            #sys.stderr.write('WARNING: Strict flag set to True, but one or more connectives do not have syntactic ambiguity information. Letting everything through (essentially defaulting to strict=False).\n')
        unannotations = {tuple(x['offsets']): x for x in annotations}
        annotations = [v for k, v in unannotations.items()]
        return sorted(annotations, key=lambda x: x['offsets'][0][0]), ambinfo_missing_warning

    def valid_match(self, canonical, offsets):
        for elem in self.rules[canonical]:
            # TODO: get rid of hardcoding rule names/labels. Move to some config file instead!
            if elem == 'skip':
                if self.offsets2tokeninfo[offsets]['lemma'] in self.rules[canonical][elem]:
                    return False
            elif elem == 'prev_token_one_of':
                if 'canonical_only' in self.rules[canonical]:
                    if self.offsets2tokeninfo[offsets]['text'].lower() != canonical:
                        continue
                conn_pos = [i for i, item in enumerate(self.offsets2tokeninfo.items()) if item[0] == offsets][0]
                left_neighbour = None
                if conn_pos > 0:
                    left_neighbour = list(self.offsets2tokeninfo.items())[conn_pos - 1][1]
                if left_neighbour:
                    if left_neighbour['lemma'] in self.rules[canonical][elem]:
                        return True
            elif elem == 'is_finite_verb_conjunction':
                if self.stanza_pipeline:
                    if self.is_finite_verb_conjunction_stanza(offsets):
                        return True
                elif self.spacy_pipeline:
                    # TODO: implement this for spacy parse.
                    pass #sys.stderr.write('WARNING: Method not implemented yet. Skipping.\n')

    def is_finite_verb_conjunction_stanza(self, offsets):
        conn = self.offsets2tokeninfo[offsets]
        ancestors = StringMatcher.get_stanza_ancestors(conn, self.offsets2tokeninfo, [])
        if ancestors:
            left_ancestors = [a for a in ancestors if a['id'][0] < conn['id'][0]]
            right_ancestors = [a for a in ancestors if a['id'][0] > conn['id'][0]]
            # tried out some toy examples and found that stanza parsing of czech is not very accurate.
            if [x for x in left_ancestors if x['upostag'] == 'VERB'] and [x for x in right_ancestors if x['upostag'] == 'VERB']:
                return True
            # if there are no left_ancestors, it's probably sentence-initial, in which case it's more likely to be a conn? (might work  exactly the other way around for Arabic...)
            elif not left_ancestors and [x for x in right_ancestors if x['upostag'] == 'VERB']:
                return True
            #if [x for x in left_ancestors if 'VerbForm' in x['feats'] and x['feats']['VerbForm'] == 'Fin'] and \
                    #[x for x in right_ancestors if 'VerbForm' in x['feats'] and x['feats']['VerbForm'] == 'Fin']:
                #return True


    @staticmethod
    def get_stanza_ancestors(item, offsets2tokeninfo, ancestors):
        newly_added = []
        for offset, token in offsets2tokeninfo.items():
            if token['id'][0] == item['head'] and item['sid'] == token['sid']:
                if token not in ancestors:
                    ancestors.append(token)
                    newly_added.append(token)
        for a in newly_added:
            if a['head'] == 0:
                return ancestors
            else:
                return StringMatcher.get_stanza_ancestors(a, offsets2tokeninfo, ancestors)

    @staticmethod
    def get_consecutive_token_matches(tokens, input_text, discont=False):
        matches = [list(re.finditer(r'\b%s\b' % t, input_text, re.IGNORECASE)) if t[0].isalpha() and t[-1].isalpha()
                   else list(re.finditer(r'%s' % t, input_text, re.IGNORECASE)) for t in tokens]
        candidates = []
        if all(matches):
            for conf in itertools.product(*matches):
                if discont:
                    if StringMatcher.is_incremental(conf):
                        candidates.append(conf)
                else:
                    if StringMatcher.is_consecutive(conf, input_text):
                        candidates.append(conf)
        return candidates

    @staticmethod
    def is_consecutive(conf, input_text):
        for i, item in enumerate(conf):
            if i > 0:
                if item.start() < conf[i-1].end():
                    return False
                if re.search(r'\w', input_text[conf[i-1].end():item.start()], re.IGNORECASE):
                    return False
            if i == len(conf)-1:
                return True

    @staticmethod
    def is_incremental(conf):
        for i, item in enumerate(conf):
            if i > 0:
                if item.start() < conf[i-1].end():
                    return False
            if i == len(conf)-1:
                return True
                    
    def within_bounds(self, candidate):
        stokens = [self.offsets2token[(x.start(), x.end())] if (x.start(), x.end()) in self.offsets2token else None for x in candidate]
        if all(stokens):  # might be tokenization diffs between lexicon and spacy
            ft = stokens[0]
            lt = stokens[-1]
            first_sid = self.offsets2sid[(ft.idx, ft.idx+len(ft.text))]
            last_sid = self.offsets2sid[(lt.idx, lt.idx+len(lt.text))]
            if last_sid - first_sid <= self.max_sent_dist:
                return True

    @staticmethod
    def filter_verified_matches(matches):
        
        sed = {(m[0].start(), m[-1].end()): m for m in matches}
        mindist = matches[0][-1].end() - matches[0][0].start()
        r = matches[0]
        for item in sed:
            if item[0] < item[1]:
                dist = item[1] - item[0]
                if dist < mindist:
                    mindist = dist
                    r = sed[item]
        return r
            

def main():
    ll = LexLoader.LexiconLoader()
    connectives = ll.load_lexicon('LREC24_experiments\czedlex1.0-basic.xml')
    sm = StringMatcher('czech', connectives, 'rules/cz_dummy.yaml')
    sentence = "Petr a Marie. Petr jí okurku a Marie pije pivo."
    #connectives = ll.load_lexicon('tests/discodict.xml')
    #sm = StringMatcher('nl', connectives)
    #sentence = 'Een voorbeeldzin, gewoon omdat het kan.'
    results = sm.match(sentence, False)
    print(results)


if __name__ == '__main__':
    main()
