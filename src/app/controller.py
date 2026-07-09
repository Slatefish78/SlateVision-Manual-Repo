import logging
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from core.json_data import JsonData
from core.model_project import DetectProject
from gui.root import GuiRoot
from core.vision_project import VisionProject

logger = logging.getLogger(__name__)

#region Base Controller
class AppController():
    def __init__(self,config):
        # @@@ obtain app configuration
        self.config = config

        # @@@ read values from app config
        # - application properties
        self.fullscreen = self.config.get("app", "fullscreen")
        self.default_width = self.config.get("app", "default_width")
        self.default_height = self.config.get("app", "default_height")
        self.x_margin = 100
        self.y_margin = 50
        self.widget_spacing = 20

        # - application folder structure paths
        self.assets_path = Path(self.config.get("path","assets"))
        self.logs_path = Path(self.config.get("path","logs"))
        self.models_path = Path(self.config.get("path","models"))
        self.projects_path = Path(self.config.get("path","projects"))
        self.themes_path = Path(self.config.get("path","themes"))
        
        # - project edit limits
        self.max_recent_projects = self.config.get("limits","max_recent_projects")
        self.max_cameras_per_project = self.config.get("limits","max_cameras_per_project")
        self.max_tools_per_project = self.config.get("limits","max_tools_per_project")
        self.max_params_per_project = self.config.get("limits","max_params_per_project")
        self.max_tools_per_camera = self.config.get("limits","max_tools_per_camera")

        # - paths
        self.recent_paths = JsonData(self.assets_path / "recent_file_paths.json")
        self.recent_model_projects = self.recent_paths.get("recent_model_prj")
        self.recent_vision_projects = self.recent_paths.get("recent_vision_prj")
        self.recent_run_projects = self.recent_paths.get("recent_run_prj")

        self.autorun_project = self.recent_paths.get("autorun_prj")

        # @@@ current project state
        self.temp_project_dir = None
        self.project_file_path = None
        self.selected_project = None

        # @@@ gui setup
        self.app = QApplication(sys.argv)
        self.load_theme()
        self.root = GuiRoot(self)
        self.app.aboutToQuit.connect(self.on_shutdown)

        logger.debug(f"Created {self}.")

    def __repr__(self):
        return self.__class__.__name__

    #region Project Methods
    def run(self):
        logger.info("Running application.")

        if self.fullscreen:
            self.root.showMaximized()
        else: self.root.show()

        # show license disclosure
        if self.autorun_project is None:
            QMessageBox.information(
                self.root,
                "License Disclosure",
                "SlateVision Utility utilizes code from [Ultralytics YOLO](https://github.com/ultralytics/ultralytics), licensed under AGPL-3.0."
            )

        # autorun project on startup
        else:
            logger.info(f"Autostarting project: {self.autorun_project}")
            
            self.open_project(self.autorun_project, "vision")

            # update recent path list
            self.update_path_list(self.selected_project.project_name,self.project_file_path,self.recent_run_projects)

            # update run screen
            self.root.screens["run"].update_header(f"Running Vision Project - {self.selected_project.project_name}")
            self.root.screens["run"].update_cam_grid(len(self.selected_project.cameras))

            # start project operation
            self.selected_project.start_operation()

            # show run screen
            self.root.show_screen("run")

        sys.exit(self.app.exec())

    def shutdown(self):
        logger.info("Closing application.")
        self.app.quit()

    def load_theme(self):
        if self.app is None:
            return
        
        self.theme_path = self.themes_path / "current_theme.qss"
        with open(self.theme_path, "r", encoding="utf-8") as f:
            app_stylesheet = f.read()

        self.app.setStyleSheet(app_stylesheet)    

    #region Save Recent Paths
    def save_paths(self):
        self.recent_paths.set("recent_model_prj",value=self.recent_model_projects)
        self.recent_paths.set("recent_vision_prj",value=self.recent_vision_projects)
        self.recent_paths.set("recent_run_prj",value=self.recent_run_projects)
        self.recent_paths.set("autorun_prj",value=self.autorun_project)
        self.recent_paths.save()

    #region Update Path List
    def update_path_list(self,project_name,file_path,list_to_update):
        """Add or move project to top of recent list, avoiding duplicates"""
        file_path = str(Path(file_path).resolve().as_posix())

        # remove entry with matching path
        list_to_update[:] = [p for p in list_to_update if str(Path(p["path"]).resolve().as_posix()) != file_path]

        # insert at top
        if project_name and Path(file_path).exists():
            list_to_update.insert(0,{"name": project_name, "path": file_path, "pinned":False})

        # keep only up to max limit
        pinned = [p for p in list_to_update if p.get("pinned",False)]
        recent = [p for p in list_to_update if not p.get("pinned",False)]
        recent = recent[:self.max_recent_projects]
        list_to_update[:] = pinned + recent

    #region On Shutdown
    def on_shutdown(self):
        self.save_paths()
        self.close_project()

    #region Close Project
    def close_project(self):
        logger.info(f"Closing project.")
        if not self.temp_project_dir:
            logger.info(f"No project to close.")
            return

        if self.temp_project_dir.exists():
            shutil.rmtree(self.temp_project_dir, ignore_errors=True)
            
        self.temp_project_dir = None
        self.project_file_path = None
        self.selected_project = None

        logger.info(f"Project closed.")

    #region Save Project
    def save_project(self, save_path=None):
        logger.info(f"Saving project.")
        if not save_path:
            save_path = self.project_file_path

        save_path = Path(save_path)

        if not self.selected_project or not self.temp_project_dir:
            logger.info(f"No project to save.")
            return
        
        # export json config
        self.selected_project.save_config(self.temp_project_dir,"project_config")

        # save project (.svp or .json)
        match save_path.suffix:
            case ".svp":
                # zip temp directory to .svp
                temp_zip_path = save_path.with_suffix(".tmp")

                with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in self.temp_project_dir.rglob("*"):
                        zipf.write(file,file.relative_to(self.temp_project_dir))

                # replace original file
                if save_path.exists():
                    save_path.unlink()
                shutil.move(temp_zip_path, save_path)

            case ".json":
                if save_path.name != "project_config.json":
                    raise RuntimeError("Invalid config file. 'project_config.json' not selected.")

                save_dir = save_path.parent

                # copy files to folder
                for file in self.temp_project_dir.rglob("*"):
                    if file.name.startswith("."):
                        continue

                    if file.is_file():
                        dest_path = save_dir / file.relative_to(self.temp_project_dir)
                        dest_path.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy(file,dest_path)

            case _:
                raise RuntimeError("Invalid project save path")

        # update project flags
        self.selected_project.exported = True
        self.selected_project.edited = False
        self.project_file_path = save_path

        logger.info(f"Saved project: {self.project_file_path}.")

    #region Open Project
    def open_project(self, file_path, project_type: str):
        """Open a project (model or vision) from .svp or .json"""
        self.close_project()

        logger.info(f"Opening {project_type} project: {file_path}")

        # validate type of project to open
        if project_type not in {"model","vision"}:
            raise ValueError("Invalid project type specified")

        # check project exists
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Project not found: {file_path}")
        
        # 
        
        # create temp directory
        self.temp_project_dir = Path(tempfile.mkdtemp(prefix="slatevision_"))

        # 
        match file_path.suffix:
            #open a .svp zipped project
            case ".svp":
                # extract zip
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_project_dir)
            
            # open a non-zipped project (.json)
            case ".json":
                # copy all files to temp
                for file in file_path.parent.rglob("*"):
                    #prevent opening file already in temp folder
                    if file.resolve().is_relative_to(self.temp_project_dir.resolve()):
                        continue

                    if file.is_file():
                        dest_path = self.temp_project_dir / file.relative_to(file_path.parent)
                        dest_path.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy(file,dest_path)

            case _:
                raise RuntimeError("Invalid project filetype")

        # load config
        config_path = self.temp_project_dir / "project_config.json"

        if not config_path.exists():
                raise FileNotFoundError(f"'project_config.json' file not found")
        
        # set project
        self.project_file_path = file_path
        if project_type == "model":
            project_type_value = JsonData(config_path).get("project","type")
            if project_type_value == "detect":
                self.selected_project = DetectProject(config_path)
            else:
                raise ValueError(f"Unsupported Model Project type: {project_type_value}")
        elif project_type == "vision":
            self.selected_project = VisionProject(config_path)

        logger.info(f"Opened project: {self.selected_project.project_name} - {self.selected_project}")