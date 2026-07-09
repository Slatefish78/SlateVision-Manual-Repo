import logging
import math
from PySide6.QtWidgets import QWidget, QPushButton, QSizePolicy, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QTimer
from core.camera import Camera
from gui.popups.edit_camera import EditCameraPopup
from gui.popups.loading import LoadingPopup
from gui.popups.plc_signal_list import PlcSignalsPopup
from gui.popups.vision_param_list import VisionParametersPopup
from gui.popups.vision_prj_config import VisionPrjConfigPopup
from gui.popups.vision_tool_list import VisionToolsPopup
from gui.screens.screen import Screen
from gui.util.camera_view import CameraView

logger = logging.getLogger(__name__)

class VisionPrjScreen(Screen):
    #region Init
    def __init__(self,parent = None,controller=None):
        super().__init__("Vision Project Screen",parent,controller)

        self.framerate_timer = QTimer()
        self.framerate_timer.timeout.connect(self.update_stream)

        self.cam_loading_popup = None
        
        # camera grid
        cam_grid = QWidget()
        cam_grid.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.cam_layout = QGridLayout(cam_grid)
        self.cam_layout.setSpacing(self.controller.widget_spacing)
        self.cam_layout.setContentsMargins(0,0,0,0)
        self.content_layout.addWidget(cam_grid)

        # two columns of buttons
        btn_column_widget = QWidget()
        btn_column_layout = QHBoxLayout(btn_column_widget)
        btn_column_layout.setSpacing(self.controller.widget_spacing)
        btn_column_layout.setContentsMargins(0,0,0,0)
        self.content_layout.addWidget(btn_column_widget)

        btn_col1_widget = QWidget()
        btn_col1_layout = QVBoxLayout(btn_col1_widget)
        btn_col1_layout.setContentsMargins(0,0,0,0)
        btn_column_layout.addWidget(btn_col1_widget)

        btn_col2_widget = QWidget()
        btn_col2_layout = QVBoxLayout(btn_col2_widget)
        btn_col2_layout.setContentsMargins(0,0,0,0)
        btn_column_layout.addWidget(btn_col2_widget)

        # place buttons
        buttons_def = [
            ("Project Config", self.on_btn_config),
            ("Add Camera", self.on_btn_add_cam),
            ("Vision Parameters", self.on_btn_vision_params),
            ("PLC Signals", self.on_btn_plc_signals),
            ("Run Project", self.on_btn_run_vision_prj),
            ("Save Vision Project", self.on_btn_save),
            ("Save As/Export", self.on_btn_save_export),
            ("Done", self.on_btn_done)
        ]

        for i, (text, callback) in enumerate(buttons_def):
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

            btn.setProperty("role","default")

            btn.clicked.connect(callback)

            if i < 4:
                btn_col1_layout.addWidget(btn)
            else:
                btn_col2_layout.addWidget(btn)

    #region Button Handlers




    #region Config
    def on_btn_config(self):
        logger.debug(f"Button Press - edit Project Config.")
        self.controller.selected_project.edited = True
        VisionPrjConfigPopup(self,self.controller).exec()

    #region Add Cam
    def on_btn_add_cam(self):
        logger.debug(f"Button Press - Add Camera")
        # check number of cameras
        num_cameras = len(self.controller.selected_project.cameras)
        if num_cameras >= self.controller.max_cameras_per_project:
            QMessageBox.warning(self,"Max Camera Count", f"The maximum number of cameras per project ({self.controller.max_cameras_per_project}) has been reached. Please delete or edit an existing camera.")
            return

        self.controller.selected_project.edited = True
        self.controller.selected_project.cameras.append(Camera(
            name=f"Camera {num_cameras}",
            source=0,
            resolution_width=640,
            resolution_height=480,
            fps=20
        ))

        EditCameraPopup(self.controller.selected_project.cameras[-1],self,self.controller).show()

        self.update_cam_grid()

    #region Vision Parameters
    def on_btn_vision_params(self):
        logger.debug(f"Button Press - edit Vision Parameters.")
        VisionParametersPopup(self,self.controller).exec()

    #region PLC Signals
    def on_btn_plc_signals(self):
        logger.debug(f"Button Press - edit PLC Signals.")
        PlcSignalsPopup(self,self.controller).exec()

    #region Run Vision Project
    def on_btn_run_vision_prj(self):
        logger.debug(f"Button Press - Run Vision Project.")
        # check if file is saved
        if self.controller.selected_project.edited:
            save_confirm = QMessageBox.question(
                self,
                "Project Not Saved",
                "The current Vision Project may have unsaved edits. Unsaved changes will be lost. Do you want to save?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if save_confirm == QMessageBox.Yes:
                self.on_btn_save()
            elif save_confirm == QMessageBox.No:
                pass
            else: # Cancel
                return

        # update recent path list
        self.controller.update_path_list(self.controller.selected_project.project_name,self.controller.project_file_path,self.controller.recent_run_projects)

        # update run screen
        self.controller.root.screens["run"].update_header(f"Running Vision Project - {self.controller.selected_project.project_name}")
        self.controller.root.screens["run"].update_cam_grid(len(self.controller.selected_project.cameras))

        # start project operation
        self.controller.selected_project.start_operation()

        # show run screen
        self.controller.root.show_screen("run")

    #region Save
    def on_btn_save(self):
        logger.debug(f"Button Press - Save Vision Project.")
        # check if file is exported
        if self.controller.selected_project.exported:
            self.gui_save_project(save_path=None)
        else:
            export_confirm = QMessageBox.question(
                self,
                "Project Not Exported",
                "The current Vision Project has not been exported. Would you like to export it?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if export_confirm == QMessageBox.Yes:
                self.on_btn_save_export()

    #region Export
    def on_btn_save_export(self):
        logger.debug(f"Button Press - Export Vision Project.")
        # get location to export/save as
        export_path,_ = QFileDialog.getSaveFileName(
            self,
            "Enter Export Path",
            "",
            "SlateVision Project (*.svp)"
        )

        if not export_path:
            return

        # save project to selected path
        self.gui_save_project(export_path)

    #region Edit Done
    def on_btn_done(self):
        logger.debug(f"Button Press - Done - back to main menu.")
        # check if file is saved
        if self.controller.selected_project.edited:
            save_confirm = QMessageBox.question(
                self,
                "Project Not Saved",
                "The current Vision Project may have unsaved edits. Unsaved changes will be lost. Do you want to save?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if save_confirm == QMessageBox.Yes:
                self.on_btn_save()
            elif save_confirm == QMessageBox.No:
                pass
            else: # Cancel
                return
        
        self.controller.root.show_screen("menu")

    #region Screen Methods
    def showEvent(self,event):
        self.update_cam_grid()
        self.framerate_timer.start(10)
        return super().showEvent(event)

    def hideEvent(self, event):
        self.framerate_timer.stop()
        if self.controller.selected_project is not None:
            self.controller.selected_project.stop_cameras()
        return super().hideEvent(event)
    
    #region GUI process - Save
    def gui_save_project(self,save_path=None):
            self.controller.save_project(save_path)
            
            self.controller.update_path_list(self.controller.selected_project.project_name,self.controller.project_file_path,self.controller.recent_vision_projects)
            
            QMessageBox.information(
                self,
                "Project Save Successful",
                "Project saved successfully."
            )

    #region Update Cam Grid
    def update_cam_grid(self):
        # remove existing canvases
        while self.cam_layout.count():
            item = self.cam_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.display_views = []

        num_cameras = len(self.controller.selected_project.cameras)
        if num_cameras == 0:
            label = QLabel("No cameras connected.")
            label.setAlignment(Qt.AlignCenter)
            self.cam_layout.addWidget(label)
            return

        # grid all camera views into canvas. Expand to largest that can fill, but keep aspect ratio
        for i, cam in enumerate(self.controller.selected_project.cameras):
            # get row and column this image fills
            row = i // math.ceil(math.sqrt(num_cameras))
            column = i % math.ceil(math.sqrt(num_cameras))

            # container widget for cam view and edit button
            cam_block_widget = QWidget()
            cam_block_layout = QVBoxLayout(cam_block_widget)
            cam_block_layout.setContentsMargins(0,0,0,0)
            self.cam_layout.addWidget(cam_block_widget, row, column)

            # camera view            
            cam_widget = CameraView()
            cam_widget.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

            self.display_views.append(cam_widget)
            cam_block_layout.addWidget(cam_widget)

            # toggle cam button
            toggle_labels = {True: "Stop Camera", False: "Start Camera"}
            toggle_btn = QPushButton()
            toggle_btn.setText(toggle_labels[cam.is_running])

            toggle_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            toggle_btn.setProperty("role","default")

            def on_btn_toggle_cam(index,btn):
                logger.debug(f"Button Press - Toggle camera {index}")

                cam = self.controller.selected_project.cameras[index]
                if cam.is_running:
                    cam.end_connection()
                    btn.setText("Start Camera")
                else:
                    self.controller.selected_project.start_cam(index)
                    btn.setText("Stop Camera")

            toggle_btn.clicked.connect(
                lambda checked=False, index=i, btn=toggle_btn: on_btn_toggle_cam(index,btn)
            )       

            cam_block_layout.addWidget(toggle_btn)        

            # edit button
            edit_btn = QPushButton(f"Edit {cam.name}")
            edit_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            edit_btn.setProperty("role","default")                

            edit_btn.clicked.connect(
                lambda checked=False, camera=cam: EditCameraPopup(camera,self,self.controller).exec()
            )
            cam_block_layout.addWidget(edit_btn)

            # vision tools button
            tool_btn = QPushButton("Vision Tools")
            tool_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            tool_btn.setProperty("role","default")

            tool_btn.clicked.connect(
                lambda checked=False, camera=cam: VisionToolsPopup(camera,self,self.controller).exec()
            )
            cam_block_layout.addWidget(tool_btn)
    
    #region Update Cam Stream
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
            if i >= len(self.display_views):
                continue
            
            # Get frame from camera
            cv_frame = camera.get_last_frame()
            if cv_frame is None:
                continue

            # Resize and convert frame
            cam_view = self.display_views[i]

            if cam_view.width() <2 or cam_view.height() < 2:
                continue

            # Clear previous frame and draw new
            cam_view.set_frame(cv_frame)