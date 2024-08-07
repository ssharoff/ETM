#/usr/bin/python

from __future__ import print_function

import time
starttime=int(time.time())


import argparse
import torch
import pickle 
import numpy as np 
import os 
import math 
import random 
import sys
import data
import scipy.io

from torch import nn, optim
from torch.nn import functional as F

from etm import ETM
from utils import nearest_neighbors, get_topic_coherence, get_topic_diversity

parser = argparse.ArgumentParser(description='The Embedded Topic Model')
parser.add_argument('--mode', type=str, default='train', help='train, eval or apply model')

### data and file related arguments
parser.add_argument('--dataset', type=str, default='20ng', help='dataset name')
parser.add_argument('-b', '--data_path', type=str, default='data/20ng', help='directory containing BoW data')
parser.add_argument('--emb_path', type=str, default='data/20ng_embeddings.txt', help='file containing word embeddings')
parser.add_argument('--save_path', type=str, default='./results', help='path to save results')
parser.add_argument('-o', '--output', type=str, default='', help='the name of the output file')
parser.add_argument('-d', '--dictionary', type=str, help='existing dictionary file')

### model-related arguments
parser.add_argument('-K', '--num_topics', type=int, default=0, help='number of topics')
parser.add_argument('--rho_size', type=int, default=300, help='dimension of rho')
parser.add_argument('--emb_size', type=int, default=300, help='dimension of embeddings')
parser.add_argument('--t_hidden_size', type=int, default=530, help='dimension of hidden space of q(theta)')
parser.add_argument('--theta_act', type=str, default='relu', help='tanh, softplus, relu, rrelu, leakyrelu, elu, selu, glu)')
parser.add_argument('--best', type=str, default='val_ppl', help='Saving the model for the best: val_ppl, kl_theta, nelbo)')
parser.add_argument('--train_embeddings', type=int, default=1, help='whether to fix rho or train it')

### optimization-related arguments
parser.add_argument('--batch_size', type=int, default=1000, help='input batch size for training')
parser.add_argument('--lr', type=float, default=0.005, help='learning rate')
parser.add_argument('--lr_factor', type=float, default=4.0, help='divide learning rate by this...')
parser.add_argument('-e', '--epochs', type=int, default=20, help='number of epochs to train...150 for 20ng 100 for others')
parser.add_argument('--optimizer', type=str, default='adam', help='choice of optimizer')
parser.add_argument('--seed', type=int, default=42, help='random seed')
parser.add_argument('--enc_drop', type=float, default=0.0, help='dropout rate on encoder')
parser.add_argument('--clip', type=float, default=0.0, help='gradient clipping')
parser.add_argument('--nonmono', type=int, default=10, help='number of bad hits allowed')
parser.add_argument('--wdecay', type=float, default=1.2e-6, help='some l2 regularization')
parser.add_argument('--anneal_lr', type=int, default=0, help='whether to anneal the learning rate or not')
parser.add_argument('--bow_norm', type=int, default=1, help='normalize the bows or not')
parser.add_argument('--cpu', default=False, action='store_true', help='whether to force using cpu')

### evaluation, visualization, and logging-related arguments
parser.add_argument('-k', '--num_words', type=int, default=20, help='number of words for topic viz')
parser.add_argument('--toptopicsnum', type=int, default=20, help='number of top topics for evaluation')
parser.add_argument('--log_interval', type=int, default=200, help='when to log training')
parser.add_argument('--visualize_every', type=int, default=10, help='when to visualize results')
parser.add_argument('--eval_batch_size', type=int, default=1000, help='input batch size for evaluation')
parser.add_argument('-l', '--load_from', type=str, default='', help='the name of the ckpt to eval from')
parser.add_argument('--queries', type=str, default='', help='space-separated words to visualise embeddings')
parser.add_argument('--tc', default=False, action='store_true', help='whether to compute topic coherence; this is time consuming')
parser.add_argument('--td', default=False, action='store_true', help='whether to compute topic diversity')
parser.add_argument('--tp', default=False, action='store_true', help='whether to compute topic proportions')
parser.add_argument('--threshold', type=float, default=0.5, help='threshold for printing less significant topics')
parser.add_argument('-v', '--verbosity', type=int, default=1)
parser.add_argument('--topK', type=int, default=3, help='max number of topics for predictions')


args = parser.parse_args()

device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")

print(device)

outfile=open(args.output,'w') if (len(args.output)>0 and not args.output=='-') else sys.stdout
np.random.seed(args.seed)
torch.manual_seed(args.seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed(args.seed)
queries = args.queries.split()

if args.mode == 'apply':
    vocab=pickle.load(open(args.dictionary,'rb'))
    vocab_size = len(vocab)
    args.vocab_size = vocab_size
    token_file = os.path.join(args.data_path, 'bow_ts_tokens.mat')
    count_file = os.path.join(args.data_path, 'bow_ts_counts.mat')
    train_tokens = scipy.io.loadmat(token_file)['tokens'].squeeze()
    train_counts = scipy.io.loadmat(count_file)['counts'].squeeze()
    args.num_docs_train = len(train_tokens)
else:
    # 1. vocabulary
    vocab, train, valid, test = data.get_data(os.path.join(args.data_path))
    vocab_size = len(vocab)
    args.vocab_size = vocab_size

    # 1. training data
    train_tokens = train['tokens']
    train_counts = train['counts']
    args.num_docs_train = len(train_tokens)

    # 2. dev set
    valid_tokens = valid['tokens']
    valid_counts = valid['counts']
    args.num_docs_valid = len(valid_tokens)

    # 3. test data
    test_tokens = test['tokens']
    test_counts = test['counts']
    args.num_docs_test = len(test_tokens)
    test_1_tokens = test['tokens_1']
    test_1_counts = test['counts_1']
    args.num_docs_test_1 = len(test_1_tokens)
    test_2_tokens = test['tokens_2']
    test_2_counts = test['counts_2']
    args.num_docs_test_2 = len(test_2_tokens)

xtime=int(time.time())
if args.verbosity>0:
    print('Loaded data in {} secs'.format(xtime-starttime))
embeddings = None
if not args.train_embeddings:
    emb_path = args.emb_path
    vect_path = os.path.join(args.data_path.split('/')[0], 'embeddings.pkl')   
    vectors = {}
    with open(emb_path, 'rb') as f:
        for l in f:
            line = l.decode().split()
            word = line[0]
            if word in vocab:
                vect = np.array(line[1:]).astype(np.float)
                vectors[word] = vect
    embeddings = np.zeros((vocab_size, args.emb_size))
    words_found = 0
    for i, word in enumerate(vocab):
        try: 
            embeddings[i] = vectors[word]
            words_found += 1
        except KeyError:
            embeddings[i] = np.random.normal(scale=0.6, size=(args.emb_size, ))
    embeddings = torch.from_numpy(embeddings).to(device)
    args.embeddings_dim = embeddings.size()

xtime=int(time.time())
if args.verbosity>0:
    print('Loaded data and embeddings in {} secs'.format(xtime-starttime))

## define checkpoint
if not os.path.exists(args.save_path):
    os.makedirs(args.save_path)

if args.mode in ['eval', 'apply']:
    ckpt = args.load_from
    with open(ckpt, 'rb') as f:
        model = torch.load(f,map_location=torch.device(device))
    args.num_topics=model.alphas.out_features  # otherwise the dimensions are not compatible
    model = model.to(device)
    model.eval()
else:
    ckpt = os.path.join(args.save_path, 
        f'etm_{args.dataset}_K_{args.num_topics}_Htheta_{args.t_hidden_size}_Lr_{args.lr}_RhoSize_{args.rho_size}')
    model = ETM(args.num_topics, vocab_size, args.t_hidden_size, args.rho_size, args.emb_size, 
                args.theta_act, embeddings, args.train_embeddings, args.enc_drop).to(device)

print('model: {}'.format(model))

if args.optimizer == 'adam':
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.wdecay)
elif args.optimizer == 'adagrad':
    optimizer = optim.Adagrad(model.parameters(), lr=args.lr, weight_decay=args.wdecay)
elif args.optimizer == 'adadelta':
    optimizer = optim.Adadelta(model.parameters(), lr=args.lr, weight_decay=args.wdecay)
elif args.optimizer == 'rmsprop':
    optimizer = optim.RMSprop(model.parameters(), lr=args.lr, weight_decay=args.wdecay)
elif args.optimizer == 'asgd':
    optimizer = optim.ASGD(model.parameters(), lr=args.lr, t0=0, lambd=0., weight_decay=args.wdecay)
else:
    print('Defaulting to vanilla SGD')
    optimizer = optim.SGD(model.parameters(), lr=args.lr)

def train(epoch):
    model.train()
    acc_loss = 0
    acc_kl_theta_loss = 0
    cnt = 0
    indices = torch.randperm(args.num_docs_train)
    indices = torch.split(indices, args.batch_size)
    for idx, ind in enumerate(indices):
        optimizer.zero_grad()
        model.zero_grad()
        data_batch = data.get_batch(train_tokens, train_counts, ind, args.vocab_size, device)
        sums = data_batch.sum(1).unsqueeze(1)
        if args.bow_norm:
            normalized_data_batch = data_batch / sums
        else:
            normalized_data_batch = data_batch
        recon_loss, kld_theta = model(data_batch, normalized_data_batch)
        total_loss = recon_loss + kld_theta
        total_loss.backward()

        if args.clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
        optimizer.step()

        acc_loss += torch.sum(recon_loss).item()
        acc_kl_theta_loss += torch.sum(kld_theta).item()
        cnt += 1

        if idx % args.log_interval == 0 and idx > 0:
            cur_loss = round(acc_loss / cnt, 2) 
            cur_kl_theta = round(acc_kl_theta_loss / cnt, 2) 
            cur_real_loss = round(cur_loss + cur_kl_theta, 2)

            print('Epoch: {} .. batch: {}/{} .. LR: {} .. KL_theta: {} .. Rec_loss: {} .. NELBO: {}'.format(
                epoch, idx, len(indices), optimizer.param_groups[0]['lr'], cur_kl_theta, cur_loss, cur_real_loss),file=sys.stderr)
    
    cur_loss = round(acc_loss / cnt, 2) 
    cur_kl_theta = round(acc_kl_theta_loss / cnt, 2) 
    cur_real_loss = round(cur_loss + cur_kl_theta, 2)
    print('*'*100,file=outfile)
    print('Epoch----->{} .. LR: {} .. KL_theta: {} .. Rec_loss: {} .. NELBO: {}'.format(
            epoch, optimizer.param_groups[0]['lr'], cur_kl_theta, cur_loss, cur_real_loss),file=outfile)
    print('*'*100,file=outfile)
    return cur_kl_theta, cur_real_loss

def visualize(m, show_emb=True):
    if not os.path.exists('./results'):
        os.makedirs('./results')

    m.eval()

    ## visualize topics using monte carlo
    with torch.no_grad():
        print('#'*100)
        print('Visualize topics...')
        topics_words = []
        gammas = m.get_beta()
        for k in range(args.num_topics):
            gamma = gammas[k]
            top_words = list(gamma.cpu().numpy().argsort()[-args.num_words+1:][::-1])
            topic_words = [vocab[a] for a in top_words]
            topics_words.append(' '.join(topic_words))
            print('Topic {}: {}'.format(k, topic_words),file=outfile)

        if show_emb:
            ## visualize word embeddings by using V to get nearest neighbors
            print('#'*100,file=outfile)
            print('Visualize word embeddings by using output embedding matrix')
            try:
                embeddings = m.rho.weight  # Vocab_size x E
            except:
                embeddings = m.rho         # Vocab_size x E
            neighbors = []
            for word in queries:
                print('word: {} .. neighbors: {}'.format(
                    word, nearest_neighbors(word, embeddings, vocab)),file=outfile)
            print('#'*100,file=outfile)

def evaluate(m, source, tc=False, td=False):
    """Compute perplexity on document completion.
    """
    m.eval()
    with torch.no_grad():
        if source == 'val':
            indices = torch.split(torch.tensor(range(args.num_docs_valid)), args.eval_batch_size)
            tokens = valid_tokens
            counts = valid_counts
        else: 
            indices = torch.split(torch.tensor(range(args.num_docs_test)), args.eval_batch_size)
            tokens = test_tokens
            counts = test_counts

        ## get \beta here
        beta = m.get_beta()

        ### do dc and tc here
        acc_loss = 0
        cnt = 0
        indices_1 = torch.split(torch.tensor(range(args.num_docs_test_1)), args.eval_batch_size)
        for idx, ind in enumerate(indices_1):
            ## get theta from first half of docs
            data_batch_1 = data.get_batch(test_1_tokens, test_1_counts, ind, args.vocab_size, device)
            sums_1 = data_batch_1.sum(1).unsqueeze(1)
            if args.bow_norm:
                normalized_data_batch_1 = data_batch_1 / sums_1
            else:
                normalized_data_batch_1 = data_batch_1
            theta, _ = m.get_theta(normalized_data_batch_1)

            ## get prediction loss using second half
            data_batch_2 = data.get_batch(test_2_tokens, test_2_counts, ind, args.vocab_size, device)
            sums_2 = data_batch_2.sum(1).unsqueeze(1)
            res = torch.mm(theta, beta)
            preds = torch.log(res)
            recon_loss = -(preds * data_batch_2).sum(1)
            
            loss = recon_loss / sums_2.squeeze()
            loss = loss.mean().item()
            acc_loss += loss
            cnt += 1
        cur_loss = acc_loss / cnt
        ppl_dc = round(math.exp(cur_loss), 1)
        print('*'*100,file=outfile)
        print(f'{source.upper()} Doc Completion PPL: {ppl_dc}', file=outfile)
        print('*'*100,file=outfile)
        if tc or td:
            beta = beta.data.cpu().numpy()
            if td:
                td_val=get_topic_diversity(beta, 25) # for top 25 words
                print(f'topic diversity is: {td_val}', file=outfile)
                outfile.flush()
            if tc:
                tc_val=get_topic_coherence(beta, train_tokens, vocab)
                print(f'Topic coherence is: {tc_val}', file=outfile)
            if td and tc:
                print(f'TD*TC={round(td_val*tc_val,4)}', file=outfile)
        return ppl_dc

if args.mode == 'train':
    print('=*'*100)
    print(f'Training an Embedded Topic Model on {args.dataset.upper()} with the following settings: {args}')
    ## train model on data 
    best_epoch = 0
    best_val_ppl = 1e9
    best_kl_theta = 0
    best_nelbo = 1e9
    all_val_ppls = []
    print('\n',file=outfile)
    print('Visualizing model quality before training...',file=outfile)
    visualize(model)
    print('\n',file=outfile)
    for epoch in range(1, args.epochs):
        kl_theta,nelbo=train(epoch)
        val_ppl = evaluate(model, 'val')
        if (args.best=='val_ppl' and val_ppl < best_val_ppl) or (args.best=='kl_theta' and kl_theta > best_kl_theta) or (args.best=='nelbo' and nelbo < best_nelbo):
            with open(ckpt, 'wb') as f:
                torch.save(model, f)
            best_epoch = epoch
            best_val_ppl = val_ppl
            best_kl_theta = kl_theta
            best_nelbo = nelbo
        else:
            ## check whether to anneal lr
            lr = optimizer.param_groups[0]['lr']
            if args.anneal_lr and (len(all_val_ppls) > args.nonmono and val_ppl > min(all_val_ppls[:-args.nonmono]) and lr > 1e-5):
                optimizer.param_groups[0]['lr'] /= args.lr_factor
        if epoch % args.visualize_every == 0:
            visualize(model)
        all_val_ppls.append(val_ppl)
        outfile.flush()
    with open(ckpt, 'rb') as f:
        model = torch.load(f,map_location=torch.device(device))
    model = model.to(device)
    val_ppl = evaluate(model, 'val')
elif args.mode=='eval':   
    with open(ckpt, 'rb') as f:
        model = torch.load(f,map_location=torch.device(device))
    model = model.to(device)
    model.eval()

    with torch.no_grad():
        ## get document completion perplexities
        test_ppl = evaluate(model, 'test', tc=args.tc, td=args.td)
        beta = model.get_beta()

        if args.tp: ## get most used topics
            indices = torch.tensor(range(args.num_docs_train))
            indices = torch.split(indices, args.batch_size)
            thetaAvg = torch.zeros(1, args.num_topics).to(device)
            thetaWeightedAvg = torch.zeros(1, args.num_topics).to(device)
            cnt = 0
            for idx, ind in enumerate(indices):
                data_batch = data.get_batch(train_tokens, train_counts, ind, args.vocab_size, device)
                sums = data_batch.sum(1).unsqueeze(1)
                cnt += sums.sum(0).squeeze().cpu().numpy()
                if args.bow_norm:
                    normalized_data_batch = data_batch / sums
                else:
                    normalized_data_batch = data_batch
                theta, _ = model.get_theta(normalized_data_batch)
                thetaAvg += theta.sum(0).unsqueeze(0) / args.num_docs_train
                weighed_theta = sums * theta
                thetaWeightedAvg += weighed_theta.sum(0).unsqueeze(0)
                if idx % 100 == 0 and idx > 0:
                    print('batch: {}/{}'.format(idx, len(indices)),file=sys.stderr)
            thetaWeightedAvg = thetaWeightedAvg.squeeze().cpu().numpy() / cnt
            toptopics=thetaWeightedAvg.argsort()[::-1][:args.toptopicsnum]
            print(f'\nThe {args.toptopicsnum} most used topics are {toptopics}', file=outfile)
            for k in toptopics:
                gamma = beta[k]
                top_word_ids = list(gamma.cpu().numpy().argsort()[-args.num_words+1:][::-1])
                topic_words = [vocab[a] for a in top_word_ids]
                print(f'Topic {k}: {topic_words}',file=outfile)

        outfile.flush()

        ## show full topics
        print('\n',file=outfile)
        for k in range(args.num_topics):
            gamma = beta[k]
            top_word_ids = list(gamma.cpu().numpy().argsort()[-args.num_words+1:][::-1])
            topic_words = [(vocab[a],float(gamma[a])) for a in top_word_ids]
            print(f'Topic {k}: {topic_words}',file=outfile)

        if args.train_embeddings:
            ## show etm embeddings 
            try:
                rho_etm = model.rho.weight.cpu()
            except:
                rho_etm = model.rho.cpu()
            print('\n',file=outfile)
            print('ETM embeddings...',file=outfile)
            for word in queries:
                print('word: {} .. etm neighbors: {}'.format(word, nearest_neighbors(word, rho_etm, vocab)),file=outfile)
            print('\n',file=outfile)
elif args.mode=='apply':
    with torch.no_grad():
        beta = model.get_beta()
        ## get most used topics
        indices = torch.tensor(range(args.num_docs_train))
        indices = torch.split(indices, args.batch_size)
        thetaAvg = torch.zeros(1, args.num_topics).to(device)
        thetaWeightedAvg = torch.zeros(1, args.num_topics).to(device)
        cnt = 0
        for idx, ind in enumerate(indices):
            data_batch = data.get_batch(train_tokens, train_counts, ind, args.vocab_size, device)
            sums = data_batch.sum(1).unsqueeze(1)
            cnt += sums.sum(0).squeeze().cpu().numpy()
            if args.bow_norm:
                normalized_data_batch = data_batch / sums
            else:
                normalized_data_batch = data_batch
            theta, _ = model.get_theta(normalized_data_batch)
            thetabest = theta.argsort()
            for doc in range(theta.shape[0]): # for each document in the batch
                besttopics = thetabest[doc,-args.topK:].tolist()
                bestvalues = theta[doc,besttopics].tolist()
                lastv=2.0
                out=[]
                for t, v in zip(reversed(besttopics),reversed(bestvalues)):
                    try: # to handle occasional NaNs
                        outtuple=(float(int(v*1000))/1000,t)
                        if args.threshold>0: 
                            if (lastv>1) or (v/lastv>args.threshold): # Outputting only the most significant topics
                                out.append(outtuple)
                                lastv=v
                            else:
                                break
                        else: # or everything
                            out.append(outtuple)
                    except:
                        break
                print(out,file=outfile)
            thetaAvg += theta.sum(0).unsqueeze(0) / args.num_docs_train
            weighed_theta = sums * theta
            thetaWeightedAvg += weighed_theta.sum(0).unsqueeze(0)
            if idx % 100 == 0 and idx > 0:
                print('batch: {}/{}'.format(idx, len(indices)),file=sys.stderr)
        thetaWeightedAvg = thetaWeightedAvg.squeeze().cpu().numpy() / cnt
        print('\nThe 10 most used topics are {}'.format(thetaWeightedAvg.argsort()[::-1][:10]))
xtime=int(time.time())
if args.verbosity>0:
    print('Finished in {} secs'.format(xtime-starttime), file=sys.stderr)
outfile.close()
