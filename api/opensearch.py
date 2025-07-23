"""
Update job details to opensearch

Usage:
    opensearch.py --config=<cfg-file> --testruns=<json-file>

Options:
    --config=<cfg-file>     Path to the configuration file.
    --testruns=<file>       Path to the test runs json file.
"""

import json
from datetime import datetime

from docopt import docopt
from opensearchpy import OpenSearch
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


def update_teuthology_runs(client, testruns):
    """Update teuthology runs in OpenSearch"""
    for testrun in testruns:
        job_ids = []
        for job in testrun.get("jobs", []):
            print(f"Updating job: {job.get('job_id')}")
            index_opensearch_record(client, "jobs", job.get("job_id"), job)
            job_ids.append(job.get("job_id"))

        testrun["jobs"] = job_ids

        print(f"Updating testrun: {testrun.get('name')}")
        index_opensearch_record(client, "runs", testrun.get("name"), testrun)


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
    testruns = get_testruns(args["--testruns"])

    # Connect to OpenSearch
    client = connect_to_opensearch(config)

    set_opensearch_client_configs(client)

    # Update teuthology runs
    update_teuthology_runs(client, testruns)
