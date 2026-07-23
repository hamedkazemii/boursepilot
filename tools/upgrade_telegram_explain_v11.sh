#!/bin/bash

set -e

echo "🚀 Telegram Fund Explain v1.1 upgrade"

mkdir -p services/telegram

cat > services/telegram/fund_commands.py <<'PY'
from services.analysis.fund_explainer import explain_fund


def format_fund_explain(symbol: str) -> str:
    data = explain_fund(symbol)

    if not data:
        return f"❌ صندوق {symbol} پیدا نشد"

    lines=[]

    lines.append(f"📊 تحلیل صندوق {data['symbol']}")
    lines.append("")
    lines.append(f"رتبه بازار: {data['rank']}")
    lines.append(f"امتیاز: {data['score']}")
    lines.append("")
    lines.append(
        f"وضعیت: {data['recommendation']}"
    )

    lines.append("")
    lines.append("نقاط کلیدی:")

    for f in data.get("raw",{}).get("factors",[])[:5]:
        lines.append(
            f"• {f['title']}: {f['label']} ({f['score']})"
        )

    return "\n".join(lines)
PY


cat > tools/test_telegram_explain.py <<'PY'
from services.telegram.fund_commands import format_fund_explain

for s in ["سیگلو","یاقوت","اهرم"]:
    print("="*40)
    print(format_fund_explain(s))
PY


echo "🧪 test"

PYTHONPATH=. python tools/test_telegram_explain.py


echo "✅ Telegram Explain v1.1 ready"

