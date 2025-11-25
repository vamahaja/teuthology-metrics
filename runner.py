"""
Ingest teuthology runs data to OpenSearch.

Usage:
    runner.py --config <cfg-file>
        [--user <user>]
        [--branch <branch>]
        [--machine-type <machine_type>]
        [--suite <suite>]
        [--status <status>]
        [--date <date>]
        [--skip-drain3-templates]
        [--log-level <LOG>]
        [--log-path <LOG_PATH>]

Options:
    --config <cfg-file>           Path to the configuration file.
    --user <user>                 Filter by user.
    --branch <branch>             Filter by branch.
    --machine-type <machine_type> Filter by machine_type.
    --suite <suite>               Filter by suite.
    --status <status>             Filter by status.
    --date <date>                 Filter by date (YYYY-MM-DD).
    --skip-drain3-templates       Skip processing Drain3 templates.
    --log-level <LOG>             Log level for log utility
    --log-path <LOG_PATH>         Log file path for log utility
"""

from docopt import docopt
from src.processer import process
from src.utils import set_logging_env


def main(args):
    # Set logging environment
    set_logging_env(args["--log-level"],  args["--log-path"])

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

    # Process teuthology jobs and runs
    process(config_file, skip_drain3_templates, segments)


if __name__ == "__main__":
    # Get docopt and process
    main(docopt(__doc__))
