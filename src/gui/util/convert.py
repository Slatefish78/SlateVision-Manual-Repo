from PySide6.QtGui import QImage, QPixmap
import cv2

def cv_to_pixmap(cv_img):
    rgb_img = cv2.cvtColor(cv_img,cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_img.shape
    bytes_per_line = ch * w

    q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(q_img)