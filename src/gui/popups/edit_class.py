import logging

from PySide6.QtWidgets import QPushButton, QLineEdit, QSpinBox, QMessageBox, QColorDialog
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class EditClassPopup(SVPopup):
    #region Init
    def __init__(self, cls: dict, parent, controller, on_delete_callback = None, on_done_callback = None):
        super().__init__("Edit Class",parent,controller)
        
        self.cls = cls
        self.on_delete_callback = on_delete_callback
        self.on_done_callback = on_done_callback

        # flag project as being edited
        self.controller.selected_project.edited = True

        # class name string field
        self.name_input = QLineEdit()
        self.name_input.setToolTip("Display name of this annotation class.")
        self.content_layout.addWidget(self.name_input)
        
        # color preview/picker
        self.btn_color_pick = QPushButton("Pick Color")
        self.btn_color_pick.setStyleSheet("padding: 6px; background-color: rgb(0,0,0); border: 1px solid #000")
        self.btn_color_pick.clicked.connect(self.on_btn_pick_color)
        self.content_layout.addWidget(self.btn_color_pick)

        self.r_spin = QSpinBox()
        self.g_spin = QSpinBox()
        self.b_spin = QSpinBox()

        for spinbox in (self.r_spin,self.g_spin,self.b_spin):
            spinbox.setMinimum(0)
            spinbox.setMaximum(255)
            spinbox.setSingleStep(1)
            spinbox.valueChanged.connect(self.on_spinbox_change)
            self.content_layout.addWidget(spinbox)

        # delete button
        self.content_layout.addWidget(self.delete_btn)
        
        # done button
        self.content_layout.addWidget(self.done_btn)

        # cancel button
        self.content_layout.addWidget(self.cancel_btn)

    #region Save, Load, Update Color Preview
    def load_from_project(self):
        logger.debug(f"Loaded class data to edit: {self.cls}")

        self.name_input.setText(self.cls["name"])
        
        self.r_spin.setValue(int(self.cls["color"][1:3],16))
        self.g_spin.setValue(int(self.cls["color"][3:5],16))
        self.b_spin.setValue(int(self.cls["color"][5:7],16))

    def on_spinbox_change(self):
        r = self.r_spin.value()
        g = self.g_spin.value()
        b = self.b_spin.value()

        self.btn_color_pick.setStyleSheet(f"padding: 6px; background-color: rgb({r},{g},{b}); border: 1px solid #000")

    def save_to_project(self):
        self.cls["name"] = self.name_input.text()
        r = self.r_spin.value()
        g = self.g_spin.value()
        b = self.b_spin.value()
        self.cls["color"] = f"#{r:02x}{g:02x}{b:02x}"

        logger.debug(f"Saved edited class data: {self.cls}")

    #region Button Handlers  
    def on_btn_pick_color(self):
        logger.debug(f"Button Press - pick color.")
        color = QColorDialog.getColor()

        if color.isValid():
            r,g,b,_ = color.getRgb()

            self.btn_color_pick.setStyleSheet(f"padding: 6px; background-color: rgb({r},{g},{b}); border: 1px solid #000")

            self.r_spin.setValue(r)
            self.g_spin.setValue(g)
            self.b_spin.setValue(b)

    def on_btn_delete(self):
        logger.debug(f"Button Press - Delete class.")

        if self.on_delete_callback and self.on_delete_callback(self.cls):
            self.accept()

    def on_btn_done(self):
        logger.debug(f"Button Press - Done with edit.")
        self.save_to_project()

        if self.on_done_callback is not None:
            self.on_done_callback(self.cls)

        self.accept()