import os

import requests
from dotenv import load_dotenv

from twilio.rest import Client
from mysql.connector import connect

mysql = connect(host="localhost", user="root", password="root", database="task_app")
cursor = mysql.cursor(dictionary=True)

load_dotenv()

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)


def make_call(to, title, id, due_date):
    # ip = requests.get('http://checkip.amazonaws.com').text.strip()
    ip="3.236.58.68"
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

make_call("8368472801", "test", 1, "2021-08-01")