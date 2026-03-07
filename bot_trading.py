
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import ccxt
import time
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

exchange = ccxt.binance({
    "apiKey": "SUA_API_KEY_AQUI",
    "secret": "SEU_API_SECRET_AQUI",
    "enableRateLimit": True,
})

gatilhos_pendentes = []

class NovoGatilho(BaseModel):
    moeda: str
    preco_alvo: float
    quantidade_usd: float

@app.post("/api/novo_gatilho")
def criar_gatilho(gatilho: NovoGatilho):
    novo_id = len(gatilhos_pendentes) + 1
    ordem_info = {
        "id": novo_id,
        "moeda": gatilho.moeda.upper(),
        "preco_alvo": gatilho.preco_alvo,
        "quantidade_usd": gatilho.quantidade_usd,
        "status": "PENDENTE"
    }
    gatilhos_pendentes.append(ordem_info)
    return {"msg": "Gatilho salvo!", "ordem": ordem_info}

@app.get("/api/meus_gatilhos")
def listar_gatilhos():
    return {"gatilhos": gatilhos_pendentes}

@app.get("/api/preco_atual/{moeda}")
def preco_atual(moeda: str):
    try:
        ticker = exchange.fetch_ticker(moeda.replace("-", "/"))
        return {"preco": ticker["last"]}
    except:
        return {"preco": 0}

async def loop_de_monitoramento():
    while True:
        try:
            for ordem in gatilhos_pendentes:
                if ordem["status"] == "PENDENTE":
                    ticker = exchange.fetch_ticker(ordem["moeda"])
                    preco_atual = ticker["last"]
                    
                    if preco_atual <= ordem["preco_alvo"]:
                        print(f"\n[GATILHO] O preco bateu ${preco_atual}! Comprando ${ordem['quantidade_usd']} de {ordem['moeda']}!")
                        ordem["status"] = "COMPRADO_SUCESSO"
        except:
            pass
        await asyncio.sleep(5) 

@app.on_event("startup")
async def iniciar_bot():
    print("\n?? Bot de Trading Vigia Iniciado Com Sucesso!")
    asyncio.create_task(loop_de_monitoramento())
    
app.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    uvicorn.run("bot_trading:app", host="127.0.0.1", port=5555, reload=True)

