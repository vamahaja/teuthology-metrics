import logging
from opensearchpy import OpenSearch

from .config import get_opensearch_config

log = logging.getLogger("teuthology-metrics")

# Fields that can be object or primitive - need normalization to avoid mapping conflicts
PROBLEMATIC_FIELDS = ["extra_system_packages", "extra_packages"]


def sanitize_document(doc):
    """Recursively process document to normalize problematic fields.
    
    For fields in PROBLEMATIC_FIELDS:
        - null → {}
        - string → {"value": str}
        - list → {"items": [...]}
        - dict → kept as-is
    
    Args:
        doc: Document to sanitize (dict, list, or primitive)
        
    Returns:
        Sanitized document with normalized problematic fields
    """
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key in PROBLEMATIC_FIELDS:
                # Normalize problematic fields to always be objects
                if value is None:
                    result[key] = {}
                elif isinstance(value, str):
                    result[key] = {"value": value}
                elif isinstance(value, list):
                    result[key] = {"items": value}
                elif isinstance(value, dict):
                    result[key] = sanitize_document(value)
                else:
                    result[key] = {"value": value}
            else:
                # Recursively process other fields
                result[key] = sanitize_document(value)
        return result
    elif isinstance(doc, list):
        return [sanitize_document(item) for item in doc]
    else:
        # Primitives (str, int, bool, None) - return as-is
        return doc


def connect(config):
    """Connect to OpenSearch instance"""
    # Get OpenSearch configuration
    api_url, username, password, retries, timeout = get_opensearch_config(config)

    # Connect to OpenSearch
    log.info(f"Connecting to OpenSearch at {api_url} with user {username}")
    try:
        client = OpenSearch(
            api_url,
            http_auth=(username, password),
            max_retries=retries,
            timeout=timeout,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            retry_on_timeout=True,
        )
    except Exception as e:
        log.error(f"Failed to connect to OpenSearch: {e}")
        raise e

    return client


def create_index(client, index_name, body):
    """Create OpenSearch index"""
    log.debug(f"Creating new index: {index_name}")
    if not client.indices.exists(index=index_name):
        try:
            client.indices.create(index=index_name, body=body)
        except Exception as e:
            log.error(f"Error creating index in OpenSearch: {e}")
            raise e

        log.debug(f"Created index: {index_name}")
        return

    log.debug(f"Index already present: {index_name}")


def setup_opensearch(config):
    # Connect to OpenSearch
    client = connect(config)
    for _index in get_index_config().keys():
        index = get_index_config().get(_index, {})
        if not index:
            raise ValueError(f"No config present for {index}")

        # Create required index
        create_index(client, index.get("name"), index.get("body"))

    return client


def insert_record(client, index, id, body):
    """Insert a document into OpenSearch"""
    log.debug(f"Indexing document in OpenSearch: {index}/{id}")

    # Insert the document in OpenSearch
    response = None
    try:
        response = client.index(index=index, id=id, body=body, refresh=True)
    except Exception as e:
        log.error(f"Error indexing document in OpenSearch: {e}")
        raise e

    # Check if the response is successful
    if hasattr(response, "status_code") and response.status_code != 200:
        raise ValueError(f"Failed to index documents. Response:\n{response}")


def insert_failure_template(client, message, template_miner):
    # Add failure reason to template miner
    failure_template = template_miner.add_log_message(message)

    # Insert failure template in patterns index
    log.debug(
        "Inserting failure template for cluster id "
        f"{failure_template.get('cluster_id')} in OpenSearch"
    )
    try:
        insert_record(
            client,
            get_index_config().get("patterns").get("name"),
            failure_template.get("cluster_id"),
            {"failure_template": failure_template},
        )
    except Exception as e:
        log.error(
            f"Error: Failed to insert failure template for cluster id "
            f"{failure_template.get('cluster_id')} with error\n{str(e)}"
        )

    return failure_template


def insert_job(client, job_id, job_data):
    """Insert a teuthology job in OpenSearch"""
    # Sanitize job data to normalize problematic fields
    sanitized_data = sanitize_document(job_data)
    
    # Update job data
    _index = get_index_config().get("jobs").get("name")
    try:
        insert_record(client, _index, job_id, sanitized_data)
    except Exception as e:
        log.error(
            f"Error: Failed to insert job job-id {job_id} with error\n{str(e)}"
        )


def insert_run(client, name, run_data):
    """Insert a teuthology run in OpenSearch"""
    # Sanitize run data to normalize problematic fields
    sanitized_data = sanitize_document(run_data)
    
    # Insert runs to openserach
    _index = get_index_config().get("runs").get("name")
    try:
        insert_record(client, _index, name, sanitized_data)
    except Exception as e:
        log.error(
            f"Error: Failed to insert run for {name} with error\n{str(e)}"
        )


def query(client, query, index, size=1000):
    """Search data for given query"""
    query = {"query": query}
    try:
        return client.search(index=index, body=query, size=size)
    except Exception as e:
        log.error(
            f"Error: Failed to search query {query} with error\n{str(e)}"
        )
        return None


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
