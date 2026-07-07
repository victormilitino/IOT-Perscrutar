import cv2
import os
import numpy as np
from utils import carregar_cascade

class FaceEngine:

    def __init__(self):
        self.detector_frontal = carregar_cascade('haarcascade_frontalface_default.xml')
        self.detector_perfil = carregar_cascade('haarcascade_profileface.xml')
        self.detector_olhos = carregar_cascade('haarcascade_eye.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.labels = {}
        self.trained = False

    def train(self, people):
        faces = []
        labels = []
        for i, p in enumerate(people):
            if os.path.isdir(p.image_path):
                print(f'[TREINO] Carregando múltiplos ângulos de: {p.name}')
                for filename in os.listdir(p.image_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        img_path = os.path.join(p.image_path, filename)
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            faces.append(img)
                            labels.append(i)
                self.labels[i] = p
            elif os.path.isfile(p.image_path):
                img = cv2.imread(p.image_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    detections = self.detector_frontal.detectMultiScale(img, 1.1, 4)
                    for x, y, w, h in detections:
                        faces.append(img[y:y + h, x:x + w])
                        labels.append(i)
                    self.labels[i] = p
        if faces:
            self.recognizer.train(faces, np.array(labels))
            self.trained = True
            print(f'[TREINO] Pronto! Inteligência calibrada com {len(faces)} imagens multifacetadas.')

    def detect_and_recognize(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = list(self.detector_frontal.detectMultiScale(gray, 1.1, 4))
        if len(detections) == 0:
            detections = list(self.detector_perfil.detectMultiScale(gray, 1.1, 4))
        if len(detections) == 0:
            gray_flipped = cv2.flip(gray, 1)
            detections_flipped = self.detector_perfil.detectMultiScale(gray_flipped, 1.1, 4)
            largura_img = gray.shape[1]
            for x, y, w, h in detections_flipped:
                x_real = largura_img - x - w
                detections.append((x, y, w, h))
        results = []
        for x, y, w, h in detections:
            face = gray[y:y + h, x:x + w]
            face_resized = cv2.resize(face, (200, 200))
            if self.trained:
                label, confidence = self.recognizer.predict(face_resized)
                person = self.labels.get(label) if confidence < 80 else None
            else:
                person = None
            olhos = self.detector_olhos.detectMultiScale(face, 1.1, 5)
            olhos_detectados = len(olhos) > 0
            results.append((x, y, w, h, person, olhos_detectados))
        return results