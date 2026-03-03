import socketio
import time
from database import get_db

# Criação do servidor Socket.IO (Assíncrono para aguentar muitos jogadores)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"🎮 Novo jogador conectou na fazenda! ID da sessão: {sid}")

@sio.event
async def disconnect(sid):
    print(f"❌ Jogador desconectou: {sid}")

# =======================================================
# LÓGICA AUTORITATIVA DE FARMING
# Todo clique/colheita do Frontend precisa passar por aqui
# =======================================================

@sio.on("start_farming")
async def start_farming(sid, data):
    wallet = data.get("wallet")
    farmer_id = data.get("farmer_id")
    
    # Validação Básica Anti-Cheat: Verificar se os dados existem
    if not wallet or not farmer_id:
        await sio.emit("error_msg", {"msg": "Ação de farm inválida!"}, to=sid)
        return

    conn = get_db()
    cursor = conn.cursor()
    
    # Checa se o fazendeiro pertence à pessoa e se ele está livre
    cursor.execute("SELECT is_working FROM farmers WHERE farmer_id = ? AND wallet_address = ?", (farmer_id, wallet))
    farmer = cursor.fetchone()
    
    if not farmer:
        await sio.emit("error_msg", {"msg": "Fazendeiro não pertence a você."}, to=sid)
    elif farmer['is_working']:
        await sio.emit("error_msg", {"msg": "O fazendeiro já está trabalhando na plantação!"}, to=sid)
    else:
        # Põe ele pra trabalhar salvando a HORA REAL DO SERVIDOR (Impossível burlar mudando a hora do Windows do jogador)
        current_time = int(time.time())
        cursor.execute("UPDATE farmers SET is_working = 1, last_harvest_time = ? WHERE farmer_id = ?", (current_time, farmer_id))
        conn.commit()
        print(f"🌾 Fazendeiro {farmer_id} começou a trabalhar para {wallet}!")
        
        await sio.emit("farm_started", {"farmer_id": farmer_id, "start_time": current_time, "duration": 86400}, to=sid) # 86400 = 24hrs em segundos

    conn.close()

@sio.on("claim_nero")
async def claim_nero(sid, data):
    wallet = data.get("wallet")
    farmer_id = data.get("farmer_id")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM farmers WHERE farmer_id = ? AND wallet_address = ?", (farmer_id, wallet))
    farmer = cursor.fetchone()
    
    if not farmer or not farmer['is_working']:
        await sio.emit("error_msg", {"msg": "Fazendeiro inválido ou não está trabalhando."}, to=sid)
        conn.close()
        return
        
    current_time = int(time.time())
    tempo_trabalhado = current_time - farmer['last_harvest_time']
    
    # Verifica se já passou tempo suficiente (Para testes, deixaremos que colha se já passou de 5 segundos)
    # No jogo final você colocaria 86400 (24h)
    TEMPO_MINIMO_COLHEITA = 5 
    
    if tempo_trabalhado < TEMPO_MINIMO_COLHEITA:
        await sio.emit("error_msg", {"msg": f"Ainda não deu tempo de colher o Nero. Faltam {TEMPO_MINIMO_COLHEITA - tempo_trabalhado}s!"}, to=sid)
        conn.close()
        return
        
    # Lógica Real de ganhos! (Poder do Trabalhador * Recompensa Base)
    ganho_base = 10 
    nero_gerado = ganho_base * farmer['farming_power']
    
    # 1. Dá o dinheiro pro jogador (Soma o saldo)
    cursor.execute("UPDATE players SET nero_balance = nero_balance + ? WHERE wallet_address = ?", (nero_gerado, wallet))
    
    # 2. Reseta o fazendeiro (Ele cansa e volta a ficar livre para trabalhar de novo)
    cursor.execute("UPDATE farmers SET is_working = 0, last_harvest_time = NULL WHERE farmer_id = ?", (farmer_id,))
    
    conn.commit()
    
    # Pega o saldo atualizado para mostrar na tela e não deixar dúvidas
    cursor.execute("SELECT nero_balance FROM players WHERE wallet_address = ?", (wallet,))
    novo_saldo = cursor.fetchone()['nero_balance']
    
    conn.close()
    
    print(f"💰 {wallet} colheu {nero_gerado} NERO!")
    await sio.emit("claim_success", {"farmer_id": farmer_id, "amount_won": nero_gerado, "new_balance": novo_saldo}, to=sid)