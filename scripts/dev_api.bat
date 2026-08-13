@echo off
set PYTHONPATH=%~dp0..
set DATABASE_URL=sqlite:///./careerai.db
cd /d %~dp0..
call .venv\Scripts\activate
python -m data_pipeline.collectors.ingest --synthetic 350
python -m evaluation.run_all
uvicorn backend.app.main:app --reload --port 8000
