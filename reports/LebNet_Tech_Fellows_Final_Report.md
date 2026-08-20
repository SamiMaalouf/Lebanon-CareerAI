Lebanon CareerAI: Semantic Job Matching and Skill-Gap Coaching for Engineering Students
LebNet Tech Fellows — Option 2: AI for Lebanon
Code: https://github.com/SamiMaalouf/Career-AI
Author: Sami Maalouf

1. Project Title & Abstract

Title. Lebanon CareerAI: an AI pipeline that turns publicly posted Lebanese engineering jobs into explainable CV matches and skill-gap advice.

Lebanese students search fragmented job boards whose ads use inconsistent titles and tool names. Keyword search and generic chatbots do not answer a practical question: given what employers in this collected set actually ask for, where does my CV fit, and what should I learn next? This project collects publicly accessible Lebanese postings, extracts skills with a domain taxonomy, embeds jobs and CVs, and compares keyword matching with a semantic Compatibility Score. A dashboard then coaches the student: fix the CV, learn missing tools, and apply to ranked roles (jobs vs internships; ready to apply vs learn first).

On this engineering corpus, semantic ranking outperformed keyword ranking on heuristic relevance labels (Precision@5 1.00 vs 0.73; NDCG@5 0.47 vs 0.28). The system is an analytical aid, not a placement guarantee. Coverage is limited to public ads collected during the project window, not the full Lebanese labor market.

2. Introduction & Problem Statement

Youth unemployment in Lebanon is among the most severe in the region. The CAS/ILO follow-up labor-force survey reported youth unemployment at 47.8% in 2022, with the employment-to-population ratio falling to 30.6% (from 43.3% in 2019). Later assessments put youth unemployment above 50% after the economic collapse and subsequent conflict. Roughly 50,000 young people enter the labor market each year, while formal job creation even before 2019 was estimated at only 11,000–15,000 roles. Engineering and ICT skills remain in demand, yet graduates still face skills mismatch, network-driven hiring, and brain drain.

The student-facing problem is more specific than unemployment. Public boards (JobsLebanon, Jobs for Lebanon, Daleel el 3amal, HireLebanese) mix engineering with sales, hospitality, and HR. The same skill appears under many names (Siemens PLC vs industrial automation; JS vs JavaScript). A junior CV that lists English, Arabic, and teamwork can look like a strong match for a senior software role if matching treats languages and soft skills as equivalent to tools. Internships—the realistic first step—are hard to isolate.

Goals: (1) build a real corpus of Lebanese engineering and internship ads with source, URL, and collection date; (2) normalize messy skill language with a taxonomy covering software, mechanical, electrical, mechatronics/robotics, and civil/architecture; (3) compare keyword vs semantic matching with explainable scores; (4) deliver a student loop: upload CV, Coach (Fix / Learn / Apply), skill-gap roadmap, ranked jobs and internships; (5) keep claims honest—the Compatibility Score is an estimate, and this dataset is not the entire market.

3. Methodology

Data collection. Robots-aware HTML collectors with rate limits archive public job text. LinkedIn automated scraping is out of scope. An engineering and internship gate drops sales, marketing, and hospitality ads. Latest gated ingest used for the demo: 158 engineering and internship postings, drawn from a larger multi-board collect. Each row stores source, source URL, and collection date.

Cleaning and structure. Text and company names are normalized. Skills map through a taxonomy with aliases (js to JavaScript, plc to PLC). Jobs are labeled into STEM categories with rule-first titles and a scikit-learn fallback inside engineering only.

Embeddings. Job and CV text are encoded with Sentence Transformers paraphrase-multilingual-MiniLM-L12-v2 (384 dimensions), chosen because Lebanese ads mix English, Arabic, and French. A hashing encoder is a fallback if the model is not installed. Vectors are stored in PostgreSQL (pgvector) or SQLite.

Keyword baseline. Technical skills only (languages and soft skills ignored). Score = 0.6 × required-skill coverage + 0.4 × Jaccard on canonical skill IDs. Coverage is of that ad’s tool list, so 1 of 1 can outrank 5 of 12.

Semantic Compatibility Score = 0.40 × skill similarity + 0.20 × required coverage + 0.15 × education + 0.15 × experience + 0.10 × category. Skill similarity is 0.5 × embedding cosine + 0.5 × taxonomy-related overlap. Education, experience, and category terms apply only if there is a technical signal, so a CV that only matches “English” does not inflate a senior software role.

Student ranking. Junior CVs (Internship / Entry-level / 0–2 years, or internship mentions) get internships and early roles first. Senior/lead titles and 2–5 / 5+ year ads are marked stretch and grouped under Learn first. A role is Ready to apply when technical coverage is at least 50% and it is not stretch.

CV Coach. Parses PDF, DOCX, or TXT in memory (not stored). Returns CV fixes (for example a missing Projects section), strengths, learn-next tools with market frequency, and apply-now postings from the apply band only.

Evaluation. Skill extraction uses precision, recall, and F1. Classification uses accuracy and macro-F1. Matching uses Precision@K, NDCG@K, and MRR on three student profiles (software, mechatronics, civil) against real job IDs. Matching labels are heuristic (category, title, and skill overlap), not human raters—used only as a relative keyword-vs-semantic test.

4. Implementation Details & Results

Stack. FastAPI and SQLAlchemy; scikit-learn; Sentence Transformers; PostgreSQL/pgvector or SQLite; Next.js 15. Dashboard: Overview KPIs; Job Market charts; Engineering Jobs (browse plus For you, keyword vs semantic); Internships (browse plus For you); CV Analyzer and Coach; Skill Gap (two-path comparison and learn-next).

Matching (heuristic labels, 3 profiles). Semantic retrieval was better on every headline metric:

Method      P@5    P@10   NDCG@5   NDCG@10   MRR
Keyword     0.73   0.60   0.28     0.26      0.83
Semantic    1.00   1.00   0.47     0.55      1.00

The largest gap was software: keyword P@5 = 0.40 vs semantic P@5 = 1.00. Mechatronics was already strong for both at K=5 (P@5 = 1.00); semantic still improved P@10 (1.00 vs 0.80).

Classification. Held-out accuracy 64.1%, macro-F1 0.46 on 39 ads and 11 engineering categories. Train accuracy was 95.6% on 114 ads—overfit risk on a small, imbalanced set. Production labeling is therefore rule-first, with ML as fallback.

Skill extraction. Auto-eval F1 of 1.0 is circular (the extractor labeled its own gold). It is not a research-grade extraction claim.

Qualitative results. On real CVs, Coach separates tools the student already matches from tools the ad still wants. For you lists show matched vs listed skills and what is missing. Internships are a first-class path, not mixed into senior full-time ranks.

5. Discussion & Analysis

The matching results support the hypothesis that semantic plus taxonomy matching retrieves more relevant Lebanese ads than keyword overlap, especially where terminology varies (software/web). They do not prove that a high Compatibility Score causes a hire. Labels are automatic; NDCG remains moderate because many relevant jobs exist in the pool, so recall@5 is inherently low.

Limitations: (1) coverage bias—public boards over-represent some sectors; unpublished and network hires are invisible; (2) small labeled eval—three profiles, heuristic relevance; (3) thinner civil/architecture taxonomy than software; (4) salary and geography often missing; (5) hashing fallback embeddings are not true semantics; (6) classification metrics on this sample are too weak to drive UX labels alone.

Future work: human relevance judgments; a larger gated corpus; Arabic-first CV parsing; university career-center deployment; optional LLM extraction (currently off, to keep the pipeline inspectable).

6. Reflection on Learnings

The most rewarding part was turning a noisy Lebanese board dump into something a student can use in one sitting: upload a CV, see Fix / Learn / Apply, then open a real posting URL. Building a chatbot would have been faster; building a pipeline with source URLs and collection dates taught me that provenance is the product in a crisis labor market. Invented market percentages would have been irresponsible.

The hardest problems were not the embedding model. They were data and ranking policy. Boards mix engineering with sales; an early matcher treated English and Arabic as skills and ranked a junior CV into senior roles; Jaccard over a global skill set hid the fact that a student might cover 1 of 1 tools on a small internship ad and 5 of 12 on a senior ad. I overcame this by gating the corpus, scoring technical skills only, ranking by coverage of that ad, and splitting Ready to apply vs Learn first for junior profiles. Evaluation honesty was another challenge: a circular F1 of 1.0 looks impressive and is meaningless. Documenting that the gold labels were auto-generated mattered more than a flattering table.

If I continued the project, I would invest the next month in human-labeled matching and a partnership with one university career office, not in a larger model. The AI that matters here is the one that tells a Lebanese engineering student, clearly and locally, what to learn next.

References

CAS / ILO. Follow-up Labor Force Survey in Lebanon, 2022. Youth unemployment 47.8%; employment-to-population ratio 30.6%.
UNICEF / labor-market mapping assessments (2024): youth unemployment reported above 50% amid economic collapse and conflict.
GIZ / ILO–UNICEF: about 50,000 youth labor-market entrants per year vs 11,000–15,000 jobs created annually pre-2019.
Reimers, N., and Gurevych, I. (2019). Sentence-BERT. EMNLP. Model used: paraphrase-multilingual-MiniLM-L12-v2.
