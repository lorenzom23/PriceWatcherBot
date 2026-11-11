import logging


logger = logging.getLogger("pricewatcherbot")


def configure_logging(application_level: str, basic_level: str) -> None:
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    if application_level not in levels:
        raise ValueError(
            f"Invalid application_log_level {application_level!r}; "
            f"choose from {', '.join(levels)}"
        )
    if basic_level not in levels:
        raise ValueError(
            f"Invalid basic_log_level {basic_level!r}; "
            f"choose from {', '.join(levels)}"
        )

    logging.basicConfig(
        level=levels[basic_level],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(levels[basic_level])
    logger.setLevel(levels[application_level])
