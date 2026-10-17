"""Validated public API contracts and immutable disruption scenarios."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Scenario(BaseModel):
    """Capacity reduction applied to selected organizations without database mutation."""

    model_config = ConfigDict(extra="forbid")
    supplier_ids: list[str] = Field(min_length=1, max_length=5)
    reduction: float = Field(default=1.0, ge=0.0, le=1.0)
    depth: int = Field(default=6, ge=1, le=6)
    activate_backups: bool = False
    sku: str | None = Field(default=None, pattern=r"^SKU-\d+$")

    @field_validator("supplier_ids")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        """Reject duplicates and noncanonical organization identifiers."""
        import re  # pylint: disable=import-outside-toplevel

        if len(set(value)) != len(value):
            raise ValueError("Organization IDs must be unique")
        if any(not re.fullmatch(r"(SUP|MFG|DST|RET)-\d{2}", item) for item in value):
            raise ValueError("Expected an organization ID such as SUP-01")
        return value


class Question(BaseModel):
    """Natural-language request with explicitly selected response language."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=5, max_length=600)


class Envelope(BaseModel):
    """Structured JSON response used for evidence-rich endpoints."""

    data: Any
    evidence: dict[str, Any] = Field(default_factory=dict)


class Health(BaseModel):
    """Public runtime readiness information without credentials."""

    status: Literal["ok", "degraded"]
    database: str
    gds: str | None = None
    llm: str | None = None
