"""
Update teuthology runs in OpenSearch.

Usage:
    run.py --config=<cfg-file>
        [--user=<user>]
        [--branch=<branch>]
        [--machine-type=<machine_type>]
        [--suite=<suite>]
        [--status=<status>]
        [--date=<date>]
        [--skip-drain3-templates]
        [--log-level <LOG>]
        [--log-path <LOG_PATH>]

Options:
    --config=<cfg-file>           Path to the configuration file.
    --user=<user>                 Filter by user.
    --branch=<branch>             Filter by branch.
    --machine-type=<machine_type> Filter by machine_type.
    --suite=<suite>               Filter by suite.
    --status=<status>             Filter by status.
    --date=<date>                 Filter by date (YYYY-MM-DD).
    --skip-drain3-templates       Skip processing Drain3 templates.
    --log-level <LOG>             Log level for log utility
    --log-path <LOG_PATH>         Log file path for log utility
"""

import logging

from docopt import docopt

from api.opensearch import (
    get_template_miner,
    insert_failure_template,
    insert_job,
    insert_run,
    setup_opensearch,
)
from api.paddle import get_data, get_paddle_baseurl, get_runs

LOG = logging.getLogger("teuthology-metrics")


def process_job(client, job, template_miner):
    # Get log reference and job id
    job_id, failure_reason = job.get("job_id"), job.get("failure_reason")
    LOG.debug(f"Processing job: {job_id}")

    # Update template miner with failure_reason
    if template_miner and failure_reason:
        LOG.debug(
            f"Adding failure reason for job-id {job_id} to template miner"
        )
        job["failure_template"] = insert_failure_template(
            client, failure_reason, template_miner
        )

    # Update job metadata in OpenSearch
    insert_job(client, job_id, job)

    return job_id


def process_runs(client, run, template_miner):
    # Get hrefs and initialize job_ids
    hrefs, name, run["job_ids"] = run.get("href"), run.get("name"), []

    # Check if hrefs is a list and has elements
    if hrefs and isinstance(hrefs, list) and len(hrefs) > 0:
        LOG.debug(f"Fetching jobs for run: {name}")
        for job in get_data(hrefs[0]).get("jobs", []):
            # Update job with run metadata
            job_id = process_job(client, job, template_miner)

            # Update job id list
            run["job_ids"].append(job_id)

    # Update run metadata in OpenSearch
    insert_run(client, name, run)


def main(config_file, skip_drain3_templates, segments):
    # Get paddle base URL
    base_url = get_paddle_baseurl(config_file)

    # Get Drain3 templates flag
    template_miner = None
    if not skip_drain3_templates:
        template_miner = get_template_miner(config_file)

    # Setup OpenSearch
    client = setup_opensearch(config_file)

    # Fetch jobs for the given teuthology runs
    for run in get_runs(base_url, segments):
        LOG.debug(f"Processing run: {run.get('name')}")

        # Update run metadata
        process_runs(client, run, template_miner)


if __name__ == "__main__":

    # Parse command line arguments
    args = docopt(__doc__)

    # Get configuration file
    config_file = args["--config"]

    # Get Drain3 templates flag
    skip_drain3_templates = args["--skip-drain3-templates"]

    # Build URL segments
    segments = []
    if args["--user"]:
        segments += ["user", args["--user"]]
    if args["--branch"]:
        segments += ["branch", args["--branch"]]
    if args["--machine-type"]:
        segments += ["machine_type", args["--machine-type"]]
    if args["--suite"]:
        segments += ["suite", args["--suite"]]
    if args["--date"]:
        segments += ["date", args["--date"]]
    if args["--status"]:
        segments += ["status", args["--status"]]

    # Call main function
    main(config_file, skip_drain3_templates, segments)
