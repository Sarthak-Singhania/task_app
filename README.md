# Task App Backend

## Introduction
Hi, I'm Sarthak Singhania. This document introduces the Task App Backend developed for an assignment. The backend is designed to manage tasks and subtasks with various functionalities including user authentication, task creation, updating, deletion (with soft deletion), and more.

## Requirements
The backend supports the following APIs:
1. **Create Task**: Requires title, description, due_date, and JWT auth token.
2. **Create Subtask**: Requires task_id.
3. **Get All User Tasks**: Supports filters like priority, due_date, and includes pagination.
4. **Get All User Subtasks**: Filters by task_id.
5. **Update Task**: Can change due_date and status.
6. **Update Subtask**: Allows status updates.
7. **Delete Task**: Soft deletion.
8. **Delete Subtask**: Soft deletion.
Additionally, it includes cron logic for priority adjustment based on due date and Twilio integration for user notification based on task priority.

## Database Structure
The project uses MySQL with the following tables:
- **users**
- **tasks**
- **sub_tasks**
- **task_user_link**: Links users and tasks.

## Backend Code
Developed in Python using Flask, it employs JWT for authentication, with token expiry set to one week. It includes comprehensive request handling to ensure user-task association for updates and deletions.

## API Endpoints
- **/register**: Registers a new user.
- **/login**: Authenticates a user and issues a JWT token.
- **/tasks**: Endpoint for creating, getting, updating, and deleting tasks and subtasks.
- **/task_users**: Manages users associated with tasks.
- **/call_status**: Callback URL for Twilio call status.

## Cron Jobs
1. **Priority Update**: Runs at 00:10, updates task priorities based on due dates.
2. **User Notification**: Runs at 09:00, uses Twilio to call users associated with overdue tasks, leveraging Redis for call status management.

## Setup and Installation

To set up and run the Task App Backend, follow these steps:

1. **Clone the repository:**
   Clone the Task App repository to your local machine using the following git command:
   ```bash
   git clone https://github.com/Sarthak-Singhania/task_app.git

2. **Install dependencies:**
   Navigate to the cloned repository directory and install the required Python dependencies using pip:
   ```bash
    cd task_app
    pip install -r requirements.txt

3. **Run the Flask application:**
   Start the backend server by running the Flask application with:
   ```bash
   python main.py

4. **Database setup:**
   Ensure MySQL is installed and running on your machine. Use the provided .sql file to create the necessary database and tables as per the schema defined for the application.
   Make sure to update the .env file with your MySQL database connection details and any other environment-specific configurations before starting the application.

5. **Cron job setup:**
   Run the cron_setup.py file to put the cron jobs in crontab.
