import sys
import json
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QScrollArea, QGroupBox, QWidget, QRadioButton, QButtonGroup, QDialogButtonBox, QDialog, QFileDialog, QPushButton, QLabel, QLineEdit, QTextEdit, QSpinBox, QVBoxLayout, QHBoxLayout, QGridLayout
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter, QPen
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint, QRectF
from microtiter_methods import MicrotiterMethods

class MainWindow(QMainWindow):
    config_loaded_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microtiter Analyzer")
        self.left = 0
        self.top = 0
        self.width = 1080
        self.height = 1080
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.config = {}
        self.load_config()
        self.central_widget = CentralWidget(self, self.width, self.config)
        self.setCentralWidget(self.central_widget)
        menubar = self.menuBar()
        menu = menubar.addMenu('Config')
        load_config_action = menu.addAction("Load config")
        load_config_action.triggered.connect(self.load_config)
        save_config_action = menu.addAction("Save config")
        save_config_action.triggered.connect(self.save_config)

    def load_config(self):
        config = {}
        try:
            with open("config.json", "r") as file:
                config = json.load(file)
        except:
            pass
        if not config:
            config = {
                "path_samples": "samples.jpeg",
                "path_control": "control.jpeg",
                "n_rows": 3,
                "n_columns": 3,
                "top_left_x": 100,
                "top_left_y": 100,
                "bottom_right_x": 500,
                "bottom_right_y": 500,
                "control_x": 100,
                "control_y": 100,
                "AoI_size": 5,
                "aggregation_method": "arithmetic_mean",
                "scoring_method": "euclidian_rgb",
            }
            msg_box = MessageBox("No config found   ", "Using default values.")
            msg_box.exec()
        self.config.update(config)
        self.config_loaded_signal.emit()
    
    def save_config(self):
        with open("config.json", "w") as file:
            json.dump(self.config, file, indent=4)
    
    def closeEvent(self, a0):
        print(self.config)

class MessageBox(QDialog):
    def __init__(self, title, text):
        super().__init__()
        self.setWindowTitle(title)
      
        QBtn = QDialogButtonBox.StandardButton.Ok #| QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        # self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(text)
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def accept(self):
        super().accept()

class CentralWidget(QWidget):
    def __init__(self, parent, width, config):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        samples_tab = TabSamples(width, config)
        parent.config_loaded_signal.connect(samples_tab.config_loaded_callback)
        self.tab_widget.addTab(samples_tab, "Samples")
        control_tab = TabControl(width, config)
        parent.config_loaded_signal.connect(control_tab.config_loaded_callback)
        self.tab_widget.addTab(control_tab, "Control")
        self.processing_tab = TabProcessing(config)
        parent.config_loaded_signal.connect(self.processing_tab.config_loaded_callback)
        self.tab_widget.addTab(self.processing_tab, "Processing")
        self.tab_widget.currentChanged.connect(self.current_changed)
        self.layout.addWidget(self.tab_widget)
        self.setLayout(self.layout)

    def current_changed(self, index):
        if self.tab_widget.currentWidget() == self.processing_tab:
            self.processing_tab.update_spacing_label()

class TabSamples(QWidget):
    def __init__(self, width, config):
        super(QWidget, self).__init__()
        self.config = config
        self.layout = QVBoxLayout()
        self.target_spinboxes = []

        # input file
        self.input_layout = QHBoxLayout()
        self.input_label = QLabel("Samples Image:")
        self.input_layout.addWidget(self.input_label)
        self.input_text = QLineEdit()
        self.input_text.setText(self.config["path_samples"])
        self.input_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.input_layout.addWidget(self.input_text)
        self.input_button = QPushButton("Select file")
        self.input_button.clicked.connect(self.on_input_button_clicked)
        self.input_layout.addWidget(self.input_button)
        self.layout.addLayout(self.input_layout)

        # display image
        self.target_width = width
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.img_label = QLabel()
        self.scroll_area.setWidget(self.img_label)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.draw_crosses()
        self.img_label.mousePressEvent = self.get_pixel
        self.img_details_label = QLabel()
        self.update_img_details()
        self.layout.addWidget(self.img_details_label)
        self.layout.addWidget(self.scroll_area,2)

        # calibrate button
        self.calib_widget_set = []
        self.calib_layout = QGridLayout()
        self.calib_button = QPushButton("Calibrate")
        self.calib_button.clicked.connect(self.on_calib_button_clicked)
        self.calib_layout.addWidget(self.calib_button, 0, 0, 2, 1)
        # rows
        self.calib_layout.addWidget(QLabel(), 0, 1)
        self.calib_upper_rows_label = QLabel("# Rows:")
        self.calib_layout.addWidget(self.calib_upper_rows_label, 0, 2)
        self.calib_upper_rows_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.calib_upper_rows_label.setFixedHeight(self.calib_upper_rows_label.sizeHint().height())
        self.calib_upper_rows_input = QSpinBox()
        self.calib_widget_set.append(self.calib_upper_rows_input)
        self.calib_upper_rows_input.setMinimum(1)
        self.calib_upper_rows_input.setValue(self.config["n_rows"])
        self.calib_layout.addWidget(self.calib_upper_rows_input, 0, 3)
        self.calib_layout.addWidget(QLabel(), 0, 4)
        # columns
        self.calib_layout.addWidget(QLabel(), 1, 1)
        self.calib_lower_cols_label = QLabel("# Columns:")
        self.calib_lower_cols_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.calib_layout.addWidget(self.calib_lower_cols_label, 1, 2)
        self.calib_lower_cols_input = QSpinBox()
        self.calib_lower_cols_input.setMinimum(1)
        self.calib_lower_cols_input.setValue(self.config["n_columns"])
        self.calib_widget_set.append(self.calib_lower_cols_input)
        self.calib_layout.addWidget(self.calib_lower_cols_input, 1, 3)
        self.calib_lower_cols_label.setFixedHeight(self.calib_lower_cols_label.sizeHint().height())
        self.calib_layout.addWidget(QLabel(), 1, 4)
        # top left corner
        self.calib_upper_corner_label = QLabel("Top left corner:")
        self.calib_upper_corner_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.calib_upper_corner_label.setFixedHeight(self.calib_upper_rows_label.sizeHint().height())
        self.calib_layout.addWidget(self.calib_upper_corner_label, 0, 5)
        self.calib_upper_corner_x = QSpinBox()
        self.calib_widget_set.append(self.calib_upper_corner_x)
        self.calib_upper_corner_x.setMinimum(1)
        self.calib_upper_corner_x.setMaximum(10000)
        self.calib_upper_corner_x.setPrefix("x: ")
        self.calib_upper_corner_x.setValue(self.config["top_left_x"])
        self.calib_layout.addWidget(self.calib_upper_corner_x, 0, 6)
        self.calib_upper_corner_y = QSpinBox()
        self.calib_widget_set.append(self.calib_upper_corner_y)
        self.calib_upper_corner_y.setMinimum(1)
        self.calib_upper_corner_y.setMaximum(10000)
        self.calib_upper_corner_y.setPrefix("y: ")
        self.calib_upper_corner_y.setValue(self.config["top_left_y"])
        self.calib_layout.addWidget(self.calib_upper_corner_y, 0, 7)
        self.calib_upper_corner_button = QPushButton("Select")
        self.calib_upper_corner_button.clicked.connect(self.on_upper_corner_button_clicked)
        self.calib_widget_set.append(self.calib_upper_corner_button)
        self.calib_layout.addWidget(self.calib_upper_corner_button, 0, 8)
        # bottom right corner
        self.calib_lower_corner_label = QLabel("Bottom right corner:")
        self.calib_lower_corner_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.calib_lower_corner_label.setFixedHeight(self.calib_lower_cols_label.sizeHint().height())
        self.calib_layout.addWidget(self.calib_lower_corner_label, 1, 5)
        self.calib_lower_corner_x = QSpinBox()
        self.calib_widget_set.append(self.calib_lower_corner_x)
        self.calib_lower_corner_x.setMinimum(1)
        self.calib_lower_corner_x.setMaximum(10000)
        self.calib_lower_corner_x.setPrefix("x: ")
        self.calib_lower_corner_x.setValue(self.config["bottom_right_x"])
        self.calib_layout.addWidget(self.calib_lower_corner_x, 1, 6)
        self.calib_lower_corner_y = QSpinBox()
        self.calib_widget_set.append(self.calib_lower_corner_y)
        self.calib_lower_corner_y.setMinimum(1)
        self.calib_lower_corner_y.setMaximum(10000)
        self.calib_lower_corner_y.setPrefix("y: ")
        self.calib_lower_corner_y.setValue(self.config["bottom_right_y"])
        self.calib_layout.addWidget(self.calib_lower_corner_y, 1, 7)
        self.calib_lower_corner_button = QPushButton("Select")
        self.calib_lower_corner_button.clicked.connect(self.on_lower_corner_button_clicked)
        self.calib_widget_set.append(self.calib_lower_corner_button)
        self.calib_layout.addWidget(self.calib_lower_corner_button, 1, 8)
        # apply button
        self.calib_upper_button = QPushButton("Apply")
        self.calib_upper_button.clicked.connect(self.on_apply_button_clicked)
        self.calib_widget_set.append(self.calib_upper_button)
        self.calib_layout.addWidget(QLabel(), 0, 9)
        self.calib_layout.addWidget(self.calib_upper_button, 0, 10, 2, 1)
        # cancel button
        self.calib_lower_button = QPushButton("Cancel")
        self.calib_lower_button.clicked.connect(self.on_cancel_button_clicked)
        self.calib_widget_set.append(self.calib_lower_button)
        self.calib_layout.addWidget(self.calib_lower_button, 0, 11, 2, 1)

        self.widget_set_enabled(self.calib_widget_set, False)

        self.layout.addLayout(self.calib_layout)

        self.layout.addStretch()

        self.setLayout(self.layout)
        
    def draw_crosses(self):
        self.update_pixmap()
        self.generate_grid()
        for point in self.grid:
            self.draw_one_cross(point[0], point[1])
        self.img_label.setPixmap(self.pixmap)
        self.img_label.update()
                    
    def update_pixmap(self):
        self.img = QImage(self.config["path_samples"])
        if self.img.isNull():
            # self.img = QImage("image_not_found.jpg")
            temp_width = 1600
            temp_height = 1200
            temp_scale = 7
            self.img = QImage(QSize(1600,1200),QImage.Format.Format_RGB32)
            painter = QPainter(self.img)
            painter.scale(temp_scale,temp_scale)
            painter.fillRect(QRectF(0,0,round(temp_width/temp_scale),round(temp_height/temp_scale)),QColor(255, 255, 255))
            painter.setPen(QPen(QColor(0, 0, 0), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawText(QPoint(round(temp_width/temp_scale/4), round(temp_height/temp_scale/2)), "Image not found")
            painter.end()
        self.pixmap = QPixmap.fromImage(self.img)
        self.pixmap = self.pixmap.scaledToWidth(self.target_width)
        self.scale = self.img.width() / self.pixmap.width()
        self.img_label.setPixmap(self.pixmap)

    def generate_grid(self):
        grid = []
        spacing_x = (self.config["bottom_right_x"]-self.config["top_left_x"])/(self.config["n_columns"] - 1)
        spacing_y = (self.config["bottom_right_y"]-self.config["top_left_y"])/(self.config["n_rows"] - 1)
        for i in range(self.config["n_rows"]):
            for j in range(self.config["n_columns"]):
                grid.append((round(self.config["top_left_x"]+j*spacing_x), round(self.config["top_left_y"]+i*spacing_y)))
        self.grid = grid
    
    def draw_one_cross(self, x, y):
        x = round(x/self.scale)
        y = round(y/self.scale)
        cross_color = QColor(0, 255, 0)
        painter = QPainter(self.pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(cross_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cross_size = 10  # Fixed display pixels
        painter.drawLine(x-cross_size, y, x+cross_size, y)
        painter.drawLine(x, y-cross_size, x, y+cross_size)
        painter.end()

    def update_img_details(self):
        if self.img.isNull():
            return
        self.img_details_label.setText(f"Image Details | Width: {self.img.width()} | Height: {self.img.height()} | Scale: {round(1/self.scale, 2)}")

    def get_pixel(self, event):
        xoffset = (self.img_label.width() - self.pixmap.width()) / 2
        yoffset = (self.img_label.height() - self.pixmap.height()) / 2
        x = round(self.scale * (event.pos().x() - round(xoffset)))
        y = round(self.scale * (event.pos().y() - round(yoffset)))
        color = self.img.pixelColor(x, y)
        print(f"Pixel at ({x}, {y}) has color: {color.name()}")
        if self.target_spinboxes:
            self.target_spinboxes[0].setValue(x)
            self.target_spinboxes[0].setEnabled(True)
            self.target_spinboxes[1].setValue(y)
            self.target_spinboxes[1].setEnabled(True)
            self.target_spinboxes = []

    def update_config(self):
        self.config["path_samples"] = self.input_text.text()
        self.config["top_left_x"] = self.calib_upper_corner_x.value()
        self.config["top_left_y"] = self.calib_upper_corner_y.value()
        self.config["bottom_right_x"] = self.calib_lower_corner_x.value()
        self.config["bottom_right_y"] = self.calib_lower_corner_y.value()
        self.config["n_columns"] = self.calib_lower_cols_input.value()
        self.config["n_rows"] = self.calib_upper_rows_input.value()

    def revert_to_config(self):
        self.input_text.setText(self.config["path_samples"])
        self.calib_upper_corner_x.setValue(self.config["top_left_x"])
        self.calib_upper_corner_y.setValue(self.config["top_left_y"])
        self.calib_lower_corner_x.setValue(self.config["bottom_right_x"])
        self.calib_lower_corner_y.setValue(self.config["bottom_right_y"])
        self.calib_lower_cols_input.setValue(self.config["n_columns"])
        self.calib_upper_rows_input.setValue(self.config["n_rows"])

    def on_input_button_clicked(self):
        file_name = QFileDialog.getOpenFileName(self, "Select Image of Samples", "", "Image files (*.*)")
        if file_name[0]:
            self.config["path_samples"] = file_name[0]
            self.input_text.setText(file_name[0])
            self.update_img_details()
            self.draw_crosses()

    def on_upper_corner_button_clicked(self):
        self.calib_upper_corner_x.setEnabled(False)
        self.calib_upper_corner_y.setEnabled(False)
        self.calib_lower_corner_x.setEnabled(True)
        self.calib_lower_corner_y.setEnabled(True)
        self.target_spinboxes = [self.calib_upper_corner_x, self.calib_upper_corner_y]

    def on_lower_corner_button_clicked(self):
        self.calib_lower_corner_x.setEnabled(False)
        self.calib_lower_corner_y.setEnabled(False)
        self.calib_upper_corner_x.setEnabled(True)
        self.calib_upper_corner_y.setEnabled(True)
        self.target_spinboxes = [self.calib_lower_corner_x, self.calib_lower_corner_y]

    def on_calib_button_clicked(self):
        self.widget_set_enabled(self.calib_widget_set, True)
        self.calib_button.setEnabled(False)
    
    def on_apply_button_clicked(self):
        self.update_config()
        self.widget_set_enabled(self.calib_widget_set, False)
        self.calib_button.setEnabled(True)
        self.draw_crosses()

    def on_cancel_button_clicked(self):
        self.revert_to_config()
        self.widget_set_enabled(self.calib_widget_set, False)
        self.calib_button.setEnabled(True)

    def config_loaded_callback(self):
        self.revert_to_config()
        self.widget_set_enabled(self.calib_widget_set, False)
        self.calib_button.setEnabled(True)
        self.draw_crosses()

    def widget_set_enabled(self, widgets, enabled):
        for widget in widgets:
            try:
                widget.setEnabled(enabled)
            except:
                pass

class TabControl(QWidget):
    def __init__(self, width, config):
        super(QWidget, self).__init__()
        self.config = config
        self.layout = QVBoxLayout()

        # input file
        self.input_layout = QHBoxLayout()
        self.input_label = QLabel("Control Image:")
        self.input_layout.addWidget(self.input_label)
        self.input_text = QLineEdit()
        self.input_text.setText(self.config["path_control"])
        self.input_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.input_layout.addWidget(self.input_text)
        self.input_button = QPushButton("Select file")
        self.input_button.clicked.connect(self.on_input_button_clicked)
        self.input_layout.addWidget(self.input_button)
        self.layout.addLayout(self.input_layout)

        # display image
        self.target_width = width
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.img_label = QLabel()
        self.scroll_area.setWidget(self.img_label)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.draw_crosses()
        self.img_label.mousePressEvent = self.get_pixel
        self.img_details_label = QLabel()
        self.update_img_details()
        self.layout.addWidget(self.img_details_label)
        self.layout.addWidget(self.scroll_area,2)

        # calibrations settings
        self.calib_layout = QHBoxLayout()
        self.calib_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
 
        self.calib_control_center_label = QLabel("Control center:")
        self.calib_control_center_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.calib_control_center_label.setFixedHeight(self.calib_control_center_label.sizeHint().height())
        self.calib_layout.addWidget(self.calib_control_center_label)

        self.calib_control_center_x = QSpinBox()
        self.calib_control_center_x.setMinimum(1)
        self.calib_control_center_x.setMaximum(10000)
        self.calib_control_center_x.setPrefix("x: ")
        self.calib_control_center_x.setValue(self.config["control_x"])
        self.calib_control_center_x.valueChanged.connect(self.on_control_center_changed)
        self.calib_layout.addWidget(self.calib_control_center_x)

        self.calib_control_center_y = QSpinBox()
        self.calib_control_center_y.setMinimum(1)
        self.calib_control_center_y.setMaximum(10000)
        self.calib_control_center_y.setPrefix("y: ")
        self.calib_control_center_y.setValue(self.config["control_y"])
        self.calib_control_center_y.valueChanged.connect(self.on_control_center_changed)
        self.calib_layout.addWidget(self.calib_control_center_y)

        self.calib_control_center_button = QPushButton("Select")
        self.calib_control_center_button.clicked.connect(self.on_control_center_button_clicked)
        self.calib_layout.addWidget(self.calib_control_center_button)

        self.layout.addLayout(self.calib_layout)

        self.layout.addStretch()

        self.setLayout(self.layout)
    
    def on_control_center_changed(self):
        self.update_config()
        self.draw_crosses()
        
    def draw_crosses(self):
        self.update_pixmap()
        # self.generate_grid()
        self.draw_one_cross(self.config["control_x"], self.config["control_y"])
        self.img_label.setPixmap(self.pixmap)
        self.img_label.update()
                    
    def update_pixmap(self):
        self.img = QImage(self.config["path_control"])
        if self.img.isNull():
            # self.img = QImage("image_not_found.jpg")
            temp_width = 1600
            temp_height = 1200
            temp_scale = 7
            self.img = QImage(QSize(1600,1200),QImage.Format.Format_RGB32)
            painter = QPainter(self.img)
            painter.scale(temp_scale,temp_scale)
            painter.fillRect(QRectF(0,0,round(temp_width/temp_scale),round(temp_height/temp_scale)),QColor(255, 255, 255))
            painter.setPen(QPen(QColor(0, 0, 0), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawText(QPoint(round(temp_width/temp_scale/4), round(temp_height/temp_scale/2)), "Image not found")
            painter.end()
        self.pixmap = QPixmap.fromImage(self.img)
        self.pixmap = self.pixmap.scaledToWidth(self.target_width)
        self.scale = self.img.width() / self.pixmap.width()
        self.img_label.setPixmap(self.pixmap)

    
    def draw_one_cross(self, x, y):
        x = round(x/self.scale)
        y = round(y/self.scale)
        cross_color = QColor(0, 255, 0)
        painter = QPainter(self.pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(cross_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cross_size = 10  # Fixed display pixels
        painter.drawLine(x-cross_size, y, x+cross_size, y)
        painter.drawLine(x, y-cross_size, x, y+cross_size)
        painter.end()

    def update_img_details(self):
        if self.img.isNull():
            return
        self.img_details_label.setText(f"Image Details | Width: {self.img.width()} | Height: {self.img.height()} | Scale: {round(1/self.scale, 2)}")

    def get_pixel(self, event):
        xoffset = (self.img_label.width() - self.pixmap.width()) / 2
        yoffset = (self.img_label.height() - self.pixmap.height()) / 2
        x = round(self.scale * (event.pos().x() - round(xoffset)))
        y = round(self.scale * (event.pos().y() - round(yoffset)))
        color = self.img.pixelColor(x, y)
        print(f"Pixel at ({x}, {y}) has color: {color.name()}")
        if self.target_spinboxes:
            self.target_spinboxes[0].setValue(x)
            self.target_spinboxes[0].setEnabled(True)
            self.target_spinboxes[1].setValue(y)
            self.target_spinboxes[1].setEnabled(True)
            self.target_spinboxes = []

    def update_config(self):
        self.config["path_control"] = self.input_text.text()
        self.config["control_x"] = self.calib_control_center_x.value()
        self.config["control_y"] = self.calib_control_center_y.value()

    def revert_to_config(self):
        self.input_text.setText(self.config["path_control"])
        self.calib_control_center_x.setValue(self.config["control_x"])
        self.calib_control_center_y.setValue(self.config["control_y"])

    def on_input_button_clicked(self):
        file_name = QFileDialog.getOpenFileName(self, "Select Image of Control", "", "Image files (*.*)")
        if file_name[0]:
            self.config["path_control"] = file_name[0]
            self.input_text.setText(file_name[0])
            self.update_img_details()
            self.draw_crosses()

    def on_control_center_button_clicked(self):
        self.calib_control_center_x.setEnabled(False)
        self.calib_control_center_y.setEnabled(False)
        self.target_spinboxes = [self.calib_control_center_x, self.calib_control_center_y]

    def config_loaded_callback(self):
        self.revert_to_config()
        self.draw_crosses()

class TabProcessing(QWidget):
    def __init__(self, config):
        super(QWidget, self).__init__()
        self.config = config
        self.layout = QVBoxLayout()
        self.methods = MicrotiterMethods()

        self.settings_layout = QHBoxLayout()

        # AoI settings
        self.AoI_groupbox = QGroupBox("Area of Interest")
        self.AoI_layout = QVBoxLayout()

        self.AoI_hbox = QHBoxLayout()
        self.AoI_spinbox = QSpinBox()
        self.AoI_spinbox.setMinimum(1)
        self.AoI_spinbox.setSingleStep(2)
        self.AoI_spinbox.setValue(self.sanitize_AoI(config["AoI_size"]))
        self.AoI_hbox.addWidget(self.AoI_spinbox)
        self.AoI_label = QLabel("x "+str(config["AoI_size"]))
        self.AoI_spinbox.editingFinished.connect(self.AoI_updated)
        self.AoI_hbox.addWidget(self.AoI_label)
        self.AoI_layout.addLayout(self.AoI_hbox)

        self.AoI_hint = QLabel()
        self.update_spacing_label()
        self.AoI_layout.addWidget(self.AoI_hint)

        self.AoI_groupbox.setLayout(self.AoI_layout)
        self.settings_layout.addWidget(self.AoI_groupbox)

        # Aggregation method
        self.aggregation_groupbox = QGroupBox("Aggregation Method")
        self.aggregation_layout = QVBoxLayout()
        self.aggregation_button_group = QButtonGroup()
        for (idx, method) in enumerate(self.methods.aggregation_methods):
            radiobutton = QRadioButton(method.label)
            if method.code == self.config["aggregation_method"]:
                radiobutton.setChecked(True)
            self.aggregation_layout.addWidget(radiobutton)
            self.aggregation_button_group.addButton(radiobutton, id=idx)
        self.aggregation_button_group.buttonClicked.connect(self.aggregation_method_changed)
        self.aggregation_groupbox.setLayout(self.aggregation_layout)
        self.settings_layout.addWidget(self.aggregation_groupbox)

        # Scoring method
        self.scoring_groupbox = QGroupBox("Scoring Method")
        self.scoring_layout = QVBoxLayout()
        self.scoring_button_group = QButtonGroup()
        for (idx, method) in enumerate(self.methods.scoring_methods):
            radiobutton = QRadioButton(method.label)
            if method.code == self.config["scoring_method"]:
                radiobutton.setChecked(True)
            self.scoring_layout.addWidget(radiobutton)
            self.scoring_button_group.addButton(radiobutton, id=idx)
        self.scoring_button_group.buttonClicked.connect(self.scoring_method_changed)
        self.scoring_groupbox.setLayout(self.scoring_layout)
        self.settings_layout.addWidget(self.scoring_groupbox)

        self.layout.addLayout(self.settings_layout)

        # Evaluate button
        self.evaluate_button = QPushButton("Evaluate")
        self.evaluate_button.clicked.connect(self.evaluate_clicked)
        self.layout.addWidget(self.evaluate_button)

        # Results box
        self.results_box = QTextEdit()
        self.results_box.setReadOnly(True)
        self.layout.addWidget(self.results_box, 2)

        # Save as CSV button
        self.save_as_csv_button = QPushButton("Save as CSV")
        self.save_as_csv_button.clicked.connect(self.save_as_csv_clicked)
        self.layout.addWidget(self.save_as_csv_button)

        self.update_spacing_label()

        # self.layout.addStretch()
        self.setLayout(self.layout)

    def evaluate_clicked(self):
        samples_image = QImage(self.config["path_samples"])
        control_image = QImage(self.config["path_control"])
        # control_color = control_image.pixelColor(self.config["control_x"], self.config["control_y"])
        results_array = []
        spacing_x = (self.config["bottom_right_x"]-self.config["top_left_x"])/(self.config["n_columns"] - 1)
        spacing_y = (self.config["bottom_right_y"]-self.config["top_left_y"])/(self.config["n_rows"] - 1)
        aggregation_method_id = self.aggregation_button_group.checkedId()
        scoring_method_id = self.scoring_button_group.checkedId()
        # get control colors
        control_r, control_g, control_b = self.aggregate_location(control_image, self.config["control_x"], self.config["control_y"], aggregation_method_id)
        for i in range(self.config["n_rows"]):
            row = []
            for j in range(self.config["n_columns"]):
                x = round(self.config["top_left_x"]+j*spacing_x)
                y = round(self.config["top_left_y"]+i*spacing_y)
                sample_r, sample_g, sample_b = self.aggregate_location(samples_image, x, y, aggregation_method_id)
                score = self.methods.scoring_methods[scoring_method_id].calculate(sample_r, sample_g, sample_b, control_r, control_g, control_b)
                row.append(score)
            results_array.append(row)
        res_string = self.get_results_string(results_array)
        self.results_box.setText(res_string)
        print(res_string)

    def aggregate_location(self, image, x, y, method_id):
        aoi_r, aoi_g, aoi_b = self.get_AoI_rgb(image, x, y)
        aggregated_r = self.methods.aggregation_methods[method_id].calculate(aoi_r)
        aggregated_g = self.methods.aggregation_methods[method_id].calculate(aoi_g)
        aggregated_b = self.methods.aggregation_methods[method_id].calculate(aoi_b)
        return aggregated_r, aggregated_g, aggregated_b

    def get_AoI_rgb(self, image, x, y):
        aoi_r, aoi_g, aoi_b = [], [], []
        half = self.config["AoI_size"]//2
        for dy in range(-half, half+1):
            row_r, row_g, row_b = [], [], []
            for dx in range(-half, half+1):
                pixel_r, pixel_g, pixel_b, _ = image.pixelColor(x+dx, y+dy).getRgb()
                row_r.append(pixel_r)
                row_g.append(pixel_g)
                row_b.append(pixel_b)
            aoi_r.append(row_r)
            aoi_g.append(row_g)
            aoi_b.append(row_b)
        return np.array(aoi_r), np.array(aoi_g), np.array(aoi_b)
    
    def get_results_string(self, array):
        nparray = np.array(array)
        res = ""
        # Embed settings as comments
        res += "# Settings:\n"
        res += "# path_samples = "+self.config["path_samples"]+"\n"
        res += "# path_control = "+self.config["path_control"]+"\n"
        res += "# top_left_x = "+str(self.config["top_left_x"])+"\n"
        res += "# top_left_y = "+str(self.config["top_left_y"])+"\n"
        res += "# bottom_right_x = "+str(self.config["bottom_right_x"])+"\n"
        res += "# bottom_right_y = "+str(self.config["bottom_right_y"])+"\n"
        res += "# n_rows = "+str(self.config["n_rows"])+"\n"
        res += "# n_columns = "+str(self.config["n_columns"])+"\n"
        res += "# control_x = "+str(self.config["control_x"])+"\n"
        res += "# control_y = "+str(self.config["control_y"])+"\n"
        res += "# AoI_size = "+str(self.config["AoI_size"])+"\n"
        res += "# aggregation_method = "+self.methods.aggregation_methods[self.aggregation_button_group.checkedId()].label+"\n"
        res += "# scoring_method = "+self.methods.scoring_methods[self.scoring_button_group.checkedId()].label+"\n"
        # Simple min max positions
        res += "# Results:\n"
        idx_min = np.unravel_index(nparray.argmin(), nparray.shape)
        res += "# Closest match: " + self.idx_to_letter(idx_min[0]) + str(idx_min[1]+1) + "\n"
        idx_max = np.unravel_index(nparray.argmax(), nparray.shape)
        res += "# Farthest match: " + self.idx_to_letter(idx_max[0]) + str(idx_max[1]+1) + "\n"

        header = [str(i) for i in range(self.config["n_columns"]+1)]
        for number in header:
            res += str(number) + "\t"
        res += "\n"
        for idx, row in enumerate(array):
            res += self.idx_to_letter(idx) + "\t"
            for value in row:
                res += str(round(value, 2)) + "\t"
            res += "\n"
        return res

    def save_as_csv_clicked(self):
        filename = QFileDialog.getSaveFileName(self, "Save as CSV", "", "CSV files (*.csv)")[0]
        if filename:
            if not filename.endswith(".csv"):
                filename += ".csv"
            with open(filename, "w") as file:
                file.write(self.results_box.toPlainText())
    
    def idx_to_letter(self, idx):
        return chr(ord('A')+idx)

    def AoI_updated(self):
        value = self.sanitize_AoI(self.AoI_spinbox.value())
        self.AoI_spinbox.setValue(value)
        self.config["AoI_size"] = value
        self.AoI_label.setText("x "+str(value))

    def sanitize_AoI(self, num):
        if num % 2 == 1:
            return num
        else:
            return num+1
    
    def aggregation_method_changed(self):
        id = self.aggregation_button_group.checkedId()
        self.config["aggregation_method"] = self.methods.aggregation_methods[id].code

    def scoring_method_changed(self):
        id = self.scoring_button_group.checkedId()
        self.config["scoring_method"] = self.methods.scoring_methods[id].code

    def update_spacing_label(self):
        spacing_x = (self.config["bottom_right_x"]-self.config["top_left_x"])/(self.config["n_columns"] - 1)
        spacing_y = (self.config["bottom_right_y"]-self.config["top_left_y"])/(self.config["n_rows"] - 1)
        self.AoI_hint.setText("Current spacing: "+str(round(min(spacing_x, spacing_y)))+" pixels")
    
    def revert_to_config(self):
        self.AoI_spinbox.setValue(self.config["AoI_size"])
        self.update_spacing_label()
        for (idx, method) in enumerate(self.methods.aggregation_methods):
            if self.config["aggregation_method"] == method.code:
                self.aggregation_button_group.button(idx).setChecked(True)
        for (idx, method) in enumerate(self.methods.scoring_methods):
            if self.config["scoring_method"] == method.code:
                self.scoring_button_group.button(idx).setChecked(True)
    
    def config_loaded_callback(self):
        self.revert_to_config()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()