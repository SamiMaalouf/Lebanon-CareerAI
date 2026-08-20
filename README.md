# AI-Powered Lebanese Career & Skill Gap Analyzer

**Lebanon CareerAI** turns publicly accessible Lebanese job postings into structured labor-market knowledge, then matches a student CV with both **keyword** and **semantic** methods and produces explainable skill-gap coaching.

Code: [https://github.com/SamiMaalouf/Career-AI](https://github.com/SamiMaalouf/Career-AI)

> Compatibility Score is an analytical estimate and does **not** represent a guarantee of employment.  
> This dataset represents publicly accessible Lebanese job postings collected during the project’s data-collection period — **not** the entire Lebanese job market.

## Problem

Lebanese students face fragmented job ads with inconsistent terminology (e.g. *Siemens PLC* vs *industrial automation*). Keyword search misses semantic relationships. Languages and soft skills on a junior CV can look like a match for a senior role if they are treated as tools. This project builds a data-driven pipeline—not a generic chatbot—to answer: *given what Lebanese employers ask for in the collected postings, where do I fit, and what should I learn next?*

## Architecture

```text
Public Lebanese boards → collection → cleaning → NLP extraction / classification
        → skill taxonomy → embeddings → PostgreSQL (or SQLite)
                ↘ market APIs
                ↘ CV analysis → keyword + semantic matching
                        → skill gap / CV Coach → ranked jobs + internships
                                                        → Next.js dashboard
```

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, scikit-learn |
| Embeddings | Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`) with hashing fallback |
| DB | PostgreSQL + pgvector (Docker host port **5434**) or SQLite for local demo |
| Frontend | Next.js 15, Tailwind, Recharts (`http://localhost:3000`) |
| Data | Real Lebanese board collectors (JobsLebanon, Jobs for Lebanon, Daleel el 3amal, HireLebanese, …) |

API default: **http://127.0.0.1:8001**. Docker Compose maps the API as `8001:8000` and Postgres as `5434:5432`.

## Repository layout

```text
backend/           FastAPI app + tests
data_pipeline/     collectors, cleaning, taxonomy
evaluation/        skill extraction, classification, matching metrics
frontend/          Next.js dashboard
raw_data/          raw postings (gitignored)
processed_data/    cleaned exports + sample fixtures
models/            trained classifiers
```

## Quick start

### 1. Python environment

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
```

`sentence-transformers` and `torch` are in `requirements.txt` (needed for real semantic embeddings). Copy [`.env.example`](.env.example) to `.env` and [`frontend/.env.example`](frontend/.env.example) to `frontend/.env.local`.

Set `PYTHONPATH` to the repo root whenever you run Python modules (collect, ingest, API, eval).

### 2. Database

**Option A — SQLite (no Docker):** set `DATABASE_URL=sqlite:///./careerai.db` in `.env`.

**Option B — PostgreSQL + pgvector (recommended):**

```bash
docker compose up -d db
```

Host connection string (matches `.env.example`):

```text
DATABASE_URL=postgresql+psycopg://careerai:careerai@localhost:5434/careerai
```

Inside Compose, the API talks to the db service on port **5432**. On the host, use **5434**.

### 3. Collect & ingest real Lebanese engineering jobs

```powershell
$env:PYTHONPATH = "."
$env:PYTHONUNBUFFERED = "1"
.\.venv\Scripts\python -m data_pipeline.collectors.run_all --min-jobs 200 --min-eng-jobs 100
$env:DATABASE_URL = "postgresql+psycopg://careerai:careerai@localhost:5434/careerai"
.\.venv\Scripts\python -m data_pipeline.collectors.ingest --json raw_data/real_jobs_merged.json --require-real
```

Ingest applies an **engineering + internship gate** by default (sales/marketing/etc. dropped). Use `--all-jobs` only if you intentionally want the unfiltered board dump.

Latest gated demo ingest: **158** engineering and internship postings. LinkedIn automated scraping is out of scope.

### 4. Run evaluation

```bash
python -m evaluation.run_all
```

### 5. Start API

```powershell
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

API docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

Without `--reload`, restart the process after backend code changes (otherwise endpoints such as CV Coach can serve a stale traceback).

The frontend defaults to `http://localhost:8001` if `NEXT_PUBLIC_API_URL` is unset.

### 6. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Tests

```powershell
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m pytest backend/tests
```

(`pytest` is not in `requirements.txt`; install it if needed.)

## Dashboard pages

1. **Overview** — KPIs (jobs vs internships, sources) and the CV → Skill Gap → Ranked jobs path  
2. **Eng. Market** — skills, locations, industries, education, experience, languages  
3. **Eng. Jobs** — browse filters plus **For you** (keyword vs semantic; Ready to apply / Learn first)  
4. **Internships** — browse plus **For you** (`POST /api/match` with `internship=true`)  
5. **Companies** — named employers in the collected set  
6. **CV Analyzer** — PDF/DOCX/TXT upload (ephemeral) and Coach: Fix / Learn / Apply  
7. **Skill Gap** — two-path comparison plus a short learn-next roadmap  

`/careers` redirects to Engineering Jobs.

The skill taxonomy is strongest on software, mechanical, electrical, and mechatronics/robotics. Civil / Architecture has a thinner tool tree (Revit, BIM, ETABS, …).

## Matching methodology

Matching uses **technical skills only** (spoken languages and soft skills are ignored). Coverage is of **that ad’s tool list** (1 of 1 can outrank 5 of 12).

### Baseline — keyword

`0.6 × required-skill coverage + 0.4 × Jaccard` on canonical skill IDs.

### Proposed — semantic Compatibility Score

```text
0.40 × skill_similarity
+ 0.20 × required_coverage
+ 0.15 × education_compatibility
+ 0.15 × experience_compatibility
+ 0.10 × category_similarity
```

`skill_similarity` is `0.5 × embedding cosine + 0.5 × taxonomy-related overlap`. Education / experience / category terms apply only when there is a technical signal, so matching “English” does not inflate a senior software role.

### Student ranking

- Jobs **For you** sends `internship=false`; Internships **For you** sends `internship=true`.
- Junior CVs (Internship / Entry-level / 0–2 years, or internship mentions) get internships and early roles first.
- Senior/lead titles and 2–5 / 5+ year ads are **stretch** and listed under **Learn first**.
- **Ready to apply** = technical coverage ≥ 50% and not stretch.
- Cards show matched vs listed tools and missing skills. Stretch roles are visible; there is no hide-senior toggle.

Coach **Apply** uses the apply band from `rank_jobs` only.

## Experiments

| Experiment | Metrics |
|------------|---------|
| Skill extraction | Precision, Recall, F1 — **circular auto-eval unless `gold.json` is filled** |
| Job classification | Accuracy **64.1%**, macro-F1 **0.46** on 39 held-out ads (11 classes; production labels are rule-first) |
| Matching | Heuristic labels, 3 profiles: semantic **P@5 1.00 / NDCG@5 0.47** vs keyword **P@5 0.73 / NDCG@5 0.28** |

Primary research question: **Does semantic matching retrieve more relevant Lebanese jobs than keyword matching?**

Results live in `evaluation/*/results.json` and `GET /api/evaluation/summary`. Skill-extraction F1 of 1.0 in the checked-in file is **not** a research claim (`gold_source: auto_extractor_circular`). Matching P@K is a relative keyword-vs-semantic comparison, not human relevance judgments.

## Data collection ethics

- Public job descriptions only; store `source` + `collection_date` + `source_url`
- Respect robots.txt, rate limits, and ToS (`data_pipeline/collectors/html_collector.py`)
- Do not collect private profiles or personal contacts
- Do not redistribute copyrighted full dumps; ship scripts + synthetic/sample fixtures
- CVs processed in memory; not permanently stored by default

## Limitations

- Public boards over-represent some sectors; network hiring and unpublished roles are outside this dataset
- Classification was trained on a small, imbalanced set — re-evaluate on manually labeled real postings
- Skill-extraction F1 in auto-eval is circular unless `evaluation/skill_extraction/gold.json` is filled
- Matching P@K uses heuristic relevance labels, not human raters
- Salary often missing; geography only reported when enough data exists
- Hashing fallback embeddings are not true semantics

## Demo (~3 minutes)

1. Overview — job vs internship counts, then Step 1–3  
2. CV Coach — Fix / Learn / Apply  
3. Skill Gap — two paths plus Learn next (optional if short on time)  
4. Jobs → **For you** — keyword vs semantic, Ready to apply / Learn first  
5. Internships → **For you** — open one source URL  

## License / academic use

Built for a Tech Fellows–style research project. Cite sources of any real postings you collect. Keep redistribution compliant with each site’s terms.
