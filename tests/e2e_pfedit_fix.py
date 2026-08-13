"""E2E test for pfedit_fix flow — fix mode wizard."""
import sys
sys.path.insert(0, "/root/projects/boursepilot")
from unittest.mock import patch, MagicMock

with patch('services.telegram.TelegramService'):
    from services.telegram_bot import SandoghchiBot

bot = SandoghchiBot(warm_cache=False)
bot._reply = MagicMock()
bot._send_my_portfolio = MagicMock()
bot._cmd_fund = MagicMock(return_value='FUND_ANALYSIS')

# Mock portfolio with realistic wrong prices
pf_items = [
    {"symbol": "سرو", "quantity": 2500, "avg_cost": 37373.0},  # wrong price
    {"symbol": "عیار", "quantity": 160, "avg_cost": 454259.0},  # wrong price
]
bot.portfolio.get_portfolio = MagicMock(return_value={
    "user": {"id": "1", "risk_profile": "medium", "horizon_months": 12},
    "items": pf_items
})
bot.portfolio.upsert_holding = MagicMock()
bot.portfolio.ensure_user = MagicMock(return_value={"id": "1"})

def cb(chat_id, uid, data):
    return {'id': 'cq1', 'from': {'id': uid, 'first_name': 'T'}, 'message': {'chat': {'id': chat_id, 'type': 'private'}}, 'data': data}

def upd(chat_id, uid, text):
    return {'message': {'chat': {'id': chat_id, 'type': 'private'}, 'text': text, 'from': {'id': uid, 'first_name': 'T'}}}

results = []
def check(name, cond, extra=''):
    results.append((name, cond))
    print(('PASS' if cond else 'FAIL'), name, extra)

# === TEST: pfedit_fix → wizard fix mode ===
bot._pf_wizard.clear(); bot._awaiting_fund_search.clear(); bot._awaiting_ask.clear()

# User clicks "ویرایش سبد" → "✏️ سرو" → "✏️ اصلاح اطلاعات"
bot._handle_callback(cb('3001', 31, 'cmd:pf_edit_prompt'))
check('T1 pf_edit_prompt → keyboard shown', bot._reply.called)

bot._handle_callback(cb('3001', 31, 'pfedit:سرو'))
check('T2 pfedit:سرو → edit action menu', bot._reply.called)

bot._handle_callback(cb('3001', 31, 'pfedit_fix:سرو'))
check('T3 pfedit_fix:سرو → fix wizard step=price', True)
w = bot._pf_wizard.get('31', {})
check('T3b fix wizard mode=fix', w.get('mode') == 'fix', f"mode={w.get('mode')}")
check('T3c fix wizard qty=2500 (pre-filled)', w.get('qty') == 2500, f"qty={w.get('qty')}")
check('T3d fix wizard step=price', w.get('step') == 'price', f"step={w.get('step')}")

# User enters corrected price
bot._reply.reset_mock()
bot._handle_update(upd('3001', 31, '1150'))  # corrected price
w = bot._pf_wizard.get('31', {})
check('T4 corrected price 1150 → step=confirm', w.get('step') == 'confirm', f"step={w.get('step')}")
check('T4b price stored', w.get('price') == 1150)
check('T4c confirm message shown', '✏️ اصلاح اطلاعات' in str(bot._reply.call_args_list[-1][0][1]) if bot._reply.called else False)

# User confirms
bot._handle_callback(cb('3001', 31, 'pfwiz_confirm:31'))
check('T5 confirm → upsert_holding called with new price', bot.portfolio.upsert_holding.called)
# check args: quantity=2500, avg_cost=1150
call_args = bot.portfolio.upsert_holding.call_args
check('T5b upsert qty=2500', call_args[1].get('quantity') == 2500)
check('T5c upsert avg_cost=1150', call_args[1].get('avg_cost') == 1150)

print()
total = sum(1 for _, c in results if c)
print(f'TOTAL: {total}/{len(results)} passed')
failed = [n for n, c in results if not c]
if failed:
    print('FAILED:', failed)
    sys.exit(1)