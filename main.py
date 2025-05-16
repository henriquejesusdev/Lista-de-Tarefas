from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Modelo Pydantic para Tarefa
class Tarefa(BaseModel):
    nome: str
    descricao: str
    concluida: bool = False

# Lista para armazenar objetos Tarefa
tarefas: List[Tarefa] = []

@app.post("/tarefas/", response_model=Tarefa)
async def adicionar_tarefa(tarefa: Tarefa):
    tarefas.append(tarefa)
    return tarefa

@app.get("/tarefas/", response_model=List[Tarefa])
async def listar_tarefas():
    return tarefas

@app.put("/tarefas/{nome_tarefa}", response_model=Tarefa)
async def marcar_concluida(nome_tarefa: str):
    for tarefa in tarefas:
        if tarefa.nome == nome_tarefa:
            tarefa.concluida = True
            return tarefa
    raise HTTPException(status_code=404, detail="Tarefa não encontrada")

@app.delete("/tarefas/{nome_tarefa}")
async def remover_tarefa(nome_tarefa: str):
    for i, tarefa in enumerate(tarefas):
        if tarefa.nome == nome_tarefa:
            return tarefas.pop(i)
    raise HTTPException(status_code=404, detail="Tarefa não encontrada")