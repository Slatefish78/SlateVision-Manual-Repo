import logging

from PySide6.QtWidgets import QDialog, QFormLayout, QPushButton, QSizePolicy, QSpinBox
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class VidCapturePopup(SVPopup):
    #region Init
    def __init__(self, parent=None, controller=None):
        super().__init__("Multi-Frame Capture Settings",parent,controller)

        form = QFormLayout()
        form.setContentsMargins(9,0,9,9)
        form.setSpacing(10)

        # time field
        self.time_input = QSpinBox()
        self.time_input.setRange(1,60)
        self.time_input.setToolTip("How long to capture frames (sec).")
        self.time_input.setSuffix(" sec")
        form.addRow("Time:",self.time_input)

        # frames field
        self.frames_input = QSpinBox()
        self.frames_input.setRange(1,600)
        self.frames_input.setToolTip("How many frames to capture.")
        form.addRow("Frames:",self.frames_input)

        self.content_layout.addLayout(form)

        # update fields
        self.frames_input.setSingleStep(self.controller.selected_project.camera.fps)

        self.time_input.valueChanged.connect(
            lambda: self.frames_input.setValue(
                int(self.time_input.value() * self.controller.selected_project.camera.fps)
            ))
                
        self.frames_input.valueChanged.connect(
            lambda: self.time_input.setValue(
                int(self.frames_input.value() / self.controller.selected_project.camera.fps)
            ))

        # Execute button
        exec_btn = QPushButton("Execute")
        exec_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        exec_btn.setProperty("role","default")

        exec_btn.clicked.connect(self.on_btn_execute)

        self.content_layout.addWidget(exec_btn)
        
        # cancel button
        self.content_layout.addWidget(self.cancel_btn)

    #region Update Screen
    def load_from_project(self):
        self.time_input.setValue(1)
        self.frames_input.setValue(int(self.time_input.value() * self.controller.selected_project.camera.fps))

    #region Button Handlers
    def on_btn_execute(self):
        logger.debug(f"Button Press - Execute multi-frame capture.")
        self.controller.selected_project.edited = True
        self.accept()

    #region Get Value on Close
    @staticmethod
    def get_frame_num(parent, controller):
        dialog = VidCapturePopup(parent, controller)
        if dialog.exec() == QDialog.Accepted:
            return dialog.frames_input.value()
        return None