#!/bin/bash
set -e

echo "🚀 Portfolio Selector v1.4.1"


python - <<'PY'

from pathlib import Path

p=Path("services/advisor/portfolio_advisor.py")

text=p.read_text()


text=text.replace(
"""        selected=[]

        used={}

        for item in funds:

            ftype=getattr(item,"fund_type","")

            for key,w in weights.items():

                if key in ftype and used.get(key,0)==0:
                    selected.append({
                        "symbol":item.symbol,
                        "type":ftype,
                        "score":item.final_score,
                        "weight":w
                    })
                    used[key]=1
""",
"""
        selected=[]

        groups={}

        for item in funds:
            ftype=getattr(item,"fund_type","")
            groups.setdefault(ftype,[]).append(item)


        for key,w in weights.items():

            candidates=[]

            for ftype,items in groups.items():
                if key in ftype:
                    candidates.extend(items)


            if candidates:

                best=max(
                    candidates,
                    key=lambda x:getattr(x,"final_score",0)
                )

                selected.append({
                    "symbol":best.symbol,
                    "type":getattr(best,"fund_type",""),
                    "score":best.final_score,
                    "weight":w
                })
"""
)


p.write_text(text)

print("patched")

PY


python tools/test_advisor_v14.py

echo "✅ Portfolio Selector v1.4.1 READY"

