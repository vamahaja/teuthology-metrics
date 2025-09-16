import configparser
import os


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
        _config["index"] = config[server].get("INDEX")
        if not _config["index"]:
            raise ValueError("Index not found in configuration file.")

    if server == "email":
        _config["email_from"] = config[server].get("EMAIL_FROM")
        _config["email_to"] = config[server].get("EMAIL_TO")
        if not _config["email_from"] or not _config["email_to"]:
            raise ValueError(
                "Email from and to addresses not found in configuration file."
            )

    return _config
