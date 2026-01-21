import datetime
import json
import logging
import os
import smtplib
import tempfile

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import get_smtp_config
from .logger import LOG_FORMAT, Logger

log = logging.getLogger("teuthology-metrics")


def set_logging_env(level=None, path=None, job_type=None):
    """Set up logging environment.

    Args:
        level (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                        Default is DEBUG.
        path (str): Log directory path. Default is a temporary directory.
        job_type (str): Optional job type identifier (e.g., 'task', 'report')
                        to include in log filename.

    Returns:
        Log: Log object.
    """
    _log = Logger()
    for handler in _log.logger.handlers[:]:
        handler.close()
        _log.logger.removeHandler(handler)

    log.info("Setting up logging environment")
    level = level.upper() if level else "DEBUG"
    _log.logger.setLevel(level)

    log.info(f"Log level set to: {level}")
    if not path:
        path = os.path.join(tempfile.gettempdir(), "teuthology-metrics-logs")
        log.info(f"Generating log directory: {path}")
        if not os.path.exists(path):
            os.makedirs(path)

    # Build log filename with optional job type
    name = "teuthology-metrics"
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    if job_type:
        log_filename = f"{name}-{job_type}-{timestamp}.log"
    else:
        log_filename = f"{name}-{timestamp}.log"
    
    path = os.path.join(path, log_filename)
    log.info(f"Log path: {path}")

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = logging.FileHandler(path)
    file_handler.setFormatter(formatter)
    _log.logger.addHandler(file_handler)

    return _log


def write_json(_file, _json):
    """Write data to a JSON file
    
    Args:
        _file: File path
        _data: Json to be written
    """
    log.info(f"Writing data to {_file}")

    # Open the file and write the json
    with open(_file, "w") as _f:
        json.dump(_json, _f, indent=2)


def read_json(_file):
    """Read json from file
    
    Args:
        _file: File path
    """
    # Check if the json file exists
    if not os.path.exists(_file):
        raise FileNotFoundError(f"Json file '{_file}' not found.")

    log.info(f"Reading json from {_file}")

    # Open the file and read the json
    with open(_file, "r") as _f:
        return json.load(_f)


def write_data(_file, _data):
    """Write data to a file
    
    Args:
        _file: File path
        _data: Text to be written
    """
    log.info(f"Writing data to {_file}")

    # Open the file and write data
    with open(_file, "w") as _f:
        _f.write(_data)


def batchify(items, batch_size=1000):
    """Iterate over list for given batch size
    
    Args:
        items: Items in the batch
        batch_size: No of items to be processed in
                    single batch
    """
    # Set up an empty batch
    batch = []

    # Iterate over items and yield batches
    for item in items:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []

    # Yield the last batch if it has items
    if batch:
        yield batch


def send_email(config, subject, html_body, address):
    """Send the email with the report.

    Args:
        config: SMTP server config file path
        subject: Subject of the email
        html_body: HTML content of the email
        address: Receiver email address(es). Can be a single email string
                 or comma-separated list of emails.
    """
    # Get SMTP server configuration
    config = get_smtp_config(config)

    # Parse email addresses (support comma-separated list)
    if isinstance(address, str):
        recipients = [email.strip() for email in address.split(",")]
    else:
        recipients = [address]

    # Set email metadata
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.get("sender")
    msg["To"] = ", ".join(recipients)

    # Set email body
    mime_text = MIMEText(html_body, "html")
    msg.attach(mime_text)

    # Set email server config
    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.starttls()

        # Check for login credentials
        username, password = config.get("username"), config.get("password")
        if username and password:
            server.login(username, password)

        # Send email to all recipients
        server.sendmail(msg.get("From"), recipients, msg.as_string())
    
    # Debug
    log.debug(f"Report sent to {recipients} successfully")
