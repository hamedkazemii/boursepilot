from services.telegram.fund_commands import format_fund_explain

for s in ["سیگلو","یاقوت","اهرم"]:
    print("="*40)
    print(format_fund_explain(s))
