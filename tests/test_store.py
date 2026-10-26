from datetime import date, timedelta

import core.store as store
from core.models import Verdict


def make_verdict() -> Verdict:
    return Verdict(
        document_type="bill",
        action_required=True,
        amount_due=42.0,
        deadline="2026-12-01",
        two_line_verdict="Pay this bill.",
        confidence=0.9,
    )


def test_init_db_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "items.db")

    store.init_db()
    store.init_db()

    assert store.DB_PATH.exists()


def test_upsert_same_hash_yields_one_row(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "items.db")
    verdict = make_verdict()

    first_id = store.upsert("same-hash", verdict, "SOON")
    second_id = store.upsert("same-hash", verdict, "URGENT")

    assert first_id == second_id
    assert len(store.open_items()) == 1


def test_prior_amounts_round_trips_verdict(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "items.db")
    store.upsert("bill-hash", make_verdict(), "SOON")

    assert store.prior_amounts() == [("bill", 42.0)]


def test_snooze_returns_one_then_two(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "items.db")
    item_id = store.upsert("bill-hash", make_verdict(), "SOON")

    assert store.snooze(item_id) == 1
    assert store.snooze(item_id) == 2


def test_resurface_date_caps_at_deadline(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "items.db")
    first_seen = date(2026, 1, 1)

    assert store.resurface_date(
        first_seen,
        snoozes=2,
        deadline=first_seen + timedelta(days=10),
    ) == first_seen + timedelta(days=4)
