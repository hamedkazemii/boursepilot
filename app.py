from core.real_market_scanner import RealMarketScanner
from reports.recommendation_report import save_report



print("="*60)
print("Sandoghchi Real Market Scan")
print("="*60)


scanner=RealMarketScanner()


results=scanner.scan()


print()
print("="*60)
print("TOP RECOMMENDATIONS")
print("="*60)


for r in results[:20]:

    print(
        r["symbol"],
        "|",
        r["type"],
        "|",
        r["score"],
        "|",
        r["decision"]
    )


save_report(results)


print()
print("Saved:")
print("reports/recommendations.json")
print("reports/recommendations.txt")
