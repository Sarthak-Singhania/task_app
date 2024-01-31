from mysql.connector import connect

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "task_app",
}

mysql = connect(**db_config)
cursor = mysql.cursor(dictionary=True)

cursor.execute("SELECT * FROM tasks")
tasks = cursor.fetchall()
print(tasks)
