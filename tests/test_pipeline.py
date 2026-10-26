from datetime import date, timedelta
from unittest.mock import Mock

from core.models import Verdict
from core import pipeline


def make_verdict(**overrides) -> Verdict:
    values = {
        "document_type": "bill",
        "action_required": True,
        "deadline": (date.today() + timedelta(days=3)).isoformat(),
        "two_line_verdict": "Pay this bill.",
        "confidence": 0.9,
    }
    values.update(overrides)
    return Verdict(**values)


def test_process_file_creates_audio_for_actionable_bill(tmp_path, monkeypatch):
    path = tmp_path / "bill.txt"
    path.write_text("A bill is due soon. Please pay it.")
    monkeypatch.setattr(pipeline.store, "exists", lambda _: False)
    monkeypatch.setattr(pipeline.ocr, "ocr_confidence_ok", lambda _: True)
    monkeypatch.setattr(pipeline.classify, "classify", lambda _: (make_verdict(), "triage"))
    monkeypatch.setattr(pipeline.tts, "speak", lambda text, out: "espeak")

    result = pipeline.process_file(path)

    assert result["tier"] in {"URGENT", "SOON"}
    assert result["audio"] is not None


def test_process_file_low_ocr_confidence_does_not_classify(tmp_path, monkeypatch):
    path = tmp_path / "scan.txt"
    path.write_text("garbled")
    monkeypatch.setattr(pipeline.store, "exists", lambda _: False)
    monkeypatch.setattr(pipeline.ocr, "extract_text", lambda _: ("garbled", 0.2))
    chat = Mock(side_effect=AssertionError("should not be called"))
    monkeypatch.setattr(pipeline.classify, "classify", chat)

    result = pipeline.process_file(path)

    assert result["tier"] == "UNSURE"
    chat.assert_not_called()


def test_process_file_skips_existing_hash(tmp_path, monkeypatch):
    path = tmp_path / "existing.txt"
    path.write_text("already processed")
    monkeypatch.setattr(pipeline.store, "exists", lambda _: True)

    result = pipeline.process_file(path)

    assert result["skipped"] is True


def test_process_dir_dry_run_does_not_persist_or_speak(tmp_path, monkeypatch):
    (tmp_path / "note.txt").write_text("A sufficiently long document for testing.")
    monkeypatch.setattr(pipeline.store, "exists", lambda _: False)
    monkeypatch.setattr(pipeline.store, "upsert", Mock())
    monkeypatch.setattr(pipeline.ocr, "ocr_confidence_ok", lambda _: True)
    monkeypatch.setattr(pipeline.classify, "classify", lambda _: (make_verdict(), "triage"))
    speak = Mock()
    monkeypatch.setattr(pipeline.tts, "speak", speak)

    results = pipeline.process_dir(tmp_path, apply=False)

    assert not pipeline.store.upsert.called
    speak.assert_not_called()
    assert all(result["dry_run"] is True for result in results)
