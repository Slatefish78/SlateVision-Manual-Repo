import logging

from PySide6.QtWidgets import QLabel, QProgressBar
from PySide6.QtCore import Qt
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class LoadingPopup(SVPopup):
    def __init__(self,title,parent,controller,message="Please wait..."):
        super().__init__(title,parent,controller)

        self.message = QLabel(message)
        self.message.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.message)

        self.progress = QProgressBar()
        self.progress.setRange(0,0)
        self.content_layout.addWidget(self.progress)

    def update(self,message: str=None, min: int=None, max: int=None, value: int=None):
        if message is not None:
            self.message.setText(message)
        if min is not None:
            self.progress.setMinimum(min)
        if max is not None:
            self.progress.setMaximum(max)
        if value is not None:
            self.progress.setValue(value)

    def close(self):
        self.progress.setRange(0,1)
        super().close()