class BaseStatus:
    @classmethod
    def get_status_name(cls, status_value):
        for name, value in vars(cls).items():
            if value == status_value:
                return name

        raise ValueError(f"Invalid status value: {status_value}")

    @classmethod
    def get_status_from_name(cls, status_name):
        for name, value in vars(cls).items():
            if name == status_name:
                return value

        raise ValueError(f"Invalid status name: {status_name}")

class Status:
    class Task(BaseStatus):
        TODO = 0
        IN_PROGRESS = 1
        DONE = 2

        updateable_statuses = [TODO, DONE]

    class SubTask(BaseStatus):
        TODO = 0
        DONE = 1
