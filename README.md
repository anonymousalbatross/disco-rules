# disco-rules
A tool kit to develop a rule-based discourse connective identifier. 

Usage example:
```
>>> import LexLoader
>>> import StringMatcher
>>> ll = LexLoader.LexiconLoader()
>>> connectives = ll.load_lexicon('LREC24_experiments\czedlex1.0-basic.xml')
>>> sm = StringMatcher.StringMatcher('czech', connectives)
2023-10-05 14:23:28 INFO: Checking for updates to resources.json in case models have been updated.  Note: this behavior can be turned off with download_method=None or download_method=DownloadMethod.REUSE_RESOURCES
Downloading https://raw.githubusercontent.com/stanfordnlp/stanza-resources/main/resources_1.5.1.json: 366kB [00:00, 34.5MB/s]
2023-10-05 14:23:28 INFO: "czech" is an alias for "cs"
2023-10-05 14:23:29 INFO: Loading these models for language: cs (Czech):
============================
| Processor | Package      |
----------------------------
| tokenize  | pdt          |
| mwt       | pdt          |
| pos       | pdt_nocharlm |
| lemma     | pdt_nocharlm |
| depparse  | pdt_nocharlm |
============================

2023-10-05 14:23:29 INFO: Using device: cpu
2023-10-05 14:23:29 INFO: Loading: tokenize
2023-10-05 14:23:29 INFO: Loading: mwt
2023-10-05 14:23:29 INFO: Loading: pos
2023-10-05 14:23:29 INFO: Loading: lemma
2023-10-05 14:23:29 INFO: Loading: depparse
2023-10-05 14:23:29 INFO: Done loading processors!
>>> sentence = "Nemáme  proto potíže se získáváním trhu pro své výrobní odpady."
>>> results = sm.match(sentence, False)
>>> print(results)
([{'canonical_connective': 'proto', 'surface_form': 'proto', 'offsets': [(8, 13)], 'senses': ['reason-result', 'pragmatic reason-result', 'equivalence']}], False)
```
