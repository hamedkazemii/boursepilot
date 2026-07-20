class DecisionEngine:

    def decide(self, bpi_score: int) -> str:

        if bpi_score >= 85:
            return "BUY"

        if bpi_score >= 70:
            return "HOLD"

        return "REDUCE"
