from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List
from passlib.context import CryptContext
import secrets

app = FastAPI()
security = HTTPBasic()

# Configuração para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelo Pydantic para Tarefa
class Tarefa(BaseModel):
    nome: str
    descricao: str
    concluida: bool = False

# Banco de dados simulado de usuários (em produção, use um banco de dados real)
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123")  # Senha: admin123
    }
}

# Lista para armazenar objetos Tarefa
tarefas: List[Tarefa] = []

# Função para verificar credenciais
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    user = USERS_DB.get(credentials.username)
    if not user or not pwd_context.verify(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.post("/tarefas/", response_model=Tarefa)
async def adicionar_tarefa(tarefa: Tarefa, username: str = Depends(verify_credentials)):
    # Verifica se já existe uma tarefa com o mesmo nome
    if any(t.nome == tarefa.nome for t in tarefas):
        raise HTTPException(status_code=400, detail="Tarefa com este nome já existe")
    tarefas.append(tarefa)
    return tarefa

@app.get("/tarefas/", response_model=List[Tarefa])
async def listar_tarefas(
    username: str = Depends(verify_credentials),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Itens por página"),
    sort_by: str = Query("nome", regex="^(nome|descricao|concluida)$", description="Campo para ordenação")
):
    # Validação dos parâmetros de paginação
    if page < 1:
        raise HTTPException(status_code=400, detail="O número da página deve ser maior que 0")
    if size < 1 or size > 100:
        raise HTTPException(status_code=400, detail="O tamanho da página deve estar entre 1 e 100")

    # Ordenação
    sorted_tarefas = sorted(tarefas, key=lambda x: getattr(x, sort_by))

    # Paginação
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    
    if start_idx >= len(tarefas):
        return []
    
    return sorted_tarefas[start_idx:end_idx]

@app.put("/tarefas/{nome_tarefa}", response_model=Tarefa)
async def marcar_concluida(nome_tarefa: str, username: str = Depends(verify_credentials)):
    for tarefa in tarefas:
        if tarefa.nome == nome_tarefa:
            tarefa.concluida = True
            return tarefa
    raise HTTPException(status_code=404, detail="Tarefa não encontrada")

@app.delete("/tarefas/{nome_tarefa}")
async def remover_tarefa(nome_tarefa: str, username: str = Depends(verify_credentials)):
    for i, tarefa in enumerate(tarefas):
        if tarefa.nome == nome_tarefa:
            return tarefas.pop(i)
    raise HTTPException(status_code=404, detail="Tarefa não encontrada")