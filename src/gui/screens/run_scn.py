import logging
import math
from PySide6.QtWidgets import QWidget, QPushButton, QSizePolicy, QGridLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import QTimer
from gui.screens.screen import Screen
from gui.popups.loading import LoadingPopup
from gui.util.camera_view import CameraView

logger = logging.getLogger(__name__)

class RunScreen(Screen):
    #region Init
    def __init__(self,parent = None,controller=None):
        super().__init__("Vision Project Run Screen",parent,controller)

        # camera stream grid
        cam_grid = QWidget()
        self.cam_grid_layout = QGridLayout(cam_grid)
        self.cam_grid_layout.setSpacing(self.controller.widget_spacing)
        self.content_layout.addWidget(cam_grid)

        self.display_views = []
        self.framerate_timer = QTimer()
        self.framerate_timer.timeout.connect(self.update_stream)

        self.cam_loading_popup = None

        bottom_row_layout = QHBoxLayout()
        self.content_layout.addLayout(bottom_row_layout)

        # buttons
        self.set_autorun_btn = QPushButton("Set Autorun Project")
        self.set_autorun_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

        self.set_autorun_btn.setProperty("role","default")

        self.set_autorun_btn.clicked.connect(self.on_btn_set_autorun)
        bottom_row_layout.addWidget(self.set_autorun_btn)

        clear_autorun_btn = QPushButton("Clear Autorun Project")
        clear_autorun_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

        clear_autorun_btn.setProperty("role","default")

        clear_autorun_btn.clicked.connect(self.on_btn_clear_autorun)
        bottom_row_layout.addWidget(clear_autorun_btn)

        stop_btn = QPushButton("Stop Running")
        stop_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

        stop_btn.setProperty("role","default")

        stop_btn.clicked.connect(self.on_btn_back)
        bottom_row_layout.addWidget(stop_btn)

    #region Update Cam Grid
    def update_cam_grid(self,num_cameras):
        # remove existing canvases
        while self.cam_grid_layout.count():
            item = self.cam_grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.display_views = []

        if num_cameras == 0:
            return

        # grid all camera views into canvas. Expand to largest that can fill, but keep aspect ratio
        for i in range(num_cameras):
            # get row and column this image fills
            row = i // math.ceil(math.sqrt(num_cameras))
            column = i % math.ceil(math.sqrt(num_cameras))
            
            cam_widget = CameraView()
            cam_widget.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

            self.display_views.append(cam_widget)
            self.cam_grid_layout.addWidget(cam_widget, row, column)
    
    #region Update Stream
    def update_stream(self):
        if not self.controller.selected_project:
            return
        
        # show loading popup
        opening_camera_index = self.controller.selected_project.opening_camera_index
        num_cameras=len(self.controller.selected_project.cameras)
        if opening_camera_index is not None: # open index exists -> a camera is opening
            if self.cam_loading_popup is None: # popup does not exist - create it
                self.cam_loading_popup = LoadingPopup("Cameras Loading",self,self.controller,"Please wait. Opening camera.")
                self.cam_loading_popup.show()
            self.cam_loading_popup.update(f"Please wait. Opening camera {opening_camera_index}/{num_cameras}")
        else:   
            if self.cam_loading_popup:
                self.cam_loading_popup.close()
                self.cam_loading_popup = None

        for i, camera in enumerate(self.controller.selected_project.cameras):
            if i >= len(self.display_views) or i >= len(self.controller.selected_project.frames):
                continue
            
            # Get frame from camera
            cv_frame = self.controller.selected_project.frames[i]
            if cv_frame is None:
                continue

            # Resize and convert frame
            label = self.display_views[i]

            if label.width() <2 or label.height() < 2:
                continue

            # Clear previous frame and draw new
            self.display_views[i].set_frame(cv_frame)
            self.display_views[i].set_tools([
                (tool, tool.latest_results, tool.render_settings)
                for tool in self.controller.selected_project.tools
                if tool.camera == camera
            ])
    
    #region Show/Hide Events
    def showEvent(self, event):
        self.framerate_timer.start(30)
        return super().showEvent(event)
    
    def hideEvent(self, event):
        self.framerate_timer.stop()
        self.controller.close_project()
        return super().hideEvent(event)

    #region Button Handlers
    def on_btn_set_autorun(self):
        logger.debug(f"Button Press - Set Autorun file to {str(self.controller.project_file_path)}.")
        self.controller.autorun_project = str(self.controller.project_file_path)
        self.controller.save_paths()
        QMessageBox.information(
            self,
            "Set Autorun Project",
            f"Set autorun project: {str(self.controller.project_file_path)}."
        )

    def on_btn_clear_autorun(self):
        logger.debug(f"Button Press - Clear Autorun file.")
        self.controller.autorun_project = None
        self.controller.save_paths()
        QMessageBox.information(
            self,
            "Cleared Autorun Project",
            "Cleared autorun project."
        )
        
    def on_btn_back(self):
        logger.debug(f"Button Press - Stop Running - back to main menu.")
        self.controller.selected_project.stop_operation()
        self.controller.root.show_screen("menu")