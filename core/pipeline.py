import logging
from pathlib import Path

from core import classify, extract as ocr, route, store, tts
from core.models import Verdict


OUT_DIR = Path.home() / ".local/share/nothingtodo"
SUPPORTED_EXTENSIONS = (".txt", ".pdf", ".png", ".jpg", ".jpeg", ".webp")


def _process_file(path: Path, generate_audio: bool = True) -> dict:
    text, ocr_conf = ocr.extract_text(path)
    doc_hash = store.compute_hash(text)
    if store.exists(doc_hash):
        return {"path": str(path), "skipped": True, "reason": "already processed"}

    if not ocr.ocr_confidence_ok(ocr_conf):
        verdict = Verdict(
            document_type="other",
            action_required=False,
            what_to_do=None,
            deadline=None,
            amount_due=None,
            question_to_ask=None,
            two_line_verdict="Couldn't read this one clearly.",
            confidence=0.0,
        )
        tier_source = "ocr_rejected"
        tier = "UNSURE"
    else:
        verdict, tier_source = classify.classify(text)
        tier = route.route(verdict, store.prior_amounts())

    audio_path = None
    if generate_audio and tier in {"URGENT", "SOON", "DUPLICATE"}:
        candidate = OUT_DIR / f"{doc_hash[:8]}.wav"
        try:
            tts.speak(tts.verdict_to_script(verdict), candidate)
            audio_path = candidate
        except Exception as exc:
            logging.warning("TTS failed for %s: %s", path, exc)

    return {
        "path": str(path),
        "verdict": verdict,
        "tier": tier,
        "tier_label": route.tier_label(tier),
        "audio": str(audio_path) if audio_path else None,
        "ocr_conf": ocr_conf,
        "hash": doc_hash,
    }


def process_file(path: Path) -> dict:
    return _process_file(path)


def process_dir(d: Path, apply: bool) -> list[dict]:
    results = []
    paths = sorted(
        path for extension in SUPPORTED_EXTENSIONS for path in d.glob(f"*{extension}")
    )
    for path in paths:
        try:
            result = _process_file(path, generate_audio=apply)
            if apply and "skipped" not in result:
                store.upsert(result["hash"], result["verdict"], result["tier"])
            if not apply:
                result["dry_run"] = True
            results.append(result)
        except Exception as exc:
            logging.exception("Failed to process %s", path)
            results.append({"path": str(path), "error": str(exc)})
    return results
