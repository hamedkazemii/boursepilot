

from core.market_score import MarketScore
from core.decision_engine import DecisionEngine


market={

"queue_buy":True,
"pressure":90,
"change_percent":3,
"sell_volume":0

}


score=MarketScore().calculate(
    market
)


decision=DecisionEngine().decide(
    score["score"]
)


print(score)

print(decision)


assert score["score"]>0

print(
"PIPELINE TEST OK"
)

