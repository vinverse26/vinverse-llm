import json
from typing import Optional, List, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

from .mcp_client import fetch_project_context
from .model_router import call_model
from .prompts import SYSTEM_PROMPT, extract_json

app = FastAPI(title="Vinverse LLM Orchestrator")


class ConsultRequest(BaseModel):
    project_id: Optional[str] = None
    message: str
    history: List[Dict[str, str]] = []


class ConsultResponse(BaseModel):
    reply: str
    proposed_state_changes: Optional[Any] = None


@app.post("/consult", response_model=ConsultResponse)
async def consult(payload: ConsultRequest):
    context_block = ""
    if payload.project_id:
        context = await fetch_project_context(payload.project_id)
        context_block = (
            f"CURRENT PROJECT STATE:\n{json.dumps(context['state'], indent=2)}\n\n"
            f"PROJECT DOCUMENTS:\n{json.dumps(context['documents'], indent=2)}\n\n"
        )

    messages = list(payload.history)
    messages.append({"role": "user", "content": context_block + "USER MESSAGE:\n" + payload.message})

    raw_text = await call_model(SYSTEM_PROMPT, messages)
    result = extract_json(raw_text)
    return ConsultResponse(reply=result.get("reply", raw_text), proposed_state_changes=result.get("proposed_state_changes"))


@app.get("/health")
def health():
    return {"status": "ok"}
