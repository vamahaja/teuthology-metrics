"""
Fetch teuthology runs from paddles.

Usage:
    paddle.py --config=<cfg-file> --output-dir=<dir>
        [--user=<user>]
        [--branch=<branch>]
        [--machine-type=<machine-type>]
        [--suite=<suite>]
        [--status=<status>]
        [--date=<date>]

Options:
    --config=<cfg-file>           Path to the configuration file.
    --output-dir=<dir>            Path to the output directory.
    --user=<user>                 Filter by user.
    --branch=<branch>             Filter by branch.
    --machine-type=<machine-type> Filter by machine type.
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
    response = requests.get(url)
    if response.status_code == 200:
        ctype = response.headers.get("Content-Type", "").lower()
        if ctype == "application/json":
            return response.json()

        elif ctype.startswith("text/plain"):
            return response.text

        else:
            raise ValueError(f"Unexpected Content-Type : {ctype}")

    print(
        "Failed to fetch data from url. "
        f"Status code: {response.status_code} & Text:\n{response.text}"
    )
    raise ValueError("Failed to fetch data from url ...")


def get_runs(base_url, segments):
    """Fetch teuthology runs from Paddle."""
    print(f"Requesting test runs: {segments}")
    endpoint = "/".join(segments) if segments else ""
    url = requests.utils.requote_uri(f"{base_url}/runs/{endpoint}")

    return get_data(url)


def get_jobs(runs):
    """Fetch jobs for the given teuthology runs"""
    jobs = []
    for run in runs:
        hrefs = run.get("href")
        if hrefs and isinstance(hrefs, list) and len(hrefs) > 0:
            print(f"Fetching jobs for run: {run.get('name')}")
            jobs.append(get_data(hrefs[0]))
            continue

        print(
            f"Warning: 'href' key missing or empty for run: {run.get('name')}"
        )

    return jobs


def get_logs(runs, output_dir):
    """Fetch logs for the given teuthology jobs"""
    for run in runs:
        testrun_name = run.get("name")
        testrun_dir = os.path.join(output_dir, testrun_name)
        os.makedirs(testrun_dir, exist_ok=True)

        print(f"Fetching logs for run: {testrun_name}")
        for job in run.get("jobs", {}):
            write_json(
                os.path.join(testrun_dir, f"{job.get('job_id')}.json"), job
            )

            log_href, job_id = job.get("log_href"), job.get("job_id")
            if log_href and job_id:
                print(f"Fetching logs for job id: {job_id}")
                write_logs(
                    os.path.join(testrun_dir, f"{job_id}.log"),
                    get_data(log_href),
                )
                continue

            print(
                "Warning: 'log_href' or 'job_id' key missing or empty for job"
            )


def write_logs(file_name, logs):
    """Write logs to a file"""
    print(f"Writing logs to {file_name}")
    with open(file_name, "w") as f:
        f.writelines(logs)


def write_json(file_name, _json):
    """Write data to a JSON file"""
    print(f"Writing data to {file_name}")
    with open(file_name, "w") as f:
        json.dump(_json, f, indent=2)


if __name__ == "__main__":
    print(
        "\n===== Starting new paddle session - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====="
    )

    # Parse command line arguments
    args = docopt(__doc__)

    # Get paddle base URL
    base_url = get_paddle_baseurl(args["--config"])

    # Check for output dir
    output_dir = args["--output-dir"]
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

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

    # Fetch teuthology runs
    runs = get_runs(base_url, segments)

    # Fetch jobs for the given teuthology runs
    jobs = get_jobs(runs)

    # Write jobs to JSON
    write_json(os.path.join(output_dir, "testruns.json"), jobs)

    # Fetch logs for the given teuthology jobs
    get_logs(jobs, output_dir)
