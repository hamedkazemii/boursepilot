import pandas as pd
import os


class MarketWatchLoader:


    def load_excel(self,path):

        if not os.path.exists(path):
            raise FileNotFoundError(path)


        df=pd.read_excel(path)


        return df



    def filter_funds(self,df):

        keywords=[
            "صندوق",
            "ص.",
            "س صندوق",
            "سرمایه گذاری"
        ]


        mask=False


        for k in keywords:
            mask = mask | df.astype(str).apply(
                lambda x:x.str.contains(k,na=False)
            ).any(axis=1)


        return df[mask]



    def build_registry(self,df):

        result=[]


        for _,row in df.iterrows():

            text=" ".join(
                row.astype(str).tolist()
            )


            result.append(
                {
                    "symbol":str(row.iloc[0]),
                    "name":text,
                    "ins_code":None,
                    "active":True
                }
            )


        return result

