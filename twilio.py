from twilio.rest import Client

account_sid = "AC9e5a1a4a57fbef36669aaf08e4ecdd21"
auth_token = "3e4d1fada98f366b044b6ca89ea68333"
client = Client(account_sid, auth_token)


def make_call(to, title, id, due_date):
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
        status_callback="http://54.167.176.24:5000/call_status"
    )

    return call.sid