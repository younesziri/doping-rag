from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secrets: no defaults, so the app refuses to start if they're missing ---
    openai_api_key: str
    mistral_api_key: str

    # --- Infrastructure ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "doping_chunks"

    # --- Models ---
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "mistral-small-latest"

    # --- Chunking & retrieval (you'll tune these in weeks 5–6) ---
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5


settings = Settings()
