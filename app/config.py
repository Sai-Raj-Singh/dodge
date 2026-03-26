from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Gemini
    gemini_api_key: str = "AIzaSyCdF2DGLYBwCLap5RzH5airEGmQ2STixhY"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "dodge_password_123"

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
