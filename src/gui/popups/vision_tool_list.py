import logging

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QSizePolicy, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.vision_tool import DetectTool
from gui.popups.edit_vision_tool import EditToolPopup
from gui.popups.selection_list import SelectionListPopup
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class VisionToolsPopup(SVPopup):
    #region Init
    def __init__(self, camera, parent=None, controller=None):
        super().__init__("Vision Tools",parent,controller)

        self.camera = camera

        # tool list
        self.tool_list = QListWidget()

        font = QFont()
        font.setPointSize(12)
        self.tool_list.setFont(font)
        
        self.tool_list.setMinimumWidth(180)
        self.tool_list.setFixedHeight(250)
        self.tool_list.itemClicked.connect(self.on_btn_edit_tool)

        self.content_layout.addWidget(self.tool_list)

        # Add button
        add_btn = QPushButton("Add Vision Tool")
        add_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        add_btn.setProperty("role","default")

        add_btn.clicked.connect(self.on_btn_add_vision_tool)

        self.content_layout.addWidget(add_btn)
        
        # done button
        self.content_layout.addWidget(self.done_btn)

    #region Button Handlers
    def on_btn_add_vision_tool(self):
        logger.debug(f"Button press - Add Vision Tool.")
        # check number of vision tools
        if len(self.controller.selected_project.tools) >= self.controller.max_tools_per_project:
            QMessageBox.warning(self,"Max Tool Count", f"The maximum number of vision tools per project ({self.controller.max_tools_per_project}) has been reached. Please delete or edit an existing vision tool.")
            return

        num_cam_tools = sum(
            1 for tool in self.controller.selected_project.tools
            if tool.camera == self.camera
        )

        if num_cam_tools >= self.controller.max_tools_per_camera:
            QMessageBox.warning(self,"Max Tool Count",f"The maximum number of vision tools per camera ({self.controller.max_tools_per_camera}) has been reached. Please delete or edit an existing vision tool on this camera.")
            return

        TOOLTYPES = [
            ("Detect","detect"),
            ("Classify (not implemented)","classify")
        ]

        selected_tool_type = None

        # make a sub-popup that allows for adding different types of tools
        selected_tool_type = SelectionListPopup.get_selection(
            self,
            self.controller,
            "Select Tool Type",
            TOOLTYPES
        )

        # add a tool based on selected type
        if selected_tool_type is not None:
            tool_cam = self.camera
            tool_render_settings = {
                "box": True,
                "label":False,
                "class":False,
                "class_id":False,
                "score":False,
                "label_line":False,
                "label_loc": "BTL"
            }
            match selected_tool_type:
                case "detect":
                    self.controller.selected_project.tools.append(DetectTool("New Detect Tool",tool_cam,tool_render_settings, None))
                    EditToolPopup(self.controller.selected_project.tools[-1],self.parent(),self.controller).exec()
                    self.load_from_project()
                case _:
                    print(f"Invalid type: {selected_tool_type}")
                    raise RuntimeError("Invalid tool type")

    def on_btn_edit_tool(self,tool_item):
        cur_tool = tool_item.data(Qt.UserRole)

        logger.debug(f"Button Press - Edit tool: {cur_tool}")

        EditToolPopup(cur_tool,self,self.controller).exec()

        self.load_from_project()

    def load_from_project(self):
        # remove current widgets
        self.tool_list.clear()

        # add tools for this camera
        for tool in self.controller.selected_project.tools:
            if tool.camera == self.camera:
                tool_item = QListWidgetItem()
                tool_item.setText(tool.name)
                tool_item.setData(Qt.UserRole,tool)
                tool_item.setTextAlignment(Qt.AlignCenter)
                self.tool_list.addItem(tool_item)

        logger.debug(f"Updated tool list: {self.controller.selected_project.tools}")