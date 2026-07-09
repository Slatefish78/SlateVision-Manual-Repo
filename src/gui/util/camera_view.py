import logging

import cv2
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QImage, QPen, QColor, QFont
from PySide6.QtCore import QRect, Qt, Signal

logger = logging.getLogger(__name__)

class CameraView(QWidget):

    box_created_signal = Signal(dict)

    #region Init
    def __init__(self,parent=None):
        super().__init__(parent)

        # base image
        self.img_x = 0
        self.img_y = 0
        self.img_w = 0
        self.img_h = 0

        self.frame = None
        self.qimage = None

        # rendered tools (project running)
        self.tools_to_render = None
        # Get number of labels in each corner from canvas [TL, TR, BL, BR, C]
        self.label_counts = [0,0,0,0,0]

        # rendered annotations
        self.annotations = []
        self.classes = {}

        # crosshair (annotation)
        self.setMouseTracking(True)
        self.mouse_pos = None
        self.show_crosshair = False

        # current annotation box
        self.drawing_box = False
        self.box_start = None
        self.box_end = None
        self.active_class = None

    #region Class Methods
    def set_frame(self,frame):
        self.frame = frame
        rgb = cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        self.qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.update()

    def set_tools(self,tools):
        self.tools_to_render = tools
        self.update()

    def set_annotations(self,annotations):
        self.annotations = annotations
        self.update()

    def set_classes(self,classes):
        self.classes = {cls["id"]: cls for cls in classes}

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.position().toPoint()

        if self.drawing_box:
            coords = self.normal_coords(self.mouse_pos.x(), self.mouse_pos.y())
            if coords:
                self.box_end = coords

        self.update()

    def mousePressEvent(self, event):
        if not self.show_crosshair or not self.active_class:
            return
        
        pos = event.position().toPoint()
        coords = self.normal_coords(pos.x(),pos.y())

        if coords is None:
            return
        
        self.drawing_box = True
        self.box_start = coords
        self.box_end = coords

        self.update()

    def mouseReleaseEvent(self, event):
        if not self.drawing_box:
            return
        
        self.drawing_box = False

        if not self.box_start or not self.box_end:
            return
        
        x1,y1 = self.box_start
        x2,y2 = self.box_end

        x_min, x_max = sorted([x1,x2])
        y_min, y_max = sorted([y1,y2])

        if abs(x_max - x_min) < 0.01 or abs(y_max - y_min) < 0.01:
            return

        self.box_created_signal.emit({
            "x1": x_min,
            "y1": y_min,
            "x2": x_max,
            "y2": y_max,
            "class_id": self.active_class["id"]
        })

        self.update()

    def leaveEvent(self, event):
        self.mouse_pos = None
        self.update()

    #region Render Tool
    def render_tool(self, tool, painter: QPainter, results: dict, render_settings: dict):
        # verify results obtained
        if results is None:
            return
        
        # expand rendering settings
        render_box = render_settings["box"]
        render_label = render_settings["label"]
        render_cls = render_settings["class"]
        render_cls_id = render_settings["class_id"]
        render_score = render_settings["score"]
        render_label_line = render_settings["label_line"]
        label_loc = render_settings["label_loc"]

        font = QFont()
        font_size = max(8,int(10 * self.img_h / 480))
        font.setPointSize(font_size)
        painter.setFont(font)

        # Render based on tool type
        match tool.tool_type:
            case "detect":
                render_classes = render_settings["render_classes"]

                # Render all detected object results
                for box in results:
                    color = QColor(render_classes[box["class_id"]]["color"])
                    cls = render_classes[box["class_id"]]["name"]
                    pen = QPen(color)
                    painter.setPen(pen)

                    x0 = int(box["x1"] * self.img_w + self.img_x)
                    y0 = int(box["y1"] * self.img_h + self.img_y)
                    x1 = int(box["x2"] * self.img_w + self.img_x)
                    y1 = int(box["y2"] * self.img_h + self.img_y)

                    # Draw box
                    if render_box:
                        painter.drawRect(
                            x0,
                            y0,
                            x1-x0,
                            y1-y0
                        )

                    # Determine Label text
                    label = ""
                    if render_label:
                        # Add tool name, dash if other data
                        label += tool.name
                        if render_cls or render_cls_id or render_score:
                            label += " - "
                    if render_cls:
                        # Add class name, space if other data
                        label += cls
                        if render_cls_id:
                            label += " "
                    if render_cls_id:
                        # Add class id
                        label += f"({box['class_id']})"
                    if render_score:
                        # Add score, colon if needed
                        if render_cls or render_cls_id:
                            label += ": "
                        label += f"{box['score'] * 100:.1f}%"

                    if label != "":
                        # Determine label placement
                        metrics = painter.fontMetrics()
                        label_width = metrics.horizontalAdvance(label)
                        label_height = metrics.height()
                        
                        y_shift = 5
                        loc_map = {
                            "A": {
                                "TL": (self.img_x, self.img_y + label_height + (label_height * self.label_counts[0]) - y_shift),
                                "TR": (self.img_x + self.img_w - label_width - 5, self.img_y + label_height + (label_height * self.label_counts[1]) - y_shift),
                                "BL": (self.img_x, self.img_y + self.img_h - (label_height * self.label_counts[2]) - y_shift),
                                "BR": (self.img_x + self.img_w - label_width - 5, self.img_y + self.img_h - (label_height * self.label_counts[3]) - y_shift),
                                "C": (self.img_x + self.img_w/2 - label_width/2, self.img_y + self.img_h/2 + (label_height * self.label_counts[4]) + label_height/2 - y_shift)
                            },
                            "B": {
                                "TL": (x0, y0 - y_shift),
                                "TR": (x1 - label_width, y0 - y_shift),
                                "BL": (x0, y1 + label_height - y_shift),
                                "BR": (x1 - label_width, y1 + label_height - y_shift),
                                "C": ((x0 + x1)//2 - label_width//2, (y0 + y1)//2 + label_height//2 - y_shift)
                            }
                        }

                        # Get values based on map
                        label_x, label_y= loc_map[label_loc[0]][label_loc[1:]]

                        painter.drawText(label_x,label_y,label)

                        if label_loc[0] == "A":
                            count_index = {"TL":0,"TR":1,"BL":2,"BR":3,"C":4}[label_loc[1:]]
                            self.label_counts[count_index] += 1

                    # Draw Line from box to label
                    if label_loc[0] == "A" and label_loc[1] != "C" and render_label_line:
                        # Determine end points
                        t_rect = QRect(int(label_x),int(label_y - label_height), label_width, label_height)
                        loc_map = {
                            "TL": (t_rect.right(), t_rect.bottom(), x0, y0),
                            "TR": (t_rect.left(), t_rect.bottom(), x1, y0),
                            "BL": (t_rect.right(), t_rect.top(), x0, y1),
                            "BR": (t_rect.left(), t_rect.top(), x1, y1) 
                        }

                        # Get values based on map
                        x0, y0, x1, y1 = loc_map[label_loc[1:]]

                        painter.drawLine(x0,y0,x1,y1)
            case _:
                return

    #region Render Annotations
    def render_annotations(self,painter: QPainter):
        for box in self.annotations:
            cls = self.classes.get(box["class_id"])
            color = QColor(cls["color"]) if cls else QColor("#FF0000")
            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)

            x0 = box["x1"] * self.img_w + self.img_x
            y0 = box["y1"] * self.img_h + self.img_y
            x1 = box["x2"] * self.img_w + self.img_x
            y1 = box["y2"] * self.img_h + self.img_y

            painter.drawRect(x0, y0, x1 - x0, y1 - y0)

    def render_current_box(self,painter: QPainter):
        pen = QPen(Qt.yellow)
        pen.setWidth(1)
        painter.setPen(pen)

        x1,y1 = self.box_start
        x2,y2 = self.box_end

        x_0 = min(x1, x2) * self.img_w + self.img_x
        y_0 = min(y1, y2) * self.img_h + self.img_y
        x_1 = max(x1, x2) * self.img_w + self.img_x
        y_1 = max(y1, y2) * self.img_h + self.img_y

        painter.drawRect(x_0, y_0, x_1 - x_0, y_1 - y_0)
    
    #region Render Crosshair   
    def render_crosshair(self,painter):
        pen = QPen(Qt.red)
        pen.setWidth(1)
        painter.setPen(pen)

        x = self.mouse_pos.x()
        y = self.mouse_pos.y()

        painter.drawLine(self.img_x,y,self.img_x + self.img_w,y)
        painter.drawLine(x,self.img_y,x,self.img_y + self.img_h)

    #region Paint Event
    def paintEvent(self, event):
        painter = QPainter(self)

        if self.qimage is None:
            painter.fillRect(self.rect(), Qt.black)
            painter.setPen(Qt.white)
            painter.drawText(self.rect(),Qt.AlignCenter,"Camera Inactive")
            painter.end()
            return

        scaled = self.qimage.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.img_x = (self.width() - scaled.width()) //2
        self.img_y = (self.height() - scaled.height()) // 2
        self.img_w = scaled.width()
        self.img_h = scaled.height()

        img_rect = QRect(self.img_x,self.img_y,self.img_w,self.img_h)

        # render image
        painter.drawImage(self.img_x,self.img_y,scaled)

        # render vision tools
        if self.tools_to_render:
            self.label_counts = [0,0,0,0,0]
            for tool, results, settings in self.tools_to_render:
                self.render_tool(
                    tool,
                    painter,
                    results,
                    settings
                )

        # render model annotations
        self.render_annotations(painter)

        # render crosshair
        if self.show_crosshair and self.mouse_pos and img_rect.contains(self.mouse_pos):
            self.render_crosshair(painter)

        # render selection box
        if self.drawing_box and self.box_start and self.box_end:
            self.render_current_box(painter)

        painter.end()

    #region Coordinate Helper
    def normal_coords(self,px,py):
        # prevent math errors
        if self.img_w == 0 or self.img_h == 0:
            return None
        
        # check position is on photo
        if not (self.img_x <= px <= self.img_x + self.img_w and
                self.img_y <= py <= self.img_y + self.img_h):
            return None
        
        # normalize coordinates
        norm_x = (px - self.img_x) / self.img_w
        norm_y = (py - self.img_y) / self.img_h

        return norm_x,norm_y