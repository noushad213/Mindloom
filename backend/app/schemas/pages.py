from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ContractModel, StrictModel
from app.services.canonical_url import canonical_url


ExtractionError = Literal["restricted_url", "excluded_domain", "no_permission", "injection_blocked", "empty_content", "pdf_unsupported", "timeout"]


class IngestMeta(StrictModel):
    description: str | None = None
    og_image: str | None = None
    favicon: str | None = None
    lang: str | None = None
    site_name: str | None = None
    byline: str | None = None


class Extraction(StrictModel):
    status: Literal["ok", "failed"]
    method: str = Field(min_length=1)
    error_code: ExtractionError | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def consistent_failure(self):
        if self.status == "failed" and self.error_code is None:
            raise ValueError("error_code is required when extraction fails")
        if self.status == "ok" and self.error_code is not None:
            raise ValueError("error_code must be null when extraction succeeds")
        return self


class IngestTab(StrictModel):
    browser_tab_id: int
    window_id: int | None = None
    active: bool = False


class IngestPayload(StrictModel):
    client_event_id: UUID
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str
    meta: IngestMeta
    extraction: Extraction
    tab: IngestTab
    captured_at: datetime

    @field_validator("client_event_id", mode="before")
    @classmethod
    def parse_event_id(cls, value: object) -> UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise ValueError("client_event_id must be a UUID string")

    @field_validator("captured_at", mode="before")
    @classmethod
    def parse_timestamp(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("captured_at must be an ISO-8601 timestamp")

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        canonical_url(value)
        return value.strip()

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title is required")
        return value.strip()

    @field_validator("captured_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        return value


class Position(ContractModel):
    x: float
    y: float


class PageResponse(ContractModel):
    id: UUID
    workspace_id: UUID
    url: str
    canonical_url: str
    title: str | None
    domain: str | None
    favicon_url: str | None
    og_image_url: str | None
    summary: str | None
    keywords: list[str]
    status: str
    error_code: str | None
    error_message: str | None
    pos: Position | None
    importance: int | None
    tags: list[dict]
    group_ids: list[UUID]
    tab_open: bool
    first_seen_at: datetime
    last_seen_at: datetime
    updated_at: datetime


class TabSessionResponse(ContractModel):
    id: UUID
    page_id: UUID
    browser_tab_id: int
    state: Literal["open", "closed"]
    active: bool
    opened_at: datetime
    last_seen_at: datetime
    closed_at: datetime | None


class IngestResponse(ContractModel):
    page: PageResponse
    tab_session: TabSessionResponse
    created: bool
    duplicate_of: UUID | None
    job: Literal["queued"]


class PageList(ContractModel):
    items: list[PageResponse]
    total: int
    limit: int
    offset: int


class TabSessionList(ContractModel):
    items: list[TabSessionResponse]


class TabSessionUpdate(StrictModel):
    state: Literal["closed"]
