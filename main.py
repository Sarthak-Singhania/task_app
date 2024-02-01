import json
from datetime import datetime, timedelta

import bcrypt
import jwt
import MySQLdb
import MySQLdb.cursors as cur
import pandas as pd
import redis
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS, cross_origin
from flask_mysqldb import MySQL

from logger_config import logger
from priority import Priority
from status import Status

app = Flask(__name__)
CORS(app)

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'task_app'
app.config['JSON_SORT_KEYS'] = False
mysql = MySQL(app)

# JWT configurations
app.config['SECRET_KEY'] = ";?]tSNUIb>yCV?.qlEsd*aq#u1JPnB7Q?mZE&cX<iPoif0Sk'Ftq/23RIz/;5&_W"

# Redis configurations
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Logging configurations


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
    if request.path in ['/', '/login', '/register', '/call_status']:
        return
    if 'Authorization' not in request.headers and 'token' not in request.cookies:
        return make_response(jsonify({"message": "Unauthorized"}), 401)
    token = request.headers['Authorization'].split(
        ' ')[1] if 'Authorization' in request.headers else request.cookies.get("token")
    data = verify_token(token)
    if data == False:
        return make_response(jsonify({"message": "Unauthorized"}), 401)
    request.user = data


@app.get('/')
def index():
    return make_response(jsonify({"message": "Welcome to Task App"}), 200)


@app.post('/register')
def register():
    try:
        data = request.get_json()
        if 'username' not in data or 'password' not in data or 'phone_number' not in data:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        username = data['username']
        password = data['password']
        name = data['name'] if 'name' in data else username
        phone_number = data['phone_number']
        priority = data['priority'] if 'priority' in data else Priority.User.LOW
        priority = Priority.User.get_priority_value(priority)
        cursor = mysql.connection.cursor(cur.DictCursor)
        cursor.execute(
            "SELECT * FROM `users` WHERE `username` = %s", (username,))
        user = cursor.fetchone()
        if user is not None:
            return make_response(jsonify({"message": "Username already exists"}), 409)

        salt = bcrypt.gensalt()
        password = bcrypt.hashpw(password.encode('utf-8'), salt)

        cursor.execute("INSERT INTO `users` (`name`, `username`, `password`, `salt`, `phone_number`, `priority`) VALUES (%s, %s, %s, %s, %s, %s)",
                       (name, username, password.decode(), salt.decode(), phone_number, priority))

        mysql.connection.commit()
        cursor.close()
        logger.info(f"User {username} created")
        return make_response(jsonify({"message": "User created"}), 201)
    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.post('/login')
def login():
    try:
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
            response = make_response(
                jsonify({"message": "Login successful"}), 200)
            response.set_cookie('token', token)
            logger.info(f"User {username} logged in")
            return response

        cursor.close()
        return make_response(jsonify({"message": "Invalid username or password"}), 401)
    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.post('/tasks')
def create_task():
    try:
        data = request.get_json()
        cursor = mysql.connection.cursor(cur.DictCursor)
        # This is the code for creating subtasks
        if 'task_id' in data:
            task_id = data['task_id']
            cursor.execute("INSERT INTO `sub_tasks` (`task_id`, `status`) VALUES (%s, %s)",
                           (task_id, Status.SubTask.TODO))
            mysql.connection.commit()
            cursor.close()
            logger.info(f"Subtask created for task {task_id}")
            return make_response(jsonify({"message": "Subtask created"}), 201)

        # This is the code for creating tasks
        if 'title' not in data or 'description' not in data or 'due_date' not in data:
            return make_response(jsonify({"message": "Bad Request"}), 400)
        title = data['title']
        description = data['description']
        due_date = data['due_date']

        try:
            user_id = json.loads(
                data['user_id']) if 'user_id' in data else [request.user['user_id']]
        except:
            return make_response(jsonify({"message": "User ID should be an array of user_ids."}), 400)

        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
        except:
            return make_response(jsonify({"message": "Date should be in YYYY-MM-DD format."}), 400)

        if due_date.date() < datetime.now().date():
            return make_response(jsonify({"message": "Due date cannot be in the past."}), 400)
        date_diff = (due_date - datetime.now()).days + 1

        cursor.execute("INSERT INTO `tasks` (`title`, `description`, `due_date`, `status`, `priority`)" +
                       "VALUES (%s, %s, %s, %s, %s)",
                       (title, description, due_date, Status.Task.TODO,
                        Priority.Task.get_priority_from_date_diff(date_diff)))

        cursor.execute("SELECT LAST_INSERT_ID() as task_id")
        task_id = cursor.fetchone()['task_id']
        mysql.connection.commit()
        for user in user_id:
            try:
                cursor.execute(
                    "INSERT INTO `task_user_link` (`task_id`, `user_id`) values(%s, %s)", (task_id, user))
                mysql.connection.commit()
            except MySQLdb.IntegrityError:
                return make_response(jsonify({"message": "User already exists"}), 409)
        mysql.connection.commit()
        cursor.close()

        logger.info(f"Task {task_id} created")
        return make_response(jsonify({"message": "Task created"}), 201)

    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.get('/tasks')
def get_tasks():
    try:
        cursor = mysql.connection.cursor(cur.DictCursor)

        # This is the code for getting subtasks
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

            sub_tasks = [{**sub_task,
                          'status': Status.SubTask.get_status_name(sub_task['status']),
                          'created_at': sub_task['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                          'updated_at': sub_task['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if sub_task['updated_at'] else None,
                          'deleted_at': sub_task['deleted_at'].strftime('%Y-%m-%d %H:%M:%S') if sub_task['deleted_at'] else None
                          } for sub_task in sub_tasks]

            for i in sub_tasks:
                del i['delete']
            return make_response(jsonify({"sub_tasks": sub_tasks}), 200)
        elif request.args.get('type') == 'tasks':
            # This is the code for getting tasks
            args = dict(request.args.items())

            if len(args) == 0 or 'page' not in args:
                return make_response(jsonify({"message": "Page not in request"}), 400)

            query = "SELECT * FROM `tasks` WHERE `delete` = 0"

            for i in args:
                if i == 'due_date':
                    query += " and `due_date` = %s"
                    try:
                        args[i] = datetime.strptime(args[i], '%Y-%m-%d')
                    except:
                        return make_response(jsonify({"message": "Date should be in YYYY-MM-DD format."}), 400)
                elif i == 'page':
                    continue
                elif i == 'title':
                    query += f" and `{i}` like %s"
                    args[i] = f"%{args[i]}%"
                elif i == 'status':
                    status = Status.Task.get_status_from_name(args[i])
                    query += f" and `{i}` = %s"
                    args[i] = status
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

        else:
            return make_response(jsonify({"message": "Invalid type."}), 400)

    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.put('/tasks')
def update_task():
    try:
        data = request.get_json()
        cursor = mysql.connection.cursor(cur.DictCursor)

        # This is the code for updating subtasks
        if request.args.get('type') == 'sub_tasks':
            if 'sub_task_id' not in data:
                return make_response(jsonify({"message": "Bad Request"}), 400)
            sub_task_id = data['sub_task_id']
            status = Status.SubTask.get_status_from_name(data['status'])
            cursor.execute("UPDATE `sub_tasks` SET `status` = %s WHERE `id` = %s",
                           (status, sub_task_id))

            if status == Status.SubTask.DONE:
                cursor.execute(
                    "SELECT * FROM `sub_tasks` WHERE `id` = %s", (data['sub_task_id'],))
                sub_tasks = cursor.fetchall()
                for sub_task in sub_tasks:
                    if sub_task['status'] == Status.SubTask.DONE:
                        cursor.execute(
                            "SELECT * FROM `tasks` WHERE `id` = %s", (sub_task['task_id'],))
                        task = cursor.fetchone()
                        if task['status'] == Status.Task.TODO:
                            cursor.execute("UPDATE `tasks` SET `status` = %s WHERE `id` = %s", (
                                Status.Task.IN_PROGRESS, sub_task['task_id']))
                        break

            mysql.connection.commit()
            cursor.close()

            logger.info(f"Subtask {sub_task_id} updated to {status}")
            return make_response(jsonify({"message": "Subtask updated"}), 200)
        elif request.args.get('type') == 'tasks':
            # This is the code for updating tasks
            if 'task_id' not in data:
                return make_response(jsonify({"message": "Task id not present in the request."}), 400)

            if len(data) <= 1:
                return make_response(jsonify({"message": "No data to update."}), 400)

            unexpected_keys = set(
                data.keys()) - set(['task_id', 'status', 'due_date', 'user_id'])
            if len(unexpected_keys) > 0:
                return make_response(jsonify({"message": f"Unexpected keys: {unexpected_keys}"}), 400)

            query = "UPDATE `tasks` SET "
            args = {}

            if 'status' in data:
                status = Status.Task.get_status_from_name(data['status'])

                if status not in Status.Task.updateable_statuses:
                    return make_response(jsonify({"message": "Task status not updatable."}), 400)

                if status == Status.Task.DONE:
                    cursor.execute(
                        "SELECT * FROM `sub_tasks` WHERE `task_id` = %s", (data['task_id'],))
                    sub_tasks = cursor.fetchall()
                    for sub_task in sub_tasks:
                        if sub_task['status'] != Status.SubTask.DONE:
                            return make_response(jsonify({"message": "Subtasks not completed."}), 400)
                elif status == Status.Task.TODO:
                    cursor.execute(
                        "SELECT * FROM `sub_tasks` WHERE `task_id` = %s", (data['task_id'],))
                    sub_tasks = cursor.fetchall()
                    for sub_task in sub_tasks:
                        if sub_task['status'] == Status.SubTask.DONE:
                            return make_response(jsonify({"message": "Subtasks already completed."}), 400)

                query += "`status` = %s, "
                args['status'] = status

            if 'due_date' in data:
                due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
                if due_date.date() < datetime.now().date():
                    return make_response(jsonify({"message": "Due date cannot be in the past."}), 400)
                date_diff = (due_date - datetime.now()).days
                priority = Priority.Task.get_priority_from_date_diff(date_diff)
                query += "`due_date` = %s, `priority` = %s, "
                args['due_date'] = due_date
                args['priority'] = priority

            if 'user_id' in data:
                user_id = data['user_id']
                task_id = data['task_id']

                try:
                    cursor.execute(
                        "INSERT INTO `task_user_link` values(%s, %s)", (task_id, user_id))
                    mysql.connection.commit()
                    cursor.close()
                except MySQLdb.IntegrityError:
                    return make_response(jsonify({"message": "User already exists"}), 409)

                logger.info(f"User {user_id} added to task {task_id}")
                return make_response(jsonify({"message": "User added to task"}), 200)

            query = query[:-2] + " WHERE `id` = %s"
            args['id'] = data['task_id']

            cursor.execute(query, tuple(args.values()))
            mysql.connection.commit()
            cursor.close()
            logger.info(f"Task {data['task_id']} updated")
            return make_response(jsonify({"message": "Task updated"}), 200)

        else:
            return make_response(jsonify({"message": "Invalid type."}), 400)

    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.delete('/tasks')
def delete_task():
    try:
        cursor = mysql.connection.cursor(cur.DictCursor)

        # This is the code for deleting subtasks
        if request.args.get('type') == 'sub_tasks':

            if 'sub_task_id' not in request.args:
                return make_response(jsonify({"message": "Bad Request"}), 400)

            sub_task_id = request.args.get('sub_task_id')

            cursor.execute(
                "UPDATE `sub_tasks` SET `delete` = 1 WHERE `id` = %s", (sub_task_id,))
            mysql.connection.commit()
            cursor.close()

            logger.info(f"Subtask {sub_task_id} deleted")
            return make_response(jsonify({"message": "Subtask deleted"}), 200)
        elif request.args.get('type') == 'tasks':
            # This is the code for deleting tasks
            if 'task_id' not in request.args:
                return make_response(jsonify({"message": "Bad Request"}), 400)

            task_id = request.args.get('task_id')

            cursor.execute(
                "UPDATE `tasks` SET `delete` = 1 WHERE `id` = %s", (task_id,))
            cursor.execute(
                "UPDATE `sub_tasks` SET `delete` = 1 WHERE `task_id` = %s", (task_id,))
            cursor.execute(
                "UPDATE `task_user_link` SET `delete` = 1 WHERE `task_id` = %s", (task_id,))
            mysql.connection.commit()
            cursor.close()

            logger.info(f"Task {task_id} deleted")
            return make_response(jsonify({"message": "Task deleted"}), 200)

        else:
            return make_response(jsonify({"message": "Invalid type."}), 400)

    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.delete('/task_users')
def delete_task_users():
    try:
        if 'task_id' not in request.args or 'user_id' not in request.args:
            return make_response(jsonify({"message": "Bad Request"}), 400)

        task_id = request.args.get('task_id')
        user_id = request.args.get('user_id')

        cursor = mysql.connection.cursor(cur.DictCursor)
        try:
            cursor.execute(
                "UPDATE `task_user_link` SET `delete` = 1 WHERE `task_id` = %s and `user_id` = %s", (task_id, user_id))
            mysql.connection.commit()
            cursor.close()
        except MySQLdb.IntegrityError as e:
            if 'user_id' in str(e):
                return make_response(jsonify({"message": "User does not exist"}), 404)
            elif 'task_id' in str(e):
                return make_response(jsonify({"message": "Task does not exist"}), 404)
            else:
                return make_response(jsonify({"message": "Bad Request"}), 400)

        logger.info(f"User {user_id} removed from task {task_id}")
        return make_response(jsonify({"message": "User removed from task"}), 200)

    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.get('/task_users')
def get_task_users():
    try:
        if 'task_id' not in request.args:
            return make_response(jsonify({"message": "Bad Request"}), 400)

        task_id = request.args.get('task_id')

        cursor = mysql.connection.cursor(cur.DictCursor)
        cursor.execute(
            '''SELECT `users`.`id` as user_id, `users`.`name` as name,
            `users`.`username` as username, `users`.`phone_number` as phone_number,
            `users`.`priority` as priority, `tul`.`task_id` as task_id
            FROM `task_user_link` tul
            JOIN `users` ON `tul`.`user_id` = `users`.`id`
            WHERE `tul`.`task_id` = %s AND `tul`.`delete` = 0'''.replace('\n', ' '),
            (task_id,))

        task_users = cursor.fetchall()
        cursor.close()

        task_users = [{**task_user, 'priority': Priority.User.get_priority_name(
            task_user['priority'])} for task_user in task_users]
        return make_response(jsonify({"task_users": task_users}), 200)

    except MySQLdb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return make_response(jsonify({"message": "Database error"}), 500)

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return make_response(jsonify({"message": "Internal server error", "error": str(e)}), 500)


@app.post('/call_status')
def call_status():
    status = request.form.get('CallStatus')
    if status == 'completed':
        r.set(request.form.get('CallSid'), Status.Call.ANSWERED)
    elif status == 'busy' or status == 'no-answer':
        r.set(request.form.get('CallSid'), Status.Call.NO_ANSWER)
    return make_response(jsonify({"message": "Call status updated"}), 200)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
