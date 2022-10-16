from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sqlite3
import re
from image_window import ImageWindow
from build_search_page import Worker
from scan_directories import ScanWindow
from select_folders import SelectWindow
import pickle
import json


# extending QLabel functionality to make it clickable
# and store image location
class ClickLabel(QLabel):
    clicked = pyqtSignal(str)
    delete = pyqtSignal(str)

    def __init__(self, image_loc):
        super().__init__()
        # storing image location
        self.image_loc = image_loc

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_loc)
        else:
            self.delete.emit(self.image_loc)


class MainWindow(QMainWindow):
    def __init__(self, screen):
        super().__init__()
        self.worker = None

        self.size = screen.size()
        self.count = 0
        
        main_layout = QVBoxLayout()
        self.column = QVBoxLayout()
        self.column.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.row_layout = None

        self.input_query = QLineEdit()
        self.text = ""
        main_layout.addWidget(self.input_query)

        self.input_query.returnPressed.connect(lambda : self.retrieve(self.input_query.text()))
        image_holder = QWidget()
        image_holder.setLayout(self.column)

        scroll = QScrollArea()
        scroll.setWidget(image_holder)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        scan_button = QAction("Scan Directories", self)
        scan_button.setStatusTip("Click to open scan window")
        self.scan_directories = None
        scan_button.triggered.connect(self.open_scan_window)

        select_button = QAction("Select Directories", self)
        select_button.setStatusTip("Click to open select window")
        self.select_folders = None
        select_button.triggered.connect(self.open_select_folders)

        delete_mode = QAction("Toggle Delete Mode", self)
        delete_mode.setStatusTip("Click to toggle delete mode")
        delete_mode.setCheckable(True)
        self.delete_mode_on = False
        delete_mode.toggled.connect(self.set_delete_mode)

        delete_all = QAction("Delete entire Database", self)
        delete_all.setStatusTip("Delete all entries of database")
        delete_all.triggered.connect(self.wipe_everything)

        toolbar.addAction(scan_button)
        toolbar.addAction(select_button)
        toolbar.addAction(delete_mode)
        toolbar.addAction(delete_all)

        main_layout.addWidget(scroll)

        self.setWindowTitle("Image Search")

        container = QWidget()
        container.setLayout(main_layout)

        self.setCentralWidget(container)

        self.showMaximized()

    def wipe_everything(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Are you sure?")
        dlg.setText("All entries of database will be deleted! Are you sure you want to proceed?")
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        response = dlg.exec()
        response = QMessageBox.StandardButton(response)

        if response == QMessageBox.StandardButton.Yes:
            database = sqlite3.connect("classification.db", check_same_thread=False)
            cursor = database.cursor()
            cursor.execute("DROP TABLE data")
            cursor.execute("CREATE TABLE IF NOT EXISTS data(file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels);")
            database.commit()
            self.wipe_results()

    def open_scan_window(self):
        self.scan_directories = ScanWindow()

    def open_select_folders(self):
        self.select_folders = SelectWindow()

    def set_delete_mode(self, value):
        self.delete_mode_on = value

    def wipe_results(self):
        while self.column.count():
            item = self.column.takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def retrieve(self, text):
        # remove any currently running thread
        if self.worker:
            self.worker.terminate()

        # remove any previously displayed results
        self.wipe_results()

        row = QWidget()
        self.row_layout = QHBoxLayout()
        self.row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        row.setLayout(self.row_layout)
        self.column.addWidget(row)
        self.count = 0

        self.text = text
        if not re.match('^\w+$', self.text):
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("Please only use valid ascii characters!")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return

        self.worker = Worker(self.text)
        self.worker.output.connect(self.add_image)
        self.worker.start()

    def add_image(self, image_loc):
        if self.count == 5:
            row = QWidget()
            self.row_layout = QHBoxLayout()
            row.setLayout(self.row_layout)
            self.row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.column.addWidget(row)
            self.count = 0

        label = ClickLabel(image_loc)
        height = self.size.height()
        height = height//5
        width = self.size.width()
        width = width//5 - width//80
        label.setMinimumHeight(height)
        label.setMaximumHeight(height)
        label.setMinimumWidth(width)
        label.setMaximumWidth(width)
        label.setStyleSheet("background-color : white")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(image_loc).scaled(width, height,
                                           aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                                           transformMode=Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(pixmap)
        label.clicked.connect(self.open_image)
        label.delete.connect(self.remove_image)

        self.row_layout.addWidget(label)
        self.count += 1

    def open_image(self, image_loc):
        ImageWindow(image_loc)

    def remove_image(self, image_loc):
        if self.delete_mode_on:
            database = sqlite3.connect("classification.db", check_same_thread=False)
            cursor = database.cursor()
            query = cursor.execute("SELECT file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels from data WHERE file_path='{0}'".format(image_loc))
            file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels = query.fetchall()[0]
            coco_boxes = pickle.loads(coco_boxes)
            coco_classes = json.loads(coco_classes)
            face_boxes = pickle.loads(face_boxes)
            faces_cropped = pickle.loads(faces_cropped)
            face_labels = json.loads(face_labels)

            # find indexes or values to discard
            discard_coco = [i for i in range(len(coco_classes)) if self.text in coco_classes[i]]
            discard_face = [i for i in range(len(face_labels)) if self.text in face_labels[i]]

            # discard values
            for i in discard_coco[::-1]:
                coco_boxes.pop(i)
                coco_classes.pop(i)
            for i in discard_face[::-1]:
                face_boxes.pop(i)
                faces_cropped.pop(i)
                face_labels.pop(i)
            natural_scene = None if natural_scene is not None and self.text in natural_scene else natural_scene
            place = None if place is not None and self.text in place else place

            coco_boxes = pickle.dumps(coco_boxes)
            coco_classes = json.dumps(coco_classes)
            face_boxes = pickle.dumps(face_boxes)
            faces_cropped = pickle.dumps(faces_cropped)
            face_labels = json.dumps(face_labels)

            cursor.execute("DELETE FROM data WHERE file_path='{0}'".format(image_loc))
            dataframe = (file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels)
            cursor.execute("INSERT INTO data(file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels) values (?,?,?,?,?,?,?,?,?)",
                                       dataframe)
            database.commit()
            self.retrieve(self.text)