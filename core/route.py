from datetime import date

from core.models import Verdict


def route(v: Verdict, prior_amounts: list[tuple[str, float]]) -> str:
    if v.confidence < 0.60:
        return "UNSURE"

    if not v.action_required:
        return "SILENT"

    if v.amount_due is not None and any(
        document_type == v.document_type
        and abs(amount - v.amount_due) <= 0.01
        for document_type, amount in prior_amounts
    ):
        return "DUPLICATE"

    if v.deadline is None:
        return "WEEKLY"

    days = (date.fromisoformat(v.deadline) - date.today()).days
    if days <= 7 and v.document_type in {"bill", "legal", "tax"}:
        return "URGENT"

    return "SOON"


def tier_label(tier: str) -> str:
    return {
        "SILENT": "Nothing to do",
        "DUPLICATE": "Possible duplicate",
        "UNSURE": "Couldn't read — needs you",
        "WEEKLY": "Weekly batch",
        "URGENT": "Urgent",
        "SOON": "Soon",
    }[tier]
