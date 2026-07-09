import logging

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QDoubleSpinBox, QSizePolicy, QPushButton, QLineEdit, QFormLayout, QComboBox, QMessageBox
from PySide6.QtCore import Qt
from core.vision_parameter import VisionParameter
from core.vision_tool import VisionTool
from gui.popups.selection_list import SelectionListPopup
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class EditParamPopup(SVPopup):
    #region Init
    def __init__(self, param: VisionParameter, parent: QWidget, controller):
        super().__init__("Edit Vision Parameter",parent,controller)
        
        self.controller.selected_project.edited = True

        self.param = param

        self.form = QFormLayout()
        self.form.setContentsMargins(9,0,9,9)
        self.form.setSpacing(10)

        # parameter name field
        self.name_input = QLineEdit()
        # self.name_input.setStyleSheet("text-align: right;")
        self.name_input.setToolTip("Name of the Vision Parameter. Used for display and rendering.")
        self.form.addRow("Name:",self.name_input)

        # select value field (dropdown)
        self.value_dropdown = QComboBox()
        self.value_dropdown.setToolTip("Select value criterion to be used by the Vision Parameter.")

        self.value_dropdown.addItems(VisionParameter.MEASUREMENT_VALUES)
        self.value_dropdown.addItems(VisionParameter.LOGICAL_VALUES)

        self.form.addRow("Value:",self.value_dropdown)

        # inputs field        
        self.input_list = QListWidget()
        self.input_list.itemClicked.connect(self.on_btn_remove_input)
        self.input_list.setToolTip("Click an input to delete.")
        self.input_list.setMaximumHeight(75)
        self.form.addRow("Input(s):",self.input_list)

        # add input button
        add_input_btn = QPushButton("Add Input")
        add_input_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        add_input_btn.setProperty("role","default")

        add_input_btn.clicked.connect(self.on_btn_add_input)

        self.form.addRow("",add_input_btn)
        
        # thresholds
        self.thresh_low = QDoubleSpinBox()
        self.thresh_low.valueChanged.connect(self.on_thresh_low_change)
        self.form.addRow("Low Threshold:",self.thresh_low)
        self.thresh_high = QDoubleSpinBox()
        self.thresh_high.valueChanged.connect(self.on_thresh_high_change)
        self.form.addRow("High Threshold:",self.thresh_high)

        self.content_layout.addLayout(self.form)

        # buttons
        self.content_layout.addWidget(self.delete_btn)
        self.content_layout.addWidget(self.done_btn)
        self.content_layout.addWidget(self.cancel_btn)

        # connect value change signal
        self.value_dropdown.currentTextChanged.connect(self.on_value_change)

    #region Save/Load
    def load_from_project(self):
        logger.debug(f"Loaded parameter data to edit: {self.param}")

        self.name_input.setText(self.param.name)
        value_index = self.value_dropdown.findText(self.param.value)
        self.value_dropdown.setCurrentIndex(value_index)
        self.on_value_change(self.value_dropdown.currentText())

        # clear inputs
        self.input_list.clear()

        if self.param.is_measurement():
            # measurement parameters have a single tool input and thresholds
            if self.param.tool_input is not None:
                tool_item = QListWidgetItem(self.param.tool_input.name)
                tool_item.setData(Qt.UserRole, self.param.tool_input)
                self.input_list.addItem(tool_item)
            if self.param.thresh_low is not None:
                self.thresh_low.setValue(self.param.thresh_low)
            if self.param.thresh_high is not None:
                self.thresh_high.setValue(self.param.thresh_high)

        elif self.param.is_logical():
            # logical parameters have multiple parameter inputs and no thresholds
            if self.param.param_inputs:
                for param_input in self.param.param_inputs:
                    param_item = QListWidgetItem(param_input.name)
                    param_item.setData(Qt.UserRole, param_input)
                    self.input_list.addItem(param_item)

        # update displayed values
        self.on_thresh_low_change(self.thresh_low.value())
        self.on_thresh_high_change(self.thresh_high.value())

    def save_to_project(self):    
        self.param.name = self.name_input.text()
        self.param.value = self.value_dropdown.currentText()

        if self.param.is_measurement():
            self.param.set_measurement_attributes(
                tool_input=self.input_list.item(0).data(Qt.UserRole),
                thresh_low=self.thresh_low.value(),
                thresh_high=self.thresh_high.value()
            )

        if self.param.is_logical():
            self.param.set_logical_attributes(
                param_inputs=[self.input_list.item(i).data(Qt.UserRole) for i in range(self.input_list.count())]
            )

        logger.debug(f"Saved edited parameter data: {self.param}")

    #region Button Handlers
    def on_btn_add_input(self):
        logger.debug(f"Button Press - Add parameter input.")
        if self.value_dropdown.currentText() in VisionParameter.MEASUREMENT_VALUES:
            tool_options = [(tool.name,tool) for tool in self.controller.selected_project.tools]
            selected_tool = SelectionListPopup.get_selection(
                self,
                self.controller,
                "Select Vision Tool Input",
                tool_options
            )

            if not selected_tool:
                return

            # insert new item at 0
            tool_item = QListWidgetItem(selected_tool.name)
            tool_item.setData(Qt.UserRole,selected_tool)
            self.input_list.insertItem(0,tool_item)

            # remove any items after 0
            for i in range(self.input_list.count() - 1, 0, -1):
                self.input_list.takeItem(i)

        elif self.value_dropdown.currentText() in VisionParameter.LOGICAL_VALUES:
            param_options = [
                (param.name,param) for param in self.controller.selected_project.parameters if param != self.param
                and param not in [self.input_list.item(i).data(Qt.UserRole) for i in range(self.input_list.count())]
                ]
            selected_param = SelectionListPopup.get_selection(
                self,
                self.controller,
                "Select Vision Parameter Input",
                param_options
            )

            if not selected_param:
                return

            # append new item
            param_item = QListWidgetItem(selected_param.name)
            param_item.setData(Qt.UserRole,selected_param)
            self.input_list.addItem(param_item)

    def on_btn_remove_input(self,item):
        logger.debug(f"Button Press - remove parameter input.")
        row = self.input_list.row(item)
        self.input_list.takeItem(row)

    def on_btn_delete(self):
        logger.debug(f"Button Press - Delete parameter.")
        delete_confirmation = QMessageBox.question(
            self,
            "Delete Vision Tool",
            f"Are you sure you want to delete {self.param.name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if delete_confirmation == QMessageBox.Yes:
            self.controller.selected_project.parameters.remove(self.param)
            self.parent().load_from_project()
            self.accept()

    def on_btn_done(self):
        logger.debug(f"Button Press - Done editing parameter.")
        # verify an input is selected
        if self.input_list.count() == 0:
            QMessageBox.warning(
                self,
                "Missing Parameter Input",
                "A vision parameter requires at least one input. Please add an input to the inputs list."
            )
            return
        
        self.save_to_project()
        self.accept()

    def on_btn_cancel(self):
        logger.debug(f"Button Press - Cancel editing vision parameter.")
        # verify model selected
        if not self.param.tool_input and not self.param.param_inputs and self.input_list.count() < 1:
            QMessageBox.warning(
                self,
                "Missing Parameter Input",
                "A vision parameter requires at least one input. Please add an input from the project."
            )
            return
        
        self.reject()

    #region Change Callback
    def on_value_change(self, new_value):
        if new_value in VisionParameter.MEASUREMENT_VALUES:
            # show thresholds
            self.form.setRowVisible(self.thresh_low,True)
            self.form.setRowVisible(self.thresh_high,True)

            # set threshold max/min
            self.thresh_low.setMinimum(0)
            self.thresh_high.setMaximum(1)
            self.thresh_low.setDecimals(2)
            self.thresh_high.setDecimals(2)
            self.thresh_low.setSingleStep(0.01)
            self.thresh_high.setSingleStep(0.01)

            if new_value == "class" or new_value == "count":
                self.thresh_high.setMaximum(100)
                self.thresh_low.setDecimals(0)
                self.thresh_high.setDecimals(0)
                self.thresh_low.setSingleStep(1)
                self.thresh_high.setSingleStep(1)

            # remove parameter inputs
            for i in range(self.input_list.count() - 1, -1, -1):
                if isinstance(self.input_list.item(i).data(Qt.UserRole),VisionParameter):
                    self.input_list.takeItem(i)

            # keep only single input
            for i in range(self.input_list.count() - 1, 0, -1):
                self.input_list.takeItem(i)
            
        elif new_value in VisionParameter.LOGICAL_VALUES:
            # hide thresholds
            self.form.setRowVisible(self.thresh_low,False)
            self.form.setRowVisible(self.thresh_high,False)
            self.thresh_low.setValue(0)
            self.thresh_high.setValue(0)

            # remove tool inputs
            for i in range(self.input_list.count() - 1, -1, -1):
                if isinstance(self.input_list.item(i).data(Qt.UserRole),VisionTool):
                    self.input_list.takeItem(i)

    def on_thresh_low_change(self, new_value):
        self.thresh_high.setMinimum(new_value)

    def on_thresh_high_change(self, new_value):
        self.thresh_low.setMaximum(new_value)