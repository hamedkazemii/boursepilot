from services.fund_loader import FundLoader
from services.analyzer import FundAnalyzer
from core.ranking import RankingEngine


funds = FundLoader().load()

analyzer = FundAnalyzer()


results = []


for fund in funds:

    result = analyzer.analyze(
        fund["name"]
    )

    results.append(result)


ranking = RankingEngine().rank(
    results
)


print("📊 رتبه‌بندی BoursePilot")
print("------------------------")


for index, item in enumerate(ranking, start=1):

    print(
        f"{index}) {item.name} | "
        f"BPI: {item.score}/100 | "
        f"{item.decision}"
    )
