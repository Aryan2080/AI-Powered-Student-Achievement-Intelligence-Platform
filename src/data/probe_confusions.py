import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

train = list(csv.DictReader(open('data/splits/train.csv', encoding='utf-8')))
val = list(csv.DictReader(open('data/splits/validation.csv', encoding='utf-8')))

pairs_to_test = [
    ('HACKATHON', 'COMPETITION'),
    ('PROJECT', 'HACKATHON'),
    ('RESEARCH_PUBLICATION', 'CONFERENCE'),
    ('WORKSHOP', 'CERTIFICATION'),
    ('LEADERSHIP', 'VOLUNTEERING'),
    ('SPORTS', 'CULTURAL'),
    ('INTERNSHIP', 'PROJECT'),
]

print('=== Pairwise Disambiguation Analysis (Vocabulary-Constrained Probe) ===')
for c1, c2 in pairs_to_test:
    sub_train = [r for r in train if r['category'] in (c1, c2)]
    sub_val = [r for r in val if r['category'] in (c1, c2)]
    
    vec = TfidfVectorizer(ngram_range=(1, 1), max_features=100)
    X_tr = vec.fit_transform([r['normalized_text'] for r in sub_train])
    X_v = vec.transform([r['normalized_text'] for r in sub_val])
    
    clf = LogisticRegression(C=0.1, random_state=42)
    clf.fit(X_tr, [r['category'] for r in sub_train])
    
    preds = clf.predict(X_v)
    actuals = [r['category'] for r in sub_val]
    errors = [(sub_val[i]['achievement_id'], actuals[i], preds[i], sub_val[i]['achievement_text'][:90]) for i in range(len(actuals)) if preds[i] != actuals[i]]
    
    print(f'Pair ({c1} vs {c2}): Errors = {len(errors)} / {len(actuals)}')
    for aid, act, pred, txt in errors[:2]:
        print(f'   {aid}: Actual {act} -> Pred {pred} | "{txt}..."')
