import configparser
import logging
import os

from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

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


def get_miner_config():
    """Creates and returns a drain3 configuration object."""
    # Initialize the configuration for the TemplateMiner
    config = TemplateMinerConfig()

    # The similarity threshold for grouping log messages.
    config.drain_sim_th = 0.8

    # The depth of the parsing tree.
    config.drain_depth = 4

    # Set snaopshot compression state to False.
    config.snapshot_compress_state = False

    # Masking is crucial for identifying dynamic variables within log messages.
    config.masking_instructions = [
        # Mask timestamps
        MaskingInstruction(
            pattern=r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{4}",
            mask_with="TIMESTAMP",
        ),
        # Mask smithi nodes
        MaskingInstruction(pattern=r"smithi\d+", mask_with="SMITHI*"),
        # Mask mon services
        MaskingInstruction(pattern=r"mon\.[A-Za-z0-9]+", mask_with="MON*"),
        # Mask osd services
        MaskingInstruction(pattern=r"osd\.[A-Za-z0-9]+", mask_with="OSD*"),
        # Mask osd service count
        MaskingInstruction(pattern=r"\d{1,} OSD\(s\)", mask_with="OSD_COUNT"),
        # Mask PG service count
        MaskingInstruction(pattern=r"\d{1,} (pg|PG)", mask_with="PG_COUNT"),
        # Mask mon service count
        MaskingInstruction(pattern=r"\d+\/\d+ mon", mask_with="MON_COUNT"),
        # Mask Pid number
        MaskingInstruction(pattern=r"pid=(\d+)", mask_with="PID_NUMBER"),
        # Mask retry count
        MaskingInstruction(pattern=r"tries \(\d+\)", mask_with="RETRY_COUNT"),
        # Mask ceph image references
        MaskingInstruction(pattern=r"--fsid \S+", mask_with="CLUSTER_FSID"),
        # Mask seconds count
        MaskingInstruction(
            pattern=r"\d+ sec*|\d+s", mask_with="SECONDS_COUNT"
        ),
        # Mask process count
        MaskingInstruction(
            pattern=r"process (\d+)", mask_with="PROCESS_COUNT"
        ),
        # Mask file system count
        MaskingInstruction(
            pattern=r"\d+.*filesystem", mask_with="FILESYSTEM_COUNT"
        ),
        # Mask ceph image references
        MaskingInstruction(
            pattern=r"ceph:\w+", mask_with="CEPH_IMAGE_REFERENCE"
        ),
        # Mask commit references
        MaskingInstruction(
            pattern=r"CEPH_REF=\w+", mask_with="CEPH_REFERENCE"
        ),
        # Mask audit references
        MaskingInstruction(
            pattern=r"audit\(\S+\)", mask_with="AUDIT_REFERENCE"
        ),
        # Mask centos stream references
        MaskingInstruction(
            pattern=r"centos.*(\d).*stream", mask_with="CENTOS_STREAM_VERSION"
        ),
        # Mask ubuntu references
        MaskingInstruction(
            pattern=r"ubuntu.(\d+).(\d+)", mask_with="UBUNTU_VERSION"
        ),
        # Mask ceph version
        MaskingInstruction(
            pattern=r"(\d+).(\d+).(\d+)-(\d+).(\S+)", mask_with="CEPH_VERSION"
        ),
        # Mask osd & host down counts
        MaskingInstruction(
            pattern=r"\d{1,} host \(\d{1,} osds\)",
            mask_with="OSD_HOST_DOWN_COUNT",
        ),
        # Mask cluster addresses
        MaskingInstruction(
            pattern=r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,}\/\d{1,}",
            mask_with="CLUSTER_ADDRESS",
        ),
    ]

    return config


def get_index_config():
    """Gets OpenSeach index configs"""
    return {
        "runs": {
            "name": "teuthology-runs",
            "body": {
                "settings": {
                    "index.mapping.total_fields.limit": 10000,
                    "index.mapping.ignore_malformed": True,
                },
            },
        },
        "jobs": {
            "name": "teuthology-jobs",
            "body": {
                "settings": {
                    "index.mapping.total_fields.limit": 10000,
                    "index.mapping.ignore_malformed": True,
                },
            },
        },
        "patterns": {
            "name": "teuthology-patterns",
            "body": {
                "settings": {
                    "index.mapping.total_fields.limit": 100,
                    "index.mapping.ignore_malformed": True,
                },
            },
        },
    }
