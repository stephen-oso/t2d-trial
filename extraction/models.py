from pydantic import BaseModel, Field


class PatientProfile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = None
    months_since_diagnosis: int | None = Field(default=None, ge=0)
    hba1c: float | None = Field(default=None, ge=0.0, le=20.0)
    fasting_glucose: float | None = Field(default=None, ge=0.0, description="Fasting plasma glucose in mg/dL")
    ogtt_2hr: float | None = Field(default=None, ge=0.0, description="2-hour OGTT glucose in mg/dL")
    bmi: float | None = Field(default=None, ge=10.0, le=80.0)
    egfr: float | None = Field(default=None, ge=0.0)
    ast: float | None = Field(default=None, ge=0.0, description="AST in U/L")
    alt: float | None = Field(default=None, ge=0.0, description="ALT in U/L")
    alp: float | None = Field(default=None, ge=0.0, description="ALP in U/L")
    bilirubin: float | None = Field(default=None, ge=0.0, description="Total bilirubin in mg/dL")
    current_medications: list[str] = []
    on_insulin: bool = False
    exclusion_flags: list[str] = []
