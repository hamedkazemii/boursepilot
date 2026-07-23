from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InvestorProfile:
    capital: int
    risk: str = "medium"
    horizon: str = "medium"


class PortfolioAdvisor:

    def __init__(self, ranked):
        self.ranked = ranked


    def build(self, profile: InvestorProfile):

        if profile.risk == "low":
            weights = {
                "درآمد ثابت": 70,
                "طلا": 20,
                "سهامی": 10,
                "اهرم": 0,
            }

        elif profile.risk == "high":
            weights = {
                "درآمد ثابت": 20,
                "طلا": 20,
                "سهامی": 35,
                "اهرم": 25,
            }

        else:
            weights = {
                "درآمد ثابت": 45,
                "طلا": 25,
                "سهامی": 20,
                "اهرم": 10,
            }


        groups = {}

        for item in self.ranked:
            ftype = getattr(item, "fund_type", "")
            groups.setdefault(ftype, []).append(item)


        selected = []

        for key, weight in weights.items():

            if weight == 0:
                continue

            candidates = []

            for ftype, items in groups.items():
                if key in ftype:
                    candidates.extend(items)


            if candidates:

                best = max(
                    candidates,
                    key=lambda x: getattr(x, "final_score", 0)
                )

                selected.append(
                    {
                        "symbol": best.symbol,
                        "type": getattr(best, "fund_type", ""),
                        "score": best.final_score,
                        "weight": weight,
                    }
                )


        return {
            "capital": profile.capital,
            "risk": profile.risk,
            "horizon": profile.horizon,
            "allocation": weights,
            "funds": selected,
        }
