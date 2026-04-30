from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_DIR.parent


def _load_env_files() -> None:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(PROJECT_DIR / ".env", override=True)


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_DIR / path).resolve()


def _default_embedding_model(base_url: str | None) -> str:
    if base_url and "siliconflow" in base_url.lower():
        return "Qwen/Qwen3-Embedding-4B"
    return "text-embedding-3-small"


@dataclass(frozen=True)
class Settings:
    project_dir: Path
    repo_root: Path
    workspace_dir: Path
    docs_dir: Path
    chroma_dir: Path
    collection_name: str
    chat_api_key: str | None
    chat_api_base_url: str | None
    chat_model: str
    chat_temperature: float
    embedding_model: str
    embedding_api_key: str | None
    embedding_api_base_url: str | None
    embedding_dimensions: int | None
    max_agent_iterations: int
    slack_bot_token: str | None
    slack_signing_secret: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_files()

    dimensions = os.getenv("HUANGCLAW_EMBEDDING_DIMENSIONS")
    workspace_dir = _path_from_env("HUANGCLAW_WORKSPACE_DIR", REPO_ROOT)

    return Settings(
        project_dir=PROJECT_DIR,
        repo_root=REPO_ROOT,
        workspace_dir=workspace_dir,
        docs_dir=_path_from_env("HUANGCLAW_DOCS_DIR", REPO_ROOT / "docs"),
        chroma_dir=_path_from_env("HUANGCLAW_CHROMA_DIR", PROJECT_DIR / "data" / "chroma"),
        collection_name=os.getenv("HUANGCLAW_COLLECTION", "learning_robotics_pdf"),
        chat_api_key=os.getenv("HUANGCLAW_CHAT_API_KEY") or os.getenv("OPENAI_API_KEY") or None,
        chat_api_base_url=os.getenv("HUANGCLAW_CHAT_BASE_URL")
        or os.getenv("OPENAI_API_BASE_URL")
        or None,
        chat_model=os.getenv("HUANGCLAW_CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        chat_temperature=float(os.getenv("HUANGCLAW_CHAT_TEMPERATURE", "0.1")),
        embedding_model=os.getenv("HUANGCLAW_EMBEDDING_MODEL")
        or _default_embedding_model(
            os.getenv("HUANGCLAW_EMBEDDING_BASE_URL") or os.getenv("OPENAI_API_BASE_URL")
        ),
        embedding_api_key=os.getenv("HUANGCLAW_EMBEDDING_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or None,
        embedding_api_base_url=os.getenv("HUANGCLAW_EMBEDDING_BASE_URL")
        or os.getenv("OPENAI_API_BASE_URL")
        or None,
        embedding_dimensions=int(dimensions) if dimensions else None,
        max_agent_iterations=int(os.getenv("HUANGCLAW_MAX_AGENT_ITERATIONS", "8")),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN") or None,
        slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET") or None,
    )
