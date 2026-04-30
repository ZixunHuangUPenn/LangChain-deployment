from __future__ import annotations

from pydantic import SecretStr

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .config import Settings, get_settings


def build_chat_model(settings: Settings | None = None) -> ChatOpenAI:
    settings = settings or get_settings()
    kwargs = {
        "model": settings.chat_model,
        "temperature": settings.chat_temperature,
        "max_retries": 2,
        "timeout": 60,
    }
    if settings.chat_api_key:
        kwargs["api_key"] = SecretStr(settings.chat_api_key)
    if settings.chat_api_base_url:
        kwargs["base_url"] = settings.chat_api_base_url
    return ChatOpenAI(**kwargs)


def build_embeddings(settings: Settings | None = None) -> OpenAIEmbeddings:
    settings = settings or get_settings()
    kwargs = {
        "model": settings.embedding_model,
        "max_retries": 2,
        "timeout": 60,
        "check_embedding_ctx_length": False,
    }
    if settings.embedding_api_key:
        kwargs["api_key"] = SecretStr(settings.embedding_api_key)
    if settings.embedding_api_base_url:
        kwargs["base_url"] = settings.embedding_api_base_url
    if settings.embedding_dimensions:
        kwargs["dimensions"] = settings.embedding_dimensions
    return OpenAIEmbeddings(**kwargs)
