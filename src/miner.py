import logging

from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

from .config import get_snapshot_file

log = logging.getLogger("teuthology-metrics")


def get_template_miner(config):
    """Get Drain3 template miner instance"""
    file_path = get_snapshot_file(config)
    log.debug(f"Reading drain3 snapshot file from {file_path}")

    # Create persistence handler
    persistence_handler = FilePersistence(file_path=file_path)

    # Get template miner config
    template_miner = TemplateMiner(
        config=get_miner_config(), persistence_handler=persistence_handler
    )

    log.debug(
        f"Restored drain3 templates: {len(template_miner.drain.clusters)}"
    )

    return template_miner


def get_miner_config():
    """Creates and returns a drain3 configuration object."""
    # Initialize the configuration for the TemplateMiner
    config = TemplateMinerConfig()

    # The similarity threshold for grouping log messages.
    config.drain_sim_th = 0.8

    # The depth of the parsing tree.
    config.drain_depth = 4

    # Set snaopshot compression state to False.
    config.snapshot_compress_state = False

    # Masking is crucial for identifying dynamic variables within log messages.
    config.masking_instructions = [
        # Mask timestamps
        MaskingInstruction(
            pattern=r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{4}",
            mask_with="TIMESTAMP",
        ),
        # Mask smithi nodes
        MaskingInstruction(pattern=r"smithi\d+", mask_with="SMITHI*"),
        # Mask mon services
        MaskingInstruction(pattern=r"mon\.[A-Za-z0-9]+", mask_with="MON*"),
        # Mask osd services
        MaskingInstruction(pattern=r"osd\.[A-Za-z0-9]+", mask_with="OSD*"),
        # Mask osd service count
        MaskingInstruction(pattern=r"\d{1,} OSD\(s\)", mask_with="OSD_COUNT"),
        # Mask PG service count
        MaskingInstruction(pattern=r"\d{1,} (pg|PG)", mask_with="PG_COUNT"),
        # Mask mon service count
        MaskingInstruction(pattern=r"\d+\/\d+ mon", mask_with="MON_COUNT"),
        # Mask Pid number
        MaskingInstruction(pattern=r"pid=(\d+)", mask_with="PID_NUMBER"),
        # Mask retry count
        MaskingInstruction(pattern=r"tries \(\d+\)", mask_with="RETRY_COUNT"),
        # Mask ceph image references
        MaskingInstruction(pattern=r"--fsid \S+", mask_with="CLUSTER_FSID"),
        # Mask seconds count
        MaskingInstruction(
            pattern=r"\d+ sec*|\d+s", mask_with="SECONDS_COUNT"
        ),
        # Mask process count
        MaskingInstruction(
            pattern=r"process (\d+)", mask_with="PROCESS_COUNT"
        ),
        # Mask file system count
        MaskingInstruction(
            pattern=r"\d+.*filesystem", mask_with="FILESYSTEM_COUNT"
        ),
        # Mask ceph image references
        MaskingInstruction(
            pattern=r"ceph:\w+", mask_with="CEPH_IMAGE_REFERENCE"
        ),
        # Mask commit references
        MaskingInstruction(
            pattern=r"CEPH_REF=\w+", mask_with="CEPH_REFERENCE"
        ),
        # Mask audit references
        MaskingInstruction(
            pattern=r"audit\(\S+\)", mask_with="AUDIT_REFERENCE"
        ),
        # Mask centos stream references
        MaskingInstruction(
            pattern=r"centos.*(\d).*stream", mask_with="CENTOS_STREAM_VERSION"
        ),
        # Mask ubuntu references
        MaskingInstruction(
            pattern=r"ubuntu.(\d+).(\d+)", mask_with="UBUNTU_VERSION"
        ),
        # Mask ceph version
        MaskingInstruction(
            pattern=r"(\d+).(\d+).(\d+)-(\d+).(\S+)", mask_with="CEPH_VERSION"
        ),
        # Mask osd & host down counts
        MaskingInstruction(
            pattern=r"\d{1,} host \(\d{1,} osds\)",
            mask_with="OSD_HOST_DOWN_COUNT",
        ),
        # Mask cluster addresses
        MaskingInstruction(
            pattern=r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,}\/\d{1,}",
            mask_with="CLUSTER_ADDRESS",
        ),
    ]

    return config
