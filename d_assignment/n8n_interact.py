import requests
from typing import List, Dict, Any

test_get_data_url = "https://catkinate-craftiest-cara.ngrok-free.dev/webhook-test/changes_info" # get_response, after ngrok in my device check for true url on your N8N
public_get_data_url = "https://catkinate-craftiest-cara.ngrok-free.dev/webhook/changes_info"    # get_response, after ngrok in my device check for true url on your N8N

test_post_data_url = "https://catkinate-craftiest-cara.ngrok-free.dev/webhook-test/post_data"   # notify_n8n, after ngrok in my device check for true url on your N8N
public_post_data_url = "https://catkinate-craftiest-cara.ngrok-free.dev/webhook/post_data"      # notify_n8n, after ngrok in my device check for true url on your N8N

class GetResponse(object):
    def __init__(self, webhook_url:str=None):
        self.webhook_url = webhook_url

    def get_response(self)->None|List[Dict[str,Any]]:
        if not self.webhook_url:
            print("No webhook URL provided")
            return None

        try:
            n8n_response = requests.get(self.webhook_url)
            if n8n_response.status_code == 200:
                #print("got response", n8n_response.content)
                return n8n_response.json()
            return None

        except Exception as e:
            print("Error: ",str(e))
            return None

class N8nNotify(object):
    def __init__(self, booking_id:int, name:str,date:str,time:str,status:str,webhook_url:str=None):
        self.booking_id = booking_id
        self.name = name
        self.date = date
        self.time = time
        self.status = status
        self.webhook_url = webhook_url

    def notify_n8n(self)->bool:

        if not self.webhook_url:
            print("N8N Connection Error")
            return False

        data = {
            "booking_id": self.booking_id,
            "name": self.name,
            "date": self.date,
            "time": self.time,
            "status": self.status,
        }


        try:
            response = requests.post(
                self.webhook_url,
                json={**data},
                timeout=5
            )
            if response.status_code == 200:
                return True
            return False

        except Exception as e:
            print("Error: " + str(e))
            return False



#n8n = N8nNotify(10,"ariel","15.6.27","15:00","pending_to_cancel",test_post_data_url)
#print(n8n.notify_n8n())

#response = GetResponse(test_get_data_url)
#print(response.get_response()[0])
