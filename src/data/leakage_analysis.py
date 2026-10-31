import csv
import re
from collections import Counter, defaultdict

records = list(csv.DictReader(open('data/processed/achievement_classification_dataset.csv', encoding='utf-8')))

print('--- 1. Category Name Keyword Frequency in Text ---')
for cat in sorted(set(r['category'] for r in records)):
    cat_recs = [r for r in records if r['category'] == cat]
    kw = cat.lower().replace('_', ' ')
    if cat == 'RESEARCH_PUBLICATION':
        kws = ['publication', 'published', 'paper', 'journal']
    elif cat == 'VOLUNTEERING':
        kws = ['volunteer', 'volunteering', 'community service', 'social service']
    elif cat == 'OTHER':
        kws = ['other', 'fellowship', 'scholarship', 'medal']
    elif cat == 'CULTURAL':
        kws = ['cultural', 'music', 'dance', 'drama', 'debate', 'arts', 'fine arts']
    elif cat == 'SPORTS':
        kws = ['sport', 'sports', 'badminton', 'athletics', 'cricket', 'football', 'basketball', 'chess', 'tournament']
    elif cat == 'LEADERSHIP':
        kws = ['lead', 'leader', 'president', 'secretary', 'head', 'coordinator', 'convener', 'club']
    else:
        kws = [kw]
        
    hits = sum(1 for r in cat_recs if any(k in r['achievement_text'].lower() for k in kws))
    print(f'{cat:<22}: {hits:>3} / {len(cat_recs)} ({hits/len(cat_recs):.1%}) contain indicative keywords')

print('\n--- 2. Mean Text Length by Category ---')
for cat in sorted(set(r['category'] for r in records)):
    cat_recs = [r for r in records if r['category'] == cat]
    lens = [len(r['achievement_text']) for r in cat_recs]
    words = [len(r['achievement_text'].split()) for r in cat_recs]
    print(f'{cat:<22}: Mean Chars = {sum(lens)/len(lens):.1f}, Mean Words = {sum(words)/len(words):.1f}')

print('\n--- 3. Outcome Shortcut Analysis ---')
outcome_cat = defaultdict(Counter)
for r in records:
    outcome_cat[r['outcome']][r['category']] += 1

for out, cats in sorted(outcome_cat.items()):
    top_cat, top_cnt = cats.most_common(1)[0]
    total = sum(cats.values())
    if top_cnt / total >= 0.7:
        print(f'Outcome "{out}" -> {top_cat}: {top_cnt}/{total} ({top_cnt/total:.1%}) highly concentrated')
