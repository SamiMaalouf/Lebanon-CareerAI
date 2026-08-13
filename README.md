# AI-Powered Lebanese Career & Skill Gap Analyzer

**Lebanon CareerAI** turns publicly accessible Lebanese job postings into structured labor-market knowledge, then matches a student CV with both **keyword** and **semantic** methods and produces explainable skill-gap roadmaps.

> Compatibility Score is an analytical estimate and does **not** represent a guarantee of employment.  
> This dataset represents publicly accessible Lebanese job postings collected during the project’s data-collection period — **not** the entire Lebanese job market.

## Problem

Lebanese students face fragmented job ads with inconsistent terminology (e.g. *Siemens PLC* vs *industrial automation*). Keyword search misses semantic relationships. This project builds a data-driven pipeline—not a generic chatbot—to answer: *given what Lebanese employers ask for in the collected postings, where do I fit, and what should I learn next?*

## Architecture

```text
Public sources → collection → cleaning → NLP extraction / classification
        → skill taxonomy → embeddings → PostgreSQL (or SQLite)
                ↘ market APIs
                ↘ CV analysis → keyword + semantic matching → skill gap → roadmap
                                                        → Next.js dashboard
```

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, scikit-learn |
| Embeddings | Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`) with hashing fallback |
| DB | PostgreSQL + pgvector (Docker) or SQLite for local demo |
| Frontend | Next.js 15, Tailwind, Recharts |
| Data | Real Lebanese board collectors (JobsLebanon, Daleel el 3amal, HireLebanese, …) |

## Repository layout

```text
backend/           FastAPI app
data_pipeline/     collectors, cleaning, taxonomy
evaluation/        skill extraction, classification, matching metrics
frontend/          Next.js dashboard (7 pages)
raw_data/          raw postings (gitignored)
processed_data/    cleaned exports + sample fixtures
models/            trained classifiers
reports/           final report template
notebooks/         EDA placeholders
```

## Quick start

### 1. Python environment

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
# Optional (recommended for true semantic embeddings):
pip install sentence-transformers torch
```

### 2. Database

**Option A — SQLite (default, no Docker):**

```bash
# .env already defaults to sqlite:///./careerai.db
```

**Option B — PostgreSQL + pgvector:**

```bash
docker compose up -d db
# set DATABASE_URL=postgresql+psycopg://careerai:careerai@localhost:5432/careerai
```

### 3. Collect & ingest real Lebanese engineering jobs

```powershell
$env:PYTHONPATH = "."
$env:PYTHONUNBUFFERED = "1"
.\.venv\Scripts\python -m data_pipeline.collectors.run_all --min-jobs 200 --min-eng-jobs 100
$env:DATABASE_URL = "postgresql+psycopg://careerai:careerai@localhost:5434/careerai"
.\.venv\Scripts\python -m data_pipeline.collectors.ingest --json raw_data/real_jobs_merged.json --require-real
```

Ingest applies an **engineering + internship gate** by default (sales/marketing/etc. dropped). Use `--all-jobs` only if you intentionally want the unfiltered board dump.

LinkedIn automated scraping is out of scope; public Lebanese boards are the primary real-data path.

### 4. Run evaluation

```bash
python -m evaluation.run_all
```

### 5. Start API

```bash
uvicorn backend.app.main:app --reload --port 8001
```

API docs: [http://localhost:8001/docs](http://localhost:8001/docs)

> If port 8000 is free on your machine you may use `--port 8000` and set `NEXT_PUBLIC_API_URL=http://localhost:8000`.

### 6. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Dashboard pages

1. **Overview** — KPIs, top skills, experiment snapshot  
2. **Job Market** — skills, locations, industries, education, experience, languages  
3. **Career Explorer** — category deep-dive  
4. **CV Analyzer** — PDF/DOCX/TXT upload (ephemeral)  
5. **Job Matching** — keyword vs semantic ranked lists  
6. **Skill Gap** — possessed vs missing  
7. **Career Roadmap** — prioritized skills with dataset-backed “why”

## Matching methodology

### Baseline — keyword

Normalized skill Jaccard + required-skill coverage.

### Proposed — semantic Compatibility Score

```text
0.40 × skill_similarity
+ 0.20 × required_coverage
+ 0.15 × education_compatibility
+ 0.15 × experience_compatibility
+ 0.10 × category_similarity
```

`skill_similarity` blends embedding cosine similarity with taxonomy-related skill overlap.

## Experiments

| Experiment | Metrics |
|------------|---------|
| Skill extraction | Precision, Recall, F1 on labeled subset |
| Job classification | Accuracy, macro P/R/F1, confusion matrix |
| Matching | Precision@K, Recall@K, F1@K, NDCG@K, MRR |

Primary research question: **Does semantic matching retrieve more relevant Lebanese jobs than keyword matching?**

Results are written to `evaluation/*/results.json` and exposed at `GET /api/evaluation/summary`.

## Data collection ethics

- Public job descriptions only; store `source` + `collection_date` + `source_url`
- Respect robots.txt, rate limits, and ToS (`data_pipeline/collectors/html_collector.py`)
- Do not collect private profiles or personal contacts
- Do not redistribute copyrighted full dumps; ship scripts + synthetic/sample fixtures
- CVs processed in memory; not permanently stored by default

## Limitations

- Synthetic demo corpus approximates Lebanese employers/locations for offline development; replace with permitted real collections for research claims
- Classification metrics on synthetic data can be inflated — always re-evaluate on manually labeled real postings
- Salary often missing; geography only reported when enough data exists
- Network hiring and unpublished roles are outside this dataset

## Demo script (≈3 minutes)

1. Overview — show job count and top skills  
2. Career Explorer — Automation Engineering skill demand  
3. Upload / paste a Mechatronics CV  
4. Job Matching — compare keyword vs semantic ranks  
5. Skill Gap + Roadmap — PLC, TIA Portal, SCADA priorities  
6. Evaluation snapshot — Precision@5 keyword vs semantic  

## License / academic use

Built for a Tech Fellows–style research project. Cite sources of any real postings you collect. Keep redistribution compliant with each site’s terms.
"# Career-AI" 
