import configparser
import os


def get_config(_file, server):
    """Get configuration details"""
    # Initialize config dictionary
    _config = {}

    # Check if the config file exists
    if not os.path.isfile(_file):
        raise FileNotFoundError(f"Config file '{_file}' not found.")

    print(f"Reading config file: {_file}")

    # Read the config file
    config = configparser.ConfigParser()
    try:
        config.read(_file)
    except Exception as e:
        raise RuntimeError(f"Failed to read config file '{_file}': {e}")

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
