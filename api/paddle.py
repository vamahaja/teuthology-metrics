"""
Fetch teuthology runs from paddles.

Usage:
    paddle.py --config=<cfg-file>
        [--user=<user>]
        [--branch=<branch>]
        [--machine-type=<machine_type>]
        [--suite=<suite>]
        [--status=<status>]
        [--date=<date>]
        [--output=<file>]

Options:
    --config=<cfg-file>           Path to the configuration file.
    --user=<user>                 Filter by user.
    --branch=<branch>             Filter by branch.
    --machine-type=<machine_type> Filter by machine_type.
    --suite=<suite>               Filter by suite.
    --status=<status>             Filter by status.
    --date=<date>                 Filter by date (YYYY-MM-DD).
    --output=<file>               Path to the output file.
"""

import json
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
        return response.json()

    print(
        "Failed to fetch data from url. "
        f"Status code: {response.status_code}"
    )
    print(f"Response: {response.text}")
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


def write_json(_file, data):
    """Write data to a JSON file"""
    print(f"Writing data to {_file}")
    with open(_file, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    print(
        "\n===== Starting new paddle session - "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====="
    )

    # Parse command line arguments
    args = docopt(__doc__)

    # Get paddle base URL
    base_url = get_paddle_baseurl(args["--config"])

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

    # Write jobs to output file
    output = args["--output"]
    write_json(output, jobs) if output else None
