from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuração do banco de dados
DATABASE_URL = "sqlite:///tarefas.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()
security = HTTPBasic()

# Configuração para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelo do banco de dados
class TarefaDB(Base):
    __tablename__ = "tarefas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, unique=True)
    descricao = Column(String, index=True)
    concluida = Column(Boolean, default=False, index=True)

# Criação das tabelas
Base.metadata.create_all(bind=engine)

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelo Pydantic para Tarefa
class Tarefa(BaseModel):
    nome: str
    descricao: str
    concluida: bool = False

    class Config:
        from_attributes = True  # Permite mapear objetos do SQLAlchemy para Pydantic

# Banco de dados simulado de usuários (em produção, use um banco de dados real)
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123")  # Senha: admin123
    }
}

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
async def adicionar_tarefa(tarefa: Tarefa, db: Session = Depends(get_db), username: str = Depends(verify_credentials)):
    # Verifica se já existe uma tarefa com o mesmo nome
    existing_tarefa = db.query(TarefaDB).filter(TarefaDB.nome == tarefa.nome).first()
    if existing_tarefa:
        raise HTTPException(status_code=400, detail="Tarefa com este nome já existe")
    
    # Cria nova tarefa
    db_tarefa = TarefaDB(nome=tarefa.nome, descricao=tarefa.descricao, concluida=tarefa.concluida)
    db.add(db_tarefa)
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

@app.get("/tarefas/", response_model=List[Tarefa])
async def listar_tarefas(
    username: str = Depends(verify_credentials),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Itens por página"),
    sort_by: str = Query("nome", regex="^(nome|descricao|concluida)$", description="Campo para ordenação"),
    db: Session = Depends(get_db)
):
    # Validação dos parâmetros de paginação
    if page < 1:
        raise HTTPException(status_code=400, detail="O número da página deve ser maior que 0")
    if size < 1 or size > 100:
        raise HTTPException(status_code=400, detail="O tamanho da página deve estar entre 1 e 100")

    # Consulta com ordenação
    query = db.query(TarefaDB)
    if sort_by == "nome":
        query = query.order_by(TarefaDB.nome)
    elif sort_by == "descricao":
        query = query.order_by(TarefaDB.descricao)
    elif sort_by == "concluida":
        query = query.order_by(TarefaDB.concluida)

    # Paginação
    start_idx = (page - 1) * size
    tarefas = query.offset(start_idx).limit(size).all()
    
    return tarefas

@app.put("/tarefas/{nome_tarefa}", response_model=Tarefa)
async def marcar_concluida(nome_tarefa: str, db: Session = Depends(get_db), username: str = Depends(verify_credentials)):
    tarefa = db.query(TarefaDB).filter(TarefaDB.nome == nome_tarefa).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    tarefa.concluida = True
    db.commit()
    db.refresh(tarefa)
    return tarefa

@app.delete("/tarefas/{nome_tarefa}")
async def remover_tarefa(nome_tarefa: str, db: Session = Depends(get_db), username: str = Depends(verify_credentials)):
    tarefa = db.query(TarefaDB).filter(TarefaDB.nome == nome_tarefa).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    db.delete(tarefa)
    db.commit()
    return {"detail": "Tarefa removida com sucesso"}