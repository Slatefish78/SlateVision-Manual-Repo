import logging
from pathlib import Path
import shutil
import threading
import time

from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QWidget, QPushButton, QSizePolicy, QHBoxLayout, QDialog,QVBoxLayout, QLabel, QGridLayout, QScrollArea, QListWidget
from PySide6.QtCore import Qt,QTimer, Signal
import cv2
from gui.popups.loading import LoadingPopup
from gui.popups.edit_camera import EditCameraPopup
from gui.popups.edit_class import EditClassPopup
from gui.popups.model_prj_config import ModelPrjConfigPopup
from gui.popups.multi_capture_settings import VidCapturePopup
from gui.popups.selection_list import SelectionListPopup
from gui.popups.train_model import TrainModelPopup
from gui.screens.screen import Screen
from gui.util.clear_layout import clear_layout
from gui.util.camera_view import CameraView

logger = logging.getLogger(__name__)

class ModelPrjScreen(Screen):
    frame_captured_signal = Signal(int)
    capture_done_signal = Signal()

    train_start_signal = Signal()
    epoch_end_signal = Signal(int)
    train_end_signal = Signal()
    train_error_signal = Signal(str)

    export_complete_signal = Signal()
    export_error_signal = Signal(str)

    #region Init
    def __init__(self,parent = None,controller=None):
        super().__init__("Model Project Screen",parent,controller)

        self.framerate_timer = QTimer()
        self.framerate_timer.timeout.connect(self.update_stream)
        self.selected_class = None
        self.frames_captured = 0
        self.cancel_frame_capture = False
        self.cam_loading_popup = None
        self.preview_mode = "camera"
        
        # format screen: 2 rows, 3 columns in first, 2 in second
        # three columns - classes, cam/img preview, file preview
        row1_widget = QWidget()
        row1_layout = QHBoxLayout(row1_widget)
        row1_layout.setSpacing(self.controller.widget_spacing)
        row1_layout.setContentsMargins(0,0,0,0)
        self.content_layout.addWidget(row1_widget)

        classes_widget = QWidget()
        classes_widget.setMaximumWidth(250)
        classes_layout = QVBoxLayout(classes_widget)
        classes_layout.setContentsMargins(0,0,0,0)
        row1_layout.addWidget(classes_widget)

        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0,0,0,0)
        row1_layout.addWidget(preview_widget)

        file_prev_widget = QWidget()
        file_prev_widget.setMaximumWidth(250)
        file_prev_layout = QVBoxLayout(file_prev_widget)
        file_prev_layout.setContentsMargins(0,0,0,0)
        row1_layout.addWidget(file_prev_widget)

        # two columns of buttons
        row2_widget = QWidget()
        row2_layout = QHBoxLayout(row2_widget)
        row2_layout.setSpacing(self.controller.widget_spacing)
        row2_layout.setContentsMargins(0,0,0,0)
        self.content_layout.addWidget(row2_widget)

        btn_col1_widget = QWidget()
        btn_col1_layout = QVBoxLayout(btn_col1_widget)
        btn_col1_layout.setContentsMargins(0,0,0,0)
        row2_layout.addWidget(btn_col1_widget)

        btn_col2_widget = QWidget()
        btn_col2_layout = QVBoxLayout(btn_col2_widget)
        btn_col2_layout.setContentsMargins(0,0,0,0)
        row2_layout.addWidget(btn_col2_widget)

        # class toolbar
        classes_title = QLabel("Annotation Classes")
        classes_title.setAlignment(Qt.AlignCenter)
        classes_title.setProperty("role","title")
        classes_layout.addWidget(classes_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        classes_layout.addWidget(scroll)

        class_grid_widget = QWidget()
        self.class_grid = QGridLayout(class_grid_widget)
        self.class_grid.setHorizontalSpacing(0)
        self.class_grid.setContentsMargins(0,0,0,0)
        self.class_grid.setRowStretch(999,1)
        scroll.setWidget(class_grid_widget)

        self.class_label = QPushButton("No Annotation Class Selected")
        self.class_label.setProperty("role","default")
        self.class_label.clicked.connect(self.on_btn_deselect_class)
        classes_layout.addWidget(self.class_label)

        btn_delete_ann = QPushButton("Delete Last Annotation")
        btn_delete_ann.setProperty("role","default")
        btn_delete_ann.clicked.connect(self.on_btn_delete_ann)
        classes_layout.addWidget(btn_delete_ann)

        btn_add_class = QPushButton("Add Class")
        btn_add_class.setProperty("role","default")
        btn_add_class.clicked.connect(self.on_btn_add_class)
        classes_layout.addWidget(btn_add_class)

        # cam/img preview
        self.cam_prev = CameraView()
        self.cam_prev.box_created_signal.connect(self.on_box_creation)
        preview_layout.addWidget(self.cam_prev)
        
        self.btn_toggle_cam = QPushButton("Start Camera")            
        self.btn_toggle_cam.setProperty("role","default")
        self.btn_toggle_cam.clicked.connect(self.on_btn_toggle_cam)
        preview_layout.addWidget(self.btn_toggle_cam)

        btn_edit_cam = QPushButton("Camera Settings")
        btn_edit_cam.setProperty("role","default")
        btn_edit_cam.clicked.connect(
            lambda: EditCameraPopup(self.controller.selected_project.camera,self,self.controller).exec()
        )
        preview_layout.addWidget(btn_edit_cam)

        # file preview
        self.files_title = QLabel("Image List")
        self.files_title.setAlignment(Qt.AlignCenter)
        self.files_title.setProperty("role","title")
        file_prev_layout.addWidget(self.files_title)

        self.file_list = QListWidget()
        self.file_list.itemSelectionChanged.connect(
            lambda: self.display_selected_img(self.file_list.currentItem()))
        self.file_list.itemClicked.connect(self.display_selected_img)
        file_prev_layout.addWidget(self.file_list)

        btn_frame_cap = QPushButton("Frame Capture")
        btn_frame_cap.setProperty("role","default")
        btn_frame_cap.clicked.connect(self.on_btn_frame_cap)
        file_prev_layout.addWidget(btn_frame_cap)

        btn_delete_img = QPushButton("Delete Selected Image")
        btn_delete_img.setProperty("role","default")
        btn_delete_img.clicked.connect(self.on_btn_delete_img)
        file_prev_layout.addWidget(btn_delete_img)

        # place buttons
        buttons_def = [
            ("Project Config", self.on_btn_config),
            ("Multi-Frame Capture", self.on_btn_multi_frame_cap),
            ("Import Images", self.on_btn_import_imgs),
            ("Train Model", self.on_btn_train),
            ("Export Trained Model", self.on_btn_export_model),
            ("Save Model Project",self.on_btn_save),
            ("Save As/Export",self.on_btn_export),
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




    #region Select Class
    def on_btn_select_class(self,cls):
        logger.debug(f"Button Press - Select Class: {cls}.")
        if self.preview_mode == "image":
            self.selected_class = cls

            self.cam_prev.show_crosshair = True
            self.cam_prev.active_class = cls

            self.class_label.setText(f"Annotation Class - {cls['name']}")

            r = int(cls["color"][1:3],16)
            g = int(cls["color"][3:5],16)
            b = int(cls["color"][5:7],16)

            self.class_label.setProperty("role","default")
            self.class_label.setStyleSheet(f"QPushButton {{background-color: rgb({r},{g},{b});}}")

        else:
            QMessageBox.information(
                self,
                "Cannot Select Class",
                "Please select an image for annotation before selecting a class."
            )

    #region Add Class
    def on_btn_add_class(self):
        logger.debug(f"Button Press - Add Class.")
        new_id = 0
        while new_id in {cls["id"] for cls in self.controller.selected_project.classes}:
            new_id += 1

        self.controller.selected_project.classes.append(
            {
                "id": new_id,
                "name": "New Class",
                "color": "#909090"
            }
        )

        EditClassPopup(self.controller.selected_project.classes[-1],self,self.controller,on_delete_callback=self.on_delete_class,on_done_callback=self.on_edit_class_done).exec()

    def on_delete_class(self,cls):
        close_popup = False

        confirmation = QMessageBox.question(
            self,
            "Delete Class",
            f"Are you sure you want to delete this class? Associated annotations will be removed.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            if len(self.controller.selected_project.classes) > 1:
                self.controller.selected_project.classes.remove(cls)
                
                #remove annotations using this class
                for box_list in self.controller.selected_project.annotations.values():
                    box_list[:] = [
                        box for box in box_list
                        if cls["id"] != box["class_id"]
                    ]

                self.update_classes()

                # close currently open Edit Class Popup
                close_popup = True

            else:
                QMessageBox.warning(
                    self,
                    "Cannot Delete Class",
                    "A Model Project requires at least one annotation class. Please edit an existing class."
                )

        return close_popup

    def on_edit_class_done(self,cls):
        self.update_classes()

        if self.selected_class == cls:
            self.on_btn_select_class(cls)

    #region Deselect Class
    def on_btn_deselect_class(self):
        logger.debug(f"Button Press - Deselect Class.")
        self.selected_class = None
        self.cam_prev.show_crosshair = False
        self.cam_prev.active_class = None
        self.class_label.setText("No Annotation Class Selected")
        self.class_label.setProperty("role","default")

    #region Delete Annotation
    def on_btn_delete_ann(self):
        logger.debug(f"Button Press - Delete Last Annotation.")
        item = self.file_list.currentItem()
        if len(self.controller.selected_project.annotations[item.text()]) > 0:
            self.controller.selected_project.annotations[item.text()][:] = self.controller.selected_project.annotations[item.text()][:-1]
            self.cam_prev.set_classes(self.controller.selected_project.classes)
            self.controller.selected_project.edited = True
            self.cam_prev.update()

    #region Toggle Camera
    def on_btn_toggle_cam(self):
        logger.debug(f"Button Press - Toggle model Camera.")

        cam = self.controller.selected_project.camera
        toggle_labels = {True: "Stop Camera", False: "Start Camera"}
        self.btn_toggle_cam.setText(toggle_labels[cam.is_running])

        if cam.is_running:
            cam.end_connection()
            self.btn_toggle_cam.setText("Start Camera")
        else:
            self.cam_prev.show_crosshair = False
            self.cam_prev.active_class = None
            self.cam_prev.set_classes([])
            self.cam_prev.set_annotations([])
            self.on_btn_deselect_class()
            threading.Thread(target=self.controller.selected_project.start_camera,daemon=True).start()
            self.preview_mode = "camera"
            self.btn_toggle_cam.setText("Stop Camera")

    #region Single Frame Capture
    def on_btn_frame_cap(self):
        logger.debug(f"Button Press - Capture Frame.")
        project = self.controller.selected_project

        if not project or not project.camera:
            return
        
        if not project.camera.is_running:
            QMessageBox.warning(
                self,
                "Frame Capture Failure",
                "Camera is not running. Start the camera before frame capture."
            )
            return

        frame = project.camera.get_last_frame()
        if frame is None:
            QMessageBox.warning(
                self,
                "Frame Capture Failure",
                "No frame available from camera."
            )
            return


        img_path = project.project_folder_path / "raw_images" / self.generate_img_filename("jpg")
        img_path.parent.mkdir(parents=True,exist_ok=True)

        project.edited = True
        project.camera.save_img(frame,img_path)

        self.update_files()

    #region Delete Image
    def on_btn_delete_img(self):
        logger.debug(f"Button Press - Delete Image.")
        # get selected img
        selected_item = self.file_list.currentItem()

        if not selected_item:
            QMessageBox.warning(
                self,
                "Image Delete Failure",
                "No image selected."
            )
            return

        # get filepath
        filepath = self.controller.selected_project.project_folder_path / "raw_images" / selected_item.text()

        # get current index
        selected_row = self.file_list.currentRow()

        # delete file
        
        if filepath.exists():
            if filepath.is_file():
                filepath.unlink()
            elif filepath.is_dir():
                shutil.rmtree(filepath)
            else:
                raise Exception("File could not be deleted.")
        # except Exception as e:
        #     QMessageBox.critical(
        #         self,
        #         "Image Delete Failure",
        #         str(e)
        #     )

        self.controller.selected_project.edited = True

        # refresh list
        self.file_list.blockSignals(True)
        self.update_files()
        self.file_list.blockSignals(False)

        file_count = self.file_list.count()

        # clear preview if no images
        if file_count == 0:
            self.preview_mode = "camera"
            self.cam_prev.frame = None
            self.cam_prev.qimage = None
            self.cam_prev.update()
            return
        
        # select previous item
        new_row = max(0,selected_row - 1)
        if new_row >= file_count:
            new_row = file_count - 1

        self.file_list.setCurrentRow(new_row)

    #region Config
    def on_btn_config(self):
        logger.debug(f"Button Press - edit Project Config.")
        ModelPrjConfigPopup(self,self.controller).exec()

    #region Multi Frame Capture
    def on_btn_multi_frame_cap(self):
        logger.debug(f"Button Press - Multi-Frame Capture.")
        project = self.controller.selected_project

        if not project or not project.camera:
            return
        
        if not project.camera.is_running:
            QMessageBox.warning(
                self,
                "Frame Capture Failure",
                "Camera is not running. Start the camera before frame capture."
            )
            return
        
        num_frames = VidCapturePopup.get_frame_num(self,self.controller)

        if num_frames is None:
            return
        
        if num_frames <= 0:
            raise RuntimeError("Invalid multi-frame capture number")
        
        # open popup
        popup = LoadingPopup("Capturing Frames",self,self.controller)
        popup.update(f"Capturing frames: {0}/{self.num_frames}",0,num_frames)
        popup.rejected.connect(self.cancel_frame_cap)

        # connect GUI signals
        self.frame_captured_signal.connect(
            lambda frames: popup.update(f"Capturing frames: {frames}/{self.num_frames}",value=frames)
        )
        self.capture_done_signal.connect(popup.accept)

        # start thread
        self.frames_captured = 0
        self.cancel_frame_capture = False
        threading.Thread(target=self.multi_frame_cap_worker,args=(num_frames,popup),daemon=True).start()
        popup.exec()

        # after thread completes:
        self.update_files()
        if not self.cancel_frame_capture:
            QMessageBox.information(
                self,
                "Frame Capture Successful",
                f"{self.frames_captured} images were successfully captured."
            )
        else:
            QMessageBox.information(
                self,
                "Frame Capture Canceled",
                f"Multi-frame capture was canceled. {self.frames_captured} images were captured."
            )

    def cancel_frame_cap(self):
        self.cancel_frame_capture = True

    #region Import Images
    def on_btn_import_imgs(self):
        logger.debug(f"Button Press - Import Images.")
        # open file dialog
        filepaths,_ = QFileDialog.getOpenFileNames(
            self,
            "Select Images for Import",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp)"
        )

        if not filepaths:
            return
        
        # add to file list
        for path in filepaths:
            src_path = Path(path)
            dest_path = self.controller.selected_project.project_folder_path / "raw_images" / src_path.name
            dest_path.parent.mkdir(parents=True,exist_ok=True)

            shutil.copy(src_path,dest_path)

        self.controller.selected_project.edited = True
        self.update_files()

        QMessageBox.information(
            self,
            "File Import Successful",
            f"Successfully imported {len(filepaths)} images."
        )
    
    #region Train Model
    def on_btn_train(self):
        logger.debug(f"Button Press - Train Model.")
        prj = self.controller.selected_project
        prj.edited = True

        # open settings popup
        popup = TrainModelPopup(self,self.controller)
        result = popup.exec()

        if result == QDialog.Rejected:
            return
        
        # verify training settings
        if not prj.base_model_path or not prj.base_model_path.exists():
            QMessageBox.warning(
                self,
                "Invalid Base Model Path",
                "The specified base model file could not be used. Please specify a valid base model path."
            )
            return

        if not prj.model_export_dir or not prj.model_export_dir.exists():
            QMessageBox.warning(
                self,
                "Invalid Export Path",
                "The specified export path could not be used. Please specify a valid export path."
            )
            return
        
        # confirm execution
        confirm = QMessageBox.question(
            self,
            "Confirm Training Preparation",
            "The dataset will be prepared from currently captured images. 100 annotated images recommended. Missing annotations could cause model inaccuracy. Model training requires time and computer resources. Execute training?"
        )

        if confirm == QMessageBox.No:
            return

        # open training popup
        training_progress = QProgressDialog(
            "Formatting dataset.",
            "Cancel",
            0,
            0,
            self
        )
        training_progress.setWindowTitle("Model Training")
        training_progress.setWindowModality(Qt.WindowModal)
        training_progress.setMinimumDuration(0)
        training_progress.setValue(0)

        # define training callbacks
        self.train_start_signal.disconnect()
        self.epoch_end_signal.disconnect()
        self.train_end_signal.disconnect()
        self.train_error_signal.disconnect()

        self.train_start_signal.connect(lambda: (
            training_progress.setLabelText("Training model..."),
            training_progress.setRange(0,prj.train_settings["epochs"])
        ))

        self.epoch_end_signal.connect(lambda current_epoch: (
            training_progress.setLabelText(f"Completed epoch {current_epoch}/{prj.train_settings['epochs']}"),
            training_progress.setValue(current_epoch)
        ))

        self.train_end_signal.connect(lambda: (
            training_progress.setLabelText("Training complete."),
            training_progress.accept(),
            QMessageBox.information(
                self,
                "Model Training Success",
                "Model training completed successfully."
            )
        ))

        self.train_error_signal.connect(lambda e: (
            training_progress.reject(),
            QMessageBox.critical(
                self,
                "Model Training Failure",
                e
            )
        ))

        def on_train_start(trainer):
            self.train_start_signal.emit()
        
        def on_epoch_end(trainer):
            self.epoch_end_signal.emit(trainer.epoch + 1)

        def on_train_end(trainer):
            self.train_end_signal.emit()

        # start model training process
        threading.Thread(
            target=self.controller.selected_project.train_model,
            kwargs={
                "on_train_start": on_train_start,
                "on_epoch_end": on_epoch_end,
                "on_train_end": on_train_end
            },
            daemon=True
        ).start()
        
    #region Export Model
    def on_btn_export_model(self):
        logger.debug(f"Button Press - Export Model.")
        # get base model
        model_filepath,_ = QFileDialog.getOpenFileName(
            self,
            "Select Base Model to Export",
            str(self.controller.selected_project.model_export_dir),
            "Pytorch models (*.pt)"
        )

        if not model_filepath:
            return
        
        # select output format
        output_types = [
            ("TorchScript (.torchscript)","torchscript"),
            ("ONNX (.onnx)","onnx"),
            ("OpenVINO (directory)","openvino"),
            ("TensorRT (.engine)","engine"),
            ("CoreML (.mlpackage)","coreml"),
            ("TF SavedModel (directory)","saved_model"),
            ("TF GraphDef (.pb)","pb"),
            ("TF Lite (.tflite)","tflite"),
            ("TF Edge TPU (.tflite)","edgetpu"),
            ("TF.js (directory)","tfjs"),
            ("PaddlePaddle (directory)","paddle"),
            ("MNN (.mnn)","mnn"),
            ("NCNN (directory)","ncnn"),
            ("RKNN (directory)","rknn"),
            ("ExecuTorch (directory)","executorch"),
            ("Axelera (directory)","axelera")
        ]

        output_format = SelectionListPopup.get_selection(
            self,
            self.controller,
            "Select Output Format",
            output_types
        )

        if not output_format:
            return

        # select output location
        export_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Export Location",
            str(self.controller.selected_project.model_export_dir)
        )

        if not export_folder:
            return
        
        # open popup
        export_progress = QProgressDialog(
            "Exporting model",
            "Cancel",
            0,
            0,
            self
        )
        export_progress.setWindowTitle("Model Export")
        export_progress.setWindowModality(Qt.WindowModal)
        export_progress.show()

        # connect signals for completion display
        self.export_complete_signal.disconnect()
        self.export_error_signal.disconnect()

        format_label_map = {}
        for label, format in output_types:
            format_label_map[format] = label

        self.export_complete_signal.connect(lambda: (
            export_progress.accept(),
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported model {Path(model_filepath).name} to {format_label_map[output_format]}.\n{self.controller.selected_project.exported_model_path}"
            )
        ))

        self.export_error_signal.connect(lambda e: (
            export_progress.reject(),
            QMessageBox.critical(
                self,
                "Export Failure",
                e
            )
        ))

        # run export
        threading.Thread(
            target=self.controller.selected_project.export_model,
            kwargs={
                "base_model": model_filepath,
                "output_format": output_format,
                "output_location": export_folder,
                "on_complete": self.export_complete_signal.emit
            },
            daemon=True
        ).start()
    
    #region Save Project
    def on_btn_save(self):
        logger.debug(f"Button Press - Save Model Project.")
        # check if file is exported
        if self.controller.selected_project.exported:
            self.gui_save_project(save_path=None)
        else:
            export_confirm = QMessageBox.question(
                self,
                "Project Not Exported",
                "The current Model Project has not been exported. Would you like to export it?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if export_confirm == QMessageBox.Yes:
                self.on_btn_export()

    #region Export Project
    def on_btn_export(self):
        logger.debug(f"Button Press - Export Model Project.")
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

    #region Done Button
    def on_btn_done(self):
        logger.debug(f"Button Press - Done - back to main menu.")
        # check if file is saved
        if self.controller.selected_project.edited:
            save_confirm = QMessageBox.question(
                self,
                "Project Not Saved",
                "The current Model Project may have unsaved edits. Unsaved changes will be lost. Do you want to save?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if save_confirm == QMessageBox.Yes:
                self.on_btn_save()
            elif save_confirm == QMessageBox.No:
                pass
            else: # Cancel
                return
            
        self.controller.root.show_screen("menu")

    #region Class Methods
    def showEvent(self,event):
        self.update_classes()
        self.framerate_timer.start(10)
        return super().showEvent(event)

    def hideEvent(self, event):
        self.framerate_timer.stop()
        if self.controller.selected_project is not None:
            self.controller.selected_project.camera.end_connection()
            self.controller.close_project()
        return super().hideEvent(event)
    
    def list_imgs(self):
        raw_dir = self.controller.selected_project.project_folder_path / "raw_images"
        img_list = []
        for file in sorted(raw_dir.rglob("*")):
            if file.suffix.lower() in {".jpg",".png","jpeg"}:
                img_list.append(file.name)

        return img_list
    
    def generate_img_filename(self,filetype:str):
        if filetype.startswith("."):
            filetype = filetype[1:]

        count = 0
        while True:
            filename = f"img{count:05d}.{filetype}"
            if filename not in self.list_imgs():
                return filename
            else:
                count += 1
                continue
    
    #region GUI process - Save
    def gui_save_project(self,save_path=None):
        self.controller.save_project(save_path)
        
        self.controller.update_path_list(self.controller.selected_project.project_name,self.controller.project_file_path,self.controller.recent_model_projects)
        
        QMessageBox.information(
            self,
            "Project Save Successful",
            "Project saved successfully."
        )

    #region Update Class List
    def update_classes(self):
        # update image preview
        self.cam_prev.set_classes(self.controller.selected_project.classes)

        # remove existing class display
        clear_layout(self.class_grid)

        # insert buttons
        for i, cls in enumerate(self.controller.selected_project.classes):
            name = cls["name"]
            color = cls["color"]

            label_btn = QPushButton(name)
            label_btn.setProperty("role","annotation_class")
            label_btn.setStyleSheet(f"background-color: {color}")
            label_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            label_btn.clicked.connect(
                lambda checked=False, cls_=cls: self.on_btn_select_class(cls_)
            )

            edit_btn = QPushButton("Edit")
            edit_btn.setProperty("role","annotation_class")
            edit_btn.setStyleSheet(f"background-color: {color}")
            edit_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            edit_btn.clicked.connect(
                lambda checked=False, cls_to_edit=cls: EditClassPopup(
                    cls_to_edit,
                    self,
                    self.controller,
                    on_delete_callback=self.on_delete_class,
                    on_done_callback=self.on_edit_class_done).exec()
            )

            self.class_grid.addWidget(label_btn,i,0)
            self.class_grid.addWidget(edit_btn,i,1)
    
    #region Update File Preview
    def update_files(self):
        self.file_list.blockSignals(True)

        # remove existing entries
        self.file_list.clear()

        img_list = self.list_imgs()

        for img_name in img_list:
            self.file_list.addItem(img_name)

        self.file_list.blockSignals(False)

        self.files_title.setText(f"Image List: ({len(img_list)})")

    #region Show Image Preview
    def display_selected_img(self, item):
        if not item:
            return
        
        project = self.controller.selected_project

        # stop camera
        if project.camera.is_running:
            project.camera.end_connection()

        # load image
        img_path = project.project_folder_path / "raw_images" / item.text()

        if not img_path.exists():
            return
        
        frame = cv2.imread(str(img_path))
        if frame is None:
            return
        
        # display image preview
        self.preview_mode = "image"
        self.cam_prev.set_frame(frame)

        # display stored annotations
        self.cam_prev.set_classes(self.controller.selected_project.classes)
        try:
            self.cam_prev.set_annotations(self.controller.selected_project.annotations[item.text()])
        except KeyError:
            self.cam_prev.annotations = []

    def on_box_creation(self, box):
        item = self.file_list.currentItem()
        if not item:
            return
        
        ann = self.controller.selected_project.annotations.setdefault(item.text(),[])
        ann.append(box)
        self.controller.selected_project.edited = True

        self.cam_prev.set_annotations(ann)

    #region Update Cam Stream
    def update_stream(self):
        if self.preview_mode != "camera":
            return
        
        if not self.controller.selected_project:
            return
        
        # show loading popup
        if self.controller.selected_project.opening_camera:
            if self.cam_loading_popup is None: # popup does not exist - create it
                self.cam_loading_popup = LoadingPopup("Cameras Loading",self,self.controller,"Please wait. Opening camera.")
                self.cam_loading_popup.show()
        else:   
            if self.cam_loading_popup:
                self.cam_loading_popup.close()
                self.cam_loading_popup = None
                
        
        # Get frame from camera
        cv_frame = self.controller.selected_project.camera.get_last_frame()
        if cv_frame is None:
            return

        # Resize and convert frame
        if self.cam_prev.width() <2 or self.cam_prev.height() < 2:
            return

        # Clear previous frame and draw new
        self.cam_prev.set_frame(cv_frame)

    #region Multi Frame Capture
    def multi_frame_cap_worker(self,frames,popup):
        while not self.cancel_frame_capture and self.frames_captured < frames:
            img_path = self.controller.selected_project.project_folder_path / "raw_images" / self.generate_img_filename("jpg")
            img_path.parent.mkdir(parents=True,exist_ok=True)

            frame = self.controller.selected_project.camera.get_last_frame()

            self.controller.selected_project.camera.save_img(frame,img_path)

            self.frames_captured += 1

            self.frame_captured_signal.emit(self.frames_captured)

            time.sleep(1 / self.controller.selected_project.camera.fps)

        self.capture_done_signal.emit()