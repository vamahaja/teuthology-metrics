import logging

LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(module)s:%(lineno)d - %(levelname)s - "
    + "%(message)s"
)


class Logger(logging.Logger):
    """teuthology metrics logger object to help streamline logging."""

    def __init__(self, name=None):
        """
        Initializes the logging mechanism.
        Args:
            name (str): Logger name (module name or other identifier).
        """
        super().__init__(name)
        logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
        self._logger = logging.getLogger("teuthology-metrics")

        # Set logger name
        if name:
            self.name = f"teuthology.{name}"

        # Additional attributes
        self._log_level = self.getEffectiveLevel()
        self._log_dir = None
        self.log_format = LOG_FORMAT
        self._log_errors = []
        self.info = self._logger.info
        self.debug = self._logger.debug
        self.warning = self._logger.warning
        self.error = self._logger.error
        self.exception = self._logger.exception

    @property
    def log_dir(self):
        """Return the absolute path to the logging folder."""
        return self._log_dir

    @property
    def log_level(self):
        """Return the logging level."""
        return self._log_level

    @property
    def logger(self):
        """Return the logger."""
        return self._logger
