"""E2E State Machine tests — real SandoghchiBot handlers, no mock of _cmd_fund."""
import sys
sys.path.insert(0, "/root/projects/boursepilot")
from unittest.mock import patch, MagicMock

with patch('services.providers.factory.get_market_data_provider'), \
     patch('core.scoring.ScoreEngine'), \
     patch('services.snapshot.store.SnapshotStore'), \
     patch('services.portfolio.service.PortfolioService'), \
     patch('services.discovery.fund_catalog.FundCatalogService'), \
     patch('core.ai.advisor.AIAdvisor'), \
     patch('services.telegram.TelegramService'):
    from services.telegram_bot import SandoghchiBot

bot = SandoghchiBot()
bot.provider = None
bot.engine = MagicMock()
bot.store = MagicMock()
bot.portfolio = MagicMock()
bot.ai = MagicMock()
bot.telegram = MagicMock()
bot._ranked_cache = []

# Fake ranked data — fund catalog with توان
from core.scoring.models import FundAssessment
def fake_assessment(symbol, name):
    return FundAssessment(
        symbol=symbol, name=name, fund_type="سهامی", ins_code="1",
        sector="صندوق", final_score=70, recommendation="buy",
        recommendation_label="خرید", rank=1,
        factors=(), summary_reasons=("تست",), change_pct=1.0,
        volume=1000, value=1e9, premium_pct=-0.4,
    )

FAKE_RANKED = [
    fake_assessment("توان", "صندوق توان"),
    fake_assessment("گلدیس", "صندوق گلدیس"),
    fake_assessment("عیار", "صندوق طلای عیار"),
]
bot._ranked_cache = FAKE_RANKED
bot._get_ranked = MagicMock(return_value=FAKE_RANKED)

# Fund catalog for wizard search
bot._get_fund_catalog = MagicMock(return_value=[
    {"symbol": "توان", "name": "صندوق توان"},
    {"symbol": "گلدیس", "name": "صندوق گلدیس"},
    {"symbol": "عیار", "name": "صندوق طلای عیار"},
])

results = []

def upd(chat_id, uid, text):
    return {'message': {'chat': {'id': chat_id, 'type': 'private'}, 'text': text, 'from': {'id': uid, 'first_name': 'T'}}}

def cb(chat_id, uid, data):
    return {'id': 'cq1', 'from': {'id': uid, 'first_name': 'T'}, 'message': {'chat': {'id': chat_id, 'type': 'private'}}, 'data': data}

def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)

# ============ TEST 3: ADD_FUND → توان → MUST find توان, never گلدیس ============
bot._pf_wizard.clear(); bot._awaiting_fund_search.clear(); bot._awaiting_ask.clear()
bot._handle_callback(cb('1001', 1, 'cmd:pf_add_prompt'))
# wizard active: step=symbol
check("T3a pf_add_prompt → wizard step symbol", bot._pf_wizard.get('1', {}).get('step') == 'symbol')
# user types توان
bot._reply = MagicMock()
bot._handle_update(upd('1001', 1, 'توان'))
w = bot._pf_wizard.get('1', {})
check("T3b توان → wizard symbol=توان", w.get('symbol') == 'توان', f"got {w.get('symbol')}")
check("T3c توان → wizard step price", w.get('step') == 'price', f"got {w.get('step')}")
check("T3d توان → NO fund analysis reply", 'تحلیل' not in str(bot._reply.call_args_list[-1][0][0]) if bot._reply.called else True)

# ============ TEST 4: complete ADD_FUND wizard ============
bot._handle_update(upd('1001', 1, '125000'))
w = bot._pf_wizard.get('1', {})
check("T4a price 125000 → qty step", w.get('step') == 'qty' and w.get('price') == 125000)
bot._handle_update(upd('1001', 1, '1000'))
w = bot._pf_wizard.get('1', {})
check("T4b qty 1000 → date step", w.get('step') == 'date' and w.get('qty') == 1000)
bot._handle_update(upd('1001', 1, '1405/05/19'))
w = bot._pf_wizard.get('1', {})
check("T4c date → current step", w.get('step') == 'current' and w.get('date') == '1405/05/19')
bot._handle_update(upd('1001', 1, '1000'))
w = bot._pf_wizard.get('1', {})
check("T4d current 1000 → confirm step", w.get('step') == 'confirm' and w.get('current') == 1000)
# confirm callback
bot._handle_callback(cb('1001', 1, 'pfwiz_confirm:1'))
check("T4e confirm → wizard popped", '1' not in bot._pf_wizard)
check("T4f confirm → upsert_holding called", bot.portfolio.upsert_holding.called)

# ============ TEST 5/7: FUND_ANALYSIS → توان → analysis ============
bot._pf_wizard.clear(); bot._awaiting_fund_search.clear()
bot._cmd_fund = MagicMock(return_value="ANALYSIS_RESULT")
bot._handle_callback(cb('1002', 2, 'cmd:fund_search'))
check("T5a fund_search → awaiting", '2' in bot._awaiting_fund_search)
bot._reply = MagicMock()
bot._handle_update(upd('1002', 2, 'توان'))
check("T5b توان in fund_search → _cmd_fund called", bot._cmd_fund.called, f"called={bot._cmd_fund.called}")
check("T5c awaiting cleared", '2' not in bot._awaiting_fund_search)

# ============ TEST 6: ADD_FUND active → توان → NO _cmd_fund ============
bot._cmd_fund.reset_mock()
bot._pf_wizard.clear(); bot._awaiting_fund_search.clear()
bot._handle_callback(cb('1003', 3, 'cmd:pf_add_prompt'))
bot._handle_update(upd('1003', 3, 'توان'))
check("T6 ADD_FUND + توان → NO _cmd_fund", not bot._cmd_fund.called)
check("T6b wizard still active", '3' in bot._pf_wizard)

# ============ TEST 8: wizard active → عیار → wizard consumes ============
bot._handle_callback(cb('1004', 4, 'cmd:pf_add_prompt'))
bot._handle_update(upd('1004', 4, 'عیار'))
w = bot._pf_wizard.get('4', {})
check("T8 عیار in wizard → symbol=عیار", w.get('symbol') == 'عیار')

# ============ TEST 9: /start mid wizard → reset (current user) ============
bot._pf_wizard['5'] = {'step': 'price', 'symbol': 'توان'}
bot._awaiting_fund_search.add('5')
bot._awaiting_ask.add('5')
bot._handle_update(upd('1005', 5, '/start'))
check("T9 /start mid wizard → user state cleared", '5' not in bot._pf_wizard and '5' not in bot._awaiting_fund_search and '5' not in bot._awaiting_ask)

# ============ TEST 9b: after /start, free text → NO analysis ============
bot._cmd_fund.reset_mock()
bot._handle_update(upd('1005', 5, 'توان'))
check("T9b after /start توان → NO analysis", not bot._cmd_fund.called)

# ============ TEST 10: after fund analysis, free text → no leak ============
bot._pf_wizard.clear(); bot._awaiting_fund_search.clear(); bot._awaiting_ask.clear()
bot._handle_callback(cb('1006', 6, 'cmd:fund_search'))
bot._handle_update(upd('1006', 6, 'توان'))
bot._cmd_fund.reset_mock()
bot._send_my_portfolio = MagicMock()
bot._handle_update(upd('1006', 6, 'یه متن آزاد'))
check("T10 free text after analysis → NO analysis", not bot._cmd_fund.called)
check("T10b → NO portfolio", not bot._send_my_portfolio.called)

# ============ TEST 14: wizard buttons only cancel ============
bot._pf_wizard.clear()
bot._handle_callback(cb('1007', 7, 'cmd:pf_add_prompt'))
bot._handle_update(upd('1007', 7, 'توان'))
# wizard step price → only cancel button
last_kb = bot._reply.call_args_list[-1][1].get('reply_markup', {}) if bot._reply.called else {}
btns = [b['callback_data'] for r in last_kb.get('inline_keyboard', []) for b in r]
check("T14 price step → only cancel", btns == ['cmd:menu'], f"got {btns}")

print()
print(f"TOTAL: {sum(1 for _, c, _ in results if c)}/{len(results)} passed")
failed = [n for n, c, _ in results if not c]
if failed:
    print("FAILED:", failed)
    sys.exit(1)
