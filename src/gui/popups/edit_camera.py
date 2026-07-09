import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QFormLayout, QSpinBox, QMessageBox, QRadioButton, QButtonGroup
from core.camera import Camera
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class EditCameraPopup(SVPopup):
    #region Init
    def __init__(self, camera: Camera, parent=None, controller=None):
        super().__init__(f"Edit {camera.name}", parent, controller)

        self.controller.selected_project.edited = True

        # stop edited camera
        self.camera = camera
        self.camera.end_connection()

        form = QFormLayout()
        form.setContentsMargins(9,0,9,9)
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setToolTip("Name of the camera to connect to. Used for display.")
        form.addRow("Cam Name:",self.name_input)

        # camera string source field
        self.source_input = QLineEdit()
        self.source_input.setToolTip("Source of the camera to connect to. Enter integer for webcam slot, url for livestream.")
        form.addRow("Cam Source:",self.source_input)

        # select resolution list field
        self.resolution_group = QButtonGroup(self)
        self.resolution_group.setExclusive(True)

        res_widget = QWidget()
        res_layout = QVBoxLayout(res_widget)
        
        resolution_options = [
            ("640x480",(640,480)),
            ("800x600",(800,600)),
            ("1280x720",(1280,720)),
            ("1920x1080",(1920,1080))
        ]

        self.resolution_buttons = []

        for i, (label, data) in enumerate(resolution_options):
            btn = QRadioButton(label)
            self.resolution_group.addButton(btn, i)
            res_layout.addWidget(btn)
            self.resolution_buttons.append((btn, data))

        form.addRow("Resolution:", res_widget)

        # fps field
        self.fps_input = QSpinBox()
        self.fps_input.setRange(1,60)
        self.fps_input.setToolTip("FPS setting of camera (<=30fps recommended).")
        form.addRow("FPS:",self.fps_input)

        self.content_layout.addLayout(form)

        # delete button
        if self.controller.selected_project.project_type == "vision":
            self.content_layout.addWidget(self.delete_btn)
        
        # done button
        self.content_layout.addWidget(self.done_btn)

        # cancel button
        self.content_layout.addWidget(self.cancel_btn)

    #region Save/Load
    def load_from_project(self):
        if not self.camera:
            return
        
        logger.debug(f"Loaded cam data to edit: {self.camera}")

        self.name_input.setText(str(self.camera.name))
        
        self.source_input.setText(str(self.camera.source))
        
        for btn, (w,h) in self.resolution_buttons:
            if (self.camera.resolution_width, self.camera.resolution_height) == (w,h):
                btn.setChecked(True)
                break

        self.fps_input.setValue(self.camera.fps)

    def save_to_project(self):
        if not self.camera:
            return
        
        self.camera.name = self.name_input.text().strip()
        
        try:
            new_source = int(self.source_input.text().strip())
        except ValueError:
            new_source = self.source_input.text().strip()
            
        self.camera.source = new_source
        
        selected_res_id = self.resolution_group.checkedId()
        if selected_res_id != -1:
            _, (w,h) = self.resolution_buttons[selected_res_id]
            self.camera.resolution_width = w
            self.camera.resolution_height = h

        self.camera.fps = self.fps_input.value()

        logger.debug(f"Saved edited cam data: {self.camera}")

    #region Button Handlers               
    def on_btn_delete(self):
        logger.debug(f"Button Press - Delete Camera.")

        quit_confirmation = QMessageBox.question(
            self,
            "Delete Camera",
            f"Are you sure you want to delete {self.camera.name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if quit_confirmation == QMessageBox.Yes:
            self.camera.end_connection()
            self.controller.selected_project.cameras.remove(self.camera)
            self.controller.root.screens["vision"].update_cam_grid()
            self.accept()

    def on_btn_done(self):
        logger.debug(f"Button Press - Done with edit.")
        
        self.save_to_project()
        
        if hasattr(self.controller.selected_project, "cameras"):
            for camera in self.controller.selected_project.cameras:
                if self.camera.source == camera.source and camera != self.camera:
                    QMessageBox.warning(
                        self,
                        "Invalid Camera Source",
                        "Two cameras cannot share the same source. Please enter a different source."
                    )
                    return

            self.controller.root.screens["vision"].update_cam_grid()
            
        self.accept()

    def on_btn_cancel(self):
        try:
            new_source = int(self.source_input.text().strip())
        except ValueError:
            new_source = self.source_input.text().strip()

        if hasattr(self.controller.selected_project, "cameras"):
            for camera in self.controller.selected_project.cameras:
                if new_source == camera.source and camera != self.camera:
                    QMessageBox.warning(
                        self,
                        "Invalid Camera Source",
                        "Two cameras cannot share the same source. Please enter a different source."
                    )
                    return
                
        return super().on_btn_cancel()