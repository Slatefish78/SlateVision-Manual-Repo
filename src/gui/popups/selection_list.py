import logging

from PySide6.QtWidgets import QDialog, QPushButton
from gui.popups.sv_popup import SVPopup

logger = logging.getLogger(__name__)

class SelectionListPopup(SVPopup):
    def __init__(self, parent, controller, title: str, options: list, cancel: bool=True):
        super().__init__(title,parent,controller)
        
        if cancel:
            options.append(("Cancel",None))

        for btn_label, return_val in options:
            btn = QPushButton(btn_label)
            btn.clicked.connect(
                lambda checked=False,value=return_val: self.return_value(value)
            )
            self.content_layout.addWidget(btn)

        self.setLayout(self.content_layout)

        self.val_to_return = None

    def return_value(self,value):
        self.val_to_return = value
        self.accept()

    @staticmethod
    def get_selection(parent,controller,title:str,options:list,cancel:bool=True):
        dialog = SelectionListPopup(parent,controller,title,options,cancel=cancel)
        if dialog.exec() == QDialog.Accepted:
            logger.debug(f"Got value: {dialog.val_to_return}")
            return dialog.val_to_return
        return None