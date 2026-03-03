import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import router as game_router
import socket_handler
from database import init_db

app = FastAPI(title="NeroCoin Farm Game - Server Autoritativo")

# Permite que o Frontend se conecte ao Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conecta as Rotas da API
app.include_router(game_router)

# Anexa o Socket.IO ao FastAPI (Para a comunicação em Tempo Real)
app.mount("/", socket_handler.socket_app)

if __name__ == "__main__":
    init_db() # Cria as tabelas do banco de dados na primeira vez
    print("🚀 Servidor do Jogo Iniciando em http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)