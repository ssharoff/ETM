# ETM

My modifications to the code for Embedding Topic Modeling.  My main contributions concern adding a Python script to convert a one-line corpus into a BoW (bag of words) representation and to apply an existing topic model to this dataset. 

First use your own corpus in the one-line per document format to encode it to a BoW matrix:
```
python3 data_new.py -c CORPUS.ol -o DATADIR
```

An example is available in the scripts directory.

The default list of stop words for the first step of BoW processing is for English. The scripts directory also has sample stop word lists for other languages, e.g.,
```
python3 data_new.py -c CORPUS-fr.ol -o DATADIR -s stop-fr.txt
```

If the one-line file has NOT been tokenised, it might be better to tokenise it (and possibly lower-case it) before BoW processing, for example as:
```
./tokenise1.sh <CORPUS-fr.ol | awk '{print(tolower($0))}' >CORPUS-fr.ollc 
```

You can create a new topic model from this dataset and evaluate it:
```
python3 main.py --mode train --dataset dataname --data_path DATADIR --num_topics 50 --train_embeddings 1 --epochs 50
python3 main.py --mode eval --dataset dataname --data_path DATADIR --num_topics 50 --td --tc --tp --load_from results/etm_dataname_K_50....
```

Now this model can be applied to a new corpus by extracting BoW with the same dictionary as your original model first:
```
python3 data_new.py -c CORPUS-NEW.ol -d DATADIR/vocab.pkl -o BOW-NEW
python3 main.py --mode apply --dataset dataname -b BOW-NEW --output CORPUSNEW.topics --load_from results/etm_dataname_K_50....
```

The remainder is practically the same as in the original repository (https://github.com/adjidieng/ETM) apart from more systematic parameters.

This has been tried to work with Python 3.7 and Pytorch 1.7.1, but other versions are likely to be ok as well.

For a large general-purpose corpus, I have achieved fairly good interpretable results by estimating 25 topics on [ukWac](https://wacky.sslmit.unibo.it/doku.php?id=corpora) with the resulting Topic Diversity of 0.78 and Topic Coherence of 0.195. If you have a tokenised corpus in the one-line format, you can apply this model [(downloadable from here)](http://corpus.leeds.ac.uk/serge/corpora/etm_ukwac_K_25_Htheta_530_RhoSize_300) to your corpus by encoding the corpus with the same ukWac dictionary first and then applying the model:
```
python3 data_new.py -c CORPUS-NEW.ol -d ../results/vocab.pkl -o BOW-NEW
python3 main.py --mode apply -b BOW-NEW -d results/vocab.pkl -l results/etm_ukwac_K_25_Htheta_530_RhoSize_300
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
