from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.graph import build_graph
from agent.state import AgentState
from agent.tools import detect_intent_and_route, extract_query_params


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


def _save_turn(
    conversation_id: str,
    history: list[dict[str, str]],
    user_message: str,
    assistant_message: str,
) -> list[dict[str, str]]:
    updated_history = list(history)
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": assistant_message})
    conversation_store[conversation_id] = updated_history
    return updated_history


@app.post("/api/chat/{conversation_id}/message", response_model=ChatMessageResponse)
def send_message(conversation_id: str, payload: ChatMessageRequest) -> ChatMessageResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    history = conversation_store.get(conversation_id, [])

    route = detect_intent_and_route.invoke({"message": message, "messages": history})
    if route["needs_human"]:
        reply = (
            "I can help with property search, listing details, and booking only. "
            "I am handing this conversation to a human agent."
        )
        _save_turn(conversation_id, history, message, reply)
        return ChatMessageResponse(conversation_id=conversation_id, reply=reply, escalated=True)

    params = extract_query_params.invoke(
        {
            "intent": route["intent"],
            "message": message,
            "messages": history,
        }
    )
    if params["missing_fields"]:
        reply = params["follow_up_question"]
        _save_turn(conversation_id, history, message, reply)
        return ChatMessageResponse(conversation_id=conversation_id, reply=reply, escalated=False)

    state: AgentState = {
        "conversation_id": conversation_id,
        "messages": history + [{"role": "user", "content": message}],
        "user_message": message,
        "intent": route["intent"],
        "executor_target": route["executor_target"],
        "tool_input": params["tool_input"],
        "tool_result": None,
        "final_response": None,
        "needs_human": False,
    }
    result = graph.invoke(state)
    reply = result["final_response"] or "I could not prepare a response."
    _save_turn(conversation_id, history, message, reply)

    return ChatMessageResponse(
        conversation_id=conversation_id,
        reply=reply,
        escalated=result["needs_human"],
    )


@app.get("/api/chat/{conversation_id}/history", response_model=ConversationHistoryResponse)
def get_history(conversation_id: str) -> ConversationHistoryResponse:
    history = conversation_store.get(conversation_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationHistoryResponse(conversation_id=conversation_id, messages=history)
