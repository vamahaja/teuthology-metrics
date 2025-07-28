"""
Fetch teuthology runs from paddles.

Usage:
    paddle.py --config=<cfg-file> --output-dir=<dir>
        [--user=<user>]
        [--branch=<branch>]
        [--machine-type=<machine_type>]
        [--suite=<suite>]
        [--status=<status>]
        [--date=<date>]

Options:
    --config=<cfg-file>           Path to the configuration file.
    --output-dir=<dir>            Path to the output directory.
    --user=<user>                 Filter by user.
    --branch=<branch>             Filter by branch.
    --machine-type=<machine_type> Filter by machine_type.
    --suite=<suite>               Filter by suite.
    --status=<status>             Filter by status.
    --date=<date>                 Filter by date (YYYY-MM-DD).
"""

import json
import os
from datetime import datetime

import requests
from docopt import docopt
from utils import get_config


def get_paddle_baseurl(_config, server="paddle"):
    """Get the base URL for the Paddle server"""
    _config = get_config(_config, server)
    base_url = f"https://{_config['host']}"

    if _config["port"]:
        base_url += f":{_config['port']}"

    print(f"Paddle server URL: {base_url}")

    return base_url


def get_data(url):
    """Fetch data from a URL"""
    # Get the data from the URL
    response = requests.get(url)

    # Validate the response
    if response.status_code == 200:
        # Check response content type
        ctype = response.headers.get("Content-Type", "").lower()
        if ctype == "application/json":
            return response.json()

        else:
            raise ValueError(f"Unexpected Content-Type : {ctype}")

    print(
        "Failed to fetch data from url. "
        f"Status code: {response.status_code} & Text:\n{response.text}"
    )
    raise ValueError(f"Failed to fetch data from url - {url}")


def get_runs(base_url, segments):
    """Fetch teuthology runs from Paddle."""
    print(f"Requesting test runs: {segments}")

    # Construct the URL for fetching runs
    endpoint = "/".join(segments) if segments else ""

    # construct the URL
    url = requests.utils.requote_uri(f"{base_url}/runs/{endpoint}")

    # Fetch data from the constructed URL
    return get_data(url)


def get_jobs(run, output_dir):
    """Fetch jobs for the given teuthology run"""
    hrefs, job_ids = run.get("href"), []

    # Check if hrefs is a list and has elements
    if hrefs and isinstance(hrefs, list) and len(hrefs) > 0:
        print(f"Fetching jobs for run: {run.get('name')}")
        for job in get_data(hrefs[0]).get("jobs", []):
            print(f"Processing job: {job.get('job_id')}")

            # Update job id list
            job_ids.append(job.get("job_id"))

            # Create output directory with job_id name
            run_dir = os.path.join(output_dir, f"{job.get('job_id')}.json")
            write_job_metadata(run_dir, job)

        return job_ids

    print(f"Warning: 'href' key missing or empty for run: {run.get('name')}")
    return []


def write_job_metadata(_file, metadata):
    """Write data to a JSON file"""
    print(f"Writing data to {_file}")

    # Open the file and write the metadata
    with open(_file, "w") as _f:
        json.dump(metadata, _f, indent=2)


def main(config_file, segments, output_dir):
    # Get paddle base URL
    base_url = get_paddle_baseurl(config_file)

    # Fetch jobs for the given teuthology runs
    for run in get_runs(base_url, segments):
        print(f"Processing run: {run.get('name')}")

        # Create output directory with run name
        run_dir = os.path.join(output_dir, run.get("name"))
        os.makedirs(run_dir, exist_ok=True)

        jobs_dir = os.path.join(run_dir, "jobs")
        os.makedirs(jobs_dir, exist_ok=True)

        # Get jobs for the run
        run["job_ids"] = get_jobs(run, jobs_dir)

        # Write jobs to output directory
        write_job_metadata(os.path.join(run_dir, "results.json"), run)


if __name__ == "__main__":
    print(
        "\n===== Starting new paddle session - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====="
    )

    # Parse command line arguments
    args = docopt(__doc__)

    # Get configuration file
    config_file = args["--config"]

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

    # Get output directory
    output_dir = args["--output-dir"]

    # Get data from Paddle
    main(config_file, segments, output_dir)
