import logging
from pathlib import Path
import shutil

from PySide6.QtWidgets import QSizePolicy, QPushButton, QFileDialog, QFormLayout, QCheckBox, QDoubleSpinBox, QSpinBox
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class TrainModelPopup(SVPopup):
    #region Init
    def __init__(self, parent=None, controller=None):
        super().__init__("Model Training Settings",parent,controller)
        
        self.form = QFormLayout()
        self.form.setContentsMargins(9,0,9,9)
        self.form.setSpacing(10)
        self.content_layout.addLayout(self.form)

        # base model entry
        self.base_model_btn = QPushButton()
        self.base_model_btn.setToolTip(
            "Pretrained YOLO model used as starting point for training.\n"
            "Smaller models (n, s) are faster/less accurate. Larger (m, l) are more accurate/slower.\n"
            "Recommended: yolo26n.pt"
        )
        self.base_model_btn.clicked.connect(self.on_btn_base_model)
        self.form.addRow("Base Model:",self.base_model_btn)

        # epochs entry
        self.epochs = QSpinBox()
        self.epochs.setRange(1,500)
        self.epochs.setToolTip(
            "Number of full passes through dataset.\n"
            "Higher values increase accuracy and training time. Too high can result in overfitting.\n"
            "Recommended: 100"
        )
        self.form.addRow("Epochs:",self.epochs)

        # advanced - confidence
        self.adv_conf = QDoubleSpinBox()
        self.adv_conf.setRange(0.1,1)
        self.adv_conf.setDecimals(2)
        self.adv_conf.setToolTip(
            "Minimum confidence threshold for predictions during validation.\n"
            "Lower values detect more objects, false positives. Higher values are stricter, may miss detections.\n"
            "Recommended: 0.25"
        )
        self.form.addRow("Confidence:",self.adv_conf)


        # advanced - Image size
        self.adv_imgsz = QSpinBox()
        self.adv_imgsz.setRange(320,1280)
        self.adv_imgsz.setSingleStep(32)
        self.adv_imgsz.setToolTip(
            "Image resolution for training.\n"
            "Higher values improve small object detection but increase training time and memory usage.\n"
            "Recommended: 640"
        )
        self.form.addRow("Image Size:",self.adv_imgsz)

        # advanced - batch size
        self.adv_batch = QSpinBox()
        self.adv_batch.setRange(1,64)
        self.adv_batch.setToolTip(
            "Number of images processed at once during training.\n"
            "Higher values increase training speed and required memory.\n"
            "Recommended: 8"
        )
        self.form.addRow("Batch Size:",self.adv_batch)

        # advanced - augment
        self.adv_augment = QCheckBox("")
        self.adv_augment.setToolTip(
            "Enable data augmentation (random flips, scaling, color changes).\n"
            "Improves generalization, especially with small datasets.\n"
            "Recommended: True"
        )
        self.form.addRow("Augmentation:",self.adv_augment)

        # advanced - multiscale
        self.adv_multiscale = QCheckBox("")
        self.adv_multiscale.setToolTip(
            "Randomly varies image size during training.\n"
            "Improves robustness to scale changes; slightly slows training.\n"
            "Recommended: False"
        )
        self.form.addRow("Multiscale:",self.adv_multiscale)

        self.advanced_widgets = [
            self.adv_conf,
            self.adv_imgsz,
            self.adv_batch,
            self.adv_augment,
            self.adv_multiscale
        ]

        for w in self.advanced_widgets:
            self.form.setRowVisible(w, False)

        # export render.json
        self.export_render_file = QCheckBox("")
        self.export_render_file.setToolTip(
            "Whether to export class labels and colors as a _render.json file.\n"
            "May be used to import render settings for Vision Projects.\n"
            "Recommended: True"
        )
        self.form.addRow("Export Render File:",self.export_render_file)

        # export location
        self.export_loc = QPushButton()
        self.export_loc.setToolTip(
            "Location where best.pt file is saved after training is complete.\n"
            "Best, last model files may be extracted from the saved Model Project file."
        )
        self.export_loc.clicked.connect(self.on_btn_export_loc)
        self.form.addRow("Save Location:",self.export_loc)

        # show/hide advanced button
        self.toggle_adv_btn = QPushButton("Show Advanced Settings")
        self.toggle_adv_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.toggle_adv_btn.setProperty("role","default")

        self.toggle_adv_btn.clicked.connect(self.on_btn_toggle_adv)

        self.content_layout.addWidget(self.toggle_adv_btn)

        # start training button
        train_btn = QPushButton("Start Training")
        train_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        train_btn.setProperty("role","default")

        train_btn.clicked.connect(self.on_btn_done)

        self.content_layout.addWidget(train_btn)

        # cancel button
        self.content_layout.addWidget(self.cancel_btn)

    #region Button Handlers
    def on_btn_base_model(self):
        logger.debug(f"Button Press - select Base Model.")
        project = self.controller.selected_project
        base_model_dir = Path(project.project_folder_path / "base_model")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Base Model",
            str(self.controller.models_path),
            "YOLO Model (*.pt);;All Files (*.*)"
        )

        if not file_path:
            return
        
        file_path = Path(file_path)

        # copy base model to dataset folder
        base_model_dir.mkdir(parents=True,exist_ok=True)

        for f in base_model_dir.iterdir():
            if f.is_file():
                f.unlink()

        stored_model_path = base_model_dir / file_path.name
        shutil.copy(file_path, stored_model_path)
        
        # save data
        self.base_model_btn.setText(stored_model_path.name)
        self.stored_file = stored_model_path

    def on_btn_export_loc(self):
        logger.debug(f"Button Press - select Export Location.")
        project = self.controller.selected_project

        start_dir = str(self.controller.models_path)
        if project and project.model_export_dir is not None and project.model_export_dir.exists():
            start_dir = str(project.model_export_dir)

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Trained Model Export Folder",
            start_dir
        )

        if not folder:
            return
        
        folder = Path(folder)
        
        self.export_loc.setText(folder.name)
        self.stored_folder = folder

    def on_btn_toggle_adv(self):
        logger.debug(f"Button Press - Toggle Advanced Settings.")
        new_visibility = not self.form.isRowVisible(self.advanced_widgets[0])

        for w in self.advanced_widgets:
            self.form.setRowVisible(w, new_visibility)

        self.toggle_adv_btn.setText("Hide Advanced Settings" if new_visibility else "Show Advanced Settings")

        self.adjustSize()

    #region Load/Save
    def load_from_project(self):
        prj = self.controller.selected_project
        if not prj:
            return

        self.stored_file = prj.base_model_path
        self.base_model_btn.setText(self.stored_file.name if self.stored_file and self.stored_file.exists() else "Select Base Model")

        self.epochs.setValue(prj.train_settings.get("epochs",100))
        self.adv_conf.setValue(prj.train_settings.get("conf",0.25))
        self.adv_imgsz.setValue(prj.train_settings.get("imgsz",640))
        self.adv_batch.setValue(prj.train_settings.get("batch_size",8))
        self.adv_augment.setChecked(prj.train_settings.get("augmentation",True))
        self.adv_multiscale.setChecked(prj.train_settings.get("multiscale",False))
        # self.adv_freeze.setChecked(prj.train_settings.get("freeze_backbone",False))

        self.export_render_file.setChecked(prj.train_settings.get("export_render_file",True))

        export_path = prj.train_settings.get("export_path")
        if export_path:
            self.stored_folder = Path(export_path)
        else:
            self.stored_folder = None

        if self.stored_folder and self.stored_folder.exists():
            self.export_loc.setText(self.stored_folder.name)
        else:
            self.export_loc.setText("Select Export Location")

    def save_to_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        prj.base_model_path = self.stored_file

        prj.train_settings["epochs"] = self.epochs.value()
        prj.train_settings["conf"] = self.adv_conf.value()
        prj.train_settings["imgsz"] = self.adv_imgsz.value()
        prj.train_settings["batch_size"] = self.adv_batch.value()
        prj.train_settings["augmentation"] = self.adv_augment.isChecked()
        prj.train_settings["multiscale"] = self.adv_multiscale.isChecked()
        # prj.train_settings["freeze_backbone"] = self.adv_freeze.isChecked()

        prj.train_settings["export_render_file"] = self.export_render_file.isChecked()
        prj.train_settings["export_path"] = str(self.stored_folder)
        prj.model_export_dir = self.stored_folder