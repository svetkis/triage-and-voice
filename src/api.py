"""FastAPI endpoints for triage-and-voice and naive bots."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from examples.shopco.main import build_pipeline
from src.config import get_settings
from src.models import BotResponse, ChatMessage
from src.naive.bot import process_message as naive_process

app = FastAPI(title="Triage & Voice Bot API")

_pipeline = build_pipeline()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


def _gate_internal_fields(response: BotResponse) -> BotResponse:
    """Strip internal observability fields (trace, classification) from
    responses before returning them to clients, unless `expose_trace` is on.

    Both fields carry the same class of data: how the pipeline reached its
    decision. They are useful for eval harnesses and debugging, but leaking
    them to browsers exposes triage internals (intent, harm_state, extracted
    entities) that the public response body should not surface by default.
    """
    if not get_settings().expose_trace:
        response.trace = []
        response.classification = None
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat/triage-voice", response_model=BotResponse)
async def chat_triage_voice(req: ChatRequest) -> BotResponse:
    return _gate_internal_fields(await _pipeline.process_message(req.message, req.history))


@app.post("/chat/naive", response_model=BotResponse)
async def chat_naive(req: ChatRequest) -> BotResponse:
    return _gate_internal_fields(await naive_process(req.message, req.history))
