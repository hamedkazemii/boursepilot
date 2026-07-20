#!/bin/bash

set -e

echo "====================================="
echo " BoursePilot Migration v0.2.0"
echo "====================================="


echo "[1/10] Creating directories..."

mkdir -p core
mkdir -p services
mkdir -p reports
mkdir -p data/cache
mkdir -p data/history
mkdir -p tests


echo "[2/10] Updating VERSION..."

cat > VERSION << 'EOT'
0.2.0
EOT


echo "[3/10] Updating requirements..."

cat > requirements.txt << 'EOT'
requests
pandas
openpyxl
python-dotenv
EOT



echo "[4/10] Creating indicators engine..."

cat > core/indicators.py << 'EOT'

class Indicators:


    def demand_ratio(self, market):

        buy = market.get(
            "buy_volume",
            0
        )

        sell = market.get(
            "sell_volume",
            0
        )


        if sell == 0:

            return 100


        return round(
            buy / sell,
            2
        )



    def queue_score(self, market):

        if market.get(
            "queue_buy"
        ):

            return 100


        if market.get(
            "queue_sell"
        ):

            return 0


        return 50



    def trend_score(self, change):

        if change >= 3:

            return 100


        if change >= 0:

            return 70


        return 30

EOT



echo "[5/10] Creating BPI engine..."

cat > core/bpi_engine.py << 'EOT'

from core.indicators import Indicators


class BPIEngine:


    def __init__(self):

        self.indicators = Indicators()



    def calculate(self, market):


        score = 0


        demand = self.indicators.demand_ratio(
            market
        )


        if demand >= 5:

            score += 30

        elif demand >= 2:

            score += 20

        else:

            score += 10



        score += (
            self.indicators.queue_score(
                market
            ) * 0.3
        )



        score += (
            self.indicators.trend_score(
                market.get(
                    "change_percent",
                    0
                )
            ) * 0.3
        )


        return min(
            int(score),
            100
        )

EOT



echo "[6/10] Creating Persian report generator..."

cat > reports/morning_report.py << 'EOT'


def create_report(items):


    lines = []


    lines.append(
        "📊 گزارش صبحگاهی BoursePilot"
    )


    lines.append(
        "="*45
    )


    for index,item in enumerate(items,1):


        lines.append("")


        lines.append(
            f"🏆 رتبه {index}: {item['name']}"
        )


        lines.append(
            f"⭐ امتیاز BPI: {item['bpi']} از 100"
        )


        lines.append(
            "📌 تحلیل:"
        )


        lines.append(
            item.get(
                "summary",
                "اطلاعات تکمیلی موجود نیست"
            )
        )


        lines.append(
            "-"*45
        )


    return "\n".join(lines)


EOT




echo "[7/10] Creating MarketWatch placeholder..."

cat > services/marketwatch.py << 'EOT'


class MarketWatchParser:


    def parse(self,file):

        return []



    def extract_etf(self,data):

        funds=[]


        for row in data:

            name=str(
                row.get(
                    "name",
                    ""
                )
            )


            if "صندوق" in name:

                funds.append(row)


        return funds

EOT




echo "[8/10] Creating test migration..."

cat > tests/test_migration.py << 'EOT'


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

EOT




echo "[9/10] Updating README..."

cat >> README.md << 'EOT'


---

## Version 0.2.0 Migration

Added:

- Live market architecture
- Multi factor BPI engine
- Persian morning report
- MarketWatch preparation
- ETF registry preparation

EOT




echo "[10/10] Running tests..."

python3 -m tests.test_migration


echo ""
echo "====================================="
echo "Migration Completed Successfully"
echo "====================================="


git status

