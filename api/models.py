from pydantic import BaseModel, Field, field_validator


class MatchRequest(BaseModel):
    note: str = Field(min_length=10, description="Unstructured patient note")
    location: str | None = Field(default=None, description="Patient location for nearby trial filtering (e.g. Toronto, ON)")


class OptimizeRequest(BaseModel):
    note: str = Field(min_length=10, description="Raw clinical note to optimize")


class OptimizeResponse(BaseModel):
    optimized_note: str
    missing_fields: list[str]


class CriterionResult(BaseModel):
    criterion: str
    status: str
    patient_value: str | None = None

    @field_validator('patient_value', mode='before')
    @classmethod
    def coerce_to_str(cls, v):
        if v is None:
            return None
        return str(v)


class TrialMatch(BaseModel):
    trial_id: str
    trial_name: str
    score: float
    criteria: list[CriterionResult]
    missing_info: list[str]


class MatchResponse(BaseModel):
    patient: dict
    matches: list[TrialMatch]


class TrialSummary(BaseModel):
    trial_id: str
    title: str


class HealthResponse(BaseModel):
    status: str
    model: str


class MetricsResponse(BaseModel):
    total_requests: int
    successful_requests: int
    error_count: int
    avg_latency_ms: float
