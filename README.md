# ETM

My modifications to the code for Embedding Topic Modeling.  My main contributions concern a code to convert a one-line corpus into a BoW representation and to apply an existing topic model to this dataset. 

First use your own corpus in the one-line per document format to create a topic model:
```
python3 data_new.py -c CORPUS.ol -s DATADIR
python3 main.py --mode train --dataset dataname --data_path DATADIR --num_topics 50 --train_embeddings 1 --epochs 50
python3 main.py --mode eval --dataset dataname --data_path DATADIR --num_topics 50 --td --tc --tp --load_from results/etm_dataname_K_50....
```
The default list of stop words for corpus encoding is for English. The scripts directory also has sample stop word lists for other languages, e.g.,
```
python3 data_new.py -c CORPUS-fr.ol -s DATADIR -o
```


Now this model can be applied to a new corpus
```
python3 data_new.py -c CORPUS-NEW.ol -d DATADIR/vocab.pkl -s DATADIR-NEW
python3 main.py --mode apply --dataset dataname --data_path DATADIR-NEW --output CORPUSNEW.topics --load_from results/etm_dataname_K_50....
```

The remainder is practically the same as in the original repository (https://github.com/adjidieng/ETM) 

This has been tried with Python 3.7 and Pytorch 1.7.1.
