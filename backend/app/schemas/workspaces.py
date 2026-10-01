from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import ContractModel, StrictModel


def normalized_domains(domains: list[str]) -> list[str]:
    result = []
    for raw in domains:
        domain = raw.strip().lower().strip(".")
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain or any(char in domain for char in ("/", ":", "@", " ")):
            raise ValueError("excluded_domains must contain hostnames")
        domain = domain.encode("idna").decode("ascii")
        result.append(domain)
    return list(dict.fromkeys(result))


class WorkspaceCreate(StrictModel):
    name: str = Field(min_length=1)
    description: str | None = None
    excluded_domains: list[str] = Field(default_factory=list)

    @field_validator("excluded_domains")
    @classmethod
    def valid_domains(cls, value: list[str]) -> list[str]:
        return normalized_domains(value)


class WorkspaceUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    excluded_domains: list[str] | None = None
    settings: dict | None = None
    view_state: dict | None = None
    tracking: bool | None = None

    @field_validator("excluded_domains")
    @classmethod
    def valid_domains(cls, value: list[str] | None) -> list[str] | None:
        return normalized_domains(value) if value is not None else None


class WorkspaceResponse(ContractModel):
    id: UUID
    name: str
    description: str | None
    excluded_domains: list[str]
    settings: dict
    view_state: dict
    tracking: bool
    page_count: int
    created_at: datetime
    updated_at: datetime


class WorkspaceList(ContractModel):
    items: list[WorkspaceResponse]
