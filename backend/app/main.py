import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
DB_PATH = 'backend.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS people (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            name TEXT NOT NULL,\n            tag TEXT NOT NULL UNIQUE,\n            image_path TEXT\n        )\n    ')
    conn.commit()
    conn.close()
    print('[BACKEND] Banco de dados SQLite inicializado com sucesso.')

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    print('[BACKEND] Encerrando serviços do backend.')
app = FastAPI(title='Perscrutar Acesso API', lifespan=lifespan)

@app.get('/')
def root():
    return {'status': 'ok', 'message': 'Perscrutar Acesso - API no ar'}

@app.get('/validar-tag')
def validar_tag(uid: str):
    tag = uid.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM people WHERE tag = ?', (tag,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'liberado': True, 'nome': row['name']}
    return {'liberado': False, 'nome': None}

class PessoaCadastro(BaseModel):
    name: str
    tag: str

@app.post('/pessoas')
def cadastrar_pessoa(pessoa: PessoaCadastro):
    tag = pessoa.tag.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO people (name, tag) VALUES (?, ?)', (pessoa.name.strip(), tag))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail='Essa tag já está cadastrada.')
    conn.close()
    return {'status': 'cadastrado', 'nome': pessoa.name, 'tag': tag}

@app.get('/pessoas')
def listar_pessoas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, tag FROM people')
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r['id'], 'nome': r['name'], 'tag': r['tag']} for r in rows]

@app.delete('/pessoas/{tag}')
def remover_pessoa(tag: str):
    tag = tag.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM people WHERE tag = ?', (tag,))
    conn.commit()
    removido = cursor.rowcount > 0
    conn.close()
    if not removido:
        raise HTTPException(status_code=404, detail='Tag não encontrada.')
    return {'status': 'removido', 'tag': tag}