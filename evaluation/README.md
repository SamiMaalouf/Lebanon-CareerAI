# Evaluation notes

## Skill extraction
Labeled template: `skill_extraction/label_template.json`  
Manual gold (optional): `skill_extraction/gold.json`  
Results: `skill_extraction/results.json`

Checked-in F1 of 1.0 is **auto-eval**: gold labels were produced by the same extractor (circular). Do not cite that number as research-grade skill extraction quality.

To replace it, add rows to `gold.json`:

```json
[
  { "job_id": "example_id", "gold_skills": ["python", "git", "sql"] }
]
```

`python -m evaluation.run_all` uses that file when it contains non-empty `gold_skills`; otherwise it records `gold_source: auto_extractor_circular`.

## Classification
Results: `classification/results.json` (accuracy, macro F1, confusion matrix).

Synthetic template jobs are easy to separate by title/description — expect lower metrics on real noisy ads.

## Matching
Labeled set: `matching/labeled_set.json`  
Results: `matching/results.json`

Labels in `build_matching_labels` are **heuristic** (category/title/skill overlap), not human relevance judgments. Use P@K / NDCG as a relative keyword vs semantic comparison only.

Primary comparison: keyword vs semantic Precision@K / NDCG@K / MRR.

Run all:

```bash
python -m evaluation.run_all
```
