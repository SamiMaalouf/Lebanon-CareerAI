# Evaluation notes

## Skill extraction
Labeled template: `skill_extraction/label_template.json`  
Results: `skill_extraction/results.json`

On the synthetic demo corpus, gold labels are approximated from the same taxonomy matcher applied to requirements text. **Replace with manual labels on ~100 real postings before publishing research claims.**

## Classification
Results: `classification/results.json` (accuracy, macro F1, confusion matrix).

Synthetic template jobs are easy to separate by title/description — expect lower metrics on real noisy ads.

## Matching
Labeled set: `matching/labeled_set.json`  
Results: `matching/results.json`

Primary comparison: keyword vs semantic Precision@K / NDCG@K / MRR.

Run all:

```bash
python -m evaluation.run_all
```
