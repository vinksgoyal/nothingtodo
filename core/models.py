import datetime
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Verdict(BaseModel):
    document_type: Literal[
        "eob",
        "bill",
        "legal",
        "tax",
        "statement",
        "marketing",
        "other",
    ]
    action_required: bool
    what_to_do: Optional[str] = Field(
        default=None,
        description="One imperative sentence, max 15 words, or null",
    )
    deadline: Optional[str] = Field(default=None, description="YYYY-MM-DD or null")
    amount_due: Optional[float] = None
    question_to_ask: Optional[str] = Field(
        default=None,
        description="Single question to ask a human, or null",
    )
    two_line_verdict: str = Field(max_length=220)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("deadline", mode="before")
    @classmethod
    def validate_deadline(cls, value: Optional[str]) -> Optional[str]:
        if value == "":
            return None
        if value is not None:
            try:
                datetime.date.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("deadline must be in YYYY-MM-DD format") from exc
        return value

    @field_validator("two_line_verdict")
    @classmethod
    def normalize_two_line_verdict(cls, value: str) -> str:
        return re.sub(r"(?:\r\n|\r|\n)+", " ", value.strip())
