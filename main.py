from datetime import datetime, timedelta

import bcrypt
import jwt
import MySQLdb.cursors as cur
import pandas as pd
import redis
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS, cross_origin
from flask_mysqldb import MySQL

from priority import Priority
from status import Status

# from twilio_function import make_call

app = Flask(__name__)
CORS(app)

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'task_app'
app.config['JSON_SORT_KEYS'] = False

app.config['SECRET_KEY'] = ";?]tSNUIb>yCV?.qlEsd*aq#u1JPnB7Q?mZE&cX<iPoif0Sk'Ftq/23RIz/;5&_W"

mysql = MySQL(app)

r = redis.Redis(host='localhost', port=6379, decode_responses=True)


def verify_token(token):
    try:
        data = jwt.decode(
            token, app.config['SECRET_KEY'], algorithms=["HS256"])
        return data
    except:
        return False


@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        return '', 200
    if request.path in ['/login', '/register', '/call_status']:
        return
    if 'Authorization' not in request.headers and 'token' not in request.cookies:
        return make_response(jsonify({"message": "Unauthorized"}), 401)
    token = request.headers['Authorization'].split(
        ' ')[1] if 'Authorization' in request.headers else request.cookies.get("token")
    data = verify_token(token)
    if data == False:
        return make_response(jsonify({"message": "Unauthorized"}), 401)
    request.user = data


@app.post('/register')
def register():
    data = request.get_json()
    if 'username' not in data or 'password' not in data or 'phone_number' not in data:
        return make_response(jsonify({"message": "Bad Request"}), 400)
    username = data['username']
    password = data['password']
    name = data['name'] if 'name' in data else username
    phone_number = data['phone_number']
    cursor = mysql.connection.cursor(cur.DictCursor)
    cursor.execute("SELECT * FROM `users` WHERE `username` = %s", (username,))
    user = cursor.fetchone()
    if user is not None:
        return make_response(jsonify({"message": "Username already exists"}), 409)

    salt = bcrypt.gensalt()
    password = bcrypt.hashpw(password.encode('utf-8'), salt)

    cursor.execute("INSERT INTO `users` (`name`, `username`, `password`, `salt`, `phone_number`, `priority`) VALUES (%s, %s, %s, %s, %s, %s)",
                   (name, username, password.decode(), salt.decode(), phone_number, Priority.User.LOW))

    mysql.connection.commit()
    cursor.close()
    return make_response(jsonify({"message": "User created"}), 201)


@app.post('/login')
def login():
    data = request.get_json()
    if 'username' not in data or 'password' not in data:
        return make_response(jsonify({"message": "Bad Request"}), 400)
    username = data['username']
    password = data['password']
    cursor = mysql.connection.cursor(cur.DictCursor)
    cursor.execute(
        "SELECT `id`, `password` FROM `users` WHERE `username` = %s", (username,))
    user = cursor.fetchone()
    if user is None:
        return make_response(jsonify({"message": "Invalid username or password"}), 401)

    if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(weeks=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        response = make_response(jsonify({"message": "Login successful"}), 200)
        response.set_cookie('token', token)
        return response

    return make_response(jsonify({"message": "Invalid username or password"}), 401)


@app.post('/tasks')
def create_task():
    data = request.get_json()
    cursor = mysql.connection.cursor(cur.DictCursor)
    if 'task_id' in data:
        task_id = data['task_id']
        cursor.execute("INSERT INTO `sub_tasks` (`task_id`, `status`, `created_at`, `updated_at`) VALUES (%s, %s, %s, %s)",
                       (task_id, Status.SubTask.TODO, datetime.now(), datetime.now()))
        mysql.connection.commit()
        cursor.close()
        return make_response(jsonify({"message": "Subtask created"}), 201)
    if 'title' not in data or 'description' not in data or 'due_date' not in data:
        return make_response(jsonify({"message": "Bad Request"}), 400)
    title = data['title']
    description = data['description']
    due_date = data['due_date']
    due_date = datetime.strptime(due_date, '%Y-%m-%d')
    date_diff = (due_date - datetime.now()).days + 1
    cursor.execute("INSERT INTO `tasks` (`title`, `description`, `due_date`, `status`, `priority`)" +
                   "VALUES (%s, %s, %s, %s, %s)",
                   (title, description, due_date, Status.Task.TODO,
                    Priority.Task.get_priority_from_date_diff(date_diff)))
    cursor.execute("SELECT LAST_INSERT_ID()")
    task_id = cursor.fetchone()['LAST_INSERT_ID()']
    mysql.connection.commit()
    cursor.execute("INSERT INTO `task_user_link` values(%s, %s)", (task_id, request.user['user_id']))
    mysql.connection.commit()
    cursor.close()
    return make_response(jsonify({"message": "Task created"}), 201)


@app.get('/tasks')
def get_tasks():
    cursor = mysql.connection.cursor(cur.DictCursor)
    if request.args.get('type') == 'sub_tasks':
        task_id = request.args.get(
            'task_id') if 'task_id' in request.args else None
        if task_id is None:
            cursor.execute("SELECT * FROM `sub_tasks` where `delete` = 0")
        else:
            cursor.execute(
                "SELECT * FROM `sub_tasks` WHERE `task_id` = %s and `delete` = 0", (task_id,))
        sub_tasks = cursor.fetchall()
        cursor.close()
        sub_tasks = [{**sub_task, 'status': Status.SubTask.get_status_name(
            sub_task['status'])} for sub_task in sub_tasks]
        for i in sub_tasks:
            del i['delete']
        return make_response(jsonify({"sub_tasks": sub_tasks}), 200)
    else:
        args = dict(request.args.items())
        if len(args) == 0:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        query = "SELECT * FROM `tasks` WHERE `delete` = 0"
        for i in args:
            if i == 'due_date':
                query += " and `due_date` = %s"
            elif i == 'page':
                continue
            else:
                query += f" and `{i}` = %s"
        if 'page' in args and args['page'].isdigit() and int(args['page']) > 0:
            page = int(args['page']) - 1
            del args['page']
            query += f" LIMIT {page * 20}, 20"
        cursor.execute(query, tuple(args.values()))
        tasks = cursor.fetchall()
        cursor.close()
        tasks = [{**task, 'status': Status.Task.get_status_name(task['status']), 'priority': Priority.Task.get_priority_name(
            task['priority'])} for task in tasks]
        for i in tasks:
            del i['delete']
        return make_response(jsonify({"tasks": tasks}), 200)


@app.put('/tasks')
def update_task():
    data = request.get_json()
    cursor = mysql.connection.cursor(cur.DictCursor)
    if request.args.get('type') == 'sub_tasks':
        if 'sub_task_id' not in data:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        sub_task_id = data['sub_task_id']
        status = Status.SubTask.get_status_from_name(data['status'])
        cursor.execute("UPDATE `sub_tasks` SET `status` = %s, `updated_at` = %s WHERE `id` = %s",
                       (status, datetime.now(), sub_task_id))
        
        if status == Status.SubTask.DONE:
            cursor.execute("SELECT * FROM `sub_tasks` WHERE `id` = %s", (data['sub_task_id'],))
            sub_tasks = cursor.fetchall()
            for sub_task in sub_tasks:
                if sub_task['status'] == Status.SubTask.DONE:
                    cursor.execute("SELECT * FROM `tasks` WHERE `id` = %s", (sub_task['task_id'],))
                    task = cursor.fetchone()
                    if task['status'] == Status.Task.TODO:
                        cursor.execute("UPDATE `tasks` SET `status` = %s WHERE `id` = %s", (Status.Task.IN_PROGRESS, sub_task['task_id']))
                    break

        mysql.connection.commit()
        cursor.close()
        return make_response(jsonify({"message": "Subtask updated"}), 200)
    else:
        if 'task_id' not in data:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        query = "UPDATE `tasks` SET "
        args = {}
        if data['status']:
            status = Status.Task.get_status_from_name(data['status'])
            if status not in Status.Task.updateable_statuses:
                return make_response(jsonify({"message": "Bad Request"}), 400)
            query += "`status` = %s, "
            args['status'] = status

        if data['due_date']:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
            if due_date < datetime.now():
                return make_response(jsonify({"message": "Bad Request"}), 400)
            date_diff = (due_date - datetime.now()).days
            priority = Priority.Task.get_priority_from_date_diff(date_diff)
            query += "`due_date` = %s, `priority` = %s, "
            args['due_date'] = due_date
            args['priority'] = priority

        query = query[:-2] + " WHERE `id` = %s"
        args['id'] = data['task_id']
        cursor.execute(query, tuple(args.values()))
        mysql.connection.commit()
        cursor.close()
        return make_response(jsonify({"message": "Task updated"}), 200)


@app.delete('/tasks')
def delete_task():
    cursor = mysql.connection.cursor(cur.DictCursor)
    if request.args.get('type') == 'sub_tasks':
        if 'sub_task_id' not in request.args:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        sub_task_id = request.args.get('sub_task_id')
        cursor.execute(
            "UPDATE `sub_tasks` SET `delete` = 1 WHERE `id` = %s", (sub_task_id,))
        mysql.connection.commit()
        cursor.close()
        return make_response(jsonify({"message": "Subtask deleted"}), 200)
    else:
        if 'task_id' not in request.args:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        task_id = request.args.get('task_id')
        cursor.execute(
            "UPDATE `tasks` SET `delete` = 1 WHERE `id` = %s", (task_id,))
        mysql.connection.commit()
        cursor.execute(
            "UPDATE `sub_tasks` SET `delete` = 1 WHERE `task_id` = %s", (task_id,))
        mysql.connection.commit()
        cursor.close()
        return make_response(jsonify({"message": "Task deleted"}), 200)


@app.post('/call_status')
def call_status():
    status = request.form.get('CallStatus')
    if status == 'completed':
        r.set(request.form.get('CallSid'), Status.Call.ANSWERED)
    elif status == 'busy' or status == 'no-answer':
        r.set(request.form.get('CallSid'), Status.Call.NO_ANSWER)
    return make_response(jsonify({"message": "Call status updated"}), 200)


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5000)
