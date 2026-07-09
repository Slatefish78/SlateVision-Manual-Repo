import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6 .QtCore import Qt

logger = logging.getLogger(__name__)

class Screen(QWidget):
    #region Init
    def __init__(self,header: str,parent = None,controller=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        layout.setSpacing(0)

        # header (no margins)
        self.header = QLabel(header)
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setProperty("role","screen_header")
        self.header.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

        layout.addWidget(self.header)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(
            controller.x_margin,
            controller.widget_spacing,
            controller.x_margin,
            controller.y_margin
        )
        self.content_layout.setSpacing(controller.widget_spacing)
        layout.addWidget(content_widget)

    def __repr__(self):
        return self.__class__.__name__

    def update_header(self,new_header):
        self.header.setText(new_header)