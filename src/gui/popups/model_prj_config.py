import logging

from PySide6.QtWidgets import QLabel, QLineEdit, QFormLayout
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class ModelPrjConfigPopup(SVPopup):
    #region Init
    def __init__(self, parent=None, controller=None):
        super().__init__("Edit Project Config",parent,controller)

        self.controller.selected_project.edited = True

        form = QFormLayout()
        form.setContentsMargins(9,0,9,9)
        form.setSpacing(10)

        # project name field
        self.name_input = QLineEdit()
        self.name_input.setToolTip("Name of the Model Project. Used for display.")
        form.addRow("Project Name:",self.name_input)

        # project type display
        self.type_display = QLabel("model")
        self.type_display.setToolTip("Type of the Model Project (detect, classify, etc).")
        form.addRow("Project Type: ",self.type_display)

        self.content_layout.addLayout(form)

        # buttons
        self.content_layout.addWidget(self.done_btn)
        self.content_layout.addWidget(self.cancel_btn)

    #region Load/Save Data
    def load_from_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        logger.debug(f"Loaded project config data to edit: (project_name={prj.project_name})")
        
        self.name_input.setText(prj.project_name)
        self.type_display.setText(prj.project_type)

    def save_to_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        prj.project_name = self.name_input.text().strip()

        self.controller.root.screens["model"].update_header(f"Model Project - {self.controller.selected_project.project_name}")

        logger.debug(f"Saved edited project config data: (project_name={prj.project_name})")