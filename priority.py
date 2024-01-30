class Priority:
    class Task:
        TODAY = 0
        TOMORROW_OR_DAY_AFTER = 1
        THREE_TO_FOUR_DAYS = 2
        FIVE_PLUS_DAYS = 3

        @classmethod
        def get_priority_name(cls, priority_value):
            for name, value in vars(cls).items():
                if value == priority_value:
                    return name

            raise ValueError(f"Invalid priority value: {priority_value}")
        
        @classmethod
        def get_priority_from_date_diff(cls, date_diff):
            if date_diff == 0:
                return cls.TODAY
            elif date_diff == 1 or date_diff == 2:
                return cls.TOMORROW_OR_DAY_AFTER
            elif date_diff >= 3 and date_diff <= 4:
                return cls.THREE_TO_FOUR_DAYS
            else:
                return cls.FIVE_PLUS_DAYS
    
    class User:
        LOW = 0
        MID = 1
        HIGH = 2

        @classmethod
        def get_priority_name(cls, priority_value):
            for name, value in vars(cls).items():
                if value == priority_value:
                    return name

            raise ValueError(f"Invalid priority value: {priority_value}")
        
        @classmethod
        def get_user_priority(cls, cursor, mysql, mobile_number):
            cursor.execute("SELECT `priority` FROM `users` WHERE `mobile_number` = %s limit 1", (mobile_number,))
            user_priority = cursor.fetchone()['priority']
            return user_priority
