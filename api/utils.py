import configparser
import json
import os

from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig


def read_config(_file):
    # Check if the config file exists
    if not os.path.exists(_file):
        raise FileNotFoundError(f"Config file '{_file}' not found.")

    print(f"Reading config file: {_file}")

    # Read the config file
    config = configparser.ConfigParser()
    try:
        config.read(_file)
    except Exception as e:
        raise RuntimeError(f"Failed to read config file '{_file}': {e}")

    return config


def write_json(_file, _json):
    """Write data to a JSON file"""
    print(f"Writing data to {_file}")

    # Open the file and write the json
    with open(_file, "w") as _f:
        json.dump(_json, _f, indent=2)


def read_json(_file):
    """Read json from file"""
    # Check if the json file exists
    if not os.path.exists(_file):
        raise FileNotFoundError(f"Json file '{_file}' not found.")

    print(f"Reading json from {_file}")

    # Open the file and read the json
    with open(_file, "r") as _f:
        return json.load(_f)


def write_data(_file, _data):
    """Write data to a file"""
    print(f"Writing data to {_file}")

    # Open the file and write data
    with open(_file, "w") as _f:
        _f.write(_data)


def batchify(items, batch_size=1000):
    """Iterate over list for given batch size"""
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


def get_backup_location(_file):
    """Get backup location from config"""
    config = get_config(_file)

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


def get_config(_file, server):
    """Get configuration details"""
    # Read the config file
    _config, config = {}, read_config(_file)

    # Check if the server details exists
    if server not in config:
        raise ValueError(
            f"Section '{server}' not found in configuration file."
        )

    # Get the host and port from the config
    _config["host"] = config[server].get("HOST")
    if not _config["host"]:
        raise ValueError("Host not found in configuration file.")

    # Get the port from the config
    _config["port"] = config[server].get("PORT")

    # Get the username and password from the config
    if server == "opensearch":
        _config["username"] = config[server].get("USERNAME")
        _config["password"] = config[server].get("PASSWORD")
        if not _config["username"] or not _config["password"]:
            raise ValueError(
                "Username and password not found in configuration file."
            )

    return _config


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
