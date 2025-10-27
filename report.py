"""
Generate and send Teuthology report via email.

Usage:
    report.py --config=<cfg-file> \
              --branch=<branch> \
              --date=<date> \
              --email-address=<email>

Options:
    --config=<cfg-file>        Path to the configuration file.
    --branch=<branch>          Branch name (e.g., quincy, reef, main).
    --date=<date>              Report date (YYYY-MM-DD).
    --email-address=<email>    Email address to send the report to.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from docopt import docopt
from jinja2 import Template

from api.opensearch import connect
from api.utils import get_email_config

EMAIL_SUBJECT_FORMAT = "Teuthology Test Summary - {date} - {branch}"
LOG = logging.getLogger("teuthology-metrics")


def fetch_data(client, branch, report_date, index):
    """Fetch data for a specific branch on a given date.
     Args:
        client: OpenSearch client instance.
        branch: Branch name (e.g., quincy, reef, main).
        report_date: Date string in YYYY-MM-DD format.
        index: OpenSearch index name.
    Returns:
        List of hits from OpenSearch.
    """
    LOG.debug(f"Fetching data for branch: {branch} on date: {report_date}")
    query = {
        "query": {
            "bool": {
                "must": [
                    {"wildcard": {"posted.keyword": f"{report_date}*"}},
                    {"term": {"branch.keyword": branch}},
                ]
            }
        }
    }
    response = client.search(index=index, body=query, size=1000)
    return response["hits"]["hits"]


def render_teuthology_report(hits, branch, results_server):
    """Render the HTML report using Jinja2 template.
    Args:
        hits: List of hits from OpenSearch.
        branch: Branch name (e.g., quincy, reef, main).
        results_server: Base URL for the results server.
    Returns:
        Rendered HTML string."""
    LOG.debug(f"Rendering HTML report for branch: {branch}")
    if not hits:
        LOG.warning(f"No data available for branch: {branch}")
        return f"<p>No data available for branch: {branch}</p>"

    cloud_platform = "OpenStack"

    # Prepare the data
    data = [
        {
            "suite": hit["_source"].get("suite", "N/A"),
            "href": f"{results_server}/{hit['_id']}",
            "total": hit["_source"].get("results", {}).get("total", 0),
            "passed": hit["_source"].get("results", {}).get("pass", 0),
            "failed": hit["_source"].get("results", {}).get("fail", 0),
            "dead": hit["_source"].get("results", {}).get("dead", 0),
            "waiting": hit["_source"].get("results", {}).get("waiting", 0),
            "queued": hit["_source"].get("results", {}).get("queued", 0),
        }
        for hit in hits
    ]

    # Load the HTML template and render it with data
    with open("templates/report.j2") as f:
        html_template = Template(f.read())

    return html_template.render(
        branch=branch.capitalize(), cloud_platform=cloud_platform, data=data
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


def main(config_file, report_date, branch, email_address):
    # Load configurations
    email_config = get_email_config(config_file)
    # Set up OpenSearch client
    client = connect(config_file)
    LOG.debug("OpenSearch client connected")

    # Fetch data for the given branch and date
    hits = fetch_data(
        client, branch, report_date, email_config["opensearch_index"]
    )

    # Render the HTML report
    html_content = render_teuthology_report(
        hits, branch, email_config["results_server"]
    )

    subject = EMAIL_SUBJECT_FORMAT.format(date=report_date, branch=branch)

    # Send the email with the report
    send_email(email_config, subject, html_content, email_address)


if __name__ == "__main__":
    # Parse command line arguments
    args = docopt(__doc__)

    # Get config file
    config_file = args["--config"]
    # get branch
    branch = args["--branch"]
    # get report date
    report_date = args["--date"]
    # get email address if provided
    email_address = args.get("--email-address")

    # Call main function
    main(config_file, report_date, branch, email_address)
