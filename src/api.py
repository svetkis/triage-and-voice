"""FastAPI endpoints for triage-and-voice and naive bots."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import get_settings
from src.models import BotResponse, ChatMessage
from src.naive.bot import process_message as naive_process
from src.orchestrator import process_message as triage_process

app = FastAPI(title="Triage & Voice Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


def _gate_trace(response: BotResponse) -> BotResponse:
    if not get_settings().expose_trace:
        response.trace = []
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat/triage-voice", response_model=BotResponse)
async def chat_triage_voice(req: ChatRequest) -> BotResponse:
    return _gate_trace(await triage_process(req.message, req.history))


@app.post("/chat/naive", response_model=BotResponse)
async def chat_naive(req: ChatRequest) -> BotResponse:
    return _gate_trace(await naive_process(req.message, req.history))
