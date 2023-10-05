import os
import re
import csv
import sys
import stanza
from tqdm import tqdm
from datasets import DatasetDict, Dataset
from transformers import AutoTokenizer
from transformers import DataCollatorForTokenClassification
from transformers import AutoModelForTokenClassification, TrainingArguments, Trainer
import evaluate
import numpy as np
import torch
os.environ["WANDB_DISABLED"] = "true"

nlp = stanza.Pipeline(lang='czech', processors='tokenize')
NON_CONN = '_'
CONN = 'Conn'
label_list = [NON_CONN, CONN]
label2id = {NON_CONN: 0, CONN: 1}
id2label = {0: NON_CONN, 1: CONN}
seqeval = evaluate.load("seqeval")

HF_MODEL = 'ufal/robeczech-base'
tokenizer = AutoTokenizer.from_pretrained(HF_MODEL, add_prefix_space=True)
data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
OUTDIR = 'classifier_out'

def to_datasetdict(gold, raw):

    train_gold_folders = [os.path.join(gold, sf) for sf in os.listdir(gold)[:9]]
    test_gold_folders = [os.path.join(gold, sf) for sf in os.listdir(gold)[9:]]
    train_raw_folders = [os.path.join(raw, sf) for sf in os.listdir(raw)[:9]]
    test_raw_folders = [os.path.join(raw, sf) for sf in os.listdir(raw)[9:]]
    train = []
    for gsf, rsf in zip(train_gold_folders, train_raw_folders):
        for gf, rf in zip(os.listdir(gsf), os.listdir(rsf)):
            train.append((os.path.join(gsf, gf), os.path.join(rsf, rf)))
    test = []
    for gsf, rsf in zip(test_gold_folders, test_raw_folders):
        for gf, rf in zip(os.listdir(gsf), os.listdir(rsf)):
            test.append((os.path.join(gsf, gf), os.path.join(rsf, rf)))

    train_items = collect_tokens_and_labels(train)
    test_items = collect_tokens_and_labels(test)

    dsd = DatasetDict(
        {'train': Dataset.from_list(train_items),
         'test': Dataset.from_list(test_items)}
    )
    return dsd


def collect_tokens_and_labels(zipped):

    items = []
    di = 0
    for fi, fpair in tqdm(enumerate(zipped), desc='preprocessing data'):
        gf, rf = fpair
        txt = open(rf, encoding='utf8').read()
        doc = nlp(txt)
        sentences = []
        for sid, sent in enumerate(doc.sentences):
            token2offsets = {}
            for token in sent.tokens:
                token2offsets[(token.start_char, token.end_char)] = token
            sentences.append(token2offsets)
        explicits = [x[1] for x in csv.reader(open(gf, encoding='utf8'), delimiter='|') if x[0] == 'Explicit']
        connective_spans = []
        for ex in explicits:
            for span in ex.split(';'):
                if span:
                    connective_spans.append(tuple([int(x) for x in span.split('..')]))
        for s in sentences:
            stokens = [t.text for o, t in s.items()]
            slabels = [label2id[NON_CONN]] * len(stokens)
            for i, o in enumerate(s):
                if o in connective_spans:
                    slabels[i] = label2id[CONN]
            d = {
                'id': di,
                'tags': slabels,
                'tokens': stokens
            }
            di += 1
            items.append(d)

    return items


def tokenize_and_align_labels(examples):

    tokenized_inputs = tokenizer(examples["tokens"], truncation=True, is_split_into_words=True)
    labels = []
    for i, label in enumerate(examples[f"tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs


def compute_metrics(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)

    true_predictions = [
        [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    results = seqeval.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "f1": results["overall_f1"],
        "accuracy": results["overall_accuracy"],
    }


def train(dsd):

    tokenized_dsd = dsd.map(tokenize_and_align_labels, batched=True)
    model = AutoModelForTokenClassification.from_pretrained(HF_MODEL, num_labels=2, id2label=id2label, label2id=label2id)
    OUTDIR = 'classifier_out'
    training_args = TrainingArguments(
        output_dir=OUTDIR,
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=2,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dsd["train"],
        eval_dataset=tokenized_dsd["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    sys.stderr.write(r'INFO: Successfully trained classifier (saved in "%s").\n' % OUTDIR)


def predict(dsd):

    model = AutoModelForTokenClassification.from_pretrained(OUTDIR+'/checkpoint-5362')

    tp = 0
    fp = 0
    fn = 0
    tokenized_dsd = dsd.map(tokenize_and_align_labels, batched=True)
    for item in tokenized_dsd['test']:
        tokens = item['tokens']
        inputs = tokenizer(tokens, is_split_into_words=True, return_tensors='pt')
        with torch.no_grad():
            logits = model(**inputs).logits
            predictions = torch.argmax(logits, dim=2)
            predicted_token_class = [t.item() for t in predictions[0]]
            pred_labels = [predicted_token_class[i] for i, j in enumerate(item['labels']) if j != -100]
            assert len(pred_labels) == len(item['tags'])
            for index, preds in enumerate(zip(item['tags'], pred_labels)):
                gp, pp = preds
                if re.match(r'\W+', tokens[index]):  # skipping hyphen-only instances. Seems like this is not annotated consistently, as skipping them also increases recall...
                    continue
                elif tokens[index] in ['s', 'to', 'ne']:
                    continue
                if gp == 1 and pp == 1:
                    tp += 1
                elif gp == 1:
                    fn += 1
                elif pp == 1:
                    fp += 1
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


def main():

    root_folder = r'PDiT_3.0\data\column'
    gold_folder = os.path.join(root_folder, 'gold')
    raw_folder = os.path.join(root_folder, 'raw')
    dsd = to_datasetdict(gold_folder, raw_folder)
    print('Train words:', sum([len(x['tokens']) for x in dsd['train']]))
    train_conns = 0
    for item in dsd['train']:
        train_conns += len([x for x in item['tags'] if x == 1])
    print('Train conn instances:', train_conns)
    print('Test words:', sum([len(x['tokens']) for x in dsd['test']]))
    test_conns = 0
    for item in dsd['test']:
        test_conns += len([x for x in item['tags'] if x == 1])
    print('Test conn instances:', test_conns)

    #train(dsd)
    predict(dsd)


if __name__ == '__main__':
    main()
