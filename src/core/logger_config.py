import logging
from logging.handlers import RotatingFileHandler

from datetime import datetime
from pathlib import Path
import re

TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")

def remove_extra_logs(logs_path: Path | str, keep_runs: int=5):
    logs_path = Path(logs_path)

    timestamps = set()

    for file in logs_path.glob("*.log*"):
        # get list of timestamps
        match = TIMESTAMP_PATTERN.search(file.name)
        if match:
            timestamps.add(match.group(0))

    # sort timestamps and keep first n=keep_runs
    timestamps = sorted(
        timestamps,
        key=lambda ts: datetime.strptime(ts, "%Y-%m-%d_%H-%M-%S"),
        reverse=True)
    keep_timestamps = set(timestamps[:keep_runs])

    # delete files of non-kept timestamps
    for file in logs_path.glob("*.log*"):
        match = TIMESTAMP_PATTERN.search(file.name)
        if match and match.group(0) not in keep_timestamps:
            file.unlink()

def setup_logging(logs_path: Path | str, log_to_console: bool):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    logs_path = Path(logs_path)

    logs_path.mkdir(parents=True,exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.handlers:
        return
    
    formatter = logging.Formatter("%(asctime)s - %(module)s - %(levelname)s - %(message)s")

    app_handler = RotatingFileHandler(
        logs_path / f"application_{timestamp}.log",
        encoding="utf-8",
        maxBytes=5_000_000,
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    debug_handler = RotatingFileHandler(
        logs_path / f"debug_{timestamp}.log",
        encoding="utf-8",
        maxBytes=5_000_000,
        backupCount=5
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        logs_path / f"error_{timestamp}.log",
        encoding="utf-8",
        maxBytes=5_000_000,
        backupCount=5
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

    root_logger.addHandler(app_handler)
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(error_handler)

    if log_to_console and console_handler is not None:
        root_logger.addHandler(console_handler)

    remove_extra_logs(logs_path,keep_runs=5)