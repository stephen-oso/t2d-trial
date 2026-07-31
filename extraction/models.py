from pydantic import BaseModel, Field


class PatientProfile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = None
    months_since_diagnosis: int | None = Field(default=None, ge=0)
    hba1c: float | None = Field(default=None, ge=0.0, le=20.0)
    bmi: float | None = Field(default=None, ge=10.0, le=80.0)
    egfr: float | None = Field(default=None, ge=0.0)
    current_medications: list[str] = []
    on_insulin: bool = False
    exclusion_flags: list[str] = []
