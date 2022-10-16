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


# custom thread class
class Worker(QThread):
    countChanged = pyqtSignal(int)
    finished = pyqtSignal(str)
    output = pyqtSignal(str)

    def run(self):
        count = 0
        self.output.emit("Indexing images.....")
        for i in self.image_data_generator():
            count += 1
        self.total_n = count
        self.output.emit("Done.")
        self.classify()

    def classify(self, backend='cpu'):
        work_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(work_dir, 'data.pkl'), 'rb') as f:
            data = pickle.loads(f.read())

        classificationdb = sqlite3.connect(os.path.join(work_dir, 'classification.db'), check_same_thread=False)
        classification = classificationdb.cursor()
        classification.execute("CREATE TABLE IF NOT EXISTS data(file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels);")

        nclasses = data['natural_scenes']['class_indices']
        classes =  data['places']['class_indices']

        natural = Classifier('natural_scenes.onnx', 1/255.0 , (128, 128), backend=backend)
        bin_natural = Classifier('binary_natural_scenes.onnx', 1/255.0 , (128, 128), backend=backend)
        bin_places = Classifier('binary_places.onnx', 1/255.0 , (128, 128), backend=backend)
        places = Classifier('places.onnx', 1, (224, 224), backend=backend)

        coco_classes = data['coco']['class_indices']
        coco_detector = Detector('coco.onnx', 1/255.0, (640, 640), backend=backend)

        face_detector = Detector('face.onnx', 1/255.0, (640, 640), backend=backend)

        count = 0
        total_time = time()

        for fpath, date, image in self.image_data_generator():

            results = classification.execute("SELECT COUNT(*) FROM data WHERE file_path='{0}'".format(fpath)).fetchall()[0][0]
            if results>0:
                results = classification.execute("SELECT date_modified FROM data WHERE file_path='{0}'".format(fpath)).fetchall()[0][0]
                if date==results:
                    continue
                classification.execute("DELETE FROM data WHERE file_path='{0}' AND date_modified='{1}'".format(fpath, date))

            start = time()

            output = natural.classify(image)
            bin_output = bin_natural.classify(image)
            natural_key = nclasses[output[0]] if bin_output[1]<0.01 and output[1]>0.9 else None
            output = places.classify(image)
            bin_output = bin_places.classify(image)
            places_key = classes[output[0]] if bin_output[1]>0.99 and output[1]>0.7 else None

            coco_boxes, class_ids = coco_detector.detect(image)
            coco_names = [coco_classes[class_id] for class_id in class_ids]

            face_boxes, class_ids = face_detector.detect(image)
            faces_names = ['face' for class_id in class_ids]
            faces = [image[box[1]:box[1]+box[3], box[0]:box[0]+box[2]] for box in face_boxes]

            dataframe = (fpath, date,
                         natural_key, places_key,
                         pickle.dumps(coco_boxes), json.dumps(coco_names),
                         pickle.dumps(face_boxes), pickle.dumps(faces), json.dumps(faces_names))

            classification.execute("INSERT INTO data(file_path, date_modified, natural_scene, place, coco_boxes, coco_classes, face_boxes, faces_cropped, face_labels) values (?,?,?,?,?,?,?,?,?)",
                                       dataframe)
            classificationdb.commit()

            self.output.emit(str(dataframe[0]))
            print(dataframe[0:4], dataframe[5], dataframe[-1])

            count += 1
            progress_pc = int(100 * float(count + 1) / self.total_n)
            self.output.emit("Elapsed : " + str(time()-start))
            self.countChanged.emit(progress_pc)

        self.output.emit("Total time elapsed : " + str(time()-total_time))
        self.finished.emit("Finished.")

    def image_data_generator(self):
        conn = sqlite3.connect("folders.db")
        cur = conn.cursor()
        cur.execute("select path from paths")
        dir_ = [os.walk(path[0]) for path in cur.fetchall()]
        for root, dirs, files in chain.from_iterable(dir_):
            for name in files:
                file_path = os.path.join(root, name)
                image = imread(file_path)
                if image is not None:
                    date_modified = os.path.getmtime(file_path)
                    yield file_path, date_modified, image
