"""
Schedule teuthology ingest and email report

Usage:
    scheduler.py --config <cfg-file>
        --sha1-path <sha1-txt-file>
        --user <user>
        [--skip-drain3-templates]
        [--log-level <LOG>]
        [--log-path <LOG_PATH>]

Options:
    --config <cfg-file>           Path to the configuration file
    --sha1-path <sha1-txt-path>   Path to sha1 text file
    --user <user>                 Filter by user
    --skip-drain3-templates       Skip processing Drain3 templates
    --log-level <LOG>             Log level for log utility
    --log-path <LOG_PATH>         Log file path for log utility
"""

import logging
import signal
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from docopt import docopt

from src.config import get_scheduler_config
from src.utils import set_logging_env
from src.processer import run_report, run_task

# Set scheduler configs
MISFIRE_GRACE_SECONDS = 3600
MAX_INSTANCES = 1

log = logging.getLogger("teuthology-metrics")


def start_task_scheduler(config_file, user, skip_drain3_templates, cron_expr, log_level=None, log_path=None):
    """Start task scheduler"""
    # Scheduler
    scheduler = BackgroundScheduler()

    # Set cron trigger
    trigger = CronTrigger.from_crontab(cron_expr)

    # Add job for suites
    scheduler.add_job(
        run_task,
        args=[config_file, user, skip_drain3_templates, log_level, log_path],
        trigger=trigger,
        max_instances=MAX_INSTANCES,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )

    # Start scheduler
    scheduler.start()
    log.debug("Task Scheduler started ...")

    return scheduler


def start_report_scheduler(config_file, cron_dir, cron_expr, log_level=None, log_path=None):
    """Start report scheduler"""
    # Scheduler
    scheduler = BackgroundScheduler()

    # Set cron trigger
    trigger = CronTrigger.from_crontab(cron_expr)

    # Add job for report
    scheduler.add_job(
        run_report,
        args = [config_file, cron_dir, log_level, log_path],
        trigger=trigger,
        max_instances=MAX_INSTANCES,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )

    # Start scheduler
    scheduler.start()
    log.debug("Report Scheduler started ...")

    return scheduler


def create_shutdown_handler(task_scheduler, report_scheduler):
    """Create shutdown handler"""

    def shutdown(signum, frame):
        log.debug(f"Received signal {signum}. Shutting down schedulers...")
        try:
            task_scheduler.shutdown(wait=True)
            report_scheduler.shutdown(wait=True)
        except Exception as exc:
            log.error(f"Error during scheduler shutdown: {exc}")
        finally:
            sys.exit(0)

    return shutdown


def schedule(config_file, sha1_path, user, skip_drain3_templates, log_level=None, log_path=None):
    """Schedule task and report jobs"""
    # Get scheduler configs
    _config = get_scheduler_config(config_file)

    # Start both schedulers
    task_scheduler = start_task_scheduler(
        config_file, user, skip_drain3_templates, _config["cron_task"], log_level, log_path
    )
    report_scheduler = start_report_scheduler(
        config_file, sha1_path, _config["cron_report"], log_level, log_path
    )

    # Create shutdown handler for graceful termination
    shutdown_handler = create_shutdown_handler(
        task_scheduler, report_scheduler
    )
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Keep the process alive
    signal.pause()


def main(args):
    """Start sheduler"""
    # Get log settings
    log_level = args["--log-level"]
    log_path = args["--log-path"]

    # Set up logging environment for scheduler startup
    set_logging_env(log_level, log_path, job_type="scheduler")

    # Get user configs
    config_file = args["--config"]
    sha1_path = args["--sha1-path"]
    user = args["--user"]
    skip_drain3_templates = args["--skip-drain3-templates"]

    # Schedule jobs
    schedule(config_file, sha1_path, user, skip_drain3_templates, log_level, log_path)


if __name__ == "__main__":
    # Get docopt and process
    main(docopt(__doc__))
