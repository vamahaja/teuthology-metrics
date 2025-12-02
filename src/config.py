import configparser
import logging
import os

log = logging.getLogger("teuthology-metrics")


def read_config(_file):
    # Check if the config file exists
    if not os.path.exists(_file):
        raise FileNotFoundError(f"Config file '{_file}' not found.")

    log.info(f"Reading config file: {_file}")

    # Read the config file
    config = configparser.ConfigParser()
    try:
        config.read(_file)
    except Exception as e:
        raise RuntimeError(f"Failed to read config file '{_file}': {e}")

    return config


def get_opensearch_config(_file):
    """Get OpenSeach configuration details"""
    # Read the config file
    config = read_config(_file)
    if "opensearch" not in config:
        raise ValueError(
            "Section 'opensearch' not found in configuration file."
        )

    # Convert the section to a dict
    _section = dict(config["opensearch"])

    # Check for required keys
    for key in ["api_url", "username", "password"]:
        if not _section.get(key):
            raise ValueError(f"OpenSearch config missing required key: {key}")

    return (
        _section["api_url"],
        _section["username"],
        _section["password"],
        _section.get("retries", 10),
        _section.get("timeout", 180),
    )


def get_paddle_config(_file):
    """Get paddle configuration details"""
    # Read the config file
    config = read_config(_file)
    if "paddle" not in config:
        raise ValueError("Section 'paddle' not found in configuration file.")

    # Convert the section to a dict
    _section = dict(config["paddle"])

    # Check for required keys
    for key in ["api_url"]:
        if not _section.get(key):
            raise ValueError(f"Paddle config missing required key: {key}")

    return _section["api_url"], _section.get("timeout", 10.0)


def get_smtp_config(_file):
    """Get SMTP server configuration details"""
    # Read the config file
    config = read_config(_file)
    if "smtp" not in config:
        raise ValueError("Section 'smtp' not found in configuration file.")

    # Convert the section to a dict
    _section = dict(config["smtp"])

    # Check for mandatory keys
    for key in ["host", "port", "sender"]:
        if not _section.get(key):
            raise ValueError(f"SMTP Server config missing required key {key}")

    return _section


def get_snapshot_file(_file):
    """Get snapshot file from the config file."""
    # Read the config file
    config = read_config(_file)

    # Check if the 'drain3' section exists
    if "drain3" not in config:
        raise ValueError("Section 'drain3' not found in configuration file.")

    # Check if snapshot location and filename are provided
    _config = config["drain3"]
    if not (
        _config.get("snapshot_location") and _config.get("snapshot_filename")
    ):
        raise ValueError(
            "Snapshot location and filename "
            "not found in 'drain3' configuration file."
        )

    # Construct the file path for persistence
    file_path = os.path.join(
        _config.get("snapshot_location"), _config.get("snapshot_filename")
    )

    return file_path


def get_backup_location(_file):
    """Get backup location from config"""
    config = read_config(_file)

    # Check if the backup location is provided
    if "backup" not in config:
        raise ValueError("Section 'backup' not found in configuration file.")

    # Check if backup location is provided
    _config = config["backup"]
    if not _config.get("backup_location"):
        raise ValueError(
            "Backup location not found in 'backup' configuration file."
        )

    return _config.get("backup_location")


def get_report_config(_file):
    """Get email report configs"""
    # Read the config file
    config = read_config(_file)
    if "report" not in config:
        raise ValueError("Section 'report' not found in configuration file.")

    # Convert the section to a dict
    _section = dict(config["report"])

    # Check for mandatory keys
    for key in ["opensearch_index", "results_server"]:
        if not _section.get(key):
            raise ValueError(f"Report config missing required key {key}")

    return _section

def get_scheduler_config(_file):
    """Get scheduler configs"""
    # Read the config file
    config = read_config(_file)
    if "scheduler" not in config:
        raise ValueError("Section 'scheduler' not found in configuration file.")

    # Convert the section to a dict
    _section = dict(config["scheduler"])

    # Check for mandatory keys
    _keys = [
        "branches",
        "suites",
        "cron_report",
        "cron_task",
        "email",
    ]
    for key in _keys:
        if not _section.get(key):
            raise ValueError(f"Scheduler config missing required key {key}")

    return _section