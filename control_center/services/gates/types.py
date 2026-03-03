from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GateEvalResult:
    passed: bool
    summary: str
