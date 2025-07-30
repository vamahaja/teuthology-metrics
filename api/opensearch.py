"""
Update job details to opensearch

Usage:
    opensearch.py --config=<cfg-file> --testruns-dir=<dir>

Options:
    --config=<cfg-file>     Path to the configuration file.
    --testruns-dir=<dir>    Path to the test runs directory.
"""

import json
import os
from datetime import datetime

from docopt import docopt
from opensearchpy import OpenSearch
from utils import get_config

INDEX_CONFIG = {
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
}


def get_configs(_config, server="opensearch"):
    """Get OpenSearch configuration details"""
    # Get OpenSearch configuration
    _config = get_config(_config, server)

    # Get base URL
    base_url = f"http://{_config['host']}"

    # Append port if specified
    if _config["port"]:
        base_url += f":{_config['port']}"

    # Get baseurl, username and password
    return base_url, _config["username"], _config["password"]


def connect(config):
    """Connect to OpenSearch instance"""
    # Get OpenSearch configuration
    base_url, username, password = get_configs(config, "opensearch")

    # Connect to OpenSearch
    print(f"Connecting to OpenSearch at {base_url} with user {username}")
    try:
        client = OpenSearch(
            base_url,
            http_auth=(username, password),
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            retry_on_timeout=True,
            max_retries=5,
            timeout=180,
        )
    except Exception as e:
        print(f"Failed to connect to OpenSearch: {e}")
        raise e

    return client


def create_index(client, index_name, body):
    """Create OpenSearch index"""
    print(f"Creating new index: {index_name}")
    if not client.indices.exists(index=index_name):
        try:
            client.indices.create(index=index_name, body=body)
        except Exception as e:
            print(f"Error creating index in OpenSearch: {e}")
            raise e

        print(f"Created index: {index_name}")
        return

    print(f"Index already present: {index_name}")


def read_metadata(file_name):
    """Read metadata from json"""
    with open(file_name, "r") as _f:
        return json.load(_f)


def insert_jobs(client, runs, testrun_path):
    """Insert teuthology jobs in Opensearch"""
    for job_id in runs.get("job_ids", []):
        print(f"Processing job id: {job_id}")

        # Get job data
        job_data = read_metadata(
            f"{os.path.join(testrun_path, 'jobs', job_id)}.json"
        )

        # Update job data
        _index = INDEX_CONFIG.get("jobs").get("name")
        try:
            insert_record(client, _index, job_id, job_data)
        except Exception as e:
            print(f"Error: Failed to insert job {job_id}")


def insert_record(client, index, id, body):
    """Insert a document into OpenSearch"""
    print(f"Indexing document in OpenSearch: {index}/{id}")

    # Insert the document in OpenSearch
    response = None
    try:
        response = client.index(index=index, id=id, body=body, refresh=True)
    except Exception as e:
        print(f"Error indexing document in OpenSearch: {e}")
        raise e

    # Check if the response is successful
    if hasattr(response, "status_code") and response.status_code != 200:
        raise ValueError(f"Failed to index documents. Response:\n{response}")


def update_runs(client, testruns_dir):
    """Update teuthology runs in OpenSearch"""
    for testruns in os.scandir(testruns_dir):
        # Check for directory
        if not testruns.is_dir():
            continue

        print(f"Processing testruns: {testruns.name}")

        # Get job ids from meatadata
        runs = read_metadata(os.path.join(testruns.path, "results.json"))

        # Insert jobs to opensearch
        insert_jobs(client, runs, testruns.path)

        # Insert runs to openserach
        _index = INDEX_CONFIG.get("runs").get("name")
        insert_record(client, _index, runs.get("name"), runs)


def main(config, testruns_dir):
    # Connect to OpenSearch
    client = connect(config)

    for _index in INDEX_CONFIG:
        index = INDEX_CONFIG.get(_index, {})
        if not index:
            raise ValueError(f"No config present for {index}")

        # Create required index
        create_index(client, index.get("name"), index.get("body"))

    # Update teuthology runs
    update_runs(client, testruns_dir)


if __name__ == "__main__":
    print(
        "\n======== "
        "Starting new OpenSearch session - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        " ======== "
    )

    # Parse command line arguments
    args = docopt(__doc__)

    # Get configuration and data
    config = args["--config"]
    testruns_dir = args["--testruns-dir"]

    # Update OpenSearch data
    main(config, testruns_dir)
