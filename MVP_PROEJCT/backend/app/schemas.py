"""입력 형식만 검증한다. 측정값의 품질 문제는 삭제하지 않고 검사 엔진에 전달한다."""
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class Manifest(BaseModel):
    equipment_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=150)
    software_version: str = Field(min_length=1, max_length=100)
    config_version: str = Field(min_length=1, max_length=100)
    scenario: str = Field(min_length=1, max_length=80)
    tester_software_version: str | None = None


class Measurement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    parameter_id: str = Field(min_length=1, max_length=80)
    timestamp: str | None = None
    value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str | None = None
    run_id: str | None = None
    chamber: str | None = None


class ReleasePayload(BaseModel):
    manifest: Manifest
    measurements: list[Measurement] = Field(min_length=1, max_length=20000)


class CompareRequest(BaseModel):
    baseline_id: int
    candidate_id: int
    profile_id: str


class ReviewRequest(BaseModel):
    disposition: str = Field(pattern='^(APPROVED|HOLD)$')
    reviewer: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=1, max_length=2000)


class DemoRequest(BaseModel):
    scenario: str = Field(pattern='^(baseline|faulty|healthy)$')
