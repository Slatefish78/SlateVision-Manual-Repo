import logging

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QSizePolicy, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.vision_parameter import VisionParameter
from gui.popups.edit_vision_param import EditParamPopup
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class VisionParametersPopup(SVPopup):
    #region Init
    def __init__(self, parent=None, controller=None):
        super().__init__("Vision Parameters",parent,controller)

        # parameter list
        self.param_list = QListWidget()

        font = QFont()
        font.setPointSize(12)
        self.param_list.setFont(font)
        
        self.param_list.setMinimumWidth(180)
        self.param_list.setFixedHeight(250)
        self.param_list.itemClicked.connect(self.on_btn_edit_param)

        self.content_layout.addWidget(self.param_list)

        # Add button
        add_btn = QPushButton("Add Vision Parameter")
        add_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        add_btn.setProperty("role","default")

        add_btn.clicked.connect(self.on_btn_add_param)

        self.content_layout.addWidget(add_btn)
        
        # done button
        self.content_layout.addWidget(self.done_btn)

    #region Button Handlers
    def on_btn_add_param(self):
        logger.debug(f"Button Press - Add new parameter")
        self.controller.selected_project.parameters.append(VisionParameter(
            name="New Vision Parameter",
            value="score"
        ))

        EditParamPopup(self.controller.selected_project.parameters[-1],self,self.controller).exec()

        self.load_from_project()

    def on_btn_edit_param(self,param_item):
        cur_param = param_item.data(Qt.UserRole)

        logger.debug(f"Button Press - Edit parameter: {cur_param}")

        EditParamPopup(cur_param,self,self.controller).exec()
        self.load_from_project()

    def load_from_project(self):
        # remove current widgets
        self.param_list.clear()

        # add current parameters
        for param in self.controller.selected_project.parameters:

            param_item = QListWidgetItem()
            param_item.setText(param.name)
            param_item.setData(Qt.UserRole,param)
            param_item.setTextAlignment(Qt.AlignCenter)
            self.param_list.addItem(param_item)

        logger.debug(f"Updated parameter list: {self.controller.selected_project.parameters}")