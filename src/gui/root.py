import logging
import sys

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QIcon
from gui.screens.info_scn import InfoScreen
from gui.screens.menu_scn import MenuScreen
from gui.screens.model_prj_scn import ModelPrjScreen
from gui.screens.vision_prj_scn import VisionPrjScreen
from gui.screens.run_scn import RunScreen

logger = logging.getLogger(__name__)

class GuiRoot(QMainWindow):
    #region Init
    def __init__(self, controller):
        # @@@ create app main window
        super().__init__()
        self.controller = controller
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.setObjectName("AppRoot")

        icon_path = self.controller.assets_path / "icons" / "logo.png"
        self.setWindowIcon(QIcon(str(icon_path)))

        # set windows taskbar icon in windows
        if sys.platform == "win32":
            import ctypes
            app_id = "geminigroup.slatevision.slatevision_utility.2.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0,0,0,0)

        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # @@@ setup main window attributes
        self.setWindowTitle("SlateVision Utility v2.0")
        self.resize(self.controller.default_width,self.controller.default_height)

        # @@@ register screens
        self.screens = {}

        for name, ScreenClass in {
            "menu": MenuScreen,
            "model": ModelPrjScreen,
            "vision": VisionPrjScreen,
            "run": RunScreen,
            "info": InfoScreen
        }.items():
            screen = ScreenClass(parent=self.stack,controller=self.controller)
            self.stack.addWidget(screen)
            self.screens[name] = screen

        # show menu screen
        self.show_screen("menu")

    def show_screen(self, name):
        self.stack.setCurrentWidget(self.screens[name])
        logger.debug(f"Showing screen {self.screens[name]}")