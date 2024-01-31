import os
import threading
import time

import redis
import requests
from dotenv import load_dotenv
from mysql.connector import pooling
from twilio.rest import Client

from status import Status

mysql = pooling.MySQLConnectionPool(pool_name="mysql_pool",
                                    pool_size=20,
                                    pool_reset_session=True,
                                    host='localhost',
                                    user='root',
                                    password='root',
                                    database='task_app',)

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

load_dotenv()

# Twilio credentials
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

# Function to get a connection from the pool


def get_connection():
    return mysql.get_connection()

# Function to release a connection


def release_connection(conn):
    conn.close()


# Function to make a call
def make_call(to, title, id, due_date):
    ip = requests.get('http://checkip.amazonaws.com').text.strip()
    # ip = "3.236.58.68"
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


# Function to check call status from the database
def check_call_status(call_sid):
    try:
        return r.get(call_sid)
    except Exception as e:
        print(f"Error checking call status: {e}")
        return None

# Thread function to handle each task


def handle_task(task_id, title, due_date):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT users.phone_number
            FROM users
            JOIN task_user_link ON users.id = task_user_link.user_id
            WHERE task_user_link.task_id = %s
            ORDER BY users.priority DESC
        """, (task_id,))
        users = cursor.fetchall()
        cursor.close()
        release_connection(connection)

        for user in users:
            call_sid = make_call(
                user['phone_number'], title, task_id, due_date)
            time.sleep(30)  # Wait for call status to be updated
            status = check_call_status(call_sid)
            if Status.Call.parse_status(status):
                break
    except Exception as e:
        print(f"Error handling task {task_id}: {e}")

# Main cron job function


def cron_job():
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM tasks WHERE due_date < NOW() AND status != %s", (Status.Task.DONE,))
        tasks = cursor.fetchall()
        cursor.close()
        release_connection(connection)

        threads = []
        for task in tasks:
            t = threading.Thread(target=handle_task, args=(
                task['id'], task['title'], task['due_date'],))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    except Exception as e:
        print(f"Error in cron job: {e}")


# Run the cron job
cron_job()
