from pathlib import Path
import json
import hashlib
import base64
import requests
import time
from datetime import datetime


CHUNK_SIZE = 1024


class SyncSender:

    def __init__(self, receiver_url, api_key):
        self.receiver_url = receiver_url
        self.api_key = api_key


    def checksum(self,data):
        return hashlib.sha256(data).hexdigest()


    def chunk_file(self,path):

        data=Path(path).read_bytes()

        chunks=[]

        for i in range(0,len(data),CHUNK_SIZE):
            chunks.append(data[i:i+CHUNK_SIZE])

        return chunks


    def send(self,file_path,batch_id):

        chunks=self.chunk_file(file_path)

        manifest={
            "batch_id":batch_id,
            "total_chunks":len(chunks),
            "chunk_size":CHUNK_SIZE,
            "checksum":self.checksum(
                b"".join(chunks)
            ),
            "snapshot_count":0
        }


        headers={
            "X-Sync-Key":self.api_key
        }


        r=requests.post(
            self.receiver_url+"/sync/manifest",
            json=manifest,
            headers=headers,
            timeout=30
        )

        r.raise_for_status()


        for i,c in enumerate(chunks):

            payload=base64.b64encode(c).decode()

            body={
                "batch_id":batch_id,
                "chunk_number":i,
                "payload":payload,
                "checksum":self.checksum(c)
            }


            print(f"SENDING CHUNK {i+1}/{len(chunks)} SIZE={len(c)}")

            for attempt in range(3):
                try:
                    r=requests.post(
                        self.receiver_url+"/sync/chunk",
                        json=body,
                        headers=headers,
                        timeout=(10,120)
                    )

                    r.raise_for_status()
                    break

                except Exception as e:
                    print(
                        f"CHUNK {i} FAILED attempt={attempt+1}: {e}"
                    )

                    if attempt == 2:
                        raise

                    time.sleep(2)


        return True
