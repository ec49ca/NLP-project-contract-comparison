import logging
import datetime

class CustomFormatter(logging.Formatter):
    """
    Custom log formatter to produce logs in the format:
    <timestamp> [LEVEL] <service> - <message> [key=value ...]
    """

    # These are the standard attributes of a LogRecord. We'll use this to differentiate
    # them from the user-provided 'extra' attributes.
    standard_keys = set(logging.LogRecord('', '', '', '', '', '', '', '').__dict__.keys())

    def format(self, record):
        # Create a UTC timestamp
        timestamp = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # Base log message
        log_message = f"{timestamp} [{record.levelname}] {record.name} - {record.getMessage()}"

        # Find and format extra key-value pairs
        extra_items = []
        for key, value in record.__dict__.items():
            if key not in self.standard_keys:
                extra_items.append(f"{key}={value}")

        if extra_items:
            log_message += f" [{ ' '.join(extra_items) }]"
            
        return log_message

def setup_logging():
    """
    Sets up the root logger with the custom formatter.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create a handler and set the custom formatter
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())

    # Add the handler to the root logger
    root_logger.addHandler(handler)