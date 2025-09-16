"""
Generate and send Teuthology report via email.

Usage:
    report.py --config=<cfg-file> --branch=<branch> --date=<date>

Options:
    --config=<cfg-file>        Path to the configuration file.
    --branch=<branch>          Branch name (e.g., quincy, reef, main).
    --date=<date>              Report date (YYYY-MM-DD).
"""

import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from docopt import docopt
from jinja2 import Template
from opensearchpy import OpenSearch

from api.utils import get_config


# --- CONFIGURATION ---
def load_config(config_file):
    opensearch_config = get_config(config_file, "opensearch")
    email_config = get_config(config_file, "email")

    return {"opensearch": opensearch_config, "email": email_config}


# --- CONNECT TO OPENSEARCH ---
def setup_opensearch(config):
    opensearch_config = config["opensearch"]
    return OpenSearch(
        hosts=[
            {
                "host": opensearch_config["host"],
                "port": opensearch_config["port"],
            }
        ],
        http_auth=(
            opensearch_config["username"],
            opensearch_config["password"],
        ),
        use_ssl=False,
        verify_certs=False,
    )


# --- FETCH DATA ---
def fetch_data(client, branch: str, report_date: str, index: str):
    """Fetch data for a specific branch on a given date."""
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


# --- RENDER HTML REPORT ---
def render_teuthology_report(hits, branch: str):
    if not hits:
        return f"<p>No data available for branch: {branch}</p>"

    cloud_platform = "OpenStack"

    # Prepare the data
    data = [
        {
            "suite": hit["_source"].get("suite", "N/A"),
            "href": f"http://pulpito-ng.ceph.com/{hit['_id']}",
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
    with open("templates/report_template.html") as f:
        html_template = Template(f.read())

    return html_template.render(
        branch=branch.capitalize(), cloud_platform=cloud_platform, data=data
    )


# --- SEND EMAIL ---
def send_email(config, subject, html_body):
    email_config = config["email"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_config["email_from"]
    msg["To"] = email_config["email_to"]

    mime_text = MIMEText(html_body, "html")
    msg.attach(mime_text)

    with smtplib.SMTP(email_config["host"], email_config["port"]) as server:
        server.starttls()
        server.sendmail(
            email_config["email_from"],
            [email_config["email_to"]],
            msg.as_string(),
        )
        print(f"Report sent to {email_config['email_to']}")


def main(config_file, report_date, branch):
    # Load config
    config = load_config(config_file)

    # Set up OpenSearch client
    client = setup_opensearch(config)

    # Fetch data for the given branch and date
    hits = fetch_data(
        client, branch, report_date, config["opensearch"]["index"]
    )

    # Render the HTML report
    html_content = render_teuthology_report(hits, branch)

    # Send the email with the report
    send_email(
        config,
        f"Teuthology Test Summary - {report_date} - {branch}",
        html_content,
    )


if __name__ == "__main__":
    # Parse command line arguments
    args = docopt(__doc__)

    # Get config file
    config_file = args["--config"]
    # get branch
    branch = args["--branch"]
    # get report date
    report_date = args["--date"]

    # Call main function
    main(config_file, report_date, branch)
