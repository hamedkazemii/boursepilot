import sys, json
data = json.load(sys.stdin)
for item in data:
    if item.get("l18") == "عیار":
        print("m_board:", item.get("m_board"))
        print("m_board_id:", item.get("m_board_id"))
        print("cs:", item.get("cs"))
        print("cs_id:", item.get("cs_id"))
        print("cs_sub:", item.get("cs_sub"))
        print("cs_sub_id:", item.get("cs_sub_id"))
        break