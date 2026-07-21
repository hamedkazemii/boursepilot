
from services.live_pipeline import LivePipeline
from reports.live_report import generate


pipeline=LivePipeline()

data=pipeline.run()


generate(data)

