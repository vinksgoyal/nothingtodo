import logging
import shutil
import subprocess
from datetime import date
from pathlib import Path
import re

from core.models import Verdict


VOICE_ONNX = Path.home() / ".local/share/nothingtodo/voice.onnx"


def _backend() -> str:
    if shutil.which("piper"):
        return "piper"
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    if shutil.which("espeak"):
        return "espeak"
    raise RuntimeError("No TTS backend found. Install piper-tts or espeak-ng.")


def speak(text: str, out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    backend = _backend()
    if backend == "piper" and not VOICE_ONNX.exists():
        backend = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
        if not shutil.which(backend):
            raise FileNotFoundError(
                f"{VOICE_ONNX} is missing; run `make voice` to install the Piper voice."
            )

    if backend == "piper":
        command = [
            "piper",
            "--model",
            str(VOICE_ONNX),
            "--output_file",
            str(out_path),
            "--length_scale",
            "1.35",
        ]
        input_data: bytes | str = text.encode()
    else:
        command = [backend, "-s", "130", "-w", str(out_path), text]
        input_data = None

    result = subprocess.run(
        command,
        input=input_data,
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else result.stderr
        logging.error("%s TTS failed: %s", backend, stderr)
        raise RuntimeError(f"{backend} TTS failed with exit code {result.returncode}")
    return backend


_DOCUMENT_NAMES = {
    "eob": "an explanation of benefits",
    "bill": "a bill",
    "legal": "a legal notice",
    "tax": "a tax notice",
    "statement": "a statement",
    "marketing": "an advertisement",
    "other": "a letter",
}


def _num_to_words(n: int) -> str:
    ones = [
        "zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if n < 20:
        return ones[n]
    return tens[n // 10] + (f" {ones[n % 10]}" if n % 10 else "")


def _deadline_phrase(deadline: str) -> str:
    try:
        days = (date.fromisoformat(deadline) - date.today()).days
    except ValueError:
        return "later this month"
    if days < 7:
        return "soon"
    if days < 21:
        return "in a couple weeks"
    return "later this month"


def verdict_to_script(v: Verdict) -> str:
    sentence = f"This is {_DOCUMENT_NAMES[v.document_type]}."
    detail = v.two_line_verdict if len(v.two_line_verdict) < 120 else (
        v.what_to_do or "Please look at this one."
    )
    if v.amount_due is not None:
        if v.amount_due < 100:
            amount = _num_to_words(int(v.amount_due)) + " dollars"
        else:
            amount = "an amount"
        detail = re.sub(r"\$?\d+(?:\.\d+)?", amount, detail, count=1)
        if str(int(v.amount_due)) not in detail and amount not in detail:
            detail = f"{detail} The amount is {amount}."
    if v.deadline:
        deadline_phrase = _deadline_phrase(v.deadline)
        updated_detail = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", deadline_phrase, detail)
        if updated_detail == detail:
            detail = f"{detail.rstrip('.')} The deadline is {deadline_phrase}."
        else:
            detail = updated_detail
    detail = re.sub(r"\b\d{5,}\b", "that number", detail)
    sentences = [sentence, detail.rstrip(".") + "."]
    if v.question_to_ask:
        sentences.append(f"One question: {v.question_to_ask.rstrip('?')}?" )
    return " ".join(sentences)
