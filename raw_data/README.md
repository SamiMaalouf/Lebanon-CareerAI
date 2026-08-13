# Raw job data

Collected public Lebanese job postings live here (gitignored contents).

## Collect real data

```powershell
$env:PYTHONPATH = "c:\Users\Admin\AI Job"
$env:PYTHONUNBUFFERED = "1"
.\.venv\Scripts\python -m data_pipeline.collectors.run_all --min-jobs 500
```

Sources (see README for robots stance):

- JobsLebanon
- Jobs for Lebanon (admin-ajax listing + job pages)
- Daleel el 3amal
- HireLebanese (best-effort; robots.txt missing)
- Daleel Madani when reachable

Quality gates drop short/junk/non-Lebanon/duplicate rows before merge.
## Ingest (reject synthetic)

```powershell
$env:DATABASE_URL = "postgresql+psycopg://careerai:careerai@localhost:5434/careerai"
.\.venv\Scripts\python -m data_pipeline.collectors.ingest --json raw_data/real_jobs_merged.json --require-real
```

## Import your own CSV/Excel/JSON

```powershell
.\.venv\Scripts\python -m data_pipeline.collectors.ingest --file path\to\jobs.csv --require-real
```

Required columns: `job_title`, `description`  
Recommended: `company`, `location`, `source`, `source_url`, `collection_date`
