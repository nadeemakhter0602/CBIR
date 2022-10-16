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


class MultiScan(multiprocessing.Process):

    def __init__(self, choice):
        super().__init__()
        self.choice = choice


    def run(self):
    # if self.choice==0:
        self.classify()
    # elif self.choice==1:
        self.coco_detect()
    # elif self.choice==2:
        self.face_detect()


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


    def classify(self, backend='cpu', pbar=None, label=None):
        work_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(work_dir, 'data.pkl'), 'rb') as f:
            data = pickle.loads(f.read())
        nclasses = data['natural_scenes']['class_indices']
        classes =  data['places']['class_indices']
        conn = sqlite3.connect(os.path.join(work_dir, 'classify.db'), check_same_thread=False)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS data(file_path, date_modified, natural_scene, place);')
        natural = Classifier('natural_scenes.onnx', 1/255.0 , (128, 128), backend=backend)
        bin_natural = Classifier('binary_natural_scenes.onnx', 1/255.0 , (128, 128), backend=backend)
        bin_places = Classifier('binary_places.onnx', 1/255.0 , (128, 128), backend=backend)
        places = Classifier('places.onnx', 1, (224, 224), backend=backend)
        for fpath, date, image in self.image_data_generator():
            start = time()
            output = natural.classify(image)
            bin_output = bin_natural.classify(image)
            natural_key = nclasses[output[0]] if bin_output[1]<0.01 and output[1]>0.9 else None
            output = places.classify(image)
            bin_output = bin_places.classify(image)
            places_key = classes[output[0]] if bin_output[1]>0.99 and output[1]>0.7 else None
            dataframe = (fpath, date, natural_key, places_key)
            print(dataframe)
            cur.execute("INSERT INTO data(file_path, date_modified, natural_scene, place) values (?,?,?,?)", dataframe)
            print("Elapsed :", time()-start)
        conn.commit()


    def coco_detect(self, backend='cpu', pbar=None, label=None):
        work_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(work_dir, 'data.pkl'), 'rb') as f:
            data = pickle.loads(f.read())
        coco_classes = data['coco']['class_indices']
        conn = sqlite3.connect(os.path.join(work_dir, 'coco.db'), check_same_thread=False)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS data(file_path, date_modified, boxes, classes);')
        model = Detector('coco.onnx', 1/255.0, (640, 640), backend=backend)
        for fpath, date, image in self.image_data_generator():
            start = time()
            boxes, class_ids = model.detect(image)
            class_names = [coco_classes[class_id] for class_id in class_ids]
            dataframe = (fpath, date, pickle.dumps(boxes), json.dumps(class_names))
            print(dataframe[0],dataframe[1],dataframe[3])
            cur.execute("INSERT INTO data(file_path, date_modified, boxes, classes) values (?,?,?,?)", dataframe)
            print("Elapsed :", time()-start)
        conn.commit()


    def face_detect(self, backend='cpu', pbar=None, label=None):
        work_dir = os.path.dirname(os.path.realpath(__file__))
        conn = sqlite3.connect(os.path.join(work_dir, 'face.db'), check_same_thread=False)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS data(file_path, date_modified, box, face, label);')
        model = Detector('face.onnx', 1/255.0, (640, 640), backend=backend)
        for fpath, date, image in self.image_data_generator():
            start = time()
            boxes, class_ids = model.detect(image)
            faces = [image[box[1]:box[1]+box[3], box[0]:box[0]+box[2]] for box in boxes]
            dataframe = [(fpath, date, pickle.dumps(boxes[i]), pickle.dumps(faces[i]), None) for i in range(len(faces))]
            print(fpath, date)
            cur.executemany("INSERT INTO data(file_path, date_modified, box, face, label) values (?,?,?,?,?)", dataframe)
            print("Elapsed :", time()-start)
        conn.commit()


if __name__=='__main__':
    start = time()
    # classify = MultiScan(0)
    # coco = MultiScan(1)
    face = MultiScan(2)
    # classify.start()
    # coco.start()
    face.start()
    # classify.join()
    # coco.join()
    face.join()
    print('total time :', time()-start)
