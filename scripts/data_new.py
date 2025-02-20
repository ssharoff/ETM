#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

# Serge Sharoff, University of Leeds. An extension from https://github.com/adjidieng/ETM
# Modifications concern the possibility to choose the parameters and to encode new datasets using the same vocabulary
# It does read the entire corpus into memory for efficient conversion to the BoW representation.
# For a large (20GW) corpus this ends up with consuming 70G

import time
starttime=int(time.time())

import argparse
import pickle
import sys, os, os.path
import random
from smart_open import open

from sklearn.feature_extraction.text import CountVectorizer
import numpy as np
from scipy import sparse
from scipy.io import savemat, loadmat

# helper functions
def make_dictionary(vocab):
    word2id = dict([(w, j) for j, w in enumerate(vocab)])
    id2word = dict([(j, w) for j, w in enumerate(vocab)])
    return word2id, id2word

def create_list_words(in_docs):
    if args.verbosity>0:
        print('creating lists of words...', file=sys.stderr)
    return [x for y in in_docs for x in y]

def create_doc_indices(in_docs):
    aux = [[j for i in range(len(doc))] for j, doc in enumerate(in_docs)]
    return [int(x) for y in aux for x in y]


def create_bow(doc_indices, words, n_docs, vocab_size):
    return sparse.coo_matrix(([1]*len(doc_indices),(doc_indices, words)), shape=(n_docs, vocab_size)).tocsr()
def split_bow(bow_in, n_docs):
    indices = [[w for w in bow_in[doc,:].indices] for doc in range(n_docs)]
    counts = [[c for c in bow_in[doc,:].data] for doc in range(n_docs)]
    return indices, counts

parser = argparse.ArgumentParser(description='The Embedded Topic Model')

### data and file related arguments
parser.add_argument('-c', '--corpusfile', type=str, help='corpus file name')
parser.add_argument('-d', '--dictionary', type=str, help='Use an existing dictionary')
parser.add_argument('-o', '--output', type=str, help='directory to save BoW corpus')
parser.add_argument('-s', '--stops', type=str, default='stop-en.txt', help='stop words file')
parser.add_argument('-m', '--min_df', type=float, default=200, help='Ignore terms that have a document frequency or percentage lower than')
parser.add_argument('-x', '--max_df', type=float, default=0.7, help='Ignore terms that have a document frequency or percentage higher than')

parser.add_argument('-v', '--verbosity', type=int, default=1)

args = parser.parse_args()

assert os.path.isfile(args.corpusfile), f'Corpus file {args.corpusfile} does not exist'
if args.dictionary:
    assert os.path.isfile(args.dictionary), f'Dictionary file {args.dictionary} does not exist'
else:
    assert os.path.isfile(args.stops), f'Stop file {args.stops} does not exist'

path_save = args.output + '/' if args.output else args.corpusfile + str(args.min_df) + '/'

# Read data
with open(args.corpusfile, 'r') as f:
    docs = f.readlines()
if args.verbosity>0:
    xtime=int(time.time())
    print(f'Read text file from {args.corpusfile} with {len(docs)} docs')
    print(f'Loaded data in {xtime-starttime} secs')

if not os.path.isdir(path_save):
    os.system('mkdir -p ' + path_save)

if args.dictionary:
    vocab=pickle.load(open(args.dictionary,'rb'))
    if args.verbosity>0:
        print(f'Read existing dictionary {len(vocab)} words')
    word2id, id2word = make_dictionary(vocab)
    tsSize = len(docs)
    # docs_ts consists of ids of words in vocab
    docs_ts = [[word2id[w] for w in docs[idx_d].split() if w in word2id] for idx_d in range(tsSize)]
    if args.verbosity>1: # for testing how doc indices align with the line count in .ol
        k = 30
        rr = [0] + sorted(random.sample(range(len(docs)), k))
        print(rr)
        for i in rr:
            doc = docs[i]
            doc_ts = ' '.join([id2word[id] for id in docs_ts[i]])
            print(str(i+1)+'\t'+doc[:100]+'\t'+doc_ts[:100])

    del docs
    words_ts = create_list_words(docs_ts)
    doc_indices_ts = create_doc_indices(docs_ts)
    n_docs_ts = len(docs_ts)
    bow_ts = create_bow(doc_indices_ts, words_ts, n_docs_ts, len(vocab))
    bow_ts_tokens, bow_ts_counts = split_bow(bow_ts, n_docs_ts)
    if args.verbosity>0:
        ztime=int(time.time())
        print('Bow created in {} secs'.format(ztime-xtime))
    savemat(path_save + 'bow_ts_tokens.mat', {'tokens': bow_ts_tokens}, do_compression=True)
    savemat(path_save + 'bow_ts_counts.mat', {'counts': bow_ts_counts}, do_compression=True)

else:
    # Read stopwords
    with open(args.stops, 'r') as f:
        stops = f.read().split('\n')
    # Create count vectorizer
    cvectorizer = CountVectorizer(min_df=args.min_df, max_df=args.max_df, stop_words=None)
    cvz = cvectorizer.fit_transform(docs).sign()

    sum_counts = cvz.sum(axis=0)
    v_size = sum_counts.shape[1]
    sum_counts_np = np.zeros(v_size, dtype=int)
    for v in range(v_size):
        sum_counts_np[v] = sum_counts[0,v]
    word2id = dict([(w, cvectorizer.vocabulary_.get(w)) for w in cvectorizer.vocabulary_])
    id2word = dict([(cvectorizer.vocabulary_.get(w), w) for w in cvectorizer.vocabulary_])
    del cvectorizer
    if args.verbosity>0:
        print(f'  initial vocabulary size: {v_size}')
        ytime=int(time.time())
        print(f'Initial vocabulary built in {(ytime-xtime)} secs')

    # Sort elements in vocabulary
    idx_sort = np.argsort(sum_counts_np)
    vocab_aux = [id2word[idx_sort[cc]] for cc in range(v_size)]
    if args.verbosity>0:
        print('  vocabulary size before removing stopwords from list: {}'.format(len(vocab_aux)), file=sys.stderr)

    # Filter out stopwords (if any)
    vocab_aux = [w for w in vocab_aux if w not in stops]
    if args.verbosity>0:
        print('  vocabulary after removing stopwords: {}'.format(len(vocab_aux)), file=sys.stderr)

    # Create dictionary and inverse dictionary
    word2id, id2word= make_dictionary(vocab_aux)

    # Split in train/test/valid
    if args.verbosity>0:
        print('tokenizing documents and splitting into train/test/valid...', file=sys.stderr)
    num_docs = cvz.shape[0]
    trSize = int(np.floor(0.85*num_docs))
    tsSize = int(np.floor(0.10*num_docs))
    vaSize = int(num_docs - trSize - tsSize)
    del cvz
    idx_permute = np.random.permutation(num_docs).astype(int)

    # Remove words not in train_data
    vocab = list(set([w for idx_d in range(trSize) for w in docs[idx_permute[idx_d]].split() if w in word2id]))
    word2id, id2word = make_dictionary(vocab)
    if args.verbosity>0:
        print('  vocabulary after removing words not in train: {}'.format(len(vocab)), file=sys.stderr)

    docs_tr = [[word2id[w] for w in docs[idx_permute[idx_d]].split() if w in word2id] for idx_d in range(trSize)]
    docs_ts = [[word2id[w] for w in docs[idx_permute[idx_d+trSize]].split() if w in word2id] for idx_d in range(tsSize)]
    docs_va = [[word2id[w] for w in docs[idx_permute[idx_d+trSize+tsSize]].split() if w in word2id] for idx_d in range(vaSize)]
    del docs

    print('  number of documents (train): {} [this should be equal to {}]'.format(len(docs_tr), trSize))
    print('  number of documents (test): {} [this should be equal to {}]'.format(len(docs_ts), tsSize))
    print('  number of documents (valid): {} [this should be equal to {}]'.format(len(docs_va), vaSize))

    # Remove empty documents
    print('removing empty documents...')

    def remove_empty(in_docs):
        return [doc for doc in in_docs if doc!=[]]

    docs_tr = remove_empty(docs_tr)
    docs_ts = remove_empty(docs_ts)
    docs_va = remove_empty(docs_va)

    # Remove test documents with length=1
    docs_ts = [doc for doc in docs_ts if len(doc)>1]

    # Split test set in 2 halves
    print('splitting test documents in 2 halves...')
    docs_ts_h1 = [[w for i,w in enumerate(doc) if i<=len(doc)/2.0-1] for doc in docs_ts]
    docs_ts_h2 = [[w for i,w in enumerate(doc) if i>len(doc)/2.0-1] for doc in docs_ts]

    # Getting lists of words and doc_indices
    words_tr = create_list_words(docs_tr)
    words_ts = create_list_words(docs_ts)
    words_ts_h1 = create_list_words(docs_ts_h1)
    words_ts_h2 = create_list_words(docs_ts_h2)
    words_va = create_list_words(docs_va)

    if args.verbosity>0:
        print('  len(words_tr): ', len(words_tr))
        print('  len(words_ts): ', len(words_ts))
        print('  len(words_ts_h1): ', len(words_ts_h1))
        print('  len(words_ts_h2): ', len(words_ts_h2))
        print('  len(words_va): ', len(words_va))
        print('getting doc indices...')

    # Get doc indices

    doc_indices_tr = create_doc_indices(docs_tr)
    doc_indices_ts = create_doc_indices(docs_ts)
    doc_indices_ts_h1 = create_doc_indices(docs_ts_h1)
    doc_indices_ts_h2 = create_doc_indices(docs_ts_h2)
    doc_indices_va = create_doc_indices(docs_va)

    if args.verbosity>0:
        print('  len(np.unique(doc_indices_tr)): {} [this should be {}]'.format(len(np.unique(doc_indices_tr)), len(docs_tr)))
        print('  len(np.unique(doc_indices_ts)): {} [this should be {}]'.format(len(np.unique(doc_indices_ts)), len(docs_ts)))
        print('  len(np.unique(doc_indices_ts_h1)): {} [this should be {}]'.format(len(np.unique(doc_indices_ts_h1)), len(docs_ts_h1)))
        print('  len(np.unique(doc_indices_ts_h2)): {} [this should be {}]'.format(len(np.unique(doc_indices_ts_h2)), len(docs_ts_h2)))
        print('  len(np.unique(doc_indices_va)): {} [this should be {}]'.format(len(np.unique(doc_indices_va)), len(docs_va)))

    # Number of documents in each set
    n_docs_tr = len(docs_tr)
    n_docs_ts = len(docs_ts)
    n_docs_ts_h1 = len(docs_ts_h1)
    n_docs_ts_h2 = len(docs_ts_h2)
    n_docs_va = len(docs_va)

    # Remove unused variables
    del docs_tr
    del docs_ts
    del docs_ts_h1
    del docs_ts_h2
    del docs_va

    # Create bow representation
    bow_tr = create_bow(doc_indices_tr, words_tr, n_docs_tr, len(vocab))
    bow_ts = create_bow(doc_indices_ts, words_ts, n_docs_ts, len(vocab))
    bow_ts_h1 = create_bow(doc_indices_ts_h1, words_ts_h1, n_docs_ts_h1, len(vocab))
    bow_ts_h2 = create_bow(doc_indices_ts_h2, words_ts_h2, n_docs_ts_h2, len(vocab))
    bow_va = create_bow(doc_indices_va, words_va, n_docs_va, len(vocab))
    if args.verbosity>0:
        ztime=int(time.time())
        print('Bow created in {} secs'.format(ztime-ytime))

    del words_tr
    del words_ts
    del words_ts_h1
    del words_ts_h2
    del words_va
    del doc_indices_tr
    del doc_indices_ts
    del doc_indices_ts_h1
    del doc_indices_ts_h2
    del doc_indices_va

    # Save vocabulary to file
    with open(path_save + 'vocab.pkl', 'wb') as f:
        pickle.dump(vocab, f)
    del vocab

    # Split bow into token/value pairs
    if args.verbosity>0:
        print('splitting bow into token/value pairs and saving to disk...')

    bow_tr_tokens, bow_tr_counts = split_bow(bow_tr, n_docs_tr)
    savemat(path_save + 'bow_tr_tokens.mat', {'tokens': bow_tr_tokens}, do_compression=True)
    savemat(path_save + 'bow_tr_counts.mat', {'counts': bow_tr_counts}, do_compression=True)
    del bow_tr
    del bow_tr_tokens
    del bow_tr_counts

    bow_va_tokens, bow_va_counts = split_bow(bow_va, n_docs_va)
    savemat(path_save + 'bow_va_tokens.mat', {'tokens': bow_va_tokens}, do_compression=True)
    savemat(path_save + 'bow_va_counts.mat', {'counts': bow_va_counts}, do_compression=True)
    del bow_va
    del bow_va_tokens
    del bow_va_counts

    bow_ts_tokens, bow_ts_counts = split_bow(bow_ts, n_docs_ts)
    savemat(path_save + 'bow_ts_tokens.mat', {'tokens': bow_ts_tokens}, do_compression=True)
    savemat(path_save + 'bow_ts_counts.mat', {'counts': bow_ts_counts}, do_compression=True)
    del bow_ts
    del bow_ts_tokens
    del bow_ts_counts

    bow_ts_h1_tokens, bow_ts_h1_counts = split_bow(bow_ts_h1, n_docs_ts_h1)
    savemat(path_save + 'bow_ts_h1_tokens.mat', {'tokens': bow_ts_h1_tokens}, do_compression=True)
    savemat(path_save + 'bow_ts_h1_counts.mat', {'counts': bow_ts_h1_counts}, do_compression=True)
    del bow_ts_h1
    del bow_ts_h1_tokens
    del bow_ts_h1_counts

    bow_ts_h2_tokens, bow_ts_h2_counts = split_bow(bow_ts_h2, n_docs_ts_h2)
    savemat(path_save + 'bow_ts_h2_tokens.mat', {'tokens': bow_ts_h2_tokens}, do_compression=True)
    savemat(path_save + 'bow_ts_h2_counts.mat', {'counts': bow_ts_h2_counts}, do_compression=True)
    del bow_ts_h2
    del bow_ts_h2_tokens
    del bow_ts_h2_counts

if args.verbosity>0:
    print('Data ready !!')
    ztime=int(time.time())
    print('All completed in {} secs'.format(ztime-starttime))
    print('*************')

