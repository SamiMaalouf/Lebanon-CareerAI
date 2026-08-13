from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./careerai.db"
    cors_origins: str = "http://localhost:3000"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    use_llm_extraction: bool = False
    taxonomy_path: str = "data_pipeline/taxonomy/skills.yaml"
    confidence_threshold: float = 0.28
    # Compatibility score weights (semantic matcher)
    w_skill_sim: float = 0.40
    w_required_coverage: float = 0.20
    w_education: float = 0.15
    w_experience: float = 0.15
    w_category: float = 0.10


settings = Settings()
