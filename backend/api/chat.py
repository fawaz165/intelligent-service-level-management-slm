"""
Chat endpoint — the main natural-language interface.

Pipeline:
  User message → LLM → Structured Intent → Validation → Dispatcher → DB → Response

Provides both a standard POST and an SSE streaming endpoint.
"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db, SessionLocal
from backend.database.schemas import ChatRequest, ChatResponse
from backend.services.llm_service import get_intent
from backend.tools.dispatcher import dispatch, execute_confirmed_action

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Process a natural-language message through the ISLM pipeline.

    If confirm_action is provided, execute the pending destructive operation
    instead of calling the LLM.
    """

    # ── Handle confirmation response ─────────────────────────────────
    if req.confirm_action:
        try:
            action = json.loads(req.confirm_action)
        except (json.JSONDecodeError, TypeError):
            return ChatResponse(reply="Invalid confirmation data.", requires_confirmation=False)

        result = await execute_confirmed_action(action, db)
        return ChatResponse(**result)

    # ── Normal chat pipeline ─────────────────────────────────────────
    # 1. Send to LLM for intent extraction
    intent = await get_intent(req.message)

    # 2. Dispatch intent to backend services
    result = await dispatch(intent, db)

    return ChatResponse(**result)


@router.get("/chat/stream")
async def chat_stream(message: str):
    """
    SSE streaming endpoint — sends progress updates while the LLM processes,
    then dispatches the intent and sends the final structured result.

    Events:
      - event: status  → progress update ("Analyzing your request...")
      - event: result  → final structured response (same shape as ChatResponse)
      - event: done    → signals stream end
    """

    async def event_generator():
        # Send immediate feedback so the user knows something is happening
        yield f"event: status\ndata: {json.dumps({'status': 'Analyzing your request...'})}\n\n"

        # Create our own DB session (not via Depends, to avoid early cleanup)
        db = SessionLocal()

        try:
            # 1. Get intent from LLM (this is the slow part)
            yield f"event: status\ndata: {json.dumps({'status': 'Processing with DeepSeek-R1...'})}\n\n"
            intent = await get_intent(message)

            # 2. Dispatch intent to get structured results
            yield f"event: status\ndata: {json.dumps({'status': 'Fetching results...'})}\n\n"
            result = await dispatch(intent, db)

            # 3. Send the final result
            yield f"event: result\ndata: {json.dumps(result, default=str)}\n\n"

        except Exception as e:
            yield f"event: result\ndata: {json.dumps({'reply': f'⚠️ Error: {str(e)}', 'data': None, 'data_type': None, 'requires_confirmation': False, 'pending_action': None})}\n\n"

        finally:
            db.close()

        # Signal completion
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
