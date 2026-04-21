import httpx
import ollama as ollama_sdk
from openai import OpenAI
from backend.models import LLMServer


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


def chat(server: LLMServer, messages: list[dict], tools: list[dict] | None = None) -> dict:
    if server.provider == "ollama":
        kwargs = {"model": server.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = ollama_sdk.Client(host=server.url).chat(**kwargs)
        return response["message"]

    elif server.provider == "openai":
        client = OpenAI(api_key=server.api_key, base_url=server.url if "localhost" in server.url else None)
        kwargs = {"model": server.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        result = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            result["tool_calls"] = [
                {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        return result

    elif server.provider == "anthropic":
        return {"role": "assistant", "content": "Anthropic support coming soon."}

    return {"role": "assistant", "content": "Unknown provider."}
