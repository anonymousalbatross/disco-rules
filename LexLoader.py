import os
import sys
import lxml.etree

class Connective:

    def __init__(self, canonical, orths, is_discont, amb_info, is_amb, senses, postag):
        self.canonical = canonical
        self.orths = orths
        self.is_discont = is_discont
        self.amb_info = amb_info
        self.is_amb = is_amb
        self.senses = senses
        self.postag = postag
        
    def get_orths(self):
        return self.orths
    def is_discontinuous(self):
        return self.is_discont
    def has_ambinfo(self):
        return self.amb_info
    def is_ambiguous(self):
        return self.is_amb
    def get_senses(self):
        return self.senses
    

class LexiconLoader:

    def __init__(self):
        self.parser = lxml.etree.XMLParser()
        
    def load_lexicon(self, xmlf):
        tree = lxml.etree.parse(xmlf, parser=self.parser)
        connectives = []
        for entry in tree.getroot().findall('.//entry'):
            canonical = entry.get('word')
            orths = [[x.text for x in y.findall('.//part')] for y in entry.findall('.//orth')]
            # TODO: currently is_discont is decided at connective (top) level. 
            # Might be orths which are continuous, and others discontinuous. Fix and debug this!
            is_discont = True if [x for x in entry.findall('.//orth') if x.get('type') == 'discont'] else False
            ncr = entry.find('.//non_conn_reading')
            amb_info = False
            is_amb = False
            if ncr is not None:
                amb_info = True
                is_amb = True if [x.tag == 'example' for x in ncr] else False
            senses = [x.get('sense') for x in entry.findall('.//pdtb3_relation')]
            if not senses:
                senses = [x.get('sense') for x in entry.findall('.//pdtb2_relation')]  # eng-dimlex
            if not senses:
                senses = [x.get('sense') for x in entry.findall('.//sdrt_relation')]  # lexconn
            postag = entry.find('.//cat').text
            conn = Connective(canonical, orths, is_discont, amb_info, is_amb, senses, postag)
            connectives.append(conn)
        return connectives
