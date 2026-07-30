"""امتیازدهی صندوق‌ها."""

from core.scoring.models import FactorScore, FundAssessment

__all__ = ["FactorScore", "FundAssessment", "ScoreEngine", "load_scoring_config"]


def __getattr__(name: str):
    if name == "ScoreEngine":
        from core.scoring.score_engine import ScoreEngine

        return ScoreEngine
    if name == "load_scoring_config":
        from core.scoring.weights import load_scoring_config

        return load_scoring_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
