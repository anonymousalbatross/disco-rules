import sys
import os
import json
currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 
from LexLoader import LexiconLoader
from StringMatcher import StringMatcher

def test(xmlf, txt, lang):
    
    ll = LexiconLoader()
    connectives = ll.load_lexicon(xmlf)
    sm = StringMatcher(lang, connectives)
    strict = False
    annotations, ambinfo_missing = sm.match(txt, strict)
    print(json.dumps(annotations, indent=2, ensure_ascii=False))
    

def main():
    """
    de_xml = 'dimlex.xml'
    de_txt = open('de.txt').read()
    test(de_xml, de_txt, 'de')
    
    en_xml = 'eng-dimlex.xml'
    en_txt = open('en.txt').read()
    test(en_xml, en_txt, 'en')

    nl_xml = 'discodict.xml'
    nl_txt = open('nl.txt').read()
    test(nl_xml, nl_txt, 'nl')
    
    ru_xml = 'Ru_XML.xml'
    ru_txt = open('ru.txt').read()
    test(ru_xml, ru_txt, 'ru')
    """
    it_xml = 'lico_d.xml'
    it_txt = open('it.txt').read()
    test(it_xml, it_txt, 'it')
    """ 
    fr_xml = 'lexconn_d.xml'
    fr_txt = open('fr.txt').read()
    test(fr_xml, fr_txt, 'fr')
    
    bn_xml = 'bangla_dimlex.xml'
    bn_txt = open('bn.txt').read()
    test(bn_xml, bn_txt, 'bn')
        
    zh_xml = 'chinese_dimlex.xml'
    zh_txt = open('zh.txt').read()
    test(zh_xml, zh_txt, 'zh')
        
    ar_xml = 'arabic_d.xml'
    ar_txt = open('ar.txt').read()
    test(ar_xml, ar_txt, 'ar')
        
    cz_xml = 'czedlex_connective_lex.xml'
    cz_txt = open('cz.txt').read()
    test(cz_xml, cz_txt, 'cz')
        
    pt_xml = 'ldm-pt_d.xml'
    pt_txt = open('pt.txt').read()
    test(pt_xml, pt_txt, 'pt')
        
    np_xml = 'naijalex.xml'
    np_txt = open('np.txt').read()
    test(np_xml, np_txt, 'np')
        
    tr_xml = 'TCL.xml'
    tr_txt = open('tr.txt').read()
    test(tr_xml, tr_txt, 'tr')
    
    uk_xml = 'UK_DiMLex.xml'
    uk_txt = open('uk.txt').read()
    test(uk_xml, uk_txt, 'uk')
    """

if __name__ == '__main__':
    main()