from PySide6.QtWidgets import QLayout

def clear_layout(layout: QLayout):
    if layout is None:
        return
    
    while layout.count() > 0:
        item = layout.takeAt(0)

        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

        sub_layout = item.layout()
        if sub_layout is not None:
            clear_layout(sub_layout)