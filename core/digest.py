from datetime import date
from pathlib import Path

from core.route import tier_label


TIER_ORDER = ["URGENT", "SOON", "DUPLICATE", "UNSURE", "WEEKLY"]


def render_digest(items: list[dict]) -> str:
    today = date.today().isoformat()
    groups = {
        tier: [item for item in items if item.get("tier") == tier]
        for tier in TIER_ORDER
    }
    if not any(groups.values()):
        return f"# While you slept — {today}\n\nNothing needed you.\n"

    lines = [f"# While you slept — {today}", ""]
    for tier in TIER_ORDER:
        group = groups[tier]
        if not group:
            continue
        lines.extend([f"## {tier_label(tier)}", ""])
        for item in group:
            verdict = item["verdict"]
            action = verdict.what_to_do or verdict.question_to_ask or "see below"
            suffix = ""
            if tier == "DUPLICATE":
                suffix = f" _(same amount as a previous {verdict.document_type})_"
            lines.append(f"- **{verdict.two_line_verdict}** — {action}{suffix}")
            details = []
            if item.get("deadline"):
                details.append(f"deadline: {item['deadline']}")
            if item.get("snoozes", 0) > 0:
                details.append(f"snoozes: {item['snoozes']}")
            if details:
                lines.append(f"  {' · '.join(details)}")
        lines.append("")
    return "\n".join(lines)


def write_digest(content: str) -> Path:
    path = Path.home() / f".local/share/nothingtodo/digest-{date.today().isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    try:
        from rich.console import Console
    except ImportError:
        print(content)
    else:
        Console().print(content)
    return path
