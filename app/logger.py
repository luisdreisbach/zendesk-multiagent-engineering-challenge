"""Custom logging utilities & configs."""

import logging
import logging.config


def setup_logger():
    uvicorn_logger = logging.getLogger("uvicorn")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(levelname).4s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "default",
                }
            },
            "loggers": {
                logger_name: {
                    "handlers": ["console"],
                    "level": uvicorn_logger.level,
                    "propagate": False,
                }
                for logger_name in ("app", "uvicorn", "uvicorn.logger")
            },
            "root": {
                "handlers": ["console"],
                "level": uvicorn_logger.level,
            },
        }
    )
    filter_technical_logs()


def filter_technical_logs():
    """Filter out access logs to /health and /metrics endpoints."""

    class EndpointFilter(logging.Filter):
        """Filter all 'GET /health' and 'GET /metrics' logs from uvicorn output."""

        def filter(self, record: logging.LogRecord) -> bool:
            log_message = record.getMessage()
            return "GET /health" not in log_message and "GET /metrics" not in log_message

    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
