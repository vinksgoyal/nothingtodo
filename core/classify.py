import logging
import os
import time
from typing import Any

import ollama

from core.models import Verdict
from core.prompts import SYSTEM_PROMPT


def _response_content(response: Any) -> str:
    if isinstance(response, dict):
        message = response["message"]
        return message["content"] if isinstance(message, dict) else message.content
    return response.message.content


def _fallback_verdict() -> Verdict:
    return Verdict(
        document_type="other",
        action_required=False,
        confidence=0.0,
        two_line_verdict="Could not classify this document.",
    )


def _chat(model: str, text: str) -> Verdict:
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extracted mail text:\n\n{text[:2000]}"},
        ],
        format=Verdict.model_json_schema(),
        options={"temperature": 0},
    )
    return Verdict.model_validate_json(_response_content(response))


def classify(text: str) -> tuple[Verdict, str]:
    if not text or len(text.strip()) < 20:
        return (
            Verdict(
                document_type="other",
                action_required=False,
                confidence=0.0,
                two_line_verdict="Could not read this document.",
            ),
            "ocr_rejected",
        )

    started_at = time.perf_counter()
    triage_model = os.environ.get("OLLAMA_MODEL_TRIAGE", "llama3.2:3b")
    try:
        triage_verdict = _chat(triage_model, text)
    except Exception:
        escalate_model = os.environ.get("OLLAMA_MODEL_ESCALATE", "qwen2.5:7b")
        try:
            verdict = _chat(escalate_model, text)
        except Exception:
            verdict = _fallback_verdict()
            tier = "escalate_failed"
        else:
            tier = "escalate"
        logging.info(
            "Classification tier=%s triage_latency_ms=%.2f",
            tier,
            (time.perf_counter() - started_at) * 1000,
        )
        return verdict, tier

    if triage_verdict.confidence < 0.70 or triage_verdict.document_type in {
        "legal",
        "tax",
    }:
        escalate_model = os.environ.get("OLLAMA_MODEL_ESCALATE", "qwen2.5:7b")
        try:
            verdict = _chat(escalate_model, text)
        except Exception:
            verdict = _fallback_verdict()
            tier = "escalate_failed"
        else:
            tier = "escalate"
        logging.info(
            "Classification tier=%s triage_latency_ms=%.2f",
            tier,
            (time.perf_counter() - started_at) * 1000,
        )
        return verdict, tier

    logging.info(
        "Classification tier=triage triage_latency_ms=%.2f",
        (time.perf_counter() - started_at) * 1000,
    )
    return triage_verdict, "triage"
