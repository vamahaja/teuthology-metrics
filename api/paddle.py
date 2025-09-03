import logging
import os

import requests

from .utils import get_config, write_data, write_json

LOG = logging.getLogger("teuthology-metrics")


def get_paddle_baseurl(_config, server="paddle"):
    """Get the base URL for the Paddle server"""
    _config = get_config(_config, server)
    base_url = f"https://{_config['host']}"

    if _config["port"]:
        base_url += f":{_config['port']}"

    LOG.info(f"Paddle server URL: {base_url}")

    return base_url


def get_data(url):
    """Fetch data from a URL"""
    # Get the data from the URL
    response = requests.get(url)

    # Validate the response
    if response.status_code == 200:
        ctype = response.headers.get("Content-Type", "").lower()
        if ctype == "application/json":
            return response.json()

        elif ctype.startswith("text/plain"):
            return response.text

        else:
            raise ValueError(f"Unexpected Content-Type : {ctype}")

    LOG.error(
        "Failed to fetch data from url. "
        f"Status code: {response.status_code} & Text:\n{response.text}"
    )
    raise ValueError(f"Failed to fetch data from url - {url}")


def get_runs(base_url, segments):
    """Fetch teuthology runs from Paddle."""
    LOG.debug(f"Requesting test runs: {segments}")

    # Construct the URL for fetching runs
    endpoint = "/".join(segments) if segments else ""

    # construct the URL
    url = requests.utils.requote_uri(f"{base_url}/runs/{endpoint}")

    # Fetch data from the constructed URL
    return get_data(url)


def get_jobs(run, jobs_dir, logs_dir, skip_pass_logs):
    """Fetch jobs for the given teuthology run"""
    hrefs, job_ids = run.get("href"), []

    # Check if hrefs is a list and has elements
    if hrefs and isinstance(hrefs, list) and len(hrefs) > 0:
        LOG.debug(f"Fetching jobs for run: {run.get('name')}")
        for job in get_data(hrefs[0]).get("jobs", []):
            # Get log reference and job id
            log_href, job_id = job.get("log_href"), job.get("job_id")

            LOG.debug(f"Processing job: {job.get('job_id')}")

            # Update job id list
            job_ids.append(job_id)

            # Write job id metadata
            job_path = os.path.join(jobs_dir, f"{job_id}.json")
            write_json(job_path, job)

            if logs_dir and (skip_pass_logs and job.get("status") == "fail"):
                # Write job id logs
                log_path = os.path.join(logs_dir, f"{job_id}.log")
                write_data(log_path, get_data(log_href))

        return job_ids

    LOG.debug(
        f"Warning: 'href' key missing or empty for run: {run.get('name')}"
    )
    return []
