import logging

from PySide6.QtWidgets import QPushButton, QWidget, QDialog, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class SVPopup(QDialog):
    #region Init
    def __init__(self, title:str, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.title = title

        self.setWindowTitle(title)

        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.setFixedWidth(300)
        self.setMaximumHeight(800)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        # header
        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header.setProperty("role","popup_header")
        header.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        layout.addWidget(header)

        # contents
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(9,0,9,9)
        self.content_layout.setSpacing(0)
        layout.addWidget(content_widget)

        self.finished.connect(lambda: logger.debug(f"Closing popup {self}."))

        # common buttons (added by children)
        self.delete_btn = QPushButton("Delete")
        self.done_btn = QPushButton("Done")
        self.cancel_btn = QPushButton("Cancel")

        for btn in (self.delete_btn,self.done_btn,self.cancel_btn):
            btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            btn.setProperty("role","default")

        self.delete_btn.clicked.connect(self.on_btn_delete)
        self.done_btn.clicked.connect(self.on_btn_done)
        self.cancel_btn.clicked.connect(self.on_btn_cancel)

        logger.debug(f"Created popup {self}.")

    def __repr__(self):
        return f"{self.__class__.__name__}(title={self.title})"

    #region Events
    def showEvent(self, event):
        super().showEvent(event)

        # populate values from project
        self.load_from_project()

        # center on screen
        if self.parent():
            self.move(
                self.parent().geometry().center() - self.rect().center()
            )

    def on_btn_delete(self):
        # implemented by children
        pass

    def on_btn_done(self):
        logger.debug(f"Button Press - Done on {self}")
        self.save_to_project()
        self.accept()

    def on_btn_cancel(self):
        logger.debug(f"Button Press - Cancel on {self}")
        self.reject()

    #region Load/Save Data
    def load_from_project(self):
        """Implemented by child class."""
        pass

    def save_to_project(self):
        """Implemented by child class."""
        pass