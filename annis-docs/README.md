# DisCo-StringMatcher ANNIS Workflow
This folder describes how to run the StringMatcher from the parent folder on some input text, dump the results, combined with dependency trees, to conllu-format and convert that to an [ANNIS](https://corpus-tools.org/annis/) corpus, so that it can be visualised and queried, to construct heuristics which can be fed back into the string matching procedure.
The procedure consists of the following steps:

1.  Run `annotate.py` in the parent folder on some input text. The script accepts both pre-tokenized (and/or sentence-splitted) input and unprocessed, raw input strings.
For example, for `cs_love_and_garbage_first1k_sents.txt` in this folder, the command would be: `annotate.py -i cs_love_and_garbage_first1k_sents.txt -o cz_love_and_garbage -l cz -s -t` (with `-t` indicating the input is pre-tokenized (whitespace splitting results in a list of tokens), and `-s` indicating that the input is sentence-splitted (newline splitting results in a list of sentences)).
This dumps the output in the folder `cz_love_and_garbage`.
2.  Download [Pepper](https://corpus-tools.org/pepper/#download), the ANNIS tool kit for format conversion. After [starting](https://corpus-tools.org/pepper/userGuide.html) Pepper, type `convert cz_love_and_garbage_pepper_workflow.xml` to convert the corpus generated in the previous step to ANNIS format. The output is dumped in the folder specified in the [XML workflow file](https://github.com/PeterBourgonje/disco-stringmatcher/blob/73e7bc0cae1378e97d464b8ab8005ea2598e05fd/annis-docs/cz_love_and_garbage_pepper_workflow.xml#L11). Created a zip-file of this folder.
3.  Download [ANNIS](https://corpus-tools.org/annis/download.html) in its desktop version, or use it on a server where you have admin access (to the ANNIS interface).
4.  Import the corpus created with Pepper in step 2 in the GUI, by going to the "Administration" tab (only available if you have admin access):
  ![Alt text](images/import_corpus_1.png?raw=true "Importing a corpus in ANNIS")
  Under the "Import Corpus" tab, select the zip-file of the folder/dump created in step 2:
  ![Alt text](images/import_corpus_2.png?raw=true "Importing a corpus in ANNIS")
5. Returning to the "Search interface", you can now browse and query the corpus you have just imported.
   Queries can be entered in the top-left window (see the [docs](https://korpling.github.io/ANNIS/4.0/user-guide/aql/) for some examples to get started), and the results can be inspected visually.
  The following query, for example, returns all tokens that are marked with "B-connective" by the StringMatcher, and have the lemma "a".
  ![Alt text](images/query_corpus.png?raw=true "Querying a corpus in ANNIS")

The idea is that any heuristics found, based on dependency labels or pos-tags, can be fed back into the StringMatcher to improve matching. Definition of rules is done in YAML format. Which exact rules and features are supported is somewhat in flux still, but see ../rules/cz_dummy.yaml to get an idea of what this looks like.

  
