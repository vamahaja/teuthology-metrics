import logging

from datetime import datetime, timedelta
from jinja2 import Template

from .config import get_report_config
from .fetcher import (
    connect as paddle_connect,
    get_data,
    get_runs,
)
from .ingest import (
    connect as opensearch_connect,
    get_template_miner,
    insert_failure_template,
    insert_job,
    insert_run,
    query,
    setup_opensearch,
)
from .utils import send_email

# Set email subject template
EMAIL_SUBJECT_FORMAT = "Teuthology Test Summary - {end_date} - {branch}"

# Set logging environment config
log = logging.getLogger("teuthology-metrics")


def update_job(client, job, template_miner):
    # Get log reference and job id
    job_id, failure_reason = job.get("job_id"), job.get("failure_reason")
    log.debug(f"Processing job: {job_id}")

    # Update template miner with failure_reason
    if template_miner and failure_reason:
        log.debug(
            f"Adding failure reason for job-id {job_id} to template miner"
        )
        job["failure_template"] = insert_failure_template(
            client, failure_reason, template_miner
        )

    # Update job metadata in OpenSearch
    insert_job(client, job_id, job)

    return job_id


def update_runs(client, run, template_miner):
    # Get hrefs and initialize job_ids
    hrefs, name, run["job_ids"] = run.get("href"), run.get("name"), []

    # Check if hrefs is a list and has elements
    if hrefs and isinstance(hrefs, list) and len(hrefs) > 0:
        log.debug(f"Fetching jobs for run: {name}")
        for job in get_data(hrefs[0]).get("jobs", []):
            # Update job with run metadata
            job_id = update_job(client, job, template_miner)

            # Update job id list
            run["job_ids"].append(job_id)

    # Update run metadata in OpenSearch
    insert_run(client, name, run)


def process(config_file, skip_drain3_templates, segments):
    # Get paddle api URL
    api_url = paddle_connect(config_file)

    # Get Drain3 templates flag
    template_miner = None
    if not skip_drain3_templates:
        template_miner = get_template_miner(config_file)

    # Setup OpenSearch
    client = setup_opensearch(config_file)

    # Fetch jobs for the given teuthology runs
    for run in get_runs(api_url, segments):
        log.debug(f"Processing run: {run.get('name')}")

        # Update run metadata
        update_runs(client, run, template_miner)


def query_data(client, branch, start_date, end_date, index, sha_id=None):
    """Fetch data for a specific branch within a date range.

    Args:
        config_file: Configuration file path
        branch: Branch name (e.g., quincy, reef, main).
        start_date: Start date string in YYYY-MM-DD format.
        end_date: End date string in YYYY-MM-DD format.
        index: OpenSearch index name.
        sha_id: SHA ID to filter results.

    Returns:
        List of hits from OpenSearch.
    """
    # Debug
    log.debug(
        f"Fetching data for branch {branch} from {start_date} to {end_date}"
    )

    # Fetch data for given period of time
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = datetime.strptime(start_date, "%Y-%m-%d")
    all_hits = []
    while current <= end:
        date = current.strftime("%Y-%m-%d")
        _query = { 
            "bool":
                { "must": 
                    [
                        {"wildcard": {"posted.keyword": f"{date}*"}},
                        {"term": {"branch.keyword": branch}},
                        {"term": {"sha1.keyword": sha_id}},
                    ]
                }
            }
        response = query(client, _query, index)
        all_hits.extend(response["hits"]["hits"])
        current += timedelta(days=1)

    return all_hits


def teuthology_report(
        hits, branch, results_server, sha_id, platform="OpenStack"
    ):
    """Render the HTML report using Jinja2 template.

    Args:
        hits: List of hits from OpenSearch.
        branch: Branch name (e.g., quincy, reef, main).
        results_server: Base URL for the results server.
        sha_id: SHA ID to include in the report.
        platform: Cloud platform

    Returns:
        Rendered HTML string.
    """
    log.debug(f"Rendering HTML report for branch {branch}")
    if not hits:
        log.warning(f"No data available for branch {branch}")
        return f"<p>No data available for branch {branch}</p>"

    # Keep only the last posted entry for each suite
    suite_latest = {}
    for hit in hits:
        suite_name = hit["_source"].get("suite", "N/A")
        posted = hit["_source"].get("posted", "")

        # If suite not seen yet, or this entry is more recent, keep it
        if (
            suite_name not in suite_latest
            or posted > suite_latest[suite_name]["posted"]
        ):
            suite_latest[suite_name] = {"posted": posted, "hit": hit}

    # Prepare the data from the latest entries
    data = []
    for suite_name, entry in suite_latest.items():
        hit = entry["hit"]
        results = hit["_source"].get("results", {})
        data.append(
            {
                "suite": suite_name,
                "href": f"{results_server}/{hit['_id']}",
                "total": results.get("total", 0),
                "passed": results.get("pass", 0),
                "failed": results.get("fail", 0),
                "dead": results.get("dead", 0),
                "waiting": results.get("waiting", 0),
                "queued": results.get("queued", 0),
            }
        )

    # Load the HTML template and render it with data
    with open("../templates/report.j2") as f:
        html_template = Template(f.read())

    return html_template.render(
        branch=branch.capitalize(),
        cloud_platform=platform,
        sha_id=sha_id,
        data=data,
    )


def publish_report(
        config_file, start_date, end_date, branch, address, sha_id
    ):
    """Send teuthology report mail
    
    Args:
        config_file: Report & OpenSearch config file path
        start_date: Report start date
        end_date: Report end date
        branch: Ceph build branch
        address: Sender email address
        sha_id: Build shaman id
    """
    # Load configurations
    config = get_report_config(config_file)
    index, server = (
        config.get("opensearch_index"), config.get("results_server")
    )

    # Connect to OpenSearch client
    client = opensearch_connect(config_file)

    # Fetch data for the given branch and date range
    hits = query_data(
        client, branch, start_date, end_date, index, sha_id,
    )

    # Check if data is available
    if not hits:
        log.warning(f"No data found for branch {branch}, skipping email ..")
        return

    # Render the HTML report
    html_content = teuthology_report(hits, branch,server, sha_id)

    # Set email subject & send the email with the report
    subject = EMAIL_SUBJECT_FORMAT.format(end_date=end_date, branch=branch)
    send_email(config_file, subject, html_content, address)
