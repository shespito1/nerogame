
from fastapi import APIRouter, Request, HTTPException, Body
from database import get_db
import sqlite3
import hashlib
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel
from typing import Optional
import random

router = APIRouter()

FREEBET_SESSIONS = {}

# Tenta carregar partidas do socket_handler para monitoramento
try:
    import socket_handler
except ImportError:
    socket_handler = None

@router.get("/")
async def root():
    return {"message": "NeroCoin Farm Game API Online"}

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
    # Registra transação de devolução
    cursor.execute("INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)", (user['id'], saldo_bot, 'Premio'))
    # Exclui bot
    cursor.execute("DELETE FROM bots WHERE id = ?", (request.bot_id,))
    conn.commit()
    conn.close()
    return {"success": True, "novo_saldo_usuario": novo_saldo_usuario, "valor_devolvido": saldo_bot}
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

# Reciclagem de imports removida para evitar redefinição de 'router'

# Endpoint para ativar bot do usuário em uma partida
class BotAtivarRequest(BaseModel):
    usuario_email: str
    bot_id: int

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

    if bot['status'] == "Parado":
        # Antes de ativar, verifica se o saldo já não está fora dos limites
        if bot['saldo'] <= bot['stop_loss'] or bot['saldo'] >= bot['stop_win']:
            limite_atingido = "Stop Loss" if bot['saldo'] <= bot['stop_loss'] else "Stop Win"
            conn.close()
            return {"success": False, "detail": f"Não é possível iniciar: {limite_atingido} já atingido. Ajuste o bot."}
        
        novo_status = "Ativo"
        cursor.execute("UPDATE bots SET status = ?, motivo_status = NULL WHERE id = ?", (novo_status, request.bot_id))
    else:
        novo_status = "Parado"
        cursor.execute("UPDATE bots SET status = ? WHERE id = ?", (novo_status, request.bot_id))
    conn.commit()
    conn.close()
    return {"success": True, "novo_status": novo_status}

@router.get("/api/bots/listar")
async def listar_bots(usuario_email: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bots WHERE usuario_email = ?", (usuario_email,))
    bots = []
    for row in cursor.fetchall():
        d = dict(row)
        d['lucro'] = d['saldo'] - d.get('saldo_inicial', d['saldo'])
        
        # Procura se este bot está em alguma partida ativa agora
        d['partida_id'] = None
        if socket_handler and hasattr(socket_handler, 'partidas'):
            for pid, p in socket_handler.partidas.items():
                if any(j.get("bot_id") == d['id'] for j in p["jogadores"]):
                    d['partida_id'] = pid
                    break
        
        bots.append(d)
    conn.close()
    return {"success": True, "bots": bots}

class BotEditRequest(BaseModel):
    usuario_email: str
    bot_id: int
    stop_loss: float
    stop_win: float

@router.post("/api/bots/editar")
async def editar_bot(request: BotEditRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE bots SET stop_loss = ?, stop_win = ?, motivo_status = NULL WHERE id = ? AND usuario_email = ?", 
                   (request.stop_loss, request.stop_win, request.bot_id, request.usuario_email))
    conn.commit()
    conn.close()
    return {"success": True}

class BotDeleteRequest(BaseModel):
    usuario_email: str
    bot_id: int

@router.post("/api/bots/deletar")
async def deletar_bot(request: BotDeleteRequest):
    conn = get_db()
    cursor = conn.cursor()
    # Busca bot e saldo antes de deletar
    cursor.execute("SELECT saldo FROM bots WHERE id = ? AND usuario_email = ?", (request.bot_id, request.usuario_email))
    bot = cursor.fetchone()
    if not bot:
        conn.close()
        return {"success": False, "detail": "Bot não encontrado."}
    
    saldo_bot = bot['saldo']
    
    # Busca usuário
    cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (request.usuario_email,))
    user = cursor.fetchone()
    if user:
        # Devolve saldo
        novo_saldo = user['saldo'] + saldo_bot
        cursor.execute("UPDATE usuarios SET saldo = ? WHERE id = ?", (novo_saldo, user['id']))
        cursor.execute("INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)", (user['id'], saldo_bot, 'Premio'))
    
    cursor.execute("DELETE FROM bots WHERE id = ? AND usuario_email = ?", (request.bot_id, request.usuario_email))
    conn.commit()
    conn.close()
    return {"success": True}
# Reciclagem de imports removida para evitar redefinição de 'router'


class BotCreateRequest(BaseModel):
    usuario_email: str
    nome: str
    saldo: float
    stop_loss: float
    stop_win: float
    valor_aposta: float = 1.0

@router.post("/api/bots/criar")
async def criar_bot(request: BotCreateRequest):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 1. Verifica saldo do usuário na tabela usuarios (Uno)
        cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (request.usuario_email,))
        user = cursor.fetchone()
        if not user:
            # Se não existe em usuarios, cria com 100 de presente pra ele não ficar travado
            cursor.execute("INSERT INTO usuarios (nome, email, senha, saldo) VALUES (?, ?, '123', 100.00)", 
                           (request.usuario_email, request.usuario_email))
            conn.commit()
            cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (request.usuario_email,))
            user = cursor.fetchone()
        
        if user['saldo'] < request.saldo:
            conn.close()
            return {"success": False, "detail": f"Saldo insuficiente em sua conta Uno. Você tem R$ {user['saldo']:.2f}"}

        # 2. Desconta do usuário
        cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE id = ?", (request.saldo, user['id']))

        # 3. Cria o Bot
        cursor.execute("INSERT INTO bots (usuario_email, nome, saldo, stop_loss, stop_win, valor_aposta, status, saldo_inicial) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (request.usuario_email, request.nome, request.saldo, request.stop_loss, request.stop_win, request.valor_aposta, 'Parado', request.saldo))
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
    print(f"POST /api/register hit: {request.email}")
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

    # Pega o saldo e avatar da tabela usuarios (Uno)
    cursor.execute("SELECT saldo, avatar_seed FROM usuarios WHERE email = ?", (email_limpo,))
    uno_user = cursor.fetchone()
    uno_saldo = uno_user['saldo'] if uno_user else 100.00 # Padrão se não existir
    avatar_seed = uno_user['avatar_seed'] if uno_user else None

    conn.close()

    # Retorna os dados removendo a senha por segurança
    player_data = dict(player)
    player_data.pop('password', None)

    return {
        "success": True,
        "player_data": player_data,
        "uno_saldo": uno_saldo,
        "avatar_seed": avatar_seed,
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
        # Pega o saldo e avatar da tabela usuarios (Uno)
        cursor.execute("SELECT saldo, avatar_seed FROM usuarios WHERE email = ?", (email_limpo,))
        uno_user = cursor.fetchone()
        uno_saldo = uno_user['saldo'] if uno_user else 100.00 # Padrão
        avatar_seed = uno_user['avatar_seed'] if uno_user else None
        
        conn.close()


        player_data = dict(player)
        player_data.pop('password', None)

        return {
            "success": True,
            "player_data": player_data,
            "uno_saldo": uno_saldo,
            "avatar_seed": avatar_seed,
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
    cursor.execute("SELECT id, saldo, avatar_seed FROM usuarios WHERE email = ?", (usuario_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO usuarios (nome, email, senha, saldo) VALUES (?, ?, '123', 100.00)", (usuario_id, usuario_id))
        conn.commit()
        cursor.execute("SELECT id, saldo, avatar_seed FROM usuarios WHERE email = ?", (usuario_id,))
        user = cursor.fetchone()
    
    avatar_seed = user['avatar_seed']
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
            "ticketWs": f"ticket-valido-{usuario_id}",
            "avatar_seed": avatar_seed
        }
    else:
        conn.close()
        return {"sucesso": False, "erro": "Saldo insuficiente para jogar."}

class AvatarUpdateRequest(BaseModel):
    usuario_email: str
    avatar_seed: str

@router.post("/api/perfil/atualizar-avatar")
async def atualizar_avatar(request: AvatarUpdateRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET avatar_seed = ? WHERE email = ?", (request.avatar_seed, request.usuario_email))
    conn.commit()
    conn.close()
    return {"success": True}


FREEBET_SUITS = [
    {"key": "S", "symbol": "S", "color": "black"},
    {"key": "H", "symbol": "H", "color": "red"},
    {"key": "D", "symbol": "D", "color": "red"},
    {"key": "C", "symbol": "C", "color": "black"},
]
FREEBET_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
FREEBET_TEN_RANKS = {"10", "J", "Q", "K"}


class FreeBetStartRequest(BaseModel):
    usuario_email: str
    aposta: float


class FreeBetActionRequest(BaseModel):
    usuario_email: str
    action: str
    hand_index: Optional[int] = None


def _freebet_ensure_user(cursor, email):
    cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (email,))
    user = cursor.fetchone()
    if user:
        return user

    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha, saldo) VALUES (?, ?, '123', 100.00)",
        (email, email),
    )
    cursor.connection.commit()
    cursor.execute("SELECT id, saldo FROM usuarios WHERE email = ?", (email,))
    return cursor.fetchone()


def _freebet_get_balance(usuario_email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM usuarios WHERE email = ?", (usuario_email,))
    user = cursor.fetchone()
    conn.close()
    return round(float(user["saldo"]), 2) if user else 0.0


def _freebet_build_deck():
    deck = []
    for suit in FREEBET_SUITS:
        for rank in FREEBET_RANKS:
            deck.append({
                "rank": rank,
                "suit": suit["key"],
                "symbol": suit["symbol"],
                "color": suit["color"],
            })
    random.shuffle(deck)
    return deck


def _freebet_draw_card(session):
    if not session["deck"]:
        session["deck"] = _freebet_build_deck()
    return session["deck"].pop()


def _freebet_card_value(card):
    if card["rank"] == "A":
        return 1
    if card["rank"] in FREEBET_TEN_RANKS:
        return 10
    return int(card["rank"])


def _freebet_pair_value(card):
    if card["rank"] == "A":
        return 11
    if card["rank"] in FREEBET_TEN_RANKS:
        return 10
    return int(card["rank"])


def _freebet_hand_total(cards):
    total = sum(_freebet_card_value(card) for card in cards)
    aces = sum(1 for card in cards if card["rank"] == "A")
    soft = False
    while aces > 0 and total + 10 <= 21:
        total += 10
        aces -= 1
        soft = True
    return total, soft


def _freebet_is_pair(cards):
    return len(cards) == 2 and _freebet_pair_value(cards[0]) == _freebet_pair_value(cards[1])


def _freebet_is_natural_blackjack(hand):
    total, _ = _freebet_hand_total(hand["cards"])
    return (
        len(hand["cards"]) == 2
        and total == 21
        and not hand.get("split_hand", False)
        and not hand.get("doubled", False)
    )


def _freebet_can_double(hand):
    if hand.get("finished") or hand.get("busted") or hand.get("doubled"):
        return False
    if len(hand["cards"]) != 2:
        return False
    total, _ = _freebet_hand_total(hand["cards"])
    return total in (9, 10, 11)


def _freebet_can_split(hand, session):
    if hand.get("finished") or hand.get("busted"):
        return False
    if len(session["hands"]) >= 2 or len(hand["cards"]) != 2:
        return False
    if not _freebet_is_pair(hand["cards"]):
        return False
    return _freebet_pair_value(hand["cards"][0]) != 10


def _freebet_refresh_hand(hand, session):
    total, soft = _freebet_hand_total(hand["cards"])
    hand["total"] = total
    hand["soft"] = soft
    hand["busted"] = total > 21
    hand["blackjack"] = _freebet_is_natural_blackjack(hand)


def _freebet_current_hand_index(session):
    for idx, hand in enumerate(session["hands"]):
        if not hand.get("finished"):
            return idx
    return None


def _freebet_resolve_hand(hand, dealer_total, dealer_blackjack):
    aposta = hand["bet_amount"]
    unidades = hand.get("bet_units", 1)

    if hand["busted"]:
        return "derrota", "Estourou", 0.0

    if dealer_blackjack:
        if hand["blackjack"]:
            return "push", "Empate com blackjack", aposta
        return "derrota", "Dealer fez blackjack", 0.0

    if hand["blackjack"]:
        return "blackjack", "Blackjack natural", aposta * 2.5

    if dealer_total > 21:
        if dealer_total == 22:
            return "push", "Dealer 22 empata", aposta * unidades
        return "vitoria", "Dealer estourou", aposta * unidades * 2

    if hand["total"] > dealer_total:
        return "vitoria", "Mao vencedora", aposta * unidades * 2
    if hand["total"] == dealer_total:
        return "push", "Empate", aposta * unidades
    return "derrota", "Dealer venceu", 0.0


def _freebet_finish_session(session):
    dealer_total, dealer_soft = _freebet_hand_total(session["dealer_cards"])
    dealer_blackjack = len(session["dealer_cards"]) == 2 and dealer_total == 21

    session["status"] = "dealer_turn"
    session["dealer_revealed"] = True

    if not dealer_blackjack and any(not hand["busted"] and not hand["blackjack"] for hand in session["hands"]):
        while True:
            dealer_total, dealer_soft = _freebet_hand_total(session["dealer_cards"])
            if dealer_total < 17 or (dealer_total == 17 and dealer_soft):
                session["dealer_cards"].append(_freebet_draw_card(session))
            else:
                break

    dealer_total, dealer_soft = _freebet_hand_total(session["dealer_cards"])
    dealer_blackjack = len(session["dealer_cards"]) == 2 and dealer_total == 21

    payout_total = 0.0
    resultados = []
    for idx, hand in enumerate(session["hands"], start=1):
        _freebet_refresh_hand(hand, session)
        result_key, result_text, payout = _freebet_resolve_hand(hand, dealer_total, dealer_blackjack)
        hand["result"] = result_key
        hand["result_text"] = result_text
        hand["payout"] = round(payout, 2)
        hand["finished"] = True
        payout_total += payout
        resultados.append(f"Mao {idx}: {result_text}")

    if payout_total > 0:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET saldo = saldo + ? WHERE id = ?",
            (round(payout_total, 2), session["user_id"]),
        )
        cursor.execute(
            "INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)",
            (session["user_id"], round(payout_total, 2), "Premio"),
        )
        conn.commit()
        conn.close()

    session["dealer_total"] = dealer_total
    session["dealer_soft"] = dealer_soft
    session["status"] = "finished"
    session["active_hand_index"] = None
    session["payout_total"] = round(payout_total, 2)
    session["net_result"] = round(payout_total - session["bet_amount"], 2)
    session["summary"] = resultados


def _freebet_serialize_card(card, hidden=False):
    if hidden:
        return {"rank": "?", "suit": "", "label": "?", "color": "hidden"}
    return {
        "rank": card["rank"],
        "suit": card["suit"],
        "label": f"{card['rank']}{card['symbol']}",
        "color": card["color"],
    }


def _freebet_serialize_session(session):
    dealer_hidden = session["status"] == "player_turn" and not session.get("dealer_revealed", False)
    dealer_cards = []
    for idx, card in enumerate(session["dealer_cards"]):
        dealer_cards.append(_freebet_serialize_card(card, dealer_hidden and idx == 1))

    dealer_total, _ = _freebet_hand_total(session["dealer_cards"])
    active_index = session.get("active_hand_index")
    hands = []
    for idx, hand in enumerate(session["hands"]):
        _freebet_refresh_hand(hand, session)
        hands.append({
            "index": idx,
            "title": f"Mao {idx + 1}",
            "cards": [_freebet_serialize_card(card) for card in hand["cards"]],
            "total": hand["total"],
            "soft": hand["soft"],
            "busted": hand["busted"],
            "blackjack": hand["blackjack"],
            "finished": hand.get("finished", False),
            "active": idx == active_index,
            "bet_units": hand.get("bet_units", 1),
            "can_hit": idx == active_index and session["status"] == "player_turn" and not hand.get("finished"),
            "can_stand": idx == active_index and session["status"] == "player_turn" and not hand.get("finished"),
            "can_double": idx == active_index and session["status"] == "player_turn" and _freebet_can_double(hand),
            "can_split": idx == active_index and session["status"] == "player_turn" and _freebet_can_split(hand, session),
            "result": hand.get("result"),
            "result_text": hand.get("result_text", ""),
            "payout": round(hand.get("payout", 0.0), 2),
        })

    return {
        "bet_amount": round(session["bet_amount"], 2),
        "status": session["status"],
        "dealer": {
            "cards": dealer_cards,
            "total": "?" if dealer_hidden else dealer_total,
        },
        "hands": hands,
        "active_hand_index": active_index,
        "message": session.get("message", ""),
        "payout_total": round(session.get("payout_total", 0.0), 2),
        "net_result": round(session.get("net_result", 0.0), 2),
        "summary": session.get("summary", []),
    }


def _freebet_create_session(usuario_email, user_id, aposta):
    session = {
        "user_email": usuario_email,
        "user_id": user_id,
        "bet_amount": round(aposta, 2),
        "deck": _freebet_build_deck(),
        "dealer_cards": [],
        "hands": [],
        "status": "player_turn",
        "dealer_revealed": False,
        "active_hand_index": 0,
        "payout_total": 0.0,
        "net_result": -round(aposta, 2),
        "message": "Sua vez. Bata, pare, duplique gratis ou divida gratis.",
        "summary": [],
    }

    player_hand = {
        "cards": [_freebet_draw_card(session), _freebet_draw_card(session)],
        "bet_units": 1,
        "bet_amount": round(aposta, 2),
        "finished": False,
        "split_hand": False,
        "doubled": False,
        "result": None,
        "result_text": "",
        "payout": 0.0,
    }
    session["hands"].append(player_hand)
    session["dealer_cards"] = [_freebet_draw_card(session), _freebet_draw_card(session)]
    _freebet_refresh_hand(player_hand, session)

    dealer_total, _ = _freebet_hand_total(session["dealer_cards"])
    dealer_blackjack = len(session["dealer_cards"]) == 2 and dealer_total == 21
    if player_hand["blackjack"] or dealer_blackjack:
        _freebet_finish_session(session)
    else:
        session["active_hand_index"] = 0

    return session


@router.get("/api/freebet/state")
async def get_freebet_state(usuario_email: str):
    session = FREEBET_SESSIONS.get(usuario_email)
    if not session:
        return {"success": True, "state": None, "saldo": _freebet_get_balance(usuario_email)}
    return {"success": True, "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}


@router.post("/api/freebet/start")
async def start_freebet(request: FreeBetStartRequest):
    usuario_email = request.usuario_email.lower().strip()
    aposta = round(float(request.aposta), 2)
    if aposta <= 0:
        return {"success": False, "detail": "Aposta invalida."}

    existing = FREEBET_SESSIONS.get(usuario_email)
    if existing and existing.get("status") != "finished":
        return {
            "success": False,
            "detail": "Voce ja tem uma rodada de Free Bet 21 em andamento.",
            "state": _freebet_serialize_session(existing),
            "saldo": _freebet_get_balance(usuario_email),
        }

    conn = get_db()
    cursor = conn.cursor()
    user = _freebet_ensure_user(cursor, usuario_email)
    saldo_atual = float(user["saldo"])
    if saldo_atual < aposta:
        conn.close()
        return {"success": False, "detail": f"Saldo insuficiente. Voce tem R$ {saldo_atual:.2f}"}

    cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE id = ?", (aposta, user["id"]))
    cursor.execute(
        "INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)",
        (user["id"], aposta, "Aposta"),
    )
    conn.commit()
    conn.close()

    session = _freebet_create_session(usuario_email, user["id"], aposta)
    FREEBET_SESSIONS[usuario_email] = session
    return {"success": True, "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}


@router.post("/api/freebet/action")
async def freebet_action(request: FreeBetActionRequest):
    usuario_email = request.usuario_email.lower().strip()
    session = FREEBET_SESSIONS.get(usuario_email)
    if not session:
        return {"success": False, "detail": "Nenhuma rodada ativa de Free Bet 21.", "saldo": _freebet_get_balance(usuario_email)}
    if session.get("status") != "player_turn":
        return {"success": False, "detail": "Esta rodada ja foi encerrada.", "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}

    active_index = _freebet_current_hand_index(session)
    if active_index is None:
        _freebet_finish_session(session)
        return {"success": True, "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}

    hand_index = active_index if request.hand_index is None else request.hand_index
    if hand_index != active_index or hand_index < 0 or hand_index >= len(session["hands"]):
        return {"success": False, "detail": "Essa nao e a mao ativa agora.", "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}

    hand = session["hands"][hand_index]
    action = request.action.lower().strip()

    if action == "hit":
        hand["cards"].append(_freebet_draw_card(session))
        _freebet_refresh_hand(hand, session)
        session["message"] = f"Mao {hand_index + 1} recebeu uma carta."
        if hand["busted"] or hand["total"] >= 21:
            hand["finished"] = True

    elif action == "stand":
        hand["finished"] = True
        session["message"] = f"Mao {hand_index + 1} parada em {hand['total']}."

    elif action == "double":
        if not _freebet_can_double(hand):
            return {"success": False, "detail": "Duplo gratis indisponivel nessa mao.", "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}
        hand["bet_units"] = 2
        hand["doubled"] = True
        hand["cards"].append(_freebet_draw_card(session))
        _freebet_refresh_hand(hand, session)
        hand["finished"] = True
        session["message"] = f"Mao {hand_index + 1} fez duplo gratis."

    elif action == "split":
        if not _freebet_can_split(hand, session):
            return {"success": False, "detail": "Divisao gratis indisponivel nessa mao.", "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}

        primeira_carta, segunda_carta = hand["cards"]
        primeira_mao = {
            "cards": [primeira_carta, _freebet_draw_card(session)],
            "bet_units": 1,
            "bet_amount": hand["bet_amount"],
            "finished": False,
            "split_hand": True,
            "doubled": False,
            "result": None,
            "result_text": "",
            "payout": 0.0,
        }
        segunda_mao = {
            "cards": [segunda_carta, _freebet_draw_card(session)],
            "bet_units": 1,
            "bet_amount": hand["bet_amount"],
            "finished": False,
            "split_hand": True,
            "doubled": False,
            "result": None,
            "result_text": "",
            "payout": 0.0,
        }
        session["hands"][hand_index] = primeira_mao
        session["hands"].insert(hand_index + 1, segunda_mao)
        _freebet_refresh_hand(primeira_mao, session)
        _freebet_refresh_hand(segunda_mao, session)
        session["message"] = "Divisao gratis feita. Agora jogue a primeira mao."

    else:
        return {"success": False, "detail": "Acao invalida.", "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}

    next_index = _freebet_current_hand_index(session)
    if next_index is None:
        _freebet_finish_session(session)
    else:
        session["active_hand_index"] = next_index
        if session["status"] == "player_turn" and session["hands"][next_index].get("finished"):
            _freebet_finish_session(session)

    return {"success": True, "state": _freebet_serialize_session(session), "saldo": _freebet_get_balance(usuario_email)}
