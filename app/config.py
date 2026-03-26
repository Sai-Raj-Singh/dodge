from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Gemini (GEMINI_API_KEY — set in .env, see .env.example)
    gemini_api_key: str

    # Neo4j (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD — set in .env, see .env.example)
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # Streamlit → FastAPI base URL including /api prefix (API_BASE — override in .env)
    api_base: str

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"

    # Dataset
    dataset_path: str = "./sap-order-to-cash-dataset/sap-o2c-data"

    # Gemini model names
    gemini_llm_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def dataset_dir(self) -> Path:
        return Path(self.dataset_path)


settings = Settings()
