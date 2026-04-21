from typing import Optional
from sqlmodel import SQLModel, Field, JSON, Column
from datetime import datetime


class LLMServer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    provider: str  # ollama, openai, anthropic
    url: str  # e.g. http://localhost:11434
    model: str  # e.g. qwen3.5:9b
    api_key: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MCPServer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str  # e.g. http://localhost:3000
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    system_prompt: str = "You are a helpful assistant."
    llm_server_id: int = Field(foreign_key="llmserver.id")
    tool_ids: list = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
