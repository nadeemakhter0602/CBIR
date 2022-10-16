import cv2
import onnxruntime as rt
import os
import numpy as np
from numba import njit

work_dir = os.path.dirname(os.path.realpath(__file__))

class Classifier():
    def __init__(self, model_name, rescale, input_shape, backend='cpu'):
        self.rescale = rescale
        self.input_shape = input_shape
        if backend=='cpu' or backend=='cuda':
            provider = ['CUDAExecutionProvider' if backend=='cuda' else 'CPUExecutionProvider']
            self.model = rt.InferenceSession(os.path.join(work_dir, model_name), providers=provider)
            self.input_name = self.model.get_inputs()[0].name
        elif backend=='cv2':
            self.model = cv2.dnn_ClassificationModel(os.path.join(work_dir, model_name))
            self.model.setInputParams(self.rescale, self.input_shape)

    def classify(self, image):
        if isinstance(self.model, cv2.dnn_ClassificationModel):
            return self.model.classify(image)
        elif isinstance(self.model, rt.capi.onnxruntime_inference_collection.InferenceSession):
            blob = cv2.dnn.blobFromImage(image, self.rescale, self.input_shape)
            output = self.model.run([], {self.input_name : blob})[0][0]
            return (np.argmax(output), np.amax(output))

@njit
def _detect(outputs, image):
    image_width, image_height, _ = image.shape
    x_factor = image_width / 640
    y_factor =  image_height / 640
    outputs = [row for row in outputs if np.amax(row[5:])>0.5 and row[4]>0.5]
    confidences, class_ids = ([row[4] for row in outputs], [np.argmax(row[5:]) for row in outputs])
    xywh = [(row[0], row[1], row[2], row[3]) for row in outputs]
    boxes = [np.array([int((x - 0.5 * w) * x_factor), int((y - 0.5 * h) * y_factor), int(w * x_factor), int(h * y_factor)])
    for x, y, w, h in xywh]
    return boxes, confidences, class_ids


def format_yolov5(frame):
    row, col, _ = frame.shape
    _max = max(col, row)
    result = np.zeros((_max, _max, 3), np.uint8)
    result[0:row, 0:col] = frame
    return result


class Detector():
    def __init__(self, model_name, rescale, input_shape, backend='cpu', config=None):
        self.rescale = rescale
        self.input_shape = input_shape
        if backend=='cpu' or backend=='cuda':
            provider = ['CUDAExecutionProvider' if backend=='cuda' else 'CPUExecutionProvider']
            self.model = rt.InferenceSession(os.path.join(work_dir, model_name), providers=provider)
            self.input_name = self.model.get_inputs()[0].name
        elif backend=='cv2':
            self.model = cv2.dnn_DetectionModel(os.path.join(work_dir, model_name), config=config)
            self.model.setInputParams(self.rescale, self.input_shape)

    def detect(self, image):
        image = format_yolov5(image)

        if isinstance(self.model, cv2.dnn_DetectionModel):
            outputs = self.model.predict(image)         
        elif isinstance(self.model, rt.capi.onnxruntime_inference_collection.InferenceSession):
            blob = cv2.dnn.blobFromImage(image, self.rescale, self.input_shape)
            outputs = self.model.run([], {self.input_name : blob})
        
        boxes, confidences, class_ids = _detect(outputs[0][0], image)            
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.25, 0.5)
        boxes, class_ids = ([boxes[i] for i in indexes], [class_ids[i] for i in indexes])
        return boxes, class_ids