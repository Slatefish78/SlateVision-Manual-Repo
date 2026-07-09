import logging

from PySide6.QtWidgets import QPushButton, QLabel
from gui.screens.screen import Screen

logger = logging.getLogger(__name__)

class InfoScreen(Screen):
    #region Init
    def __init__(self,parent=None,controller=None):
        super().__init__("App Info",parent,controller)

        info_text = QLabel("App: SlateVision Utility \nVersion: 2.0 \nLicense: AGPL-3.0 \nDeveloped by Sam Gordon, 2026. \nAI Assistance: ChatGPT, troubleshooting/learning tool. Any AI generated code copied manually to foster personal understanding. \nAim #2: I will Create and not merely Consume. \nThis project utilizes code from [Ultralytics YOLO](https://github.com/ultralytics/ultralytics), licensed under AGPL-3.0.")
        self.content_layout.addWidget(info_text)

        self.content_layout.addStretch()

        # back button
        btn = QPushButton("Back")

        btn.setProperty("role","default")

        btn.clicked.connect(self.on_btn_back)
        self.content_layout.addWidget(btn)

    #region Button Handlers




    #region Quit
    def on_btn_back(self):
        logger.debug(f"Button Press - Back to main menu.")
        self.controller.root.show_screen("menu")