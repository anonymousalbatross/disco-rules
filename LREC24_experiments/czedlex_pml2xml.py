import os
import re
import sys
from lxml import etree

"""
This creates a basic XML from the Prague PML format, with many attributes left blank still (just the minimum for getting a list of entries, not paying attention to pos-tags and senses).
"""

xmlp = etree.XMLParser()
ns = {"pml": "http://ufal.mff.cuni.cz/pdt/pml/"}

def create_xml(pml):

    lex_root = etree.Element('dimlex')
    doc = etree.ElementTree(lex_root)
    
    pml_tree = etree.parse(open(pml, encoding='utf8'), parser=xmlp).getroot()
    for lemma in pml_tree.findall('.//pml:lemma',  namespaces=ns):
        if lemma.find('.//pml:type', namespaces=ns).text == 'primary':
            xmlnode = etree.Element('entry')
            xmlnode.set('id', lemma.get('id'))
            word = lemma.find('.//pml:text', namespaces=ns).text
            xmlnode.set('word', word)
            orths = etree.Element('orths')
            orth = etree.Element('orth')
            orth.set('canonical', '1')
            _type = 'single'
            struct = lemma.find('.//pml:struct', namespaces=ns)
            if struct is not None:
                if struct.text == 'complex':
                    _type == 'discont'
            orth.set('type', _type)
            for part in word.split('~'):
                part = part.strip()
                pn = etree.Element('part')
                if re.search(' ', part):
                    sp_type = 'phrasal'
                else:
                    sp_type = 'single'
                pn.set('type', sp_type)
                pn.text = part
                orth.append(pn)
            orths.append(orth)
            for var in lemma.findall('.//pml:variant', namespaces=ns):
                orth = etree.Element('orth')
                orth.set('canonical', '0')
                orth.set('type', _type)
                pn = etree.Element('part')
                pn.set('type', 'single')
                pn.text = var.text
                orth.append(pn)
                orths.append(orth)
            for cf in lemma.findall('.//pml:complex_form', namespaces=ns):
                orth = etree.Element('orth')
                orth.set('canonical', '0')
                txt = cf.find('.//pml:text', namespaces=ns).text
                for part in txt.split('~'):
                    part = part.strip()
                    pn = etree.Element('part')
                    if re.search(' ', part):
                        sp_type = 'phrasal'
                    else:
                        sp_type = 'single'
                    pn.set('type', sp_type)
                    pn.text = part
                    orth.append(pn)
                orths.append(orth)

            xmlnode.append(orths)
            amb = etree.Element('ambiguity')
            xmlnode.append(amb)
            nonconn = etree.Element('non_conn_reading')
            xmlnode.append(nonconn)
            stts = etree.Element('stts')
            xmlnode.append(stts)
            syn = etree.Element('syn')
            cat = etree.Element('cat')
            cat.text = lemma.find('.//pml:pos', namespaces=ns).text  # just getting the first one I find, not even checking if there's multiple/conflicting...
            syn.append(cat)
            conn_usages = lemma.find('.//pml:conn-usages', namespaces=ns)
            for usage in conn_usages.findall('.//pml:usage', namespaces=ns):
                sem = etree.Element('sem')
                pdtb3_rel = etree.Element('pdtb3_relation')
                pdtb3_rel.set('sense', usage.find('.//pml:sense', namespaces=ns).text)
                sem.append(pdtb3_rel)
                syn.append(sem)
            xmlnode.append(syn)
            non_conn_reading = etree.Element('non_conn_reading')
            non_conn_usages = lemma.find('.//pml:non-conn-usages', namespaces=ns)
            for ncu in non_conn_usages.findall('.//pml:usage', namespaces=ns):
                for example in ncu.findall('.//pml:example', namespaces=ns):
                    ex = etree.Element('example')
                    ex.text = example.find('.//pml:text', namespaces=ns).text
                    non_conn_reading.append(ex)
            xmlnode.append(non_conn_reading)
            
            lex_root.append(xmlnode)
        
    doc.write('czedlex1.0-basic.xml', xml_declaration=True, encoding='utf-8', pretty_print=True)



def main():
    pml = 'czedlex1.0.pml'
    create_xml(pml)


if __name__ == '__main__':
	main()