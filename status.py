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

    class Call(BaseStatus):
        NO_ANSWER = 0
        ANSWERED = 1

        def parse_status(call_status):
            if call_status == "0":
                return Status.Call.NO_ANSWER
            elif call_status == "1":
                return Status.Call.ANSWERED
            else:
                raise ValueError(f"Invalid call status: {call_status}")