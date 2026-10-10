"""Read-only portfolio what-if requests; weights are percentages, including cash."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from app.schemas.planning import AllocationTargets


class ScenarioRequest(BaseModel):
    preset: Literal["current", "msr", "custom"] = "current"
    weights: AllocationTargets | None = None
    currency: Literal["USD", "CAD"] | None = None
    kind: Literal["metrics", "sector-allocation", "efficient-frontier", "monte-carlo", "cppi", "all"] = "all"
    scenarios: int = Field(default=1000, ge=1, le=10000)
    time_horizon: int = Field(default=252, ge=1, le=2520)
    cppi_time_horizon: int | None = Field(default=None, ge=1, le=2520)
    multiplier: int = Field(default=3, ge=1, le=10)
    floor: float = Field(default=0.8, gt=0, le=1)

    @model_validator(mode="after")
    def require_custom_weights(self):
        if (self.preset == "custom") != (self.weights is not None):
            raise ValueError("Provide weights only for the custom preset")
        return self
