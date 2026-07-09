import logging
import threading

from PySide6.QtWidgets import QComboBox, QFormLayout, QPushButton, QLineEdit, QSizePolicy, QMessageBox
from PySide6.QtCore import Signal
from core.vision_project import VisionProject
from gui.popups.loading import LoadingPopup
from gui.popups.sv_popup import SVPopup
from pycomm3 import LogixDriver, SLCDriver
from util.plc_communication import connect_driver

logger = logging.getLogger(__name__)

class EditPlcSignalPopup(SVPopup):

    plc_test_return = Signal(bool)

    #region Init
    def __init__(self, signal: dict, parent, controller):
        super().__init__("Edit Signal",parent,controller)
        
        self.signal = signal

        # flag project as being edited
        self.controller.selected_project.edited = True

        self.form = QFormLayout()
        self.form.setContentsMargins(9,0,9,9)
        self.form.setSpacing(10)
        self.content_layout.addLayout(self.form)

        # type dropdown field
        self.type_dropdown = QComboBox()
        self.type_dropdown.addItems(VisionProject.PLC_SIGNAL_TYPES)
        self.type_dropdown.currentTextChanged.connect(self.on_type_change)
        self.form.addRow("Signal Type:",self.type_dropdown)

        # tag name string field
        self.tag_input = QLineEdit()
        self.tag_input.setToolTip("Name of the plc tag to which to write.")
        self.form.addRow("Tag Name:",self.tag_input)

        # value dropdown field
        self.value_dropdown = QComboBox()
        self.form.addRow("Value:",self.value_dropdown)
        
        # test button
        test_btn = QPushButton("Test Connection")
        test_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        test_btn.clicked.connect(self.on_btn_test)
        test_btn.setProperty("role","default")

        self.content_layout.addWidget(test_btn)

        # delete button
        self.content_layout.addWidget(self.delete_btn)
        
        # done button
        self.content_layout.addWidget(self.done_btn)

        # cancel button
        self.content_layout.addWidget(self.cancel_btn)

    #region Save, Load, Update Color Preview
    def load_from_project(self):
        logger.debug(f"Loaded signal to edit: {self.signal}")

        type_index = self.type_dropdown.findText(self.signal["type"])
        if type_index >= 0:
            self.type_dropdown.setCurrentIndex(type_index)

        self.on_type_change(self.type_dropdown.currentText())

        self.tag_input.setText(self.signal["tag"])

        value_index = self.value_dropdown.findData(self.signal["value"])
        if value_index >= 0:
            self.value_dropdown.setCurrentIndex(value_index)

    def save_to_project(self):
        self.signal["type"] = self.type_dropdown.currentText()
        self.signal["tag"] = self.tag_input.text()
        self.signal["value"] = self.value_dropdown.currentData()

        logger.debug(f"Saved edited signal: {self.signal}")

    def on_type_change(self,new_type):
        self.value_dropdown.clear()
        self.form.setRowVisible(2, False)
        match new_type:
            case "Running Indicator":
                self.value_dropdown.addItem("None",None)
            case "Trigger Bit":
                self.value_dropdown.addItem("None",None)
            case "Output Bit":
                for i, parameter in enumerate(self.controller.selected_project.parameters):
                    self.value_dropdown.addItem(parameter.name,i)
                    self.form.setRowVisible(2, True)
            case _:
                self.value_dropdown.addItem("Error - Invalid Type", None)

    #region Button Handlers
    def on_btn_test(self):
        print(f"testing signal {self.signal}")

        logger.debug(f"Button Press - Test PLC Connection.")
        
        # test connection to plc
        load_popup = LoadingPopup(
            "PLC Comm Test",
            self,
            self.controller,
            "Testing PLC connection..."
        )

        def on_test_finish(success: bool):
            load_popup.accept()

            if success:
                QMessageBox.information(
                    self,
                    "PLC Test Success",
                    "PLC communications test was successful!"
                )
            else:
                QMessageBox.information(
                    self,
                    "PLC Test Failure",
                    "Communications test failed."
                )

        self.plc_test_return.disconnect()
        self.plc_test_return.connect(on_test_finish)

        threading.Thread(
            target=self.test_plc,
            daemon=True
        ).start()

        load_popup.exec()

    #region PLC Test
    def test_plc(self):
        ip = self.controller.selected_project.plc_ip
        tag = self.tag_input.text().strip()
        print(f"Testing connection to tag {tag} on ip {ip}")
        plc = connect_driver(ip)
        if not plc:
            print("Failed driver connection.")
            self.plc_test_return.emit(False)
            return
        
        with plc:
            result = plc.read(tag)
            print(f"Read tag: {result}")

        if result:
            print(f"Comm test success")
            self.plc_test_return.emit(True)
        else:
            print("Comm test failure")
            self.plc_test_return.emit(False)

    def on_btn_delete(self):
        logger.debug(f"Button Press - Delete signal.")

        delete_confirmation = QMessageBox.question(
            self,
            "Delete PLC Signal",
            "Are you sure you want to delete this PLC signal?",
            QMessageBox.Yes | QMessageBox.No
        )

        if delete_confirmation == QMessageBox.Yes:
            self.controller.selected_project.plc_map.remove(self.signal)
            self.accept()