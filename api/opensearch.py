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
from opensearchpy import OpenSearch, helpers
from utils import get_config


def get_opensearch_config(_config, server="opensearch"):
    """Get OpenSearch configuration details"""
    _config = get_config(_config, server)
    base_url = f"http://{_config['host']}"

    if _config["port"]:
        base_url += f":{_config['port']}"

    return base_url, _config["username"], _config["password"]


def connect_to_opensearch(config):
    """Connect to OpenSearch instance"""
    base_url, username, password = get_opensearch_config(config, "opensearch")

    print(f"Connecting to OpenSearch at {base_url} with user {username}")
    try:
        client = OpenSearch(
            base_url,
            http_auth=(username, password),
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
    except Exception as e:
        print(f"Failed to connect to OpenSearch: {e}")
        raise e

    return client


def set_opensearch_client_configs(client):
    """Set OpenSearch client configurations"""
    # Set index mapping limits for jobs
    client.indices.put_settings(
        index="jobs", body={"index.mapping.total_fields.limit": 10000}
    )

    # Set index mapping limits for runs
    client.indices.put_settings(
        index="runs", body={"index.mapping.total_fields.limit": 10000}
    )


def get_testruns(_data):
    """Get teuthology runs from the specified file"""
    data = {}

    print(f"Reading teuthology runs from {_data}")
    with open(_data, "r") as f:
        data = json.load(f)

    if not data:
        raise ValueError("No data found")

    for runs in data:
        if "name" not in runs:
            raise ValueError("No runs found in the data")

    return data


def update_teuthology_runs(client, testruns, testruns_dir):
    """Update teuthology runs in OpenSearch"""
    for testrun in testruns:
        job_ids = []
        testrun_name = testrun.get("name")
        testrun_dir = os.path.join(testruns_dir, testrun_name)
        for job in testrun.get("jobs", []):
            job_id = job.get("job_id")
            print(f"Updating job: {job_id}")
            index_opensearch_record(client, "jobs", job_id, job)
            job_ids.append(job_id)
            job_id_log = os.path.join(testrun_dir, f"{job_id}.log")
            index_opensearch_logs(client, "logs", job_id, job_id_log)

        testrun["jobs"] = job_ids

        print(f"Updating testrun: {testrun.get('name')}")
        index_opensearch_record(client, "runs", testrun.get("name"), testrun)


def index_opensearch_logs(client, index, id, log_file):
    """Insert logs into OpenSearch"""
    print(f"Indexing logs in OpenSearch: {index}/{id}")
    batch_size, batch_index = 1000, 0

    def batchify(iterable, batch_size=batch_size):
        batch = []
        for item in iterable:
            batch.append(item)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    with open(log_file, "r", encoding="utf-8") as f:
        lines = (line for line in f if line.strip())

        for batch_lines in batchify(lines, batch_size):
            print(f"Processing batch {batch_index + 1}")
            actions = [{
                    "_index": "app-logs",
                    "_source": {
                        "message": line.rstrip("\n"),
                        "job-id": id
                    }
                }
                for line in batch_lines
            ]
            helpers.bulk(client, actions)
            batch_index += 1

            try:
                helpers.bulk(client, actions)
            except Exception as e:
                print(f"Error during ingestion: {e}")


def index_opensearch_record(client, index, id, body):
    """Insert a document into OpenSearch"""
    print(f"Indexing document in OpenSearch: {index}/{id}")
    response = None
    try:
        response = client.index(index=index, id=id, body=body)
    except Exception as e:
        print(f"Error indexing document in OpenSearch: {e}")
        raise

    if hasattr(response, "status_code") and response.status_code != 200:
        raise ValueError(f"Failed to index documents. Response:\n{response}")


if __name__ == "__main__":
    print(
        "\n===== Starting new opensearch session - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====="
    )

    # Parse command line arguments
    args = docopt(__doc__)

    # Get configuration and data
    config = args["--config"]
    testruns_dir = args["--testruns-dir"]
    testruns = get_testruns(os.path.join(testruns_dir, "testruns.json"))

    # Connect to OpenSearch
    client = connect_to_opensearch(config)

    # Set OpenSearch client configurations
    set_opensearch_client_configs(client)

    # Update teuthology runs
    update_teuthology_runs(client, testruns, testruns_dir)
