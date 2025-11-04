"""
Generate and send Teuthology report via email.

Usage:
    report.py --config=<cfg-file> \
              --branch=<branch> \
              --start-date=<start-date> \
              --end-date=<end-date> \
              --email-address=<email> \
              --sha-id=<sha-id>

Options:
    --config=<cfg-file>           Path to the configuration file.
    --branch=<branch>             Branch name (e.g., quincy, reef, main).
    --start-date=<start-date>     Report start date (YYYY-MM-DD).
    --end-date=<end-date>         Report end date (YYYY-MM-DD).
    --email-address=<email>       Email address to send the report to.
    --sha-id=<sha-id>             SHA ID to filter results.
"""

import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from docopt import docopt
from jinja2 import Template

from api.opensearch import connect
from api.utils import get_email_config

EMAIL_SUBJECT_FORMAT = "Teuthology Test Summary - {end_date} - {branch}"
LOG = logging.getLogger("teuthology-metrics")


def fetch_data(client, branch, start_date, end_date, index, sha_id=None):
    """Fetch data for a specific branch within a date range.
     Args:
        client: OpenSearch client instance.
        branch: Branch name (e.g., quincy, reef, main).
        start_date: Start date string in YYYY-MM-DD format.
        end_date: End date string in YYYY-MM-DD format.
        index: OpenSearch index name.
        sha_id: SHA ID to filter results.
    Returns:
        List of hits from OpenSearch.
    """
    LOG.debug(
        f"Fetching data for branch: {branch} from {start_date} to {end_date}"
    )

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start
    all_hits = []
    while current <= end:
        date = current.strftime("%Y-%m-%d")
        must_conditions = [
            {"wildcard": {"posted.keyword": f"{date}*"}},
            {"term": {"branch.keyword": branch}},
            {"term": {"sha1.keyword": sha_id}},
        ]
        query = {"query": {"bool": {"must": must_conditions}}}
        response = client.search(index=index, body=query, size=1000)
        all_hits.extend(response["hits"]["hits"])
        current += timedelta(days=1)

    return all_hits


def render_teuthology_report(hits, branch, results_server, sha_id):
    """Render the HTML report using Jinja2 template.
    Args:
        hits: List of hits from OpenSearch.
        branch: Branch name (e.g., quincy, reef, main).
        results_server: Base URL for the results server.
        sha_id: SHA ID to include in the report.
    Returns:
        Rendered HTML string."""
    LOG.debug(f"Rendering HTML report for branch: {branch}")
    if not hits:
        LOG.warning(f"No data available for branch: {branch}")
        return f"<p>No data available for branch: {branch}</p>"

    cloud_platform = "OpenStack"

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
    with open("templates/report.j2") as f:
        html_template = Template(f.read())

    return html_template.render(
        branch=branch.capitalize(),
        cloud_platform=cloud_platform,
        sha_id=sha_id,
        data=data,
    )


def send_email(config, subject, html_body, email_address):
    """Send the email with the report.
    Args:
        config: Dictionary containing email configuration.
        subject: Subject of the email.
        html_body: HTML content of the email.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["email_from"]
    msg["To"] = email_address

    mime_text = MIMEText(html_body, "html")
    msg.attach(mime_text)

    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.starttls()
        if config.get("username") and config.get("password"):
            server.login(config["username"], config["password"])
        server.sendmail(config["email_from"], email_address, msg.as_string())
        LOG.debug("Report sent sucessfully")


def main(config_file, start_date, end_date, branch, email_address, sha_id):
    # Load configurations
    email_config = get_email_config(config_file)
    # Set up OpenSearch client
    client = connect(config_file)
    LOG.debug("OpenSearch client connected")

    # Fetch data for the given branch and date range
    hits = fetch_data(
        client,
        branch,
        start_date,
        end_date,
        email_config["opensearch_index"],
        sha_id,
    )

    # Render the HTML report
    html_content = render_teuthology_report(
        hits, branch, email_config["results_server"], sha_id
    )

    subject = EMAIL_SUBJECT_FORMAT.format(end_date=end_date, branch=branch)

    # Send the email with the report
    send_email(email_config, subject, html_content, email_address)


if __name__ == "__main__":
    # Parse command line arguments
    args = docopt(__doc__)

    # Get config file
    config_file = args["--config"]
    # get branch
    branch = args["--branch"]
    # get start and end dates
    start_date = args["--start-date"]
    end_date = args["--end-date"]
    # get email address if provided
    email_address = args.get("--email-address")
    # get sha_id if provided
    sha_id = args.get("--sha-id")

    # Call main function
    main(config_file, start_date, end_date, branch, email_address, sha_id)
