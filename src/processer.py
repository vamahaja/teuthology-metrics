import logging
import os

from datetime import datetime, timedelta, timezone
from jinja2 import Template

# Get the directory containing this file, then navigate to templates
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

from .config import get_report_config, get_scheduler_config
from .fetcher import (
    connect as paddle_connect,
    get_data,
    get_runs,
    get_runs_by_branch_and_date,
)
from .ingest import (
    connect as opensearch_connect,
    insert_failure_template,
    insert_job,
    insert_run,
    query,
    setup_opensearch,
)
from .miner import get_template_miner
from .utils import send_email, set_logging_env

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


def query_data(client, branch, start_date, end_date, index, sha_id=None, user=None):
    """Fetch data for a specific branch within a date range.

    Args:
        client: OpenSearch client
        branch: Branch name (e.g., quincy, reef, main).
        start_date: Start date string in YYYY-MM-DD format.
        end_date: End date string in YYYY-MM-DD format.
        index: OpenSearch index name.
        sha_id: Optional SHA ID to filter results.
        user: Optional user to filter results (e.g. ubuntu).

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
        # Build query conditions
        must_conditions = [
            {"wildcard": {"posted.keyword": f"{date}*"}},
            {"term": {"branch.keyword": branch}},
        ]
        # Only filter by sha_id if provided
        if sha_id:
            must_conditions.append({"term": {"sha1.keyword": sha_id}})
        # Only filter by user if provided
        if user:
            must_conditions.append({"term": {"user.keyword": user}})
        
        _query = {"bool": {"must": must_conditions}}
        response = query(client, _query, index)
        if response and "hits" in response:
            all_hits.extend(response["hits"]["hits"])
        current += timedelta(days=1)

    return all_hits

def query_data_from_paddle(config_file, branch, start_date, end_date, sha_id=None, user=None):
    """Fetch report data from Paddle by branch and date range.

    Returns a list in the same shape as OpenSearch hits so teuthology_report
    can be used unchanged. Paddle run objects must include: name, suite,
    posted, sha1, results (with pass, fail, dead, running, waiting, queued, total).
    """
    log.debug(
        f"Fetching data from Paddle for branch {branch} from {start_date} to {end_date}"
    )
    api_url = paddle_connect(config_file)
    runs = get_runs_by_branch_and_date(api_url, branch, start_date, end_date)
    if user:
        runs = [r for r in runs if r.get("user") == user]
    if sha_id:
        runs = [r for r in runs if r.get("sha1") == sha_id]
    hits = [{"_id": r.get("name", ""), "_source": r} for r in runs]
    return hits


def teuthology_report(
        hits, branch, results_server, sha_id=None, platform="OpenStack"
    ):
    """Render the HTML report using Jinja2 template.

    Args:
        hits: List of hits from OpenSearch.
        branch: Branch name (e.g., quincy, reef, main).
        results_server: Base URL for the results server.
        sha_id: Optional SHA ID to include in the report.
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

    # Extract sha_id from data if not provided
    if not sha_id and suite_latest:
        # Get sha_id from the most recent entry
        most_recent = max(suite_latest.values(), key=lambda x: x["posted"])
        sha_id = most_recent["hit"]["_source"].get("sha1", "N/A")

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
                "running": results.get("running", 0),
                "waiting": results.get("waiting", 0),
                "queued": results.get("queued", 0),
            }
        )

    # Load the HTML template and render it with data
    with open(os.path.join(_TEMPLATES_DIR, "report.j2")) as f:
        html_template = Template(f.read())

    return html_template.render(
        branch=branch.capitalize(),
        cloud_platform=platform,
        sha_id=sha_id,
        data=data,
    )


def publish_report(
        config_file, start_date, end_date, branch, address, sha_id=None,
        use_paddle=False, user=None
    ):
    """Send teuthology report mail
    
    Args:
        config_file: Report & OpenSearch config file path
        start_date: Report start date
        end_date: Report end date
        branch: Ceph build branch
        address: Sender email address
        sha_id: Optional build shaman id
        use_paddle: If True, fetch report data from Paddle instead of OpenSearch
        user: Optional user to filter report data (e.g. ubuntu)
    """
    # Load configurations
    config = get_report_config(config_file)
    index, server = (
        config.get("opensearch_index"), config.get("results_server")
    )

    if use_paddle:
        log.info(f"Fetching report data from Paddle for branch {branch}")
        hits = query_data_from_paddle(
            config_file, branch, start_date, end_date, sha_id, user
        )
    else:
        client = opensearch_connect(config_file)
        hits = query_data(
            client, branch, start_date, end_date, index, sha_id, user
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


def run_task(config_file, user, skip_drain3_templates, log_level=None, log_path=None):
    """Run teuthology testrun process"""
    # Create new log file for this cron execution
    set_logging_env(level=log_level, path=log_path, job_type="task")

    # Get current date
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get teuthology suites
    suites = get_scheduler_config(config_file).get("suites")

    # Execute run method
    try:
        for suite in suites:
            log.debug(f"[TASK JOB START] suite={suite} | date={now}")

            # Set paddle variables
            segments = ["suite", suite, "user", user, "date", now]

            # Run teuthology testrun process
            process(
                config_file=config_file,
                skip_drain3_templates=skip_drain3_templates,
                segments=segments,
            )
    except Exception as exc:
        log.error(f"[TASK JOB ERROR] {exc}")
    finally:
        log.debug("[TASK JOB END]")


def run_report(config_file, cron_dir=None, log_level=None, log_path=None, use_paddle=False, user=None):
    """Run teuthology report process"""
    # Create new log file for this cron execution
    set_logging_env(level=log_level, path=log_path, job_type="report")

    # Get current date
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")

    # Calculate date range (last 24 hours)
    schedule_date = now - timedelta(days=1)
    start_date = schedule_date.strftime("%Y-%m-%d")

    # Try to read sha_id from file if cron_dir is provided
    sha_id = None
    if cron_dir:
        sha_file = f"{cron_dir}/{start_date}"
        if os.path.exists(sha_file):
            sha_id = open(sha_file).read().strip()
            log.debug(f"Using sha_id from file: {sha_id}")
        else:
            log.debug(f"SHA file not found: {sha_file}, proceeding without sha_id")

    # Get configs
    _config = get_scheduler_config(config_file)

    # Execute report method
    branches, email = _config.get("branches"), _config.get("email")
    for branch in branches:
        try:
            log.debug(
                f"[REPORT JOB START] branch={branch} | "
                f"start_date={start_date} | end_date={end_date}"
            )

            # Run teuthology report process with date range
            publish_report(
                config_file=config_file,
                start_date=start_date,
                end_date=end_date,
                branch=branch,
                sha_id=sha_id,
                address=email,
                use_paddle=use_paddle,
                user=user,
            )
        except Exception as exc:
            log.error(f"[REPORT JOB ERROR] branch={branch} | error={exc}")

            # Continue with the next branch
            continue

    log.debug("[REPORT JOB END]")
