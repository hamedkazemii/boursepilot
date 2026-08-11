from services.analysis.portfolio_analyzer import get_portfolio_analysis

# Real user 1 (telegram 182782238) owns portfolio 1 with 3 funds
text = get_portfolio_analysis(1, 1)
print(text)