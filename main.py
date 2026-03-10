import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import router as game_router
import socket_handler
from database import init_db
import socketio

app = FastAPI(title="NeroCoin Farm Game - Server Autoritativo")

from fastapi.responses import FileResponse

@app.get("/")
async def root():
    return FileResponse("index.html")

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

# Servir a pasta public em "/public" para nÃ£o sobrescrever rotas /api
app.mount("/public", StaticFiles(directory="public", html=True), name="public")

# AplicaÃ§Ã£o ASGI combinada com o SocketIO
main_app = socketio.ASGIApp(socket_handler.sio, other_asgi_app=app)

if __name__ == "__main__":
    init_db() # Cria as tabelas do banco de dados na primeira vez
    print("Servidor do Jogo iniciando em http://localhost:8000")
    import os
    os.environ["UVICORN_APP"] = "main:main_app"
    # Use IPv6 wildcard so 'localhost' (often ::1 on Windows) works and ngrok can reach the upstream.
    uvicorn.run("main:main_app", host="::", port=8000, reload=True)
