from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sqlite3
import sys
import re
import os
import cv2
import pickle
import json


class ImageWindow(QMainWindow):
    def __init__(self, image_loc):
        super().__init__()
        self.showMaximized()

        self.image_loc = image_loc

        self.scaleFactor = 0.0

        self.imageLabel = QLabel()
        self.imageLabel.setStyleSheet("background-color : white")
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imageLabel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scrollArea.setVisible(False)
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        self.button = QAction("Show Boxes", self)
        self.button.setStatusTip("Show bounding boxes on objects or faces")
        self.button.setCheckable(True)

        self.button.toggled.connect(lambda: self.bounding(image_loc, self.imageLabel))
        toolbar.addAction(self.button)

        self.setCentralWidget(self.scrollArea)
        self.setWindowTitle(os.path.basename(image_loc))
        self.createActions()
        self.createMenus()
        self.open()

    def open(self):
        if self.image_loc:
            image = QImage(self.image_loc)
            if image.isNull():
                QMessageBox.information(self, "Image Viewer", "Cannot load %s." % os.path.basename(self.image_loc))
                return

            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            self.scaleFactor = 1.0

            self.scrollArea.setVisible(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def createActions(self):
        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.zoomInAct = QAction("Zoom &In (25%)", self, shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)
        self.zoomOutAct = QAction("Zoom &Out (25%)", self, shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)
        self.normalSizeAct = QAction("&Normal Size", self, shortcut="Ctrl+S", enabled=False, triggered=self.normalSize)
        self.fitToWindowAct = QAction("&Fit to Window", self, enabled=False, checkable=True, shortcut="Ctrl+F",
                                      triggered=self.fitToWindow)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))

    def bounding(self, image_loc, label):
        if not self.button.isChecked():
            self.open()
            return

        image = cv2.imread(image_loc)
        classify = sqlite3.connect('classification.db')
        classify_cur = classify.cursor()
        coco = "SELECT coco_boxes, coco_classes  FROM data WHERE file_path=\"{0}\"".format(image_loc)
        faces = "SELECT face_boxes, face_labels  FROM data WHERE file_path=\"{0}\"".format(image_loc)

        for coco_boxes, coco_classes in classify_cur.execute(coco):
            coco_boxes = pickle.loads(coco_boxes)
            coco_classes = json.loads(coco_classes)
            for i in range(len(coco_classes)):
                # class_ = coco_classes[i]
                box = coco_boxes[i]
                cv2.rectangle(image, box, (0, 255, 255), 2)
                # cv2.rectangle(image, (box[0], box[1] - 20), (box[0] + box[2], box[1]), (0, 255, 255), -1)
                # cv2.putText(image, class_, (box[0], box[1] - 40), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 2)

        for face_boxes, face_labels in classify_cur.execute(faces):
            face_boxes = pickle.loads(face_boxes)
            face_labels = json.loads(face_labels)
            for i in range(len(face_labels)):
                # class_ = face_labels[i]
                box = face_boxes[i]
                cv2.rectangle(image, box, (0, 255, 255), 2)
                # cv2.rectangle(image, (box[0], box[1] - 20), (box[0] + box[2], box[1]), (0, 255, 255), -1)
                # cv2.putText(image, class_, (box[0], box[1] - 40), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 2)

        height, width, channel = image.shape
        bytesPerLine = 3 * width
        qImg = QImage(image.data, width, height, bytesPerLine, QImage.Format.Format_BGR888)
        label.setPixmap(QPixmap(qImg))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
