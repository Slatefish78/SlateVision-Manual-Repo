#region Model Project
import json
import logging
from pathlib import Path

from core.json_data import JsonData

logger = logging.getLogger(__name__)

class SVProject():
    """
    Base class for a SlateVision Project.
    
    Args:
        config_file_path: path to .json config file which holds the data for this project.

    Methods:
        export_dict(): return project data in dictionary form (for json export).
        save_config(): export project data as .json file.
        """

    def __init__(self,config_file_path: Path):
        self.project_config = JsonData(config_file_path)
        self.project_folder_path = config_file_path.parent

        # Project attributes
        self.project_name = self.project_config.get("project","name")
        self.project_type = self.project_config.get("project","type")

        # variables for close project warnings
        self.exported = True
        self.edited = False

    def __repr__(self):
        return f"{self.__class__.__name__}(project_name={self.project_name})"
    
    def __str__(self):
        return repr(self)

    def export_dict(self):
        export_dict = {
            "project": {
                "name": self.project_name,
                "type": self.project_type
            }
        }
        return export_dict
    
    def save_config(self,path: Path,filename):
        settings = self.export_dict()
        file_path = path / f"{filename}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)