"""
Update job details to opensearch

Usage:
    opensearch.py --config=<cfg-file> --testruns-dir=<dir>
        [--skip-logs]

Options:
    --config=<cfg-file>     Path to the configuration file.
    --testruns-dir=<dir>    Path to the test runs directory.
    --skip-logs             Skip job logs.
"""

import json
import os
from datetime import datetime

from docopt import docopt
from opensearchpy import OpenSearch, helpers
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
    "logs": {
        "name": "teuthology-logs",
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


def insert_jobs(client, runs, testrun_path, skip_logs):
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
        except Exception:
            print(f"Error: Failed to insert job job-id {job_id}")

        if skip_logs:
            continue

        # Get log file path
        log_file = f"{os.path.join(testrun_path, 'logs', job_id)}.log"

        # Update job logs
        _index = INDEX_CONFIG.get("logs").get("name")
        try:
            insert_logs(client, _index, job_id, log_file)
        except Exception:
            print(f"Error: Failed to insert logs for job-id {job_id}")


def insert_logs(client, index, id, log_file):
    """Insert logs into OpenSearch"""
    print(f"Indexing logs in OpenSearch: {index}/{id}")
    batch_size, batch_index = 1000, 0

    # Iterate over log file for given batch size
    def batchify(iterable, batch_size=batch_size):
        batch = []
        for item in iterable:
            batch.append(item)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    # Open log file and start update logs
    with open(log_file, "r", encoding="utf-8") as f:
        # Iterate over log file lines
        lines = (line for line in f if line.strip())

        for batch_lines in batchify(lines, batch_size):
            print(f"Processing batch {batch_index + 1}")

            # Set action for job-id
            actions = [
                {
                    "_index": index,
                    "_source": {"message": line.rstrip("\n"), "job-id": id},
                }
                for line in batch_lines
            ]

            # Update logs to index
            try:
                helpers.bulk(client, actions)
            except Exception as e:
                print(f"Error during ingestion: {e}")

            batch_index += 1


def update_runs(client, testruns_dir, skip_logs):
    """Update teuthology runs in OpenSearch"""
    for testruns in os.scandir(testruns_dir):
        # Check for directory
        if not testruns.is_dir():
            continue

        print(f"Processing testruns: {testruns.name}")

        # Get job ids from meatadata
        runs = read_metadata(os.path.join(testruns.path, "results.json"))

        # Insert jobs to opensearch
        insert_jobs(client, runs, testruns.path, skip_logs)

        # Insert runs to openserach
        _index = INDEX_CONFIG.get("runs").get("name")
        insert_record(client, _index, runs.get("name"), runs)


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


def main(config, testruns_dir, skip_logs):
    # Connect to OpenSearch
    client = connect(config)

    for _index in INDEX_CONFIG:
        index = INDEX_CONFIG.get(_index, {})
        if not index:
            raise ValueError(f"No config present for {index}")

        # Create required index
        create_index(client, index.get("name"), index.get("body"))

    # Update teuthology runs
    update_runs(client, testruns_dir, skip_logs)


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

    # Get log flag
    skip_logs = args["--skip-logs"]

    # Update OpenSearch data
    main(config, testruns_dir, skip_logs)
