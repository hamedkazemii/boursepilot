from core.scoring import FundScore


def main():
    print("📊 BoursePilot")
    print("----------------")

    fund = FundScore(
        name="دارونو",
        nav_score=90,
        performance_score=85,
        risk_score=80,
    )

    bpi = fund.calculate_bpi()

    print(f"🏆 صندوق: {fund.name}")
    print(f"BPI Score: {bpi}/100")
    print()
    print("System Status: OK")


if __name__ == "__main__":
    main()
