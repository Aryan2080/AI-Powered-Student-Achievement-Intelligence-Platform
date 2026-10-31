import csv
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

train = list(csv.DictReader(open('data/splits/train.csv', encoding='utf-8')))
val = list(csv.DictReader(open('data/splits/validation.csv', encoding='utf-8')))

stop_keywords = [
    'hackathon', 'sprint', 'competition', 'olympiad', 'contest',
    'paper', 'journal', 'published', 'conference', 'symposium', 'proceedings',
    'workshop', 'bootcamp', 'training', 'certification', 'certified', 'credential',
    'internship', 'intern', 'trainee', 'volunteer', 'volunteering', 'community service',
    'elected', 'secretary', 'president', 'patent', 'co-inventor', 'claims',
    'badminton', 'athletics', 'cricket', 'football', 'drama', 'debate', 'dance', 'music'
]

pattern = re.compile(r'\b(' + '|'.join(stop_keywords) + r')\b', re.IGNORECASE)

x_tr_scrubbed = [pattern.sub('', r['normalized_text']) for r in train]
x_v_scrubbed = [pattern.sub('', r['normalized_text']) for r in val]

vec = TfidfVectorizer(ngram_range=(1, 2), max_features=3000, sublinear_tf=True)
X_tr = vec.fit_transform(x_tr_scrubbed)
X_v = vec.transform(x_v_scrubbed)

clf = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
clf.fit(X_tr, [r['category'] for r in train])

preds = clf.predict(X_v)
actuals = [r['category'] for r in val]

errors = [(val[i]['achievement_id'], actuals[i], preds[i], val[i]['achievement_text']) for i in range(len(actuals)) if preds[i] != actuals[i]]

print(f"Scrubbed Keyword Test: Total Validation Errors = {len(errors)} / {len(actuals)}")
for aid, act, pred, txt in errors:
    print(f"  {aid}: Actual {act:<20} -> Predicted {pred:<20}")
    print(f"     \"{txt[:100]}...\"")
