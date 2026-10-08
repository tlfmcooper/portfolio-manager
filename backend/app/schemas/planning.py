"""Validated allocation targets for the current portfolio."""
import math
from pydantic import BaseModel, Field, model_validator


class AllocationTargets(BaseModel):
    weights: dict[str, float] = Field(min_length=1, max_length=501)

    @model_validator(mode="after")
    def validate_weights(self):
        if any(not math.isfinite(value) or not 0 <= value <= 100 for value in self.weights.values()):
            raise ValueError("Each target must be a finite percentage from 0 to 100")
        if "CASH" not in self.weights or abs(sum(self.weights.values()) - 100) > 1e-6:
            raise ValueError("Targets, including CASH, must total 100%")
        return self
