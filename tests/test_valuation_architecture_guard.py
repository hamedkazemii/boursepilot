import ast
import os
import pytest

def test_valuation_resolver_usage():
    """Ensure portfolio valuation paths use ValuationPriceResolver."""
    target_files = [
        "services/analysis/portfolio_analyzer.py",
        "services/telegram_bot.py"
    ]
    
    for file_path in target_files:
        with open(file_path, "r") as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            # Check for direct attribute access (last_price / close_price)
            # in context of valuation-related variables
            if isinstance(node, ast.Attribute):
                if node.attr in ['last_price', 'close_price']:
                    # Simple heuristic: if it's accessed on an object that looks like a quote
                    # in a method related to valuation
                    context = ast.get_source_segment(open(file_path).read(), node)
                    assert "quote" not in context, f"Forbidden direct price access in {file_path}: {context}"

def test_market_state_ssot():
    """Ensure current_session() is used for market state."""
    target_files = [
        "services/analysis/portfolio_analyzer.py",
        "services/telegram_bot.py"
    ]
    for file_path in target_files:
        with open(file_path, "r") as f:
            content = f.read()
            # Forbidden manual time checks
            assert "datetime.now" not in content, f"Manual datetime check in {file_path}"
            assert "time.now" not in content, f"Manual time check in {file_path}"
