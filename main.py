from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.graph import build_graph
from agent.state import AgentState


app = FastAPI(title="StayEase AI Agent")
graph = build_graph()
conversation_store: dict[str, list[dict[str, str]]] = {}


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    conversation_id: str
    reply: str
    escalated: bool


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[dict[str, str]]


@app.post("/api/chat/{conversation_id}/message", response_model=ChatMessageResponse)
def send_message(conversation_id: str, payload: ChatMessageRequest) -> ChatMessageResponse:
    history = conversation_store.get(conversation_id, [])
    state: AgentState = {
        "conversation_id": conversation_id,
        "messages": history,
        "user_message": payload.message,
        "intent": None,
        "search_params": None,
        "listing_id": None,
        "booking_request": None,
        "tool_result": None,
        "final_response": None,
        "needs_human": False,
    }
    result = graph.invoke(state)
    conversation_store[conversation_id] = result["messages"]
    return ChatMessageResponse(
        conversation_id=conversation_id,
        reply=result["final_response"] or "",
        escalated=result["needs_human"],
    )


@app.get("/api/chat/{conversation_id}/history", response_model=ConversationHistoryResponse)
def get_history(conversation_id: str) -> ConversationHistoryResponse:
    history = conversation_store.get(conversation_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationHistoryResponse(conversation_id=conversation_id, messages=history)
