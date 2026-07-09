import logging
import shutil

from PySide6.QtWidgets import QPushButton, QLabel, QSizePolicy, QMessageBox, QInputDialog, QLineEdit, QGridLayout, QWidget
from PySide6 .QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from gui.popups.open_recents import OpenRecentPopup
from gui.popups.selection_list import SelectionListPopup
from gui.screens.screen import Screen

logger = logging.getLogger(__name__)

class MenuScreen(Screen):
    #region Init
    def __init__(self,parent=None,controller=None):
        super().__init__("SlateVision Utility",parent,controller)

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(self.controller.widget_spacing)
        grid_layout.setContentsMargins(0,0,0,0)
        self.content_layout.addWidget(grid_widget)

        # buttons
        num_columns = 3
        buttons_def = [
            ("Model Project", "model.png", self.on_btn_open_model_prj),
            ("Vision Project", "vision.png", self.on_btn_open_vision_prj),
            ("Project Runner", "run.png", self.on_btn_run_vision_prj),
            ("App Info", "info.png", self.on_btn_info),
            ("Change Theme", "theme.png", self.on_btn_change_theme),
            ("Quit/Exit", "quit.png", self.on_btn_quit)
        ]

        for i, (text, icon_name, callback) in enumerate(buttons_def):
            row = i // num_columns
            col = i % num_columns

            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

            btn.setProperty("role","default")

            icon_path = self.controller.assets_path / "icons" / icon_name
            btn.setIcon(QIcon(str(icon_path)))
            btn.setIconSize(QSize(128,128))

            btn.clicked.connect(callback)
            grid_layout.addWidget(btn,row,col)

        self.content_layout.addStretch()

        info_lbl = QLabel("SlateVision Utility v2.0 Developed by Sam Gordon, May 2026. AI Assistance - ChatGPT, troubleshooting/learning tool. Any AI generated code copied manually to facilitate personal understanding.\nThis project utilizes code from [Ultralytics YOLO](https://github.com/ultralytics/ultralytics), licensed under AGPL-3.0.")
        info_lbl.setAlignment(Qt.AlignCenter)
        info_lbl.setProperty("role","info")
        self.content_layout.addWidget(info_lbl)

    #region Button Handlers





    #region New Model Project
    def on_btn_new_model_prj(self):
        logger.debug(f"Button Press - New Model Project.")
        # get name of new project
        name_entry, ok = QInputDialog.getText(
            self,
            "New Model Project",
            "Enter project name:",
            QLineEdit.Normal,
            ""
        )

        if not ok or not name_entry.strip():
            return

        # open template as new project
        template_path = self.controller.assets_path / "model_project_template/project_config.json"
        self.controller.open_project(template_path, "model")

        self.controller.selected_project.exported = False
        self.controller.selected_project.edited = True
        self.controller.selected_project.project_name = name_entry.strip()

        # update model project screen
        self.controller.root.screens["model"].update_classes()
        self.controller.root.screens["model"].update_files()
        self.controller.root.screens["model"].cam_prev.frame = None
        self.controller.root.screens["model"].cam_prev.qimage = None
        self.controller.root.screens["model"].update_header(f"Model Project - {self.controller.selected_project.project_name}")

        # show model project screen
        self.controller.root.show_screen("model")

    #region Open Model Project
    def on_btn_open_model_prj(self):
        logger.debug(f"Button Press - Open Model Project.")
        # show recent projects popup (get path)
        file_path = OpenRecentPopup.get_path(
            title="Select Model Project",
            filetypes="SlateVision Model Project (*.svp);;Project Config File (*.json);;All Files (*)",
            header="Recent Model Projects",
            paths=self.controller.recent_model_projects,
            parent=self,
            controller=self.controller
        )

        if file_path is None:
            return
        
        # new project
        if file_path == "":
            self.on_btn_new_model_prj()
            return
        
        # open project
        
        self.controller.open_project(file_path, "model")

        # update recent path list
        self.controller.update_path_list(self.controller.selected_project.project_name,file_path,self.controller.recent_model_projects)

        # update model project screen
        self.controller.root.screens["model"].update_classes()
        self.controller.root.screens["model"].update_files()
        self.controller.root.screens["model"].cam_prev.frame = None
        self.controller.root.screens["model"].cam_prev.qimage = None
        self.controller.root.screens["model"].update_header(f"Model Project - {self.controller.selected_project.project_name}")
        
        self.controller.root.show_screen("model")

    #region New Vision Project
    def on_btn_new_vision_prj(self):
        logger.debug(f"Button Press - New Vision Project.")
        # get name of new project
        name_entry, ok = QInputDialog.getText(
            self,
            "New Vision Project",
            "Enter project name:",
            QLineEdit.Normal,
            ""
        )

        if not ok or not name_entry.strip():
            return
        
        # open template as new project
        template_path = self.controller.assets_path / "vision_project_template/project_config.json"
        self.controller.open_project(template_path, "vision")

        self.controller.selected_project.exported = False
        self.controller.selected_project.edited = True
        self.controller.selected_project.project_name = name_entry.strip()

        # update vision project screen
        self.controller.root.screens["vision"].update_header(f"Vision Project - {self.controller.selected_project.project_name}")

        # show vision project screen
        self.controller.root.show_screen("vision")

    #region Open Vision Project
    def on_btn_open_vision_prj(self):
        logger.debug(f"Button Press - Open Vision Project.")
        # show recent projects popup (get path)
        file_path = OpenRecentPopup.get_path(
            title="Select Vision Project",
            filetypes="SlateVision Vision Project (*.svp);;Project Config File (*.json);;All Files (*)",
            header="Recent Vision Projects",
            paths=self.controller.recent_vision_projects,
            parent=self,
            controller=self.controller
        )

        if file_path is None:
            return
        
        # new project
        if file_path == "":
            self.on_btn_new_vision_prj()
            return

        # open project
        self.controller.open_project(file_path, "vision")

        # update recent path list
        self.controller.update_path_list(self.controller.selected_project.project_name,file_path,self.controller.recent_vision_projects)

        # update vision project screen
        self.controller.root.screens["vision"].update_header(f"Vision Project - {self.controller.selected_project.project_name}")
        
        # show vision project screen
        self.controller.root.show_screen("vision")

    #region Run Vision Project
    def on_btn_run_vision_prj(self):
        logger.debug(f"Button Press - Run Vision Project.")
        # get project path
        file_path = OpenRecentPopup.get_path(
            title="Select Vision Project",
            filetypes="SlateVision Vision Project (*.svp);;Project Config File (*.json);;All Files (*)",
            header="Recently Run Vision Projects",
            paths=self.controller.recent_run_projects,
            parent=self,
            controller=self.controller
        )

        if file_path is None:
            return
        
        # new project
        if file_path == "":
            self.on_btn_new_vision_prj()
            return
        
        # open project
        self.controller.open_project(file_path, "vision")

        # update recent path list
        self.controller.update_path_list(self.controller.selected_project.project_name,file_path,self.controller.recent_run_projects)

        # update run screen
        self.controller.root.screens["run"].update_header(f"Running Vision Project - {self.controller.selected_project.project_name}")
        self.controller.root.screens["run"].update_cam_grid(len(self.controller.selected_project.cameras))

        # start project operation
        self.controller.selected_project.start_operation()

        # show run screen
        self.controller.root.show_screen("run")

    #region Info
    def on_btn_info(self):
        logger.debug(f"Button Press - View App Info.")
        self.controller.root.show_screen("info")

    #region Change Theme
    def on_btn_change_theme(self):
        logger.debug(f"Button Press - Change Theme.")
        # get list of qss themes
        theme_list = []
        for item in self.controller.themes_path.iterdir():
            if item.is_file() and item.suffix.lower() == ".qss" and item.stem != "current_theme":
                theme_list.append((item.stem,item))

        # open popup
        selected_theme_path = SelectionListPopup.get_selection(self,self.controller,"Select Theme",theme_list)

        # copy selected theme to current theme (overwrites)
        if selected_theme_path is None:
            return
        
        if not selected_theme_path.exists():
            print("error: selected theme doesn't exist.")
            return

        current_theme_path = self.controller.themes_path / "current_theme.qss"

        shutil.copy(selected_theme_path,current_theme_path)

        # load new theme
        self.controller.load_theme()

    #region Quit
    def on_btn_quit(self):
        logger.debug(f"Button Press - Quit application.")
        quit_confirmation = QMessageBox.question(
            self,
            "Exit SlateVision Utility",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )

        if quit_confirmation == QMessageBox.Yes:
            self.controller.shutdown()