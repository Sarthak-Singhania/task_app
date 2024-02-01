from mysql.connector import connect
from datetime import datetime
from priority import Priority
from status import Status

mysql = connect(host="localhost", user="root", password="root", database="task_app")
cursor = mysql.cursor(dictionary=True)

cursor.execute("SELECT * FROM `tasks` where `delete` = 0 and `due_date` >= %s and `status` != %s", (datetime.now().date(), Status.Task.DONE,))

tasks = cursor.fetchall()

for task in tasks:
    date_diff = (task['due_date'].date() - datetime.now().date()).days
    priority = Priority.Task.get_priority_from_date_diff(date_diff)
    cursor.execute("UPDATE `tasks` SET `priority` = %s WHERE `id` = %s", (priority, task['id']))

mysql.commit()