import json
import logging
from pathlib import Path
import shutil

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel, QSizePolicy, QPushButton, QFileDialog, QLineEdit, QFormLayout, QComboBox, QCheckBox, QMessageBox
from PySide6.QtGui import QColor
from gui.popups.edit_class import EditClassPopup
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class EditToolPopup(SVPopup):
    RENDER_SETTINGS = ["box","label","class","class_id","score","label_line"]
    MODEL_TYPES = {".pt",".onnx",".ncnn"}

    #region Init
    def __init__(self, tool, parent=None, controller=None):
        super().__init__("Edit Vision Tool",parent,controller)

        self.tool = tool

        form = QFormLayout()
        form.setContentsMargins(9,0,9,9)
        form.setSpacing(10)

        # tool name field
        self.name_input = QLineEdit()
        self.name_input.setToolTip("Name of the Vision Tool. Used for display and rendering.")
        form.addRow("Name:",self.name_input)

        # tool type display
        tool_type_label = QLabel(self.tool.tool_type)
        form.addRow("Tool Type:",tool_type_label)

        # select model field (dropdown)
        self.model_dropdown = QComboBox()
        self.model_dropdown.setToolTip("Select a model for the Detect Tool.")

        model_options = [f.name for f in self.controller.selected_project.model_path.iterdir() if f.suffix.lower() in self.MODEL_TYPES or f.is_dir()]

        self.model_dropdown.addItems(model_options)

        form.addRow("Model:",self.model_dropdown)

        # import model buttons
        import_file_btn = QPushButton("Import Model File")
        import_file_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        import_file_btn.setProperty("role","default")

        import_file_btn.clicked.connect(self.on_btn_import_file)

        form.addRow("",import_file_btn)

        import_folder_btn = QPushButton("Import Model Folder")
        import_folder_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        import_folder_btn.setProperty("role","default")

        import_folder_btn.clicked.connect(self.on_btn_import_folder)

        form.addRow("",import_folder_btn)

        # render settings
        form.addRow("Render Settings:",None)

        # class rendering
        self.classes_list = QListWidget()
        self.classes_list.setToolTip(
            "Click a Class to edit."
        )
        # self.classes_list.setStyleSheet(f"""
        #     QListWidget::item {{
        #         padding: 0px;
        #         margin: 0px;         
        #     }}
        # """)
        self.classes_list.setSpacing(0)
        self.classes_list.setMaximumWidth(160)
        self.classes_list.itemClicked.connect(self.on_btn_edit_class)
        form.addRow("Classes:",self.classes_list)

        import_render_btn = QPushButton("Import Render File")
        import_render_btn.clicked.connect(self.on_btn_import_render_file)
        import_render_btn.setProperty("role","default")
        form.addRow("",import_render_btn)
        add_class_btn = QPushButton("Add Class Render")
        add_class_btn.clicked.connect(self.on_btn_add_class)
        add_class_btn.setProperty("role","default")
        form.addRow("",add_class_btn)

        render_setting_labels = [
            ("Object Box:"),
            ("Tool Label:"),
            ("Found Class Name:"),
            ("Found Class ID:"),
            ("Confidence Score (%):"),
            ("Line to Label:")
        ]

        self.render_settings = {}
        for field,label in zip(self.RENDER_SETTINGS,render_setting_labels):
            self.render_settings[field] = QCheckBox()
            form.addRow(label,self.render_settings[field])

        # label location field (dropdown)
        self.label_loc_dropdown = QComboBox()
        self.label_loc_dropdown.setToolTip("Where to render the label (if any label items are to be rendered).")

        locations = [
            ("Box Top Left","BTL"),
            ("Box Top Right","BTR"),
            ("Box Bottom Left","BBL"),
            ("Box Bottom Right","BBR"),
            ("Box Center","BC"),
            ("Screen Top Left","ATL"),
            ("Screen Top Right","ATR"),
            ("Screen Bottom Left","ABL"),
            ("Screen Bottom Right","ABR"),
            ("Screen Center","AC")
        ]

        for text, code in locations:
            self.label_loc_dropdown.addItem(text,code)

        form.addRow("Label Location:",self.label_loc_dropdown)

        self.content_layout.addLayout(form)

        # buttons
        self.content_layout.addWidget(self.delete_btn)
        self.content_layout.addWidget(self.done_btn)
        self.content_layout.addWidget(self.cancel_btn) 

        self.class_render_list = []

    #region Save/Load
    def load_from_project(self):
        logger.debug(f"Loaded tool data to edit: {self.tool}")

        self.name_input.setText(self.tool.name)

        model_index = self.model_dropdown.findText(self.tool.model_name)
        if model_index >= 0:
            self.model_dropdown.setCurrentIndex(model_index)

        for field in self.RENDER_SETTINGS:
            self.render_settings[field].setChecked(self.tool.render_settings[field])

        label_loc_index = self.label_loc_dropdown.findData(self.tool.render_settings["label_loc"])
        if label_loc_index >= 0:
            self.label_loc_dropdown.setCurrentIndex(label_loc_index)

        if "render_classes" not in self.tool.render_settings:
            self.tool.render_settings["render_classes"] = []
        self.class_render_list = self.tool.render_settings["render_classes"]
        
        self.update_class_list()

    def save_to_project(self):
        self.tool.name = self.name_input.text()

        self.tool.set_model(self.controller.selected_project.model_path / self.model_dropdown.currentText())
            
        for field in self.RENDER_SETTINGS:
            self.tool.render_settings[field] = self.render_settings[field].isChecked()
        self.tool.render_settings["label_loc"] = self.label_loc_dropdown.currentData()

        self.tool.render_settings["render_classes"] = self.class_render_list

        logger.debug(f"Saved edited tool data: {self.tool}")

    def update_class_list(self,passed_data=None):
        self.classes_list.clear()

        for i, cls in enumerate(self.class_render_list):
            item = QListWidgetItem(f"{i} - {cls['name']}")
            item.setForeground(QColor(cls["color"]))
            self.classes_list.addItem(item)

    #region Button Handlers
    def on_btn_import_file(self):
        logger.debug(f"Button Press - Import Model File")
        model_filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File to Import",
            "",
            "Pytorch model (*.pt);;ONNX model (*.onnx);;All Files (*.*)"
        )

        if not model_filepath:
            return
        
        # copy file to models folder
        model_filepath = Path(model_filepath)
        self.controller.selected_project.model_path.mkdir(parents=True,exist_ok=True)
        dest_path = self.controller.selected_project.model_path / model_filepath.name
        shutil.copy(model_filepath,dest_path)

        # update dropdown list
        self.model_dropdown.addItem(model_filepath.name)

    def on_btn_import_folder(self):
        logger.debug(f"Button Press - Import Model Folder")
        model_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Model Folder to Import",
            ""
        )

        if not model_folder:
            return
        
        # copy folder to models folder
        model_folder = Path(model_folder)
        self.controller.selected_project.model_path.mkdir(parents=True,exist_ok=True)
        dest_path = self.controller.selected_project.model_path / model_folder.name
        shutil.copytree(model_folder,dest_path)

        # update dropdown list
        self.model_dropdown.addItem(model_folder.name)

    def delete_class(self,cls):
        self.class_render_list.remove(cls)
        self.classes_list.takeItem(self.classes_list.currentRow())
        return True
    
    def on_btn_edit_class(self,item):
        logger.debug(f"Button Press - edit render class.")
        cls = self.class_render_list[self.classes_list.currentRow()]

        EditClassPopup(
            cls=cls,
            parent=self,
            controller=self.controller,
            on_delete_callback=self.delete_class,
            on_done_callback=self.update_class_list).exec()

    def on_btn_import_render_file(self):
        logger.debug(f"Button Press - Import Render File.")
        render_filepath,_ = QFileDialog.getOpenFileName(
            self,
            "Select Render Settings File to Import",
            "",
            "JSON File (*.json);;All Files (*.*)"
        )

        if not render_filepath:
            return
        
        # read json file
        with open(render_filepath, "r", encoding="utf-8") as f:
            new_classes = json.load(f)

        # load new classes into stored classes
        self.class_render_list = new_classes

        self.update_class_list()

    def on_btn_add_class(self):
        logger.debug(f"Button Press - Add Class.")

        self.class_render_list.append(
            {
                "name": "New Class",
                "color": "#909090"
            }
        )

        EditClassPopup(
            cls=self.class_render_list[-1],
            parent=self,
            controller=self.controller,
            on_delete_callback=self.delete_class,
            on_done_callback=self.update_class_list).exec()

    def delete_class(self,cls):
        self.class_render_list.remove(cls)
        self.classes_list.takeItem(self.classes_list.currentRow())
        return True

    def on_btn_delete(self):
        logger.debug(f"Button Press - Delete vision tool.")

        quit_confirmation = QMessageBox.question(
            self,
            "Delete Vision Tool",
            f"Are you sure you want to delete {self.tool.name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if quit_confirmation == QMessageBox.Yes:
            self.controller.selected_project.tools.remove(self.tool)
            self.accept()

    def on_btn_done(self):
        logger.debug(f"Button Press - Done editing vision tool.")
        # verify model selected
        if self.model_dropdown.currentIndex() < 0:
            QMessageBox.warning(
                self,
                "Missing Tool Model",
                "A vision tool requires a model. Please import or select a model from the project."
            )
            return
        
        self.save_to_project()
        self.accept()

    def on_btn_cancel(self):
        logger.debug(f"Button Press - Cancel editing vision tool.")
        # verify model selected
        if self.model_dropdown.currentIndex() < 0:
            QMessageBox.warning(
                self,
                "Missing Tool Model",
                "A vision tool requires a model. Please import or select a model from the project."
            )
            return
        
        self.reject()