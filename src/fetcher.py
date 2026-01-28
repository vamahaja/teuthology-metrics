import logging
import os

import requests

from .utils import write_data, write_json
from .config import get_paddle_config

log = logging.getLogger("teuthology-metrics")


def connect(config):
    """Check paddle server connectivity"""
    api_url, timeout = get_paddle_config(config)
    try:
        requests.head(api_url, timeout=timeout)
        return api_url
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"API not accessible: {exc}") from exc


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

    log.error(
        "Failed to fetch data from url. "
        f"Status code: {response.status_code} & Text:\n{response.text}"
    )
    raise ValueError(f"Failed to fetch data from url - {url}")


def get_runs(base_url, segments):
    """Fetch teuthology runs from Paddle."""
    log.debug(f"Requesting test runs: {segments}")

    # Construct the URL for fetching runs
    endpoint = "/".join(segments) if segments else ""

    # construct the URL
    url = requests.utils.requote_uri(f"{base_url}/runs/{endpoint}")

    # Fetch data from the constructed URL
    return get_data(url)

def get_runs_by_branch_and_date(base_url, branch, start_date, end_date):
    """Fetch teuthology runs from Paddle by branch and date range.

    Args:
        base_url: Paddle API base URL
        branch: Branch name (e.g., quincy, reef, main)
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD

    Returns:
        List of run objects from Paddle
    """
    from datetime import datetime, timedelta

    log.debug(f"Fetching runs from Paddle: branch={branch} from {start_date} to {end_date}")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = datetime.strptime(start_date, "%Y-%m-%d")
    all_runs = []
    while current <= end:
        date = current.strftime("%Y-%m-%d")
        url = requests.utils.requote_uri(f"{base_url}/runs/branch/{branch}/date/{date}")
        try:
            data = get_data(url)
            if isinstance(data, list):
                all_runs.extend(data)
            elif isinstance(data, dict) and "runs" in data:
                all_runs.extend(data["runs"])
            else:
                log.warning(f"Unexpected Paddle response for {branch}/{date}, skipping")
        except (ValueError, requests.exceptions.RequestException) as e:
            log.warning(f"Failed to fetch runs for {branch}/{date}: {e}")
        current += timedelta(days=1)
    return all_runs


def get_jobs(run, jobs_dir, logs_dir, skip_pass_logs):
    """Fetch jobs for the given teuthology run"""
    hrefs, job_ids = run.get("href"), []

    # Check if hrefs is a list and has elements
    if hrefs and isinstance(hrefs, list) and len(hrefs) > 0:
        log.debug(f"Fetching jobs for run: {run.get('name')}")
        for job in get_data(hrefs[0]).get("jobs", []):
            # Get log reference and job id
            log_href, job_id = job.get("log_href"), job.get("job_id")

            log.debug(f"Processing job: {job.get('job_id')}")

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

    log.debug(
        f"Warning: 'href' key missing or empty for run: {run.get('name')}"
    )
    return []
