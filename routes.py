
from fastapi import APIRouter, Request, HTTPException, Body
from database import get_db
import sqlite3
import hashlib
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel

router = APIRouter()

# Endpoint para encerrar (excluir) bot e transferir saldo para usuário
class BotEncerrarRequest(BaseModel):
    usuario_email: str
    bot_id: int

@router.post("/api/bots/encerrar")
async def encerrar_bot(request: BotEncerrarRequest):
    conn = get_db()
    cursor = conn.cursor()
    # Busca bot
    cursor.execute("SELECT saldo FROM bots WHERE id = ? AND usuario_email = ?", (request.bot_id, request.usuario_email))
    bot = cursor.fetchone()
    if not bot:
        conn.close()
        return {"success": False, "detail": "Bot não encontrado."}
    saldo_bot = bot['saldo']
    # Busca usuário
    cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (request.usuario_email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return {"success": False, "detail": "Usuário não encontrado."}
    novo_saldo_usuario = user['saldo'] + saldo_bot
    # Atualiza saldo do usuário
    cursor.execute("UPDATE usuarios SET saldo = ? WHERE id = ?", (novo_saldo_usuario, user['id']))
    # Exclui bot
    cursor.execute("DELETE FROM bots WHERE id = ?", (request.bot_id,))
    conn.commit()
    conn.close()
    return {"success": True, "novo_saldo_usuario": novo_saldo_usuario}
# Endpoint para transferir saldo do usuário para o bot
class BotSaldoRequest(BaseModel):
    usuario_email: str
    bot_id: int
    valor: float

@router.post("/api/bots/adicionar_saldo")
async def adicionar_saldo_bot(request: BotSaldoRequest):
    if request.valor <= 0:
        return {"success": False, "detail": "Valor inválido."}
    conn = get_db()
    cursor = conn.cursor()
    # Busca usuário
    cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (request.usuario_email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return {"success": False, "detail": "Usuário não encontrado."}
    if user['saldo'] < request.valor:
        conn.close()
        return {"success": False, "detail": "Saldo insuficiente."}
    # Busca bot
    cursor.execute("SELECT saldo FROM bots WHERE id = ? AND usuario_email = ?", (request.bot_id, request.usuario_email))
    bot = cursor.fetchone()
    if not bot:
        conn.close()
        return {"success": False, "detail": "Bot não encontrado."}
    # Atualiza saldos
    novo_saldo_usuario = user['saldo'] - request.valor
    novo_saldo_bot = bot['saldo'] + request.valor
    cursor.execute("UPDATE usuarios SET saldo = ? WHERE id = ?", (novo_saldo_usuario, user['id']))
    cursor.execute("UPDATE bots SET saldo = ? WHERE id = ?", (novo_saldo_bot, request.bot_id))
    conn.commit()
    conn.close()
    return {"success": True, "novo_saldo_usuario": novo_saldo_usuario, "novo_saldo_bot": novo_saldo_bot}

from fastapi import APIRouter, Request, HTTPException
from database import get_db
import sqlite3
import hashlib
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel

router = APIRouter()

# Endpoint para ativar bot do usuário em uma partida
class BotAtivarRequest(BaseModel):
    usuario_email: str
    bot_id: int
    partida_id: int

@router.post("/api/bots/ativar")
async def ativar_bot(request: BotAtivarRequest):
    conn = get_db()
    cursor = conn.cursor()
    # Busca bot
    cursor.execute("SELECT * FROM bots WHERE id = ? AND usuario_email = ?", (request.bot_id, request.usuario_email))
    bot = cursor.fetchone()
    if not bot:
        conn.close()
        return {"success": False, "detail": "Bot não encontrado para este usuário."}

    # Busca partida
    cursor.execute("SELECT * FROM partidas WHERE id = ?", (request.partida_id,))
    partida = cursor.fetchone()
    if not partida:
        conn.close()
        return {"success": False, "detail": "Partida não encontrada."}

    # Restrição: impedir bots do mesmo usuário juntos
    cursor.execute("SELECT b.usuario_email FROM bots b JOIN partidas p ON p.id = ? WHERE b.usuario_email = ?", (request.partida_id, request.usuario_email))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "detail": "Já existe um bot deste usuário na partida."}

    # Aqui seria a integração com a lógica de partida/socket_handler
    # Exemplo: adicionar bot à partida, iniciar auto-play, etc.
    # (A integração real depende do fluxo do socket_handler)

    conn.close()
    return {"success": True, "detail": "Bot ativado na partida."}
from fastapi import APIRouter, Request, HTTPException
from database import get_db
from pydantic import BaseModel
import sqlite3

# Endpoint para ativar bot do usuário em uma partida
class BotAtivarRequest(BaseModel):
    usuario_email: str
    bot_id: int
    partida_id: int
import hashlib
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter()


class BotCreateRequest(BaseModel):
    usuario_email: str
    nome: str
    saldo: float
    stop_loss: float
    stop_win: float
    valor_aposta: float

@router.post("/api/bots/criar")
async def criar_bot(request: BotCreateRequest):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bots (usuario_email, nome, saldo, stop_loss, stop_win, valor_aposta, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (request.usuario_email, request.nome, request.saldo, request.stop_loss, request.stop_win, request.valor_aposta, 'Parado'))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "detail": str(e)}

GOOGLE_CLIENT_ID = "718604370086-acag935gch24qo5qt0s3on0os4bjaugk.apps.googleusercontent.com" # Cole aqui a chave gerada no Google Cloud Console

class GoogleLoginRequest(BaseModel):
    token: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

# Palavras proibidas (adicione mais se quiser)
BAD_WORDS = [
    "palavrao", "porra", "caralho", "buceta", "fode", "merda", 
    "puta", "cuzao", "cuzão", "pica", "rola", "viado", "veado", 
    "arrombado", "fudido", "corno", "vadia", "fdp"
]

def contains_bad_word(text: str) -> bool:
    text = text.lower()
    for word in BAD_WORDS:
        if re.search(rf'\b{word}\b', text):
            return True
    return False

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

@router.get("/api/ultimos-ganhadores")
async def get_ultimos_ganhadores():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.email, t.valor
        FROM transacoes t
        JOIN usuarios u ON u.id = t.usuario_id
        WHERE t.tipo = 'Premio'
        ORDER BY t.data DESC
        LIMIT 15
    """)
    rows = cursor.fetchall()
    conn.close()

    resultados = []
    for row in rows:
        email = row['email']
        nome_curto = email[:3].capitalize() + "***"
        prefix = "R$ "
        resultados.append(f"{nome_curto} ganhou {prefix}{row['valor']:.2f}")

    if not resultados:
        resultados = [
            "Joa*** ganhou R$ 3.80",
            "Mar*** ganhou R$ 15.20",
            "Car*** ganhou R$ 76.00",
            "Luc*** ganhou R$ 7.60",
            "Ped*** ganhou R$ 38.00"
        ]
    return resultados

@router.post("/api/register")
async def register_game(request: RegisterRequest):
    """
    Função de registro com verificação de palavrões.
    """
    conn = get_db()
    cursor = conn.cursor()

    email_limpo = request.email.lower().strip()
    username_limpo = request.username.strip()

    if not email_limpo or not request.password or not username_limpo:
        conn.close()
        raise HTTPException(status_code=400, detail="Preencha todos os campos!")

    if contains_bad_word(username_limpo):
        conn.close()
        raise HTTPException(status_code=400, detail="Nome de usuário contém palavras inadequadas!")

    cursor.execute("SELECT * FROM players WHERE email = ?", (email_limpo,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Este e-mail já está em uso!")

    senha_hash = hash_senha(request.password)

    # Cria novo jogador
    cursor.execute("INSERT INTO players (email, password, game_username) VALUES (?, ?, ?)", (email_limpo, senha_hash, username_limpo))
    # Dá o primeiro fazendeiro grátis
    cursor.execute("INSERT INTO farmers (email, farmer_name, farming_power) VALUES (?, ?, ?)", (email_limpo, "Jão Trabaiadô", 1.5))
    
    conn.commit()
    conn.close()

    return {"success": True, "message": "Conta criada com sucesso!"}

@router.post("/api/login")
async def login_game(request: LoginRequest):
    """
    Função de login com email e senha.
    Se o email não existir, ele cria a conta automaticamente com a senha fornecida!
    """
    conn = get_db()
    cursor = conn.cursor()

    email_limpo = request.email.lower().strip()
    senha_hash = hash_senha(request.password)

    cursor.execute("SELECT * FROM players WHERE email = ?", (email_limpo,))
    player = cursor.fetchone()

    if not player:
        conn.close()
        raise HTTPException(status_code=401, detail="Conta não encontrada!")
    else:
        # Conta já existe, checa a senha
        if player['password'] != senha_hash:
            conn.close()
            raise HTTPException(status_code=401, detail="Senha incorreta! Tente novamente.")

    # Pega todos os fazendeiros desse jogador
    cursor.execute("SELECT farmer_id, farmer_name, farming_power, is_working, last_harvest_time FROM farmers WHERE email = ?", (email_limpo,))
    farmers = [dict(row) for row in cursor.fetchall()]

    # Pega o inventário desse jogador
    cursor.execute("SELECT item_name, quantity FROM inventory WHERE email = ?", (email_limpo,))
    inventory = {row['item_name']: row['quantity'] for row in cursor.fetchall()}

    conn.close()

    # Retorna os dados removendo a senha por segurança
    player_data = dict(player)
    del player_data['password']

    return {
        "success": True,
        "player_data": player_data,
        "farmers": farmers,
        "inventory": inventory
    }

@router.post("/api/login/google")
async def login_google(request: GoogleLoginRequest):
    """
    Função de login através do Google OAuth.
    """
    if GOOGLE_CLIENT_ID == "SEU_CLIENT_ID_AQUI":
        raise HTTPException(status_code=400, detail="Autenticação Google ainda não configurada no servidor.")

    try:
        # Verifica o token seguro enviado pelo Frontend
        idinfo = id_token.verify_oauth2_token(request.token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        email_limpo = idinfo['email'].lower().strip()
        nome_completo = idinfo.get('name', '')
        
        # Pega só o primeiro nome como username
        username_inicial = nome_completo.split(' ')[0] if nome_completo else email_limpo.split("@")[0]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players WHERE email = ?", (email_limpo,))
        player = cursor.fetchone()

        if not player:
            # Conta não existe, cria ela magicamente pra ele não precisar de senha
            senha_dummy = "google_auth_no_password" # Nunca fará login por senha normal
            cursor.execute("INSERT INTO players (email, password, game_username) VALUES (?, ?, ?)", (email_limpo, hash_senha(senha_dummy), f"{username_inicial}"))
            cursor.execute("INSERT INTO farmers (email, farmer_name, farming_power) VALUES (?, ?, ?)", (email_limpo, "Jão Trabaiadô", 1.5))
            conn.commit()
            
            cursor.execute("SELECT * FROM players WHERE email = ?", (email_limpo,))
            player = cursor.fetchone()

        # Pega coisas da conta
        cursor.execute("SELECT farmer_id, farmer_name, farming_power, is_working, last_harvest_time FROM farmers WHERE email = ?", (email_limpo,))
        farmers = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT item_name, quantity FROM inventory WHERE email = ?", (email_limpo,))
        inventory = {row['item_name']: row['quantity'] for row in cursor.fetchall()}
        conn.close()

        player_data = dict(player)
        del player_data['password']

        return {
            "success": True,
            "player_data": player_data,
            "farmers": farmers,
            "inventory": inventory
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="Token do Google inválido ou expirado!")


# ===================================================
# ROTAS DO JOGO UNO (APOSTAS)
# ===================================================

class CobrarEntradaRequest(BaseModel):
    usuarioId: str

@router.post("/api/cobrar-entrada")
async def cobrar_entrada(request: CobrarEntradaRequest):
    usuario_id = request.usuarioId
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Busca o usuário (se não existir, cria com 10 reais para teste)
    cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (usuario_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO usuarios (nome, email, senha, saldo) VALUES (?, ?, '123', 10.00)", (usuario_id, usuario_id))
        conn.commit()
        cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (usuario_id,))
        user = cursor.fetchone()

    saldo_atual = user['saldo']

    if saldo_atual >= 1.00:
        novo_saldo = saldo_atual - 1.00
        cursor.execute("UPDATE usuarios SET saldo = ? WHERE id = ?", (novo_saldo, user['id']))
        # Registra transação
        cursor.execute("INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)", (user['id'], 1.00, 'Aposta'))
        conn.commit()
        conn.close()

        return {
            "sucesso": True,
            "mensagem": f"Entrada cobrada com sucesso. Saldo restante: R$ {novo_saldo:.2f}",
            "ticketWs": f"ticket-valido-{usuario_id}"
        }
    else:
        conn.close()
        return {"sucesso": False, "erro": "Saldo insuficiente para jogar."}