import logging
import signal
import sys
from datetime import datetime, timezone

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from api.utils import set_logging_env
from run import main as run_main

# Set scheduler configs
CONFIG_FILE = "/usr/share/scheduler/config.cfg"
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
    # Get current date
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Set up logging environment
    LOG = set_logging_env(level=log_level, path=log_path)

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


def create_shutdown_handler(scheduler):
    """Create shutdown handler"""

    def shutdown(signum, frame):
        LOG.debug(f"Received signal {signum}. Shutting down scheduler...")
        try:
            scheduler.shutdown(wait=True)
        except Exception:
            LOG.error("Error during scheduler shutdown")
        finally:
            sys.exit(0)

    return shutdown


def main():
    # Time zone
    tz = pytz.timezone(TIMEZONE)

    # Scheduler
    scheduler = BackgroundScheduler(timezone=tz)

    # Trigger
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
    LOG.debug(f"Scheduler started for TZ={TIMEZONE}")

    # Exit code
    shutdown_handler = create_shutdown_handler(scheduler)
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Keep the process alive
    signal.pause()


if __name__ == "__main__":
    main()
