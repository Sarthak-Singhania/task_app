import os
import logging

# Specify your log directory
log_directory = "logs"

# Check if the directory exists and create it if it doesn't
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Define the full path for the log files
info_log_path = os.path.join(log_directory, 'logs.log')
error_log_path = os.path.join(log_directory, 'error_logs.log')

# Create logger
logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)  # Set to lowest level to capture all messages

# Create file handler for INFO and above
info_handler = logging.FileHandler(info_log_path)
info_handler.setLevel(logging.INFO)
# Filter to include INFO and WARNING, exclude ERROR and CRITICAL
info_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
info_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
info_handler.setFormatter(info_formatter)

# Create file handler for ERROR and above
error_handler = logging.FileHandler(error_log_path)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)

# Add handlers to the logger
logger.addHandler(info_handler)
logger.addHandler(error_handler)
