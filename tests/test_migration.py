

from core.bpi_engine import BPIEngine


engine = BPIEngine()


sample = {

"buy_volume":1000000,

"sell_volume":100000,

"change_percent":3,

"queue_buy":True

}


score = engine.calculate(sample)


print()

print("==============================")

print("Migration Test")

print("==============================")

print(
    "BPI:",
    score
)


assert score > 0


print(
    "OK"
)

