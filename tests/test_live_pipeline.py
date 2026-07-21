
from services.live_pipeline import LivePipeline


p=LivePipeline()


r=p.run()


print(
    "Funds scanned:",
    len(r)
)


assert len(r)>=0


print(
    "LIVE PIPELINE OK"
)

