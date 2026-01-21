"""
Generate and send teuthology report via email.

Usage:
    report.py --config <cfg-file> 
              --branch <branch> 
              --start-date <start-date> 
              --end-date <end-date> 
              --email-address <email> 
              --sha-id <sha-id>
              [--log-level <LOG>]
              [--log-path <LOG_PATH>]

Options:
    --config <cfg-file>           Path to the configuration file.
    --branch <branch>             Branch name (e.g., quincy, reef, main).
    --start-date <start-date>     Report start date (YYYY-MM-DD).
    --end-date <end-date>         Report end date (YYYY-MM-DD).
    --email-address <email>       Email address to send the report to (or
                                  comma-separated list of emails).
    --sha-id <sha-id>             SHA ID to filter results.
    --log-level <LOG>             Log level for log utility
    --log-path <LOG_PATH>         Log file path for log utility
"""

from docopt import docopt

from src.processer import publish_report
from src.utils import set_logging_env


def main(args):
    # Set logging environment
    set_logging_env(args["--log-level"],  args["--log-path"])

    # Get config file
    config_file = args["--config"]

    # get branch
    branch = args["--branch"]

    # get start and end dates
    start_date = args["--start-date"]
    end_date = args["--end-date"]

    # get email address if provided
    address = args.get("--email-address")

    # get sha_id if provided
    sha_id = args.get("--sha-id")

    # Call main function
    publish_report(
        config_file, start_date, end_date, branch, address, sha_id
    )


if __name__ == "__main__":
    # Get docopt and process
    main(docopt(__doc__))
