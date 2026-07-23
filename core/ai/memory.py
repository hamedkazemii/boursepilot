
from datetime import datetime


class AIMemory:


    def __init__(self):

        self.lessons=[]



    def add(self,title,data):

        self.lessons.append({

            "title":title,

            "data":data,

            "created":
            datetime.utcnow().isoformat()

        })



    def all(self):

        return self.lessons

