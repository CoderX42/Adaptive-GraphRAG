from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_model: str = "llama3.1:8b"
    ollama_host: str = "http://localhost:11434"

    embedding_model: str = "nomic-embed-text"

    chunk_size: int = 512
    chunk_overlap: int = 128

    top_k: int = 5
    graph_similarity_threshold: float = 0.85

    data_dir: Path = Path("data")
    chroma_dir: Path = Path("data/chroma_db")
    graph_cache_path: Path = Path("data/graph_cache.pkl")
    sqlite_path: Path = Path("data/metadata.db")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "raw_docs").mkdir(parents=True, exist_ok=True)


settings = Settings()
