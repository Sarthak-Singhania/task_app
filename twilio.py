import os

import requests
from dotenv import load_dotenv

from twilio.rest import Client

load_dotenv()

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)


def make_call(to, title, id, due_date):
    ip = requests.get('http://checkip.amazonaws.com').text.strip()
    call = client.calls.create(
        to=f"+91{to}",
        from_="+14422765082",
        twiml=f'''
            <Response>
                <Say>The task with title {title} and id {id} is overdue, it was due on {due_date}</Say>
                <Pause length="3"/>
                <Say>Thank you</Say>
                <Hangup/>
            </Response>''',
        status_callback=f"http://{ip}:5000/call_status"
    )

    return call.sid
