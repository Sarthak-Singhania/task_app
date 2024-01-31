from crontab import CronTab

cron = CronTab()

job = cron.new(command='chmod +x /home/ubuntu/task_app/cron_executables/change_priority.sh && /home/ubuntu/task_app/cron_executables/change_priority.sh')

job.minute.on(10)
job.hour.on(0)

cron.write()

print('Cron job successfully set up')

job = cron.new(command='chmod +x /home/ubuntu/task_app/cron_executables/twilio.sh && /home/ubuntu/task_app/cron_executables/twilio.sh')

job.minute.on(0)
job.hour.on(9)

cron.write()

print('Cron job successfully set up')