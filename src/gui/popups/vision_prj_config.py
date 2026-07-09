import logging

from PySide6.QtWidgets import QLineEdit, QFormLayout, QCheckBox, QDoubleSpinBox
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class VisionPrjConfigPopup(SVPopup):
    #region Init
    def __init__(self, parent=None, controller=None):
        super().__init__("Edit Project Config",parent,controller)

        self.controller.selected_project.edited = True

        form = QFormLayout()
        form.setContentsMargins(9,0,9,9)
        form.setSpacing(10)

        # project name field
        self.name_input = QLineEdit()
        self.name_input.setToolTip("Name of the Vision Project. Used for display.")
        form.addRow("Project Name:",self.name_input)

        # loop interval field
        self.loop_interval_input = QDoubleSpinBox()
        self.loop_interval_input.setRange(0,60)
        self.loop_interval_input.setDecimals(2)
        self.loop_interval_input.setSingleStep(0.1)
        self.loop_interval_input.setSuffix(" sec")
        self.loop_interval_input.setToolTip("Minimum time between operation loops. Actual time may be longer due to inference requirements.")
        form.addRow("Loop Interval:",self.loop_interval_input)

        # triggered field
        self.triggered_input = QCheckBox("")
        self.triggered_input.setToolTip("Whether operation is only performed on rising edge of the .trigger PLC tag.")
        form.addRow("Triggered Mode:",self.triggered_input)

        self.content_layout.addLayout(form)

        # buttons
        self.content_layout.addWidget(self.done_btn)
        self.content_layout.addWidget(self.cancel_btn)

    #region Button Handlers
    def load_from_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        logger.debug(f"Loaded project config data to edit: (project_name={prj.project_name},loop_interval={prj.loop_interval},is_triggered={prj.is_triggered})")
        
        self.name_input.setText(prj.project_name)
        self.loop_interval_input.setValue(prj.loop_interval)
        self.triggered_input.setChecked(prj.is_triggered)

    def save_to_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        prj.project_name = self.name_input.text().strip()
        prj.loop_interval = self.loop_interval_input.value()
        prj.is_triggered = self.triggered_input.isChecked()

        self.controller.root.screens["vision"].update_header(f"Vision Project - {self.controller.selected_project.project_name}")

        logger.debug(f"Saved edited project config data: (project_name={prj.project_name},loop_interval={prj.loop_interval},is_triggered={prj.is_triggered})")