import os
import requests


class AIProvider:


    def __init__(self):

        self.url=os.getenv(
            "AI_API_URL"
        )

        self.key=os.getenv(
            "AI_API_KEY"
        )

        self.model=os.getenv(
            "AI_MODEL",
            "llama-3.1-8b-instant"
        )



    def ask(self,prompt):

        if not self.url:

            return self.local_response(prompt)


        try:

            r=requests.post(

                self.url,

                headers={
                    "Authorization":
                    f"Bearer {self.key}"
                },

                json={

                    "model":
                    self.model,

                    "messages":[

                        {
                        "role":"user",
                        "content":prompt
                        }

                    ]

                },

                timeout=30

            )


            return r.json()


        except Exception:

            return self.local_response(prompt)



    def local_response(self,prompt):

        return {

            "answer":
            "تحلیل هوشمند در حالت محلی فعال است."

        }

