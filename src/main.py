import logging
from pathlib import Path

from core.logger_config import setup_logging
from core.json_data import JsonData
from app.controller import AppController

logger = logging.getLogger(__name__)

PATH_TO_CONFIG = Path(r"\\ggroup.local\valley\veshare\Users\SGordon\SlateVision\SlateVision Utility v2.0\app_config.json")

def main():
    app_config = JsonData(PATH_TO_CONFIG)

    logs_path = app_config.get("path","logs")
    setup_logging(logs_path, False)

    controller = AppController(app_config)
    controller.run()

if __name__ == "__main__":
    main()