import logging

from PySide6.QtWidgets import QPushButton, QLineEdit, QFormLayout, QListWidget, QListWidgetItem, QSizePolicy
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QFont
from gui.popups.edit_plc_signal import EditPlcSignalPopup
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class PlcSignalsPopup(SVPopup):
    #region Init
    def __init__(self, parent, controller):
        super().__init__("PLC Signals",parent,controller)

        form = QFormLayout()
        form.setContentsMargins(9,0,9,9)
        form.setSpacing(10)
        self.content_layout.addLayout(form)

        # plc ip field
        self.plc_ip_input = QLineEdit()
        ip_regex = QRegularExpression(r"^(\d{1,3}\.){3}\d{1,3}$")
        self.plc_ip_input.setValidator(QRegularExpressionValidator(ip_regex))
        self.plc_ip_input.setPlaceholderText("255.255.255.255")
        self.plc_ip_input.setToolTip("IP address of PLC to communicate with (e.g. 192.168.1.2).")
        form.addRow("PLC IP Address:",self.plc_ip_input)

        # parameter list
        self.signal_list = QListWidget()

        # font = QFont()
        # font.setPointSize(12)
        # self.signal_list.setFont(font)
        
        self.signal_list.setMinimumWidth(180)
        self.signal_list.setFixedHeight(250)
        self.signal_list.itemClicked.connect(self.on_btn_edit_signal)

        self.content_layout.addWidget(self.signal_list)

        # Add button
        add_btn = QPushButton("Add PLC Signal")
        add_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        add_btn.setProperty("role","default")

        add_btn.clicked.connect(self.on_btn_add_signal)

        self.content_layout.addWidget(add_btn)
        
        # done button
        self.content_layout.addWidget(self.done_btn)

    #region Save/Load
    def load_from_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        logger.debug(f"Loaded PLC signal data to edit.")
        
        self.plc_ip_input.setText(prj.plc_ip)

        self.signal_list.clear()

        for i, signal in enumerate(prj.plc_map):
            signal_text = f"{signal['tag']} ... "
            if signal["type"] == "Running Indicator" or signal["type"] == "Trigger Bit":
                signal_text += signal["type"]
            else:
                if isinstance(signal["value"],int):
                    signal_text += prj.parameters[signal["value"]].name
                    signal_text += ".passes"

            signal_item = QListWidgetItem(signal_text)
            signal_item.setData(Qt.UserRole,i)
            signal_item.setTextAlignment(Qt.AlignCenter)
            self.signal_list.addItem(signal_item)

    def save_to_project(self):
        prj = self.controller.selected_project
        if not prj:
            return
        
        prj.plc_ip = self.plc_ip_input.text().strip()

        logger.debug(f"Saved edited PLC signal data: (plc_ip={prj.plc_ip},plc_map={prj.plc_map})")

    #region Button Handlers
    def on_btn_add_signal(self):
        logger.debug(f"Button Press - Add new PLC Signal")

        self.controller.selected_project.plc_map.append(
            {
                "type": "",
                "tag": "",
                "value": None
            }
        )

        EditPlcSignalPopup(self.controller.selected_project.plc_map[-1],self,self.controller).exec()

        self.load_from_project()

    def on_btn_edit_signal(self,signal_item):
        signal_index = signal_item.data(Qt.UserRole)
        cur_signal = self.controller.selected_project.plc_map[signal_index]

        logger.debug(f"Button Press - Edit parameter: {cur_signal}")

        EditPlcSignalPopup(cur_signal,self,self.controller).exec()
        self.load_from_project()