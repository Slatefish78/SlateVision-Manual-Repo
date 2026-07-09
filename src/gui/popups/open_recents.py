import logging

from PySide6.QtWidgets import QMessageBox, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QPushButton, QFileDialog
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from gui.popups.sv_popup import SVPopup
from gui.util.clear_layout import clear_layout

logger = logging.getLogger(__name__)

class OpenRecentPopup(SVPopup):
    def __init__(self, title: str, filetypes: str, header: str, paths, parent=None, controller=None):
        super().__init__(header,parent,controller)
        self.setFixedWidth(650)

        self.path_to_return = None
        self.paths = paths

        # recent projects
        path_list_widget = QWidget()
        self.path_list_layout = QVBoxLayout(path_list_widget)
        self.path_list_layout.setContentsMargins(9,9,9,0)
        self.path_list_layout.setSpacing(0)
        self.content_layout.addWidget(path_list_widget)

        self.update_recent_list()

        # new button
        button_row_widget = QWidget()
        button_row_layout = QHBoxLayout(button_row_widget)
        self.content_layout.addWidget(button_row_widget)

        new_btn = QPushButton("Create New")
        new_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        new_btn.setProperty("role","default")

        new_btn.clicked.connect(self.on_btn_new)

        button_row_layout.addWidget(new_btn)
        
        # browse button
        browse_btn = QPushButton("Browse")
        browse_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        browse_btn.setProperty("role","default")

        browse_btn.clicked.connect(
            lambda: self.on_btn_browse(
                title=title,
                filetypes=filetypes
            )
        )

        button_row_layout.addWidget(browse_btn)

        # cancel button
        button_row_layout.addWidget(self.cancel_btn)

    def update_recent_list(self):
        # delete old list
        clear_layout(self.path_list_layout)

        # update recent list from parameter
        if not self.paths:
            label = QLabel("No recent projects found.")
            label.setAlignment(Qt.AlignCenter)
            self.path_list_layout.addWidget(label)
            return

        for entry in self.paths:
            name = entry["name"]
            path = entry["path"]
            pinned = entry["pinned"]

            row_layout = QHBoxLayout()
            self.path_list_layout.addLayout(row_layout)

            # path button
            path_btn = QPushButton(f"{name} - {path}")
            path_btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            path_btn.setProperty("role","recent_file")

            path_btn.setToolTip(str(path))

            path_btn.clicked.connect(
                lambda checked=False, p=path: self.on_btn_recent_path(p)
            )

            row_layout.addWidget(path_btn)

            # pin button
            pin_btn = QPushButton()
            pin_btn.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            pin_btn.setProperty("role","recent_file")

            pin_btn.setToolTip(f"Pin path.")

            icon_map = {
                False: self.controller.assets_path / "icons" / "pin_hollow.png",
                True: self.controller.assets_path / "icons" / "pin_solid.png"
            }

            icon_path = icon_map[pinned]
            pin_btn.setIcon(QIcon(str(icon_path)))
            pin_btn.setIconSize(QSize(20,20))

            pin_btn.clicked.connect(
                lambda checked=False, e=entry, b=pin_btn: self.on_btn_pin(e, b)
            )

            row_layout.addWidget(pin_btn)

            # remove button
            remove_btn = QPushButton()
            remove_btn.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
            remove_btn.setProperty("role","recent_file")

            remove_btn.setToolTip("Remove path.")

            icon_path = self.controller.assets_path / "icons" / "delete.png"
            remove_btn.setIcon(QIcon(str(icon_path)))
            remove_btn.setIconSize(QSize(20,20))

            remove_btn.clicked.connect(
                lambda checked=False, p=path: self.on_btn_remove(p)
            )

            row_layout.addWidget(remove_btn)

    #region Button Handlers
    def on_btn_recent_path(self, path):
        logger.debug(f"Button Press - selected recent path: {path}.")
        self.path_to_return = path
        self.accept()

    def on_btn_pin(self, entry, button):
        entry["pinned"] = not entry.get("pinned",False)

        if entry.get("pinned",False):
            logger.debug(f"Button Press - Pinned path {entry.get('path')}.")
        else:
            logger.debug(f"Button Press - Unpinned path {entry.get('path')}.")

        icon_map = {
            False: self.controller.assets_path / "icons" / "pin_hollow.png",
            True: self.controller.assets_path / "icons" / "pin_solid.png"
        }

        icon_path = icon_map[entry["pinned"]]
        button.setIcon(QIcon(str(icon_path)))

    def on_btn_remove(self, path):
        logger.debug(f"Button Press - Remove recent path: {path}.")
        remove_confirm = QMessageBox.question(
            self,
            "Remove path",
            f"Are you sure you want to remove path {path}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if remove_confirm == QMessageBox.No:
            logger.debug("Path remove canceled.")
            return
        
        # remove the entry from the list
        self.paths[:] = [
            entry
            for entry in self.paths
            if entry["path"] != path
        ]

        self.update_recent_list()

        logger.debug(f"Removed recent path {path}.")

    def on_btn_new(self):
        logger.debug(f"Button Press - Create New project.")
        self.path_to_return = ""
        self.accept()

    def on_btn_browse(self,title="Select Project",filetypes="SlateVision Project (*.svp);;Project config file (*.json);;All Files (*.*)"):
        logger.debug(f"Button Press - Browse to project file.")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(self.controller.projects_path),
            filetypes
        )

        if not file_path:
            return
        else:
            self.path_to_return = file_path
            self.accept()
    
    def on_btn_cancel(self):
        logger.debug(f"Button Press - Cancel file selection.")
        self.path_to_return = None
        self.reject()

    @staticmethod
    def get_path(title: str, filetypes: str, header: str, paths, parent=None, controller=None):
        dialog = OpenRecentPopup(title,filetypes,header,paths,parent,controller)
        if dialog.exec() == QDialog.Accepted:
            logger.debug(f"Got path: {dialog.path_to_return}")
            return dialog.path_to_return
        return None