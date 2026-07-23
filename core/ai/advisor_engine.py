
from core.ai.provider import AIProvider


SYSTEM_RULES="""

تو مشاور هوشمند صندوقچی هستی.

وظیفه:

- تحلیل صندوق های سرمایه گذاری ایران
- تحلیل پرتفو کاربر
- توضیح وضعیت بازار

محدودیت:

- سیگنال قطعی خرید و فروش نده
- سود تضمینی وعده نده
- پاسخ خارج از حوزه سرمایه گذاری نده

"""



class AdvisorEngine:


    def __init__(self):

        self.ai=AIProvider()



    def answer(self,user_question,context=None):


        prompt=f"""

{SYSTEM_RULES}


اطلاعات زمینه:

{context}


سوال:

{user_question}

"""


        return self.ai.ask(prompt)

