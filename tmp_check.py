import sys, json
data = json.load(sys.stdin)
print("m_board:", data.get("m_board"))
print("m_board_id:", data.get("m_board_id"))
print("cs:", data.get("cs"))
print("cs_id:", data.get("cs_id"))
print("cs_sub:", data.get("cs_sub"))
print("cs_sub_id:", data.get("cs_sub_id"))