# ETM

These are some modifications to the code for Embedding Topic Modeling.  My main contributions concern adding a Python script to convert a one-line corpus into a BoW (bag of words) representation and to apply an existing topic model to this dataset. 

First use your own corpus in the one-line per document format to encode it to a BoW matrix:
```
python3 data_new.py -c CORPUS.ol -o DATADIR
```

An example of the source file is available in the scripts directory (covid-tweets-sample.ol.xz).

The default list of stop words for the first step of BoW processing is for English. The scripts directory also has sample stop word lists for other languages, e.g.,
```
python3 data_new.py -c CORPUS-fr.ol -o DATADIR -s stop-fr.txt
```

If your one-line file has NOT been tokenised, it might be better to tokenise it (and possibly lower-case it) before BoW processing, for example as:
```
./tokenise1.sh <CORPUS-fr.ol | awk '{print(tolower($0))}' >CORPUS-fr.ollc 
```

For other languages more advanced pre-processing would be needed, for example, proper segmentation for Chinese or lemmatisation for Russian or Turkish.  Anyway, the ways to estimate a topic model remain the same as long as the file for creating the BoW dataset is in the one-document-per-line format.

You can create a new topic model from this dataset and evaluate it by running:
```
python3 main.py --mode train --dataset name --data_path DATADIR --num_topics 50 --epochs 50
python3 main.py --mode eval --data_path DATADIR --td --tc --tp --load_from results/etm_name_K_50_Htheta_530_RhoSize_300
```

The product of the topic diversity (the --td argument) by the topic coherence (the --tc argument) is a useful measure to evaluate how good the hyper-parameters are.  The most important thing is to choose the right number of topics for your dataset.  For other parameters, please run
```
python3 main.py -h
```

A model can be applied to a new corpus by first making a BoW dataset for it using the *same* dictionary as our original model (the -d argument):
```
python3 data_new.py -c CORPUS-NEW.ol -d DATADIR/vocab.pkl -o BOW-NEW
python3 main.py --mode apply --dataset dataname -b BOW-NEW --output CORPUSNEW.topics --load_from results/etm_dataname_K_50....
```

The remainder is practically the same as in the original repository (https://github.com/adjidieng/ETM) apart from more systematic parameters.

This has been tested to work with Python 3.7 and Pytorch 1.7.1, but other versions are likely to be ok as well.

For a large general-purpose corpus, I have achieved fairly good interpretable results by estimating 25 topics on [ukWac](https://wacky.sslmit.unibo.it/doku.php?id=corpora) with the resulting Topic Diversity of 0.78 and Topic Coherence of 0.195. If you have a tokenised corpus in the one-line format, you can apply this model (from the ./results directory) to your corpus by encoding this corpus first with the same ukWac dictionary into a BoW dataset and then applying the model:
```
python3 scripts/data_new.py -c CORPUS-NEW.ol -d results/vocab.pkl -o BOW-NEW
python3 main.py --mode apply -b BOW-NEW -d results/vocab.pkl -l results/etm_ukwac_K_25_Htheta_350_RhoSize_220
```

I've applied this model to test the degree to which pre-trained language models (like Bert) can be fooled by topic distributions

```
@inproceedings{roussinov-sharoff-2023-bert,
    title = "{BERT} Goes Off-Topic: Investigating the Domain Transfer Challenge using Genre Classification",
    author = "Roussinov, Dmitri  and Sharoff, Serge",
    editor = "Bouamor, Houda  and Pino, Juan  and Bali, Kalika",
    booktitle = "Findings of the Association for Computational Linguistics: EMNLP 2023",
    month = dec,
    year = "2023",
    address = "Singapore",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2023.findings-emnlp.34/",
    doi = "10.18653/v1/2023.findings-emnlp.34",
    pages = "468--483"
}
```


ETM is particularly useful for estimating and interpreting topic models from short texts such as those from social media. I have created this update for our project on analysis of [COVID communication](http://corpus.leeds.ac.uk/serge/covid/) where it was used to estimate the topics of COVID-related texts in our collection:

| id | Keywords | 
|------|------------|
| 0 | patients, disease, infection, respiratory, study, clinical, patient, severe, treatment, symptoms, risk, acute, studies, blood |
| 1 | https, corona, covid, pandemic, virus, lockdown, time, good, today, covid19, read, great, make, day, fight, world, hope, free |
| 3 | play, game, season, year, show, time, love, playing, music, team, dropped, night, video, players, fans, tv, football, person |
| 4 | uk, government, lockdown, coronavirus, people, travel, nhs, restrictions, public, johnson, week, measures, rules, health, boris |
| 5 | health, care, pandemic, public, medical, risk, research, social, patients, services, disease, mental, measures, information |
| 6 | mask, social, distancing, face, wear, hands, hand, wearing, air, water, food, spread, wash, distance, sanitizer, buy, protect |
| 7 | home, work, stay, school, safe, family, children, schools, kids, parents, day, time, online, child, students, friends, families |
| 9 | people, media, stop, government, don, covid, fake, wrong, science, political, pandemic, truth, blame, fear, real, fact, stupid |
| 10 | trump, president, america, white, pandemic, house, vote, police, bill, response, american, biden, election, states, donald |
| 11 | cases, deaths, 2020, 000, total, number, death, confirmed, india, rate, coronavirus, 10, reported, million, 24, recovered, days |
| 12 | virus, vaccine, human, influenza, transmission, diseases, infectious, species, animals, samples, study, infected, strains |
| 13 | corona, india, sir, govt, due, students, situation, pm, exams, lockdown, delhi, indian, exam, fight, modi, minister, request |
| 15 | cells, al, viral, virus, protein, cell, viruses, infection, rna, proteins, human, expression, 10, gene, fig, dna, activity |
| 16 | people, covid, virus, die, death, flu, vaccine, lives, care, dying, don, sick, numbers, homes, infected, risk, immunity, dead |
| 17 | data, model, time, number, based, disease, analysis, information, study, models, results, population, system, set, rate, approach |
| 18 | things, ve, time, don, thing, good, happen, people, lot, feel, happened, bad, back, life, make, ago, years, long, ll |
| 19 | business, money, pay, economy, market, crisis, pandemic, economic, impact, jobs, businesses, industry, financial, food |
| 20 | china, world, virus, country, chinese, pandemic, global, war, people, wuhan, south, spread, africa, human, rights, europe |
| 21 | corona, god, shit, virus, fuck, gonna, fucking, lol, man, love, covid, bc, ass, im, damn, ur, dont, wanna, ppl |
| 22 | positive, test, state, hospital, quarantine, https, covid, coronavirus, health, symptoms, days, city, contact, case, app |
| 24 | https, coronavirus, news, live, latest, amid, outbreak, updates, uk, daily, report, top, bbc, times, wave, breaking, drug, sign |

For example, Topics 0, 15 and 17 are mostly coming from research updates, Topics 11 and 24 are from forwarded news items, while Topics 16, 18, 21 are mostly coming from informal exchanges.  The model also detects topics discussed in specific communities (Topics 4, 10 and 13).


This has been reported in
```
@article{boumechaal2024attitudes,
  title={Attitudes, communicative functions, and lexicogrammatical features of anti-vaccine discourse on Telegram},
  author={Boumechaal, Souad and Sharoff, Serge},
  journal={Applied Corpus Linguistics},
  volume={4},
  number={2},
  year={2024},
  publisher={Elsevier},
  url = "https://ssharoff.github.io/publications/2023-applied-covid.pdf",
  doi="https://doi.org/10.1016/j.acorp.2024.100095"
}
```
