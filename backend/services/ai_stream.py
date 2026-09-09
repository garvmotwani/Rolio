"""
Streaming AI support — yields tokens as they arrive from Nemotron/Gemini.
"""

import asyncio
import hashlib
import json
import logging
from typing import AsyncGenerator

import httpx

from config import NEMOTRON_API_KEY, GEMINI_API_KEY, NEMOTRON_MODEL, GEMINI_MODEL
from services.ai_provider import (
    _truncate_prompt, _check_ai_rate_limit, _strip_thinking,
    PROMPT_MAX_CHARS,
)

logger = logging.getLogger("rolio.ai.stream")


async def stream_nemotron(
    prompt: str,
    system: str = "",
    max_tokens: int = 500,
    user_id: int = 0,
) -> AsyncGenerator[str, None]:
    """Yield tokens from Nemotron via NVIDIA NIM streaming."""
    if not NEMOTRON_API_KEY:
        yield "AI provider is not configured."
        return

    if user_id and not _check_ai_rate_limit(user_id):
        yield "AI rate limit exceeded. Please try again later."
        return

    prompt = _truncate_prompt(prompt)
    system = system[:600]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": NEMOTRON_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {NEMOTRON_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=httpx.Timeout(60.0, connect=10.0),
            ) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    logger.error("Nemotron stream %d: %s", resp.status_code, error_body[:200])
                    yield "Sorry, AI service is temporarily unavailable."
                    return

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    except httpx.TimeoutException:
        logger.error("Nemotron stream timeout")
        yield "AI response timed out. Please try again."
    except Exception as e:
        logger.error("Nemotron stream error: %s", str(e)[:200])
        yield "Connection error with AI service."


async def stream_gemini(
    prompt: str,
    system: str = "",
    max_tokens: int = 500,
) -> AsyncGenerator[str, None]:
    """Gemini doesn't support streaming via REST easily, so we do a non-streaming call
    but yield tokens character by character to simulate streaming for consistent UX."""
    if not GEMINI_API_KEY:
        yield "AI provider is not configured."
        return

    prompt = _truncate_prompt(prompt)
    system = system[:600]

    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": system}]})
        contents.append({"role": "model", "parts": [{"text": "OK"}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": max_tokens,
                        "topP": 0.9,
                    },
                },
                timeout=60.0,
            )
            if resp.status_code == 200:
                # Gemini streams JSON array chunks
                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    if "text" in p:
                                        yield p["text"]
                        except json.JSONDecodeError:
                            continue
            else:
                logger.error("Gemini stream %d", resp.status_code)
                yield "AI service temporarily unavailable."
    except Exception as e:
        logger.error("Gemini stream error: %s", str(e)[:200])
        yield "Connection error with AI service."


async def stream_ai(
    prompt: str,
    system: str = "",
    max_tokens: int = 500,
    user_id: int = 0,
) -> AsyncGenerator[str, None]:
    """Unified streaming interface — tries Nemotron first, falls back to Gemini."""
    if NEMOTRON_API_KEY:
        async for token in stream_nemotron(prompt, system, max_tokens, user_id):
            yield token
        return

    if GEMINI_API_KEY:
        async for token in stream_gemini(prompt, system, max_tokens):
            yield token
        return

    yield "No AI provider configured. Please add NEMOTRON_API_KEY."
