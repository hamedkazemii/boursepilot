from services.analysis.portfolio_analyzer import get_portfolio_analysis

# User 1, portfolio 2 (with 3 holdings added)
text = get_portfolio_analysis(1, 2)
print(text)