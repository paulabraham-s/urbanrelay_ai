"""Explainable AI agents.

Every agent is a deterministic optimization routine that returns an
`AIDecisionRecord` with its decision, reasons, inputs, score and expected
impact, so the AI Decision Center can explain every choice. Agents never
invent facts — all scores derive from measured or simulated inputs.
"""

from dataclasses import dataclass, field


@dataclass
class AIDecisionRecord:
    agent: str
    decision: str
    reasons: list[dict] = field(default_factory=list)   # {label, value, weight?, contribution?}
    inputs: dict = field(default_factory=dict)
    score: float = 0.0
    impact: dict = field(default_factory=dict)

    def to_db_dict(self, run_id: str | None = None) -> dict:
        return {
            "agent": self.agent,
            "run_id": run_id,
            "decision": self.decision,
            "reasons": self.reasons,
            "inputs": self.inputs,
            "score": self.score,
            "impact": self.impact,
        }