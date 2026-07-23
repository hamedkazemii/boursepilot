from core.ranking import RankingEngine
from reports.ranking_report import RankingReport
from services.analyzer import FundAnalyzer
from services.fund_loader import FundLoader


def main():

    funds = FundLoader().load()

    analyzer = FundAnalyzer()

    results = []


    for fund in funds:

        result = analyzer.analyze(
            fund["name"]
        )

        results.append(result)


    ranked = RankingEngine().rank(
        results
    )


    report = RankingReport().generate(
        ranked
    )


    print(report)



if __name__ == "__main__":
    main()
