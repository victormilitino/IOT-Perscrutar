# FaceTag — Backend

Backend do sistema FaceTag

## Como rodar

### 1. Entrar na pasta do backend

```bash
cd backend
```

### 2. Criar e ativar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3. Instalar dependências

```bash
pip3 install -r requirements.txt
```

### 4. Subir o servidor

```bash
python3 -m uvicorn app.main:app --reload
```

Servidor: http://127.0.0.1:8000

Documentação: http://127.0.0.1:8000/docs
