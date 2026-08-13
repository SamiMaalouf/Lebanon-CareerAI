# Semantic Job Matching and Skill Gap Analysis for the Lebanese Labor Market

**Project title:** AI-Powered Lebanese Career & Skill Gap Analyzer  

## 1. Abstract

This system collects **real publicly accessible Lebanese job postings** from JobsLebanon, Jobs for Lebanon, Daleel el 3amal, and HireLebanese (best-effort), structures them with NLP skill extraction and classification, embeds jobs and CVs, and compares keyword vs semantic matching for skill-gap recommendations. Synthetic data is retained only as a development fallback—not for primary demo claims.

## 2. Introduction & Problem Statement

Lebanese students face fragmented job ads. The research question remains whether semantic matching improves recommendation quality over keyword overlap on a **real collected Lebanese posting set**.

## 3. Methodology

1. **Collection:** robots-aware collectors with rate limits; raw HTML archived under `raw_data/<source>/`.  
2. **Cleaning / taxonomy / extraction / classification / embeddings.**  
3. **Matching:** keyword Jaccard/coverage vs weighted semantic Compatibility Score.  
4. **Evaluation:** extraction PRF; matching Precision@K / NDCG@K / MRR on graded profiles against real job IDs.

LinkedIn automated scraping is intentionally out of scope.

## 4. Implementation & Results

- Stack: FastAPI, Sentence Transformers, Next.js, PostgreSQL/pgvector.  
- Latest real ingest: **158** engineering (+ internship) postings after quality + engineering gates (from a larger multi-board collect). Categories are rule-first STEM labels (Software, Civil, Electrical, …) with ML fallback inside engineering only.  
- Dashboard: Overview provenance badges, Jobs browser with source URLs, explainable matching.  
- See `evaluation/matching/results.json` and `evaluation/skill_extraction/results.json` for current metrics.

## 5. Discussion & Analysis

Real boards over-represent certain sectors (e.g. sales/HR/hospitality on HireLebanese). Coverage is not the entire Lebanese market. Semantic matching is designed to recover terminology variants; results should be interpreted with dataset bias in mind.

## 6. Reflection on Learnings

Evidence-based career advice requires provenance (source URL + collection date) more than invented market percentages. Ethical collection constraints shaped the architecture as much as model choice.
