import logging

from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from opensearchpy import OpenSearch

from .utils import get_config, get_miner_config, get_snapshot_file

LOG = logging.getLogger("teuthology-metrics")
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


def get_template_miner(config):
    """Get Drain3 template miner instance"""
    file_path = get_snapshot_file(config)
    LOG.debug(f"Reading drain3 snapshot file from {file_path}")

    # Create persistence handler
    persistence_handler = FilePersistence(file_path=file_path)

    # Get template miner config
    template_miner = TemplateMiner(
        config=get_miner_config(), persistence_handler=persistence_handler
    )

    LOG.debug(
        f"Restored drain3 templates: {len(template_miner.drain.clusters)}"
    )

    return template_miner


def connect(config):
    """Connect to OpenSearch instance"""
    # Get OpenSearch configuration
    base_url, username, password = get_configs(config, "opensearch")

    # Connect to OpenSearch
    LOG.info(f"Connecting to OpenSearch at {base_url} with user {username}")
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
        LOG.error(f"Failed to connect to OpenSearch: {e}")
        raise e

    return client


def create_index(client, index_name, body):
    """Create OpenSearch index"""
    LOG.debug(f"Creating new index: {index_name}")
    if not client.indices.exists(index=index_name):
        try:
            client.indices.create(index=index_name, body=body)
        except Exception as e:
            LOG.error(f"Error creating index in OpenSearch: {e}")
            raise e

        LOG.debug(f"Created index: {index_name}")
        return

    LOG.debug(f"Index already present: {index_name}")


def setup_opensearch(config):
    # Connect to OpenSearch
    client = connect(config)

    for _index in INDEX_CONFIG:
        index = INDEX_CONFIG.get(_index, {})
        if not index:
            raise ValueError(f"No config present for {index}")

        # Create required index
        create_index(client, index.get("name"), index.get("body"))

    return client


def insert_record(client, index, id, body):
    """Insert a document into OpenSearch"""
    LOG.debug(f"Indexing document in OpenSearch: {index}/{id}")

    # Insert the document in OpenSearch
    response = None
    try:
        response = client.index(index=index, id=id, body=body, refresh=True)
    except Exception as e:
        LOG.error(f"Error indexing document in OpenSearch: {e}")
        raise e

    # Check if the response is successful
    if hasattr(response, "status_code") and response.status_code != 200:
        raise ValueError(f"Failed to index documents. Response:\n{response}")


def insert_failure_template(client, message, template_miner):
    # Add failure reason to template miner
    failure_template = template_miner.add_log_message(message)

    # Insert failure template in patterns index
    LOG.debug(
        "Inserting failure template for cluster id "
        f"{failure_template.get('cluster_id')} in OpenSearch"
    )
    try:
        insert_record(
            client,
            INDEX_CONFIG.get("patterns").get("name"),
            failure_template.get("cluster_id"),
            {"failure_template": failure_template},
        )
    except Exception as e:
        LOG.error(
            f"Error: Failed to insert failure template for cluster id "
            f"{failure_template.get('cluster_id')} with error\n{str(e)}"
        )

    return failure_template


def insert_job(client, job_id, job_data):
    """Insert a teuthology job in OpenSearch"""
    # Update job data
    _index = INDEX_CONFIG.get("jobs").get("name")
    try:
        insert_record(client, _index, job_id, job_data)
    except Exception as e:
        LOG.error(
            f"Error: Failed to insert job job-id {job_id} "
            f"with error\n{str(e)}"
        )


def insert_run(client, name, run_data):
    """Insert a teuthology run in OpenSearch"""
    # Insert runs to openserach
    _index = INDEX_CONFIG.get("runs").get("name")
    try:
        insert_record(client, _index, name, run_data)
    except Exception as e:
        LOG.error(
            f"Error: Failed to insert run for {name} with error\n{str(e)}"
        )
