from services.parsers.fund_parser import FundParser


raw = {

    "name": "دارونو",

    "nav": "125,430",

    "issue_price": "126,000",

    "cancel_price": "124,800"

}


result = FundParser().parse(
    raw
)


print(result)
