import logging
import signal
import sys
from datetime import datetime, timedelta, timezone

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from api.utils import set_logging_env
from report import main as report_main
from run import main as run_main

# Set scheduler configs
CONFIG_FILE = "/usr/share/scheduler/config.cfg"
CRON_PATH = "/usr/share/scheduler/cron"
SKIP_DRAIN3_TEMPLATES = False
USER = "teuthology"
TIMEZONE = "UTC"
MISFIRE_GRACE_SECONDS = 3600
MAX_INSTANCES = 1
SUITES = [
    "smoke",
    "fs",
    "rados",
    "rbd",
    "krbd",
    "orch",
    "rgw",
    "crimson-rados",
    "powercycle",
]
log_level = "DEBUG"
log_path = "/var/log/"

LOG = logging.getLogger("teuthology-metrics")


def run_task():
    """Run teuthology testrun process"""
    # Set up logging environment for this run
    set_logging_env(level=log_level, path=log_path)

    # Get current date
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Execute run method
    try:
        for suite in SUITES:
            LOG.debug(f"[JOB START] suite={suite} | date={now}")

            # Set paddle variables
            segments = ["suite", suite, "user", USER, "date", now]

            # Run teuthology testrun process
            run_main(
                config_file=CONFIG_FILE,
                skip_drain3_templates=SKIP_DRAIN3_TEMPLATES,
                segments=segments,
            )
    except Exception as exc:
        LOG.error(f"[JOB ERROR] {exc}")
    finally:
        LOG.debug("[JOB END]")


def run_report():
    """Run teuthology report process"""
    # Set up logging environment for this run
    set_logging_env(level=log_level, path=log_path)

    # Get current date (Monday)
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")

    # Calculate date ranage
    schedule_date = now - timedelta(days=3)
    start_date = schedule_date.strftime("%Y-%m-%d")
    sha_id = open(f"{CRON_PATH}/{start_date}").read().strip()
    # Execute report method
    try:
        for branch in ["master", "squid", "tentacle"]:
            LOG.debug(
                f"[REPORT JOB START] branch={branch} | "
                f"start_date={start_date} | end_date={end_date}"
            )

            # Run teuthology report process with date range
            report_main(
                config_file=CONFIG_FILE,
                start_date=start_date,
                end_date=end_date,
                branch=branch,
                sha_id=sha_id,
                email_address=None,
            )
    except Exception as exc:
        LOG.error(f"[REPORT JOB ERROR] {exc}")
    finally:
        LOG.debug("[REPORT JOB END]")


def start_task_scheduler(tz):
    """Start task scheduler"""
    # Scheduler
    scheduler = BackgroundScheduler(timezone=tz)

    # Trigger : Every 4 hours
    trigger = CronTrigger(minute=0, hour="*/4")

    # Add job for suites
    scheduler.add_job(
        run_task,
        trigger=trigger,
        replace_existing=True,
        coalesce=True,
        max_instances=MAX_INSTANCES,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )

    # Start scheduler
    scheduler.start()
    LOG.debug(f"Task Scheduler started for TZ={TIMEZONE}")

    return scheduler


def start_report_scheduler(tz):
    """Start report scheduler"""
    # Scheduler
    scheduler = BackgroundScheduler(timezone=tz)

    # Trigger: Every Monday at 6 PM IST (12:30 UTC)
    trigger = CronTrigger(day_of_week="mon", hour=12, minute=30)

    # Add job for report
    scheduler.add_job(
        run_report,
        trigger=trigger,
        replace_existing=True,
        coalesce=True,
        max_instances=MAX_INSTANCES,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )

    # Start scheduler
    scheduler.start()
    LOG.debug(f"Report Scheduler started for TZ={TIMEZONE}")

    return scheduler


def create_shutdown_handler(task_scheduler, report_scheduler):
    """Create shutdown handler"""

    def shutdown(signum, frame):
        LOG.debug(f"Received signal {signum}. Shutting down schedulers...")
        try:
            task_scheduler.shutdown(wait=True)
            report_scheduler.shutdown(wait=True)
        except Exception as exc:
            LOG.error(f"Error during scheduler shutdown: {exc}")
        finally:
            sys.exit(0)

    return shutdown


def main():
    # Set up logging environment
    set_logging_env(level=log_level, path=log_path)

    # Time zone
    tz = pytz.timezone(TIMEZONE)

    # Start both schedulers
    task_scheduler = start_task_scheduler(tz)
    report_scheduler = start_report_scheduler(tz)

    # Log the scheduler start
    LOG.debug(f"Schedulers started for TZ={TIMEZONE}")

    # Create shutdown handler for graceful termination
    shutdown_handler = create_shutdown_handler(
        task_scheduler, report_scheduler
    )
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Keep the process alive
    signal.pause()


if __name__ == "__main__":
    main()
