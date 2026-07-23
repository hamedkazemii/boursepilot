import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.analysis.fund_explainer import explain_fund


symbols = sys.argv[1:] or ["یاقوت","رشد","سیگلو","اهرم"]

for s in symbols:
    x = explain_fund(s)

    print("\n======", s, "======")
    print("rank:", x.get("rank"))
    print("score:", x.get("score"))
    print("recommendation:", x.get("recommendation"))

    raw = x.get("raw", {})
    print("factors:", len(raw.get("factors", [])))

    for f in raw.get("factors", [])[:3]:
        print(
            "-",
            f.get("title"),
            ":",
            f.get("label"),
            "|",
            f.get("score")
        )
