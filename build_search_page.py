from time import time
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sys
from cv2 import imread
import os
import pickle
import sqlite3
from time import time
import json
from models import Classifier, Detector
from itertools import chain
import multiprocessing
import threading
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
# from PyQt6.QtGui import *


class Worker(QThread):
    output = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        classify = sqlite3.connect('classification.db')
        classify_cur = classify.cursor()
        query = "SELECT DISTINCT file_path FROM data WHERE natural_scene LIKE '%{0}%' OR place LIKE '%{0}%' OR coco_classes LIKE '%{0}%' OR face_labels LIKE '%{0}%'".format(self.text)

        for image_loc in classify_cur.execute(query):
            self.output.emit(image_loc[0])
