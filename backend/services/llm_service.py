import httpx
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from backend.models import LLMServer


def get_llm(server: LLMServer) -> BaseChatModel:
    if server.provider == "ollama":
        return ChatOllama(
            model=server.model,
            base_url=server.url,
        )
    elif server.provider == "openai":
        kwargs = {
            "model": server.model,
            "api_key": server.api_key,
        }
        if server.url and "localhost" in server.url:
            kwargs["base_url"] = server.url
        return ChatOpenAI(**kwargs)
    elif server.provider == "anthropic":
        return ChatAnthropic(
            model=server.model,
            api_key=server.api_key,
        )
    raise ValueError(f"Unknown provider: {server.provider}")


async def check_health(server: LLMServer) -> dict:
    try:
        if server.provider == "ollama":
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{server.url}/api/tags")
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"status": "ok", "models": models}
        elif server.provider in ("openai", "anthropic"):
            return {"status": "ok", "models": [server.model]}
    except Exception as e:
        return {"status": "error", "error": str(e)}
