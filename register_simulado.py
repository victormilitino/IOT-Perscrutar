import os
import cv2
from database import Database
from models import Person
from utils import carregar_cascade
face_cascade = carregar_cascade('haarcascade_frontalface_default.xml')
profile_cascade = carregar_cascade('haarcascade_profileface.xml')

def buscar_rosto_todos_angulos(frame_cinza):
    faces = face_cascade.detectMultiScale(frame_cinza, 1.1, 4)
    if len(faces) > 0:
        return faces
    faces_esq = profile_cascade.detectMultiScale(frame_cinza, 1.1, 4)
    if len(faces_esq) > 0:
        return faces_esq
    frame_espelhado = cv2.flip(frame_cinza, 1)
    faces_dir = profile_cascade.detectMultiScale(frame_espelhado, 1.1, 4)
    if len(faces_dir) > 0:
        largura_imagem = frame_cinza.shape[1]
        faces_corrigidas = []
        for x, y, w, h in faces_dir:
            x_real = largura_imagem - x - w
            faces_corrigidas.append((x_real, y, w, h))
        return faces_corrigidas
    return []

def register_person():
    db = Database()
    name = input('Nome: ')
    tag = input('Tag (digite um texto único, ex: TAG001): ').strip()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print('Erro ao acessar a câmera')
        return
    print("Pressione 'c' para iniciar a captura de fotos. Mova o rosto devagar.")
    print("Pressione 'q' para sair sem salvar.")
    saved = False
    person_dir = f'faces/{name}'
    os.makedirs(person_dir, exist_ok=True)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray_preview = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_detected = buscar_rosto_todos_angulos(gray_preview)
        frame_clone = frame.copy()
        for x, y, w, h in faces_detected:
            cv2.rectangle(frame_clone, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow('Cadastro (teste local)', frame_clone)
        key = cv2.waitKey(1) & 255
        if key == ord('c'):
            print('Capturando... Gire o rosto devagar (lados, cima, baixo)!')
            count = 0
            while count < 30:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = buscar_rosto_todos_angulos(gray)
                for x, y, w, h in faces:
                    face_roi = gray[y:y + h, x:x + w]
                    face_roi = cv2.resize(face_roi, (200, 200))
                    cv2.imwrite(f'{person_dir}/{count}.jpg', face_roi)
                    count += 1
                cv2.imshow('Cadastro (teste local)', frame)
                cv2.waitKey(1)
            print(f'Dataset criado em {person_dir}')
            saved = True
            break
        elif key == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    if not saved:
        print('Cadastro cancelado.')
        return
    person = Person(name=name, image_path=person_dir, tag=tag)
    db.add_person(person)
    print(f"Pessoa '{name}' cadastrada (id={person.id}) com tag '{tag}'.")
if __name__ == '__main__':
    register_person()