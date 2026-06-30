from __future__ import annotations
import asyncio
import json
import os
from typing import AsyncGenerator

import aio_pika
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .schemas import ChatSummary, Message, SendRequest

SEND_QUEUE = "whatsapp-send"
MESSAGE_EVENTS = ["messages.upsert", "send.message"]
ALEXA_URL = os.environ.get("ALEXA_URL", "http://alexa:8000")
ALEXA_PREFIX = "a."

router = APIRouter()


@router.get("/chats", response_model=list[ChatSummary])
async def list_chats(request: Request):
    rows = await request.app.state.pg.fetch("""
        SELECT
            remote_jid,
            MAX(payload->'data'->>'pushName') FILTER (WHERE from_me = false) AS contact_name,
            COUNT(*) AS total_messages,
            MAX(received_at) AS last_message_at,
            (
                SELECT COALESCE(
                    m2.payload->'data'->'message'->>'conversation',
                    m2.payload->'data'->'message'->'extendedTextMessage'->>'text',
                    '[media]'
                )
                FROM whatsapp_messages m2
                WHERE m2.remote_jid = m1.remote_jid
                  AND m2.event = ANY($1::text[])
                ORDER BY m2.received_at DESC
                LIMIT 1
            ) AS last_message_text
        FROM whatsapp_messages m1
        WHERE remote_jid IS NOT NULL
          AND event = ANY($1::text[])
        GROUP BY remote_jid
        ORDER BY MAX(received_at) DESC
    """, MESSAGE_EVENTS)
    return [ChatSummary(**dict(r)) for r in rows]


@router.get("/messages/{jid:path}", response_model=list[Message])
async def list_messages(jid: str, request: Request, limit: int = 200):
    rows = await request.app.state.pg.fetch("""
        SELECT id, event, remote_jid, from_me, payload, received_at
        FROM whatsapp_messages
        WHERE remote_jid = $1
          AND event = ANY($2::text[])
        ORDER BY received_at ASC
        LIMIT $3
    """, jid, MESSAGE_EVENTS, limit)
    return [Message(**dict(r)) for r in rows]


@router.post("/send")
async def send_message(body: SendRequest, request: Request):
    text = body.text

    if text.startswith(ALEXA_PREFIX):
        command = text[len(ALEXA_PREFIX):].strip()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ALEXA_URL}/command",
                json={"text": command},
                timeout=15.0,
            )
            resp.raise_for_status()
        return {"alexa": True, "text": command}

    payload = {
        "number": body.number,
        "text": text,
        "instance": body.instance or request.app.state.evolution_instance,
    }
    conn = await aio_pika.connect_robust(request.app.state.mq_uri)
    async with conn:
        ch = await conn.channel()
        await ch.declare_queue(SEND_QUEUE, durable=True)
        await ch.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=SEND_QUEUE,
        )
    return {"queued": True}


@router.get("/events")
async def sse_events(request: Request):
    subs: set[asyncio.Queue] = request.app.state.sse_subs
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    subs.add(q)

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(msg)}\n\n".encode()
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            subs.discard(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
