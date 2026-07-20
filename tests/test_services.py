from services.nav import NAVService
from services.market_data import MarketDataService
from services.storage import HistoryStorage


def main():

    nav = NAVService()
    market = MarketDataService()
    storage = HistoryStorage()

    fund = "دارونو"

    nav_data = nav.get_nav(fund)
    performance = market.get_fund_performance(fund)

    result = {
        **nav_data,
        **performance
    }

    storage.save(result)

    print(result)


if __name__ == "__main__":
    main()
