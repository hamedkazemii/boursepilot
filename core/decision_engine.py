
class DecisionEngine:


    def decide(self,score):

        if score >=85:

            return {
                "status":"مثبت",
                "action":
                "بررسی ورود یا نگهداری موقعیت"
            }


        elif score >=65:

            return {
                "status":"متوسط",
                "action":
                "نگهداری و بررسی شرایط بازار"
            }


        else:

            return {
                "status":"ضعیف",
                "action":
                "کاهش ریسک و عدم افزایش موقعیت"
            }

