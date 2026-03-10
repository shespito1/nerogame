import socketio
import time
import random
import asyncio
from database import get_db


def log(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode("ascii", errors="ignore").decode("ascii"))
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)


# Criação do servidor Socket.IO (Assíncrono para aguentar muitos jogadores)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    log(f"🎮 Novo jogador conectou na fazenda! ID da sessão: {sid}")
    # Inicia o monitor de bots se ainda não estiver rodando (usamos uma flag global)
    if not hasattr(sio, 'bot_monitor_started'):
        sio.bot_monitor_started = True
        asyncio.create_task(monitorar_bots_usuarios())
    if not hasattr(sio, 'blackjack_table_loop_started'):
        sio.blackjack_table_loop_started = True
        asyncio.create_task(blackjack_table_loop())

@sio.event
async def disconnect(sid, reason=None):
    log(f"❌ Jogador desconectou: {sid}")
    
    # Se o jogador estiver em uma partida, transforma ele em BOT
    for partida_id, partida in partidas.items():
        for jogador in partida["jogadores"]:
            if jogador.get("socketId") == sid and not jogador.get("is_bot", False):
                jogador["is_bot"] = True
                log(f"🤖 Jogador {jogador['usuarioId']} ({sid}) caiu. Auto-play ativado na partida {partida_id}!")
                # Avise os outros na sala e comece a tarefa de bot para ele
                asyncio.create_task(sio.emit("mensagem_jogo", {"msg": f"🔌 {jogador['usuarioId']} caiu da partida e agora está no modo automático!"}, room=partida_id))
                asyncio.create_task(bot_play_task(partida_id, jogador))
                break
    await blackjack_handle_disconnect(sid)

# =======================================================
# BLACKJACK MULTIPLAYER - MESA COMPARTILHADA
# =======================================================

BLACKJACK_ROOM = "BLACKJACK_SHARED_ROOM"
BLACKJACK_BETTING_SECONDS = 10
BLACKJACK_ACTION_SECONDS = 12
BLACKJACK_CHIP_VALUES = [0.50, 2.00, 5.00, 10.00, 25.00]
BLACKJACK_SUITS = [
    {"key": "S", "symbol": "♠", "color": "black"},
    {"key": "H", "symbol": "♥", "color": "red"},
    {"key": "D", "symbol": "♦", "color": "red"},
    {"key": "C", "symbol": "♣", "color": "black"},
]
BLACKJACK_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
BLACKJACK_TEN_RANKS = {"10", "J", "Q", "K"}


def blackjack_build_deck():
    deck = []
    for suit in BLACKJACK_SUITS:
        for rank in BLACKJACK_RANKS:
            deck.append({
                "rank": rank,
                "suit": suit["key"],
                "symbol": suit["symbol"],
                "color": suit["color"],
            })
    random.shuffle(deck)
    return deck


def create_blackjack_table():
    return {
        "players": {},
        "player_order": [],
        "phase": "betting",
        "countdown_end": time.time() + BLACKJACK_BETTING_SECONDS,
        "turn_deadline": None,
        "current_turn_player": None,
        "current_turn_hand_index": None,
        "dealer_cards": [],
        "dealer_revealed": False,
        "deck": blackjack_build_deck(),
        "round_id": 0,
        "message": "Mesa aberta. Escolha suas fichas para a proxima rodada.",
    }


blackjack_table = create_blackjack_table()


def blackjack_draw_card():
    if not blackjack_table["deck"]:
        blackjack_table["deck"] = blackjack_build_deck()
    return blackjack_table["deck"].pop()


def blackjack_ensure_user(cursor, email):
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


def blackjack_get_balance(usuario_email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM usuarios WHERE email = ?", (usuario_email,))
    user = cursor.fetchone()
    conn.close()
    return round(float(user["saldo"]), 2) if user else 0.0


def blackjack_reserve_bet(usuario_email, amount):
    conn = get_db()
    cursor = conn.cursor()
    user = blackjack_ensure_user(cursor, usuario_email)
    saldo_atual = round(float(user["saldo"]), 2)
    if saldo_atual < amount:
        conn.close()
        return False, saldo_atual

    cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE id = ?", (amount, user["id"]))
    cursor.execute(
        "INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)",
        (user["id"], amount, "Aposta Free Bet 21"),
    )
    conn.commit()
    conn.close()
    return True, round(saldo_atual - amount, 2)


def blackjack_refund_bet(usuario_email, amount):
    if amount <= 0:
        return blackjack_get_balance(usuario_email)

    conn = get_db()
    cursor = conn.cursor()
    user = blackjack_ensure_user(cursor, usuario_email)
    cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE id = ?", (amount, user["id"]))
    cursor.execute(
        "INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)",
        (user["id"], amount, "Estorno Free Bet 21"),
    )
    conn.commit()
    conn.close()
    return blackjack_get_balance(usuario_email)


def blackjack_credit_payout(usuario_email, amount):
    if amount <= 0:
        return blackjack_get_balance(usuario_email)

    conn = get_db()
    cursor = conn.cursor()
    user = blackjack_ensure_user(cursor, usuario_email)
    cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE id = ?", (amount, user["id"]))
    cursor.execute(
        "INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)",
        (user["id"], amount, "Premio Free Bet 21"),
    )
    conn.commit()
    conn.close()
    return blackjack_get_balance(usuario_email)


def blackjack_card_value(card):
    if card["rank"] == "A":
        return 1
    if card["rank"] in BLACKJACK_TEN_RANKS:
        return 10
    return int(card["rank"])


def blackjack_pair_value(card):
    if card["rank"] == "A":
        return 11
    if card["rank"] in BLACKJACK_TEN_RANKS:
        return 10
    return int(card["rank"])


def blackjack_hand_total(cards):
    total = sum(blackjack_card_value(card) for card in cards)
    aces = sum(1 for card in cards if card["rank"] == "A")
    soft = False
    while aces > 0 and total + 10 <= 21:
        total += 10
        aces -= 1
        soft = True
    return total, soft


def blackjack_is_pair(cards):
    return len(cards) == 2 and blackjack_pair_value(cards[0]) == blackjack_pair_value(cards[1])


def blackjack_is_natural_blackjack(hand):
    total, _ = blackjack_hand_total(hand["cards"])
    return (
        len(hand["cards"]) == 2
        and total == 21
        and not hand.get("split_hand", False)
        and not hand.get("doubled", False)
    )


def blackjack_refresh_hand(hand):
    total, soft = blackjack_hand_total(hand["cards"])
    hand["total"] = total
    hand["soft"] = soft
    hand["busted"] = total > 21
    hand["blackjack"] = blackjack_is_natural_blackjack(hand)


def blackjack_can_double(hand):
    if hand.get("finished") or hand.get("busted") or hand.get("doubled"):
        return False
    if len(hand["cards"]) != 2:
        return False
    total, _ = blackjack_hand_total(hand["cards"])
    return total in (9, 10, 11)


def blackjack_can_split(player, hand):
    if hand.get("finished") or hand.get("busted"):
        return False
    if len(player["hands"]) >= 2 or len(hand["cards"]) != 2:
        return False
    if not blackjack_is_pair(hand["cards"]):
        return False
    return blackjack_pair_value(hand["cards"][0]) != 10


def blackjack_serialize_card(card, hidden=False):
    if hidden:
        return {"rank": "?", "suit": "", "label": "?", "color": "hidden"}
    return {
        "rank": card["rank"],
        "suit": card["suit"],
        "label": f"{card['rank']}{card['symbol']}",
        "color": card["color"],
    }


def blackjack_seconds_left(deadline):
    if not deadline:
        return 0
    return max(0, int(deadline - time.time() + 0.999))


def blackjack_player_status(player, player_id):
    if blackjack_table["phase"] == "betting":
        if player["pending_bet"] > 0:
            return "Apostando"
        if player["current_bet"] > 0 and player["hands"]:
            return "Resultado na mesa"
        return "Assistindo"
    if blackjack_table["current_turn_player"] == player_id:
        return "Decidindo"
    if player["current_bet"] > 0:
        return "Na rodada"
    return "Assistindo"


def blackjack_serialize_state(viewer_id=None):
    viewer = blackjack_table["players"].get(viewer_id) if viewer_id else None
    dealer_hidden = blackjack_table["phase"] == "player_turns" and not blackjack_table["dealer_revealed"]
    dealer_cards = []
    for idx, card in enumerate(blackjack_table["dealer_cards"]):
        dealer_cards.append(blackjack_serialize_card(card, dealer_hidden and idx == 1))

    dealer_total, _ = blackjack_hand_total(blackjack_table["dealer_cards"]) if blackjack_table["dealer_cards"] else (0, False)
    players_payload = []
    for player_id in blackjack_table["player_order"]:
        player = blackjack_table["players"].get(player_id)
        if not player:
            continue
        if (
            not player.get("connected", False)
            and player["pending_bet"] <= 0
            and player["current_bet"] <= 0
            and not player["hands"]
        ):
            continue

        hands_payload = []
        for index, hand in enumerate(player["hands"]):
            blackjack_refresh_hand(hand)
            hands_payload.append({
                "index": index,
                "title": f"Mao {index + 1}",
                "cards": [blackjack_serialize_card(card) for card in hand["cards"]],
                "total": hand["total"],
                "soft": hand["soft"],
                "busted": hand["busted"],
                "blackjack": hand["blackjack"],
                "finished": hand.get("finished", False),
                "active": player_id == blackjack_table["current_turn_player"] and index == blackjack_table["current_turn_hand_index"],
                "bet_units": hand.get("bet_units", 1),
                "can_double": player_id == blackjack_table["current_turn_player"] and index == blackjack_table["current_turn_hand_index"] and blackjack_table["phase"] == "player_turns" and blackjack_can_double(hand),
                "can_split": player_id == blackjack_table["current_turn_player"] and index == blackjack_table["current_turn_hand_index"] and blackjack_table["phase"] == "player_turns" and blackjack_can_split(player, hand),
                "result": hand.get("result"),
                "result_text": hand.get("result_text", ""),
                "payout": round(hand.get("payout", 0.0), 2),
            })

        players_payload.append({
            "usuarioId": player_id,
            "avatarSeed": player.get("avatarSeed"),
            "connected": player.get("connected", False),
            "is_viewer": player_id == viewer_id,
            "is_turn": player_id == blackjack_table["current_turn_player"],
            "pending_bet": round(player.get("pending_bet", 0.0), 2),
            "current_bet": round(player.get("current_bet", 0.0), 2),
            "display_bet": round(player.get("pending_bet", 0.0) if blackjack_table["phase"] == "betting" and player.get("pending_bet", 0.0) > 0 else player.get("current_bet", 0.0), 2),
            "hands": hands_payload,
            "round_payout": round(player.get("round_payout", 0.0), 2),
            "round_net": round(player.get("round_net", 0.0), 2),
            "summary": player.get("summary", []),
            "status": blackjack_player_status(player, player_id),
            "last_action": player.get("last_action", ""),
        })

    phase = blackjack_table["phase"]
    phase_label_map = {
        "betting": "Apostas abertas",
        "player_turns": "Jogadores decidindo",
        "dealer_turn": "Dealer resolvendo",
    }
    return {
        "phase": phase,
        "phase_label": phase_label_map.get(phase, phase),
        "message": blackjack_table["message"],
        "countdown": blackjack_seconds_left(blackjack_table["countdown_end"]) if phase == "betting" else blackjack_seconds_left(blackjack_table["turn_deadline"]),
        "betting_seconds_left": blackjack_seconds_left(blackjack_table["countdown_end"]) if phase == "betting" else 0,
        "turn_seconds_left": blackjack_seconds_left(blackjack_table["turn_deadline"]) if phase == "player_turns" else 0,
        "dealer": {
            "cards": dealer_cards,
            "total": "?" if dealer_hidden else dealer_total,
        },
        "players": players_payload,
        "current_turn_player": blackjack_table["current_turn_player"],
        "current_turn_hand_index": blackjack_table["current_turn_hand_index"],
        "deck_left": len(blackjack_table["deck"]),
        "round_id": blackjack_table["round_id"],
        "viewer_balance": blackjack_get_balance(viewer_id) if viewer else None,
        "viewer_pending_bet": round(viewer.get("pending_bet", 0.0), 2) if viewer else 0.0,
        "viewer_current_bet": round(viewer.get("current_bet", 0.0), 2) if viewer else 0.0,
        "chip_values": BLACKJACK_CHIP_VALUES,
        "can_place_bets": phase == "betting",
    }


async def blackjack_emit_state(user_id):
    player = blackjack_table["players"].get(user_id)
    if not player or not player.get("connected") or not player.get("socketId"):
        return
    await sio.emit("blackjackMesaEstado", blackjack_serialize_state(user_id), to=player["socketId"])


async def blackjack_broadcast_state():
    for user_id in list(blackjack_table["player_order"]):
        await blackjack_emit_state(user_id)


async def blackjack_broadcast_message(msg):
    await sio.emit("blackjackMensagem", {"msg": msg}, room=BLACKJACK_ROOM)


def blackjack_clear_round_state(player):
    player["current_bet"] = 0.0
    player["hands"] = []
    player["round_payout"] = 0.0
    player["round_net"] = 0.0
    player["summary"] = []
    player["last_action"] = ""


def blackjack_prune_players():
    remove_ids = []
    for player_id in blackjack_table["player_order"]:
        player = blackjack_table["players"].get(player_id)
        if not player:
            continue
        if player.get("connected"):
            continue
        if player["pending_bet"] <= 0 and player["current_bet"] <= 0 and not player["hands"]:
            remove_ids.append(player_id)

    for player_id in remove_ids:
        blackjack_table["players"].pop(player_id, None)
        blackjack_table["player_order"] = [pid for pid in blackjack_table["player_order"] if pid != player_id]


def blackjack_find_next_actor():
    for player_id in blackjack_table["player_order"]:
        player = blackjack_table["players"].get(player_id)
        if not player or player["current_bet"] <= 0:
            continue
        for hand_index, hand in enumerate(player["hands"]):
            if not hand.get("finished", False):
                return player_id, hand_index
    return None, None


def blackjack_resolve_hand(hand, dealer_total, dealer_blackjack):
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


async def blackjack_finish_round():
    blackjack_table["phase"] = "dealer_turn"
    blackjack_table["dealer_revealed"] = True
    blackjack_table["current_turn_player"] = None
    blackjack_table["current_turn_hand_index"] = None
    blackjack_table["turn_deadline"] = None

    dealer_total, dealer_soft = blackjack_hand_total(blackjack_table["dealer_cards"])
    dealer_blackjack = len(blackjack_table["dealer_cards"]) == 2 and dealer_total == 21

    if not dealer_blackjack and any(
        player["current_bet"] > 0 and any(not hand.get("busted") and not hand.get("blackjack") for hand in player["hands"])
        for player in blackjack_table["players"].values()
    ):
        while True:
            dealer_total, dealer_soft = blackjack_hand_total(blackjack_table["dealer_cards"])
            if dealer_total < 17 or (dealer_total == 17 and dealer_soft):
                blackjack_table["dealer_cards"].append(blackjack_draw_card())
            else:
                break

    dealer_total, _ = blackjack_hand_total(blackjack_table["dealer_cards"])
    dealer_blackjack = len(blackjack_table["dealer_cards"]) == 2 and dealer_total == 21

    for player_id in blackjack_table["player_order"]:
        player = blackjack_table["players"].get(player_id)
        if not player or player["current_bet"] <= 0:
            continue

        payout_total = 0.0
        summary = []
        for hand_index, hand in enumerate(player["hands"], start=1):
            blackjack_refresh_hand(hand)
            result_key, result_text, payout = blackjack_resolve_hand(hand, dealer_total, dealer_blackjack)
            hand["result"] = result_key
            hand["result_text"] = result_text
            hand["payout"] = round(payout, 2)
            hand["finished"] = True
            payout_total += payout
            summary.append(f"Mao {hand_index}: {result_text}")

        player["round_payout"] = round(payout_total, 2)
        player["round_net"] = round(payout_total - player["current_bet"], 2)
        player["summary"] = summary
        player["last_action"] = summary[-1] if summary else "Rodada encerrada."
        if payout_total > 0:
            blackjack_credit_payout(player_id, round(payout_total, 2))

    blackjack_table["phase"] = "betting"
    blackjack_table["countdown_end"] = time.time() + BLACKJACK_BETTING_SECONDS
    blackjack_table["message"] = "Rodada resolvida. Apostas abertas para a proxima mao."
    await blackjack_broadcast_message("Dealer fechou a rodada. Nova contagem iniciada.")
    blackjack_prune_players()


async def blackjack_start_round():
    active_players = []

    for player_id in list(blackjack_table["player_order"]):
        player = blackjack_table["players"].get(player_id)
        if not player:
            continue
        if player["pending_bet"] > 0 and not player.get("connected"):
            blackjack_refund_bet(player_id, player["pending_bet"])
            player["pending_bet"] = 0.0

    for player_id in blackjack_table["player_order"]:
        player = blackjack_table["players"].get(player_id)
        if player and player["pending_bet"] > 0:
            active_players.append(player_id)

    if not active_players:
        blackjack_table["phase"] = "betting"
        blackjack_table["countdown_end"] = time.time() + BLACKJACK_BETTING_SECONDS
        blackjack_table["message"] = "Mesa aberta. Escolha suas fichas para a proxima rodada."
        blackjack_prune_players()
        return

    if len(blackjack_table["deck"]) < max(18, len(active_players) * 8):
        blackjack_table["deck"] = blackjack_build_deck()

    blackjack_table["round_id"] += 1
    blackjack_table["dealer_cards"] = []
    blackjack_table["dealer_revealed"] = False

    for player_id in blackjack_table["player_order"]:
        player = blackjack_table["players"].get(player_id)
        if not player:
            continue

        pending_bet = round(player["pending_bet"], 2)
        blackjack_clear_round_state(player)
        if player_id not in active_players:
            player["pending_bet"] = pending_bet if pending_bet > 0 else 0.0
            continue

        player["current_bet"] = pending_bet
        player["pending_bet"] = 0.0
        player["hands"] = [{
            "cards": [blackjack_draw_card(), blackjack_draw_card()],
            "bet_units": 1,
            "bet_amount": pending_bet,
            "finished": False,
            "split_hand": False,
            "doubled": False,
            "result": None,
            "result_text": "",
            "payout": 0.0,
        }]
        blackjack_refresh_hand(player["hands"][0])
        if player["hands"][0]["blackjack"]:
            player["hands"][0]["finished"] = True
        player["round_net"] = -pending_bet
        player["last_action"] = "Recebeu as cartas iniciais."

    blackjack_table["dealer_cards"] = [blackjack_draw_card(), blackjack_draw_card()]
    dealer_total, _ = blackjack_hand_total(blackjack_table["dealer_cards"])
    dealer_blackjack = len(blackjack_table["dealer_cards"]) == 2 and dealer_total == 21

    if dealer_blackjack:
        blackjack_table["message"] = "Dealer mostrou blackjack logo de cara."
        await blackjack_broadcast_message("O dealer abriu forte nesta rodada.")
        await blackjack_finish_round()
        return

    next_player, next_hand = blackjack_find_next_actor()
    if next_player is None:
        blackjack_table["message"] = "So blackjacks naturais apareceram. Dealer vai resolver."
        await blackjack_finish_round()
        return

    blackjack_table["phase"] = "player_turns"
    blackjack_table["current_turn_player"] = next_player
    blackjack_table["current_turn_hand_index"] = next_hand
    blackjack_table["turn_deadline"] = time.time() + BLACKJACK_ACTION_SECONDS
    blackjack_table["message"] = f"Rodada {blackjack_table['round_id']} valendo. Vez de {next_player}."
    await blackjack_broadcast_message(f"Rodada {blackjack_table['round_id']} iniciada na mesa compartilhada.")


async def blackjack_apply_action(player_id, action, auto=False):
    if blackjack_table["phase"] != "player_turns":
        return False, "A rodada nao esta aceitando decisoes agora."
    if blackjack_table["current_turn_player"] != player_id:
        return False, "Nao e a sua vez de decidir."

    player = blackjack_table["players"].get(player_id)
    if not player:
        return False, "Jogador nao encontrado na mesa."

    hand_index = blackjack_table["current_turn_hand_index"]
    if hand_index is None or hand_index >= len(player["hands"]):
        return False, "Mao ativa invalida."

    hand = player["hands"][hand_index]
    action = (action or "").lower().strip()

    if action == "hit":
        hand["cards"].append(blackjack_draw_card())
        blackjack_refresh_hand(hand)
        player["last_action"] = "Pediu carta."
        blackjack_table["message"] = f"{player_id} pediu mais uma carta."
        if hand["busted"] or hand["total"] >= 21:
            hand["finished"] = True

    elif action == "stand":
        hand["finished"] = True
        player["last_action"] = "Parou a mao."
        blackjack_table["message"] = f"{player_id} travou a mao em {hand['total']}."

    elif action == "double":
        if not blackjack_can_double(hand):
            return False, "Duplo gratis indisponivel nessa mao."
        hand["bet_units"] = 2
        hand["doubled"] = True
        hand["cards"].append(blackjack_draw_card())
        blackjack_refresh_hand(hand)
        hand["finished"] = True
        player["last_action"] = "Fez free double."
        blackjack_table["message"] = f"{player_id} ativou o free double."

    elif action == "split":
        if not blackjack_can_split(player, hand):
            return False, "Split gratis indisponivel nessa mao."
        primeira_carta, segunda_carta = hand["cards"]
        primeira_mao = {
            "cards": [primeira_carta, blackjack_draw_card()],
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
            "cards": [segunda_carta, blackjack_draw_card()],
            "bet_units": 1,
            "bet_amount": hand["bet_amount"],
            "finished": False,
            "split_hand": True,
            "doubled": False,
            "result": None,
            "result_text": "",
            "payout": 0.0,
        }
        blackjack_refresh_hand(primeira_mao)
        blackjack_refresh_hand(segunda_mao)
        player["hands"][hand_index] = primeira_mao
        player["hands"].insert(hand_index + 1, segunda_mao)
        player["last_action"] = "Abriu split gratis."
        blackjack_table["message"] = f"{player_id} dividiu o par e abriu duas maos."

    else:
        return False, "Acao invalida."

    if auto:
        player["last_action"] = "Tempo esgotado. Mao travada automaticamente."
        blackjack_table["message"] = f"{player_id} ficou sem tempo e a mesa continuou."

    next_player, next_hand = blackjack_find_next_actor()
    if next_player is None:
        await blackjack_finish_round()
    else:
        blackjack_table["current_turn_player"] = next_player
        blackjack_table["current_turn_hand_index"] = next_hand
        blackjack_table["turn_deadline"] = time.time() + BLACKJACK_ACTION_SECONDS
        if blackjack_table["phase"] == "player_turns":
            blackjack_table["message"] = f"{blackjack_table['message']} Agora {next_player} decide."
    return True, ""


async def blackjack_handle_disconnect(sid):
    for player_id, player in list(blackjack_table["players"].items()):
        if player.get("socketId") != sid:
            continue

        player["connected"] = False
        player["socketId"] = None
        if blackjack_table["phase"] == "betting" and player["pending_bet"] > 0:
            blackjack_refund_bet(player_id, player["pending_bet"])
            player["pending_bet"] = 0.0
        player["last_action"] = "Saiu da mesa."
        blackjack_prune_players()
        await blackjack_broadcast_state()
        await blackjack_broadcast_message(f"{player_id} saiu da mesa de Free Bet 21.")
        return


async def blackjack_table_loop():
    while True:
        await asyncio.sleep(1)
        try:
            state_changed = False
            if blackjack_table["phase"] == "betting":
                state_changed = True
                if time.time() >= blackjack_table["countdown_end"]:
                    await blackjack_start_round()
            elif blackjack_table["phase"] == "player_turns":
                state_changed = True
                if blackjack_table["turn_deadline"] and time.time() >= blackjack_table["turn_deadline"]:
                    current_player = blackjack_table["current_turn_player"]
                    if current_player:
                        await blackjack_apply_action(current_player, "stand", auto=True)

            if blackjack_table["player_order"]:
                blackjack_prune_players()
                if state_changed:
                    await blackjack_broadcast_state()
        except Exception as e:
            log(f"Erro no loop da mesa de blackjack: {e}")


@sio.on("entrarMesaBlackjack")
async def entrar_mesa_blackjack(sid, data):
    usuario_id = (data.get("usuarioId") or "").strip()
    if not usuario_id:
        await sio.emit("blackjackErro", {"mensagem": "Login necessario para entrar na mesa."}, to=sid)
        return

    avatar_seed = data.get("avatarSeed")
    await sio.enter_room(sid, BLACKJACK_ROOM)

    player = blackjack_table["players"].get(usuario_id)
    if not player:
        player = {
            "usuarioId": usuario_id,
            "socketId": sid,
            "avatarSeed": avatar_seed,
            "connected": True,
            "pending_bet": 0.0,
            "current_bet": 0.0,
            "hands": [],
            "round_payout": 0.0,
            "round_net": 0.0,
            "summary": [],
            "last_action": "Sentou na mesa.",
        }
        blackjack_table["players"][usuario_id] = player
        blackjack_table["player_order"].append(usuario_id)
    else:
        player["socketId"] = sid
        player["avatarSeed"] = avatar_seed or player.get("avatarSeed")
        player["connected"] = True
        player["last_action"] = "Voltou para a mesa."

    await blackjack_emit_state(usuario_id)
    await blackjack_broadcast_state()
    await blackjack_broadcast_message(f"{usuario_id} entrou na mesa compartilhada.")


@sio.on("apostarFichaBlackjack")
async def apostar_ficha_blackjack(sid, data):
    usuario_id = (data.get("usuarioId") or "").strip()
    valor = round(float(data.get("valor", 0)), 2)
    if usuario_id not in blackjack_table["players"]:
        await sio.emit("blackjackErro", {"mensagem": "Entre na mesa antes de apostar."}, to=sid)
        return
    if blackjack_table["phase"] != "betting":
        await sio.emit("blackjackErro", {"mensagem": "Aposte apenas durante a contagem da mesa."}, to=sid)
        return
    if valor <= 0 or valor not in BLACKJACK_CHIP_VALUES:
        await sio.emit("blackjackErro", {"mensagem": "Ficha invalida para esta mesa."}, to=sid)
        return

    ok, saldo = blackjack_reserve_bet(usuario_id, valor)
    if not ok:
        await sio.emit("blackjackErro", {"mensagem": f"Saldo insuficiente. Voce tem R$ {saldo:.2f}."}, to=sid)
        return

    player = blackjack_table["players"][usuario_id]
    player["pending_bet"] = round(player["pending_bet"] + valor, 2)
    player["last_action"] = f"Jogou ficha de R$ {valor:.2f}."
    blackjack_table["message"] = f"{usuario_id} reforcou a aposta na mesa."
    await blackjack_broadcast_state()


@sio.on("limparApostaBlackjack")
async def limpar_aposta_blackjack(sid, data):
    usuario_id = (data.get("usuarioId") or "").strip()
    player = blackjack_table["players"].get(usuario_id)
    if not player:
        await sio.emit("blackjackErro", {"mensagem": "Voce ainda nao esta nessa mesa."}, to=sid)
        return
    if blackjack_table["phase"] != "betting":
        await sio.emit("blackjackErro", {"mensagem": "Nao da para limpar fichas com a rodada em andamento."}, to=sid)
        return
    if player["pending_bet"] <= 0:
        return

    blackjack_refund_bet(usuario_id, player["pending_bet"])
    player["last_action"] = "Recolheu as fichas."
    player["pending_bet"] = 0.0
    blackjack_table["message"] = f"{usuario_id} limpou a area de aposta."
    await blackjack_broadcast_state()


@sio.on("acaoBlackjack")
async def acao_blackjack(sid, data):
    usuario_id = (data.get("usuarioId") or "").strip()
    action = data.get("action")
    ok, erro = await blackjack_apply_action(usuario_id, action)
    if not ok:
        await sio.emit("blackjackErro", {"mensagem": erro}, to=sid)
        return
    await blackjack_broadcast_state()


@sio.on("sairMesaBlackjack")
async def sair_mesa_blackjack(sid, data):
    usuario_id = (data.get("usuarioId") or "").strip()
    player = blackjack_table["players"].get(usuario_id)
    if not player:
        return

    if blackjack_table["phase"] == "betting" and player["pending_bet"] > 0:
        blackjack_refund_bet(usuario_id, player["pending_bet"])
        player["pending_bet"] = 0.0

    player["connected"] = False
    player["socketId"] = None
    player["last_action"] = "Deixou a mesa."
    try:
        await sio.leave_room(sid, BLACKJACK_ROOM)
    except Exception:
        pass
    blackjack_prune_players()
    await blackjack_broadcast_state()

# =======================================================
# LÓGICA AUTORITATIVA DE FARMING
# Todo clique/colheita do Frontend precisa passar por aqui
# =======================================================

@sio.on("start_farming")
async def start_farming(sid, data):
    email = data.get("email")
    farmer_id = data.get("farmer_id")
    
    # Validação Básica Anti-Cheat: Verificar se os dados existem
    if not email or not farmer_id:
        await sio.emit("error_msg", {"msg": "Ação de farm inválida!"}, to=sid)
        return

    conn = get_db()
    cursor = conn.cursor()
    
    # Checa se o fazendeiro pertence à pessoa e se ele está livre
    cursor.execute("SELECT is_working FROM farmers WHERE farmer_id = ? AND email = ?", (farmer_id, email))
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
        log(f"🌾 Fazendeiro {farmer_id} começou a trabalhar para {email}!")
        
        await sio.emit("farm_started", {"farmer_id": farmer_id, "start_time": current_time, "duration": 86400}, to=sid) # 86400 = 24hrs em segundos

    conn.close()

@sio.on("claim_nero")
async def claim_nero(sid, data):
    email = data.get("email")
    farmer_id = data.get("farmer_id")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM farmers WHERE farmer_id = ? AND email = ?", (farmer_id, email))
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
        
    # Pool de Recompensas Possíveis
    possiveis_recompensas = [
        "Trigo 🌾", 
        "Milho 🌽", 
        "Cenoura 🥕", 
        "Tomate 🍅", 
        "Madeira 🪵", 
        "Pedra 🪨", 
        "Ouro em Pó ✨", 
        "Moeda NERO 🪙", 
        "Gema de Cristal 💎"
    ]
    
    # Quantidade de RECOMPENSAS DIFERENTES (Nivel 1: de 3 a 8 itens variados)
    qtd_tipos_itens = random.randint(3, 8)
    itens_sorteados = random.sample(possiveis_recompensas, qtd_tipos_itens)
    
    itens_ganhos = {}
    poder = farmer['farming_power']
    
    # Opcional: Ainda damos um pouquinho de saldo nero fixo se for o caso, 
    # mas o foco principal são os itens!
    cursor.execute("UPDATE players SET nero_balance = nero_balance + ? WHERE email = ?", (1.0 * poder, email))
    
    # Processa os itens e salva no banco de dados (Tabela Inventory)
    for nome_item in itens_sorteados:
        # Quantidade que ele achou desse item específico
        quantidade = round(random.uniform(1.0, 5.0) * poder, 2)
        itens_ganhos[nome_item] = quantidade
        
        # Salva / Atualiza o item no inventário
        cursor.execute("""
            INSERT INTO inventory (email, item_name, quantity) 
            VALUES (?, ?, ?) 
            ON CONFLICT(email, item_name) 
            DO UPDATE SET quantity = quantity + ?
        """, (email, nome_item, quantidade, quantidade))

    # 2. Reseta o fazendeiro
    cursor.execute("UPDATE farmers SET is_working = 0, last_harvest_time = NULL WHERE farmer_id = ?", (farmer_id,))
    
    conn.commit()
    
    # Consulta como ficou o inventário completo do jogdor
    cursor.execute("SELECT item_name, quantity FROM inventory WHERE email = ?", (email,))
    novo_inventario = {row['item_name']: row['quantity'] for row in cursor.fetchall()}
    
    conn.close()
    
    log(f"🎒 {email} colheu múltiplos itens: {itens_ganhos}")
    await sio.emit("claim_success", {
        "farmer_id": farmer_id, 
        "rewards": itens_ganhos, 
        "new_inventory": novo_inventario
    }, to=sid)


# =======================================================
# LÓGICA DO UNO MULTIPLAYER (FILA E PARTIDA)
# =======================================================

filas_espera = {}
fila_tasks = {}
partidas = {}
partida_id_counter = 1

CORES_UNO = ['Vermelho', 'Azul', 'Verde', 'Amarelo']
VALORES_UNO = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'Pular', 'Inverter', '+2']

def gerar_baralho():
    import random
    baralho = []
    for cor in CORES_UNO:
        for valor in VALORES_UNO:
            baralho.append({'cor': cor, 'valor': valor})
            if valor != '0':
                baralho.append({'cor': cor, 'valor': valor})
    for _ in range(4):
        baralho.append({'cor': 'Curinga', 'valor': '+4'})
        baralho.append({'cor': 'Curinga', 'valor': 'Curinga'})
    random.shuffle(baralho)
    return baralho


def escolher_melhor_carta_index(mao, carta_mesa, penalidade=0):
    validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa, penalidade)]
    if not validas: return None
    normais = [i for i in validas if mao[i]["cor"] != "Curinga"]
    if normais:
        especiais = [i for i in normais if mao[i]["valor"] in ["+2", "Inverter", "Pular"]]
        if especiais: return especiais[0]
        return normais[0]
    return validas[0]

def validar_jogada(carta_jogador, carta_mesa, penalidade_acumulada=0):
    if penalidade_acumulada > 0:
        # Se tem penalidade acumulada, só pode jogar outra carta de compra para repassar ou aumentar
        if carta_mesa['valor'] == '+2':
            return carta_jogador['valor'] in ['+2', '+4']
        if carta_mesa['valor'] == '+4':
            return carta_jogador['valor'] in ['+2', '+4']
        return False

    if carta_jogador['cor'] == 'Curinga': return True
    if carta_jogador['valor'] == '+2': return True
    if carta_jogador['cor'] == carta_mesa['cor']: return True
    if str(carta_jogador['valor']) == str(carta_mesa['valor']): return True
    return False


async def bot_play_task(partida_id, bot_jogador):
    import time
    import random
    import asyncio
    while partida_id in partidas:
        await asyncio.sleep(1)  # Bot verifica o turno a cada 1 segundo (Mais rápido!)
        if partida_id not in partidas: break
        partida = partidas[partida_id]

        jogador_da_vez = partida["jogadores"][partida["turno_index"]]
        if jogador_da_vez["socketId"] != bot_jogador["socketId"]:
            continue
        else:
            log(f"[{partida_id}] Bot loop check confirmou o turno: {bot_jogador['usuarioId']}")

            # Se o jogador recuperou o controle (is_bot = False), o bot para de jogar por ele
            if not bot_jogador.get("is_bot", False):
                log(f"[{partida_id}] Bot {bot_jogador['usuarioId']} finalizou pq is_bot=False")
                break
        if partida_id not in partidas: break

        carta_mesa = partida["cartaMesa"]
        mao = bot_jogador["mao"]
        penalidade = partida.get("penalidade_acumulada", 0)

        if len(mao) == 0: break
        
        log(f"[{partida_id}] Turno do Mebot {bot_jogador['usuarioId']} - mesa: {carta_mesa} (Penalidade: {penalidade})")

        try:
            cartas_validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa, penalidade)]
            if cartas_validas:
                # O bot agora sempre escolhe a melhor jogada estratégica (escolher_melhor_carta_index)
                carta_index = escolher_melhor_carta_index(mao, carta_mesa, penalidade)
                
                cor_bot = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if mao[carta_index]['cor'] == 'Curinga' else None
                # Delay reduzido para 1.5 a 3 segundos para o jogo fluir melhor
                await asyncio.sleep(random.uniform(1.5, 3.0))
                await sio.emit("mensagem_jogo", {"msg": f"🤖 {bot_jogador['usuarioId']} está jogando..."}, room=partida_id)
                await processar_jogada(partida_id, bot_jogador["socketId"], carta_index, cor_bot)
            else:
                if len(partida["baralho"]) == 0:
                    partida["baralho"] = gerar_baralho()
                
                # Se tem penalidade, o bot come tudo e passa
                if penalidade > 0:
                    for _ in range(penalidade):
                        if len(partida["baralho"]) == 0: partida["baralho"] = gerar_baralho()
                        bot_jogador["mao"].append(partida["baralho"].pop())
                    partida["penalidade_acumulada"] = 0
                    await sio.emit("mensagem_jogo", {"msg": f"😢 {bot_jogador['usuarioId']} engoliu {penalidade} cartas!"}, room=partida_id)
                else:
                    # Compra normal
                    nova_carta = partida["baralho"].pop()
                    bot_jogador["mao"].append(nova_carta)

                if penalidade == 0 and validar_jogada(bot_jogador["mao"][-1], carta_mesa, 0):
                    carta_index = len(bot_jogador["mao"]) - 1
                    await sio.emit("mensagem_jogo", {"msg": f"{bot_jogador['usuarioId']} comprou uma carta e a usou!"}, room=partida_id)
                    cor_bot_nova = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if bot_jogador["mao"][-1]['cor'] == 'Curinga' else None
                    await asyncio.sleep(1.5)  # Pequeno delay antes de jogar a carta comprada
                    await processar_jogada(partida_id, bot_jogador["socketId"], carta_index, cor_bot_nova)
                else:
                    partida["turno_index"] = (partida["turno_index"] + partida["sentido_jogo"]) % len(partida["jogadores"])
                    partida["ultimo_turno_horario"] = time.time()
                    proximo_jogador = partida["jogadores"][partida["turno_index"]]["usuarioId"]
                    status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"])} for j in partida["jogadores"]]

                    await sio.emit("mensagem_jogo", {"msg": f"{bot_jogador['usuarioId']} comprou e passou a vez."}, room=partida_id)
                    await sio.emit("jogadaAceita", {
                        "jogador": bot_jogador["usuarioId"],
                        "carta": carta_mesa,
                        "proximoTurno": proximo_jogador,
                        "oponentes": status_jogadores
                    }, room=partida_id)
        except Exception as bot_err:
            import traceback
            log(f"ERRO NO BOT {bot_jogador['usuarioId']}: {bot_err}")
            traceback.print_exc()

async def check_matchmaking_timeout(aposta):
    import time
    import random
    import traceback
    import asyncio

    try:
        # Aguarda o limite pro bot entrar (10 seg)
        await asyncio.sleep(10)

        fila = filas_espera.get(aposta, [])
        if 0 < len(fila) < 4:
            log(f"⏳ Tempo limite da fila R$ {aposta:.2f} atingido. Adicionando {4 - len(fila)} BOTS...")
            falta = 4 - len(fila)

            prefixos = ["Alex", "Dani", "Gabi", "Mari", "Luiz", "Feli", "Brun", "Carl", "Vito", "Pedr", "Rafa", "Thia", "Guil", "Fern", "Leti", "Cami", "Juli", "Arth", "Bern", "Mich", "Davi", "Heit", "Math", "Luca", "Nico", "Enzo", "Yuri", "Kaua", "Igor", "Caio", "Kevi", "Will", "Ruan", "Vini", "Levi", "Theo", "Gael", "Migu", "Roge", "Dieg", "Andr", "Bata", "Silv", "Sant", "Melo", "Cost", "Lima", "Mora", "Gome", "Pere", "Ribe", "Mart", "Carv", "Alme", "Lope", "Soar", "Viei", "Mont", "Rodr", "Cunh", "Mede", "Nune", "Roch", "Frei", "Corr", "Mour", "Nasc", "Amar", "Card", "Teix", "Mach", "Tava", "Pint", "Agui", "Xavi", "Ramo", "Fari", "Borg", "Pinh", "Dias", "Brit", "Neve", "Maci", "Mati", "Vare", "Leal", "Vale", "Bast", "Texe", "Camp", "Mell", "Blan", "Garc", "Duar", "Figu", "Font", "Pess", "Fons", "Sale", "Band"]
            nomes_inteiros = ['Miguel', 'Arthur', 'Gael', 'Theo', 'Heitor', 'Ravi', 'Davi', 'Bernardo', 'Noah', 'Gabriel', 'Samuel', 'Pedro', 'Antonio', 'Joao', 'Isaac', 'Helena', 'Alice', 'Laura', 'Maria', 'Sophia', 'Manuela', 'Maite', 'Liz', 'Cecilia', 'Isabella', 'Luisa', 'Valentina', 'Heloisa', 'Julia', 'Livia', 'Lorena', 'Elisa', 'Giovanna', 'Matheus', 'Lucas', 'Nicolas', 'Joaquim', 'Henrique', 'Lorenzo', 'Benjamin', 'Thiago', 'Victor', 'Leonardo', 'Eduardo', 'Daniel', 'Vinicius', 'Francisco', 'Diego', 'Felipe', 'Carlos', 'Andre', 'Renato', 'Rodrigo', 'Fernando', 'Ricardo', 'Marcelo', 'Bruno', 'Caique', 'Igor', 'Breno', 'Alexandre', 'Caio', 'Douglas', 'Marcos', 'Rui', 'Hugo', 'Gustavo', 'Guilherme', 'Rafael', 'Otavio', 'Paulo', 'Jose', 'Julio', 'Roberto', 'Amanda', 'Beatriz', 'Bruna', 'Camila', 'Carolina', 'Leticia', 'Natalia', 'Larissa', 'Thais', 'Aline', 'Milena', 'Mariana', 'Fernanda', 'Vanessa', 'Gabriela', 'Juliana', 'Renata', 'Jessica', 'Vitoria', 'Patricia', 'Priscila', 'Tatiana', 'Daniela', 'Monica', 'Erica', 'Sabrina', 'Alessandra', 'Raquel', 'Mirella', 'Viviane', 'darkaco', 'detonatromba', 'matador_noob', 'ze_da_manga', 'sarrada_br', 'xX_matador_Xx', 'bala_tensa', 'pai_ta_on', 'mae_ta_on', 'goku_careca', 'careca_tv', 'tiringa', 'zeca_urubu', 'calvo_aos_20', 'jogador_caro', 'amassa_nozes', 'chupa_cabra', 'corta_giro', 'grau_e_corte', 'mandrake', 'cria_de_favela', 'noob_master', 'ping_999', 'so_capa', 'rei_do_gado', 'cachorro_louco', 'pao_de_batata', 'bolacha_br', 'toca_do_tatu', 'lobo_solitario', 'gato_net', 'robozao', 'deusa_gamer', 'imperador', 'cavaleiro_br', 'ninja_suave', 'assassino_br', 'bruxo_br', 'lenda_viva', 'mito_ofc', 'coringa_louco', 'peppa_pig', 'shaolin_matador', 'cabeca_de_gelo', 'bota_fogo', 'tio_patinhas', 'nego_ney', 'vidaloka', 'perna_longa', 'tropa_do_buxa', 'pro_player', 'ze_droguinha', 'mestre_yoda', 'anao_bombado']

            for _ in range(falta):
                tipo = random.random()
                if tipo < 0.33:
                    nome_bot = f"{random.choice(nomes_inteiros)}"
                elif tipo < 0.66:
                    nome_bot = f"{random.choice(prefixos)}"
                else:
                    numero = str(random.randint(0, 99)).zfill(2)
                    nome_bot = f"{random.choice(prefixos)}{numero}"

                bot_id = f"BOT_{random.randint(1000, 9999)}"
                # Bot do sistema tem avatar fixo pelo nome dele
                avatar_bot = f"sys_bot_{nome_bot}"
                bot_jogador = {"socketId": bot_id, "usuarioId": nome_bot, "mao": [], "is_bot": True, "aposta": aposta, "is_real": False, "avatar_seed": avatar_bot}
                fila.append(bot_jogador)

            await iniciar_partida_pronta(aposta)
    except Exception as e:
        log("💥 ERRO no matchmaking:", e)
        traceback.print_exc()


async def forcar_jogada_bot(partida_id, jogador):
    import time
    import random
    import asyncio
    partida = partidas.get(partida_id)
    if not partida: return
    await sio.emit("mensagem_jogo", {"msg": f"⏳ Tempo esgotado para {jogador['usuarioId']}! O sistema jogou..."}, room=partida_id)
    carta_mesa = partida["cartaMesa"]
    mao = jogador["mao"]
    penalidade = partida.get("penalidade_acumulada", 0)
    if not mao: return

    carta_index = escolher_melhor_carta_index(mao, carta_mesa, penalidade)
    if carta_index is not None:
        cor = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if mao[carta_index]['cor'] == 'Curinga' else None
        await processar_jogada(partida_id, jogador["socketId"], carta_index, cor)
    else:
        if len(partida["baralho"]) == 0:
            partida["baralho"] = gerar_baralho()
        
        if penalidade > 0:
            for _ in range(penalidade):
                if len(partida["baralho"]) == 0: partida["baralho"] = gerar_baralho()
                jogador["mao"].append(partida["baralho"].pop())
            partida["penalidade_acumulada"] = 0
            if not jogador.get("is_bot", False):
                await sio.emit("atualizarMao", {"mao": jogador["mao"]}, to=jogador["socketId"])
            await sio.emit("mensagem_jogo", {"msg": f"😢 {jogador['usuarioId']} engoliu {penalidade} cartas por timeout!"}, room=partida_id)
        else:
            nova_carta = partida["baralho"].pop()
            jogador["mao"].append(nova_carta)
            if not jogador.get("is_bot", False):
                await sio.emit("suaNovaCarta", {"carta": nova_carta}, to=jogador["socketId"])
        
        if penalidade == 0 and validar_jogada(jogador["mao"][-1], carta_mesa, 0):
            c_idx = len(jogador["mao"]) - 1
            c_nova = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if jogador["mao"][-1]['cor'] == 'Curinga' else None
            await processar_jogada(partida_id, jogador["socketId"], c_idx, c_nova)
        else:
            partida["turno_index"] = (partida["turno_index"] + partida["sentido_jogo"]) % len(partida["jogadores"])
            partida["ultimo_turno_horario"] = time.time()
            proximo_jogador = partida["jogadores"][partida["turno_index"]]["usuarioId"]
            status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"])} for j in partida["jogadores"]]
            await sio.emit("mensagem_jogo", {"msg": f"🤷‍♂️ Sistema comprou e passou a vez de {jogador['usuarioId']}."}, room=partida_id)
            await sio.emit("jogadaAceita", {
                "jogador": jogador["usuarioId"],
                "carta": partida["cartaMesa"],
                "proximoTurno": proximo_jogador,
                "oponentes": status_jogadores,
                "penalidade_acumulada": 0 # Após timeout e engolir, zera
            }, room=partida_id)

async def user_timeout_task(partida_id):
    import time
    import asyncio
    while partida_id in partidas:
        await asyncio.sleep(1)
        if partida_id not in partidas: break
        partida = partidas[partida_id]
        jogador_da_vez = partida["jogadores"][partida["turno_index"]]
        if jogador_da_vez.get("is_bot", False): continue

        tempo_agora = time.time()
        ultimo_turno = partida.get("ultimo_turno_horario", tempo_agora)
        if tempo_agora - ultimo_turno >= 10: # Timeout de 10 segundos para players reais
            await forcar_jogada_bot(partida_id, jogador_da_vez)
            if partida_id in partidas:
                partidas[partida_id]["ultimo_turno_horario"] = time.time() + 2

async def iniciar_partida_pronta(aposta):
    global partida_id_counter
    import time
    import random
    import asyncio
    fila = filas_espera.get(aposta, [])
    
    # Nova lógica: Evitar bots do mesmo dono na mesma partida
    jogadores_da_vez = []
    donos_na_partida = set()
    
    indices_para_remover = []
    for i, jog in enumerate(fila):
        dono = jog.get("owner_email")
        # Se for bot do sistema (is_real=False e nao tem is_user_bot), dono é None
        # Permitimos vários bots do sistema na mesma partida
        if dono and dono in donos_na_partida:
            continue # Pula este bot pq o dono já tem um na mesa
            
        jogadores_da_vez.append(jog)
        if dono: donos_na_partida.add(dono)
        indices_para_remover.append(i)
        
        if len(jogadores_da_vez) >= 4:
            break

    # Remove da fila os que entraram na partida (de trás pra frente para não errar index)
    for i in sorted(indices_para_remover, reverse=True):
        fila.pop(i)

    # Se não conseguimos 4 (devido à restrição de dono), mas a fila tinha gente, 
    # o timer do check_matchmaking_timeout vai acabar preenchendo com bots do sistema depois.
    # Mas se chamamos iniciar_partida_pronta MANUALMENTE (pq len >= 4), 
    # e agora temos < 4 por causa do filtro, precisamos completar com bots do sistema agora
    # para não travar a partida.
    if len(jogadores_da_vez) < 4:
        falta = 4 - len(jogadores_da_vez)
        log(f"Matchmaking: Filtrado por dono, faltam {falta} jogadores. Completando com bots do sistema...")
        # (Reutilizando a lógica de nomes de bots do timeout se possível, mas aqui faremos direto)
        for _ in range(falta):
            bot_id = f"SYS_BOT_{random.randint(1000, 9999)}"
            nome_bot = f"Bot_{random.randint(10, 99)}" 
            jogadores_da_vez.append({
                "socketId": bot_id, 
                "usuarioId": nome_bot, 
                "mao": [], 
                "is_bot": True, 
                "aposta": aposta, 
                "is_real": False,
                "owner_email": None, # Bots do sistema não têm dono
                "avatar_seed": f"sys_bot_{nome_bot}"
            })

    random.shuffle(jogadores_da_vez)
    partida_id = f"partida_{partida_id_counter}"
    partida_id_counter += 1

    baralho = gerar_baralho()
    for jog in jogadores_da_vez:
        jog["mao"] = [baralho.pop() for _ in range(7)]

    carta_mesa = baralho.pop()
    while carta_mesa['cor'] == 'Curinga':
        baralho.insert(0, carta_mesa)
        carta_mesa = baralho.pop()

    partidas[partida_id] = {
        "id": partida_id,
        "jogadores": jogadores_da_vez,
        "baralho": baralho,
        "cartaMesa": carta_mesa,
        "turno_index": 0,
        "sentido_jogo": 1,
        "ultimo_turno_horario": time.time(),
        "penalidade_acumulada": 0
    }

    status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"]), "avatar_seed": j.get("avatar_seed")} for j in jogadores_da_vez]
    
    for jog in jogadores_da_vez:
        if not jog.get("is_bot", False):
            await sio.enter_room(jog["socketId"], partida_id)
            await sio.emit("partidaIniciada", {
                "partidaId": partida_id,
                "suaMao": jog["mao"],
                "cartaMesa": carta_mesa,
                "turnoAtual": jogadores_da_vez[0]["usuarioId"],
                "oponentes": status_jogadores,
                "penalidade_acumulada": 0
            }, to=jog["socketId"])
        
        # Inicia a inteligência do bot (seja do sistema ou do usuário)
        if jog.get("is_bot", False):
            asyncio.create_task(bot_play_task(partida_id, jog))

    asyncio.create_task(user_timeout_task(partida_id))

@sio.on("verificarReconexao")
async def verificar_reconexao(sid, data):
    usuario_id = data.get("usuarioId")
    if not usuario_id: return
    
    # Procura se o jogador já está em alguma partida ativa
    for partida_id, partida in partidas.items():
        for jogador in partida["jogadores"]:
            if jogador["usuarioId"] == usuario_id:
                # O jogador estava aqui e possivelmente virou bot ou apenas fechou e reabriu rápido
                jogador["socketId"] = sid
                jogador["is_bot"] = False  # Recupera o controle para o humano!
                
                await sio.enter_room(sid, partida_id)
                status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"]), "avatar_seed": j.get("avatar_seed")} for j in partida["jogadores"]]
                log(f"📡 Enviando estado da partida {partida_id} para {usuario_id}. Oponentes: {[s['id'] for s in status_jogadores]}")
                
                # Manda o estado atualizado pro jogador
                log(f"🔄 Jogador {usuario_id} reconectado/assumiu partida {partida_id}")
                await sio.emit("partidaIniciada", {
                    "partidaId": partida_id,
                    "suaMao": jogador["mao"],
                    "cartaMesa": partida["cartaMesa"],
                    "turnoAtual": partida["jogadores"][partida["turno_index"]]["usuarioId"],
                    "oponentes": status_jogadores,
                    "reconexao": True,
                    "penalidade_acumulada": partida.get("penalidade_acumulada", 0)
                }, to=sid)
                
                # Avisa aos outros
                await sio.emit("mensagem_jogo", {"msg": f"🔄 {usuario_id} voltou e assumiu o controle!"}, room=partida_id)
                return
    
    # Se não achou na partida
    await sio.emit("reconexaoFalha", {}, to=sid)


@sio.on("deixarPartidaEmBackground")
async def deixar_background(sid, data):
    usuario_id = data.get("usuarioId")
    for partida_id, partida in partidas.items():
        for jogador in partida["jogadores"]:
            if jogador["usuarioId"] == usuario_id:
                jogador["is_bot"] = True
                log(f"🤖 {usuario_id} minimizou a partida! Bot assumiu.")
                await sio.emit("mensagem_jogo", {"msg": f"🏃 {usuario_id} deixou o jogo rodando em 2º plano. Bot assumiu!"}, room=partida_id)
                import asyncio
                asyncio.create_task(bot_play_task(partida_id, jogador))
                return


@sio.on("entrarFila")
async def entrar_fila(sid, data):
    import asyncio
    global partida_id_counter
    usuario_id = data.get("usuarioId")
    aposta = float(data.get("aposta", 1.0))
    
    # Remove se já estiver em alguma fila ou partida ativa (anti-duplicação)
    for v in filas_espera.values():
        for j in v[:]:
            if j["usuarioId"] == usuario_id:
                v.remove(j)
                log(f"🔄 {usuario_id} removido de outra fila antes de entrar na de R$ {aposta:.2f}")

    # Impede entrar na fila se já estiver em partida
    for pid, p in partidas.items():
        if any(jog["usuarioId"] == usuario_id for jog in p["jogadores"]):
            log(f"⚠️ {usuario_id} já está em uma partida ativa ({pid}). Impedindo nova fila.")
            await sio.emit("mensagem_jogo", {"msg": "Você já tem uma partida em andamento!"}, to=sid)
            return

    jogador = {
        "socketId": sid,
        "usuarioId": usuario_id,
        "mao": [],
        "is_bot": False,
        "aposta": aposta,
        "is_real": True,
        "owner_email": usuario_id, # Jogador real é dono de si mesmo
        "avatar_seed": data.get("avatarSeed")
    }
    
    if aposta not in filas_espera: filas_espera[aposta] = []
    filas_espera[aposta].append(jogador)
    log(f"➡️ {usuario_id} entrou na fila de R$ {aposta:.2f} (Total: {len(filas_espera[aposta])})")

    # Inicia timer se for o primeiro
    if len(filas_espera[aposta]) == 1:
        if aposta in fila_tasks and not fila_tasks[aposta].done():
            fila_tasks[aposta].cancel()
        fila_tasks[aposta] = asyncio.create_task(check_matchmaking_timeout(aposta))

    if len(filas_espera[aposta]) >= 4:
        if aposta in fila_tasks and not fila_tasks[aposta].done():
            fila_tasks[aposta].cancel()
        await iniciar_partida_pronta(aposta)

async def processar_jogada(partida_id, socket_id, carta_index, cor_escolhida=None):
    if partida_id not in partidas:
        return {"valida": False, "erro": "Partida não existe ou já finalizada."}

    partida = partidas[partida_id]
    jogador = next((j for j in partida["jogadores"] if j["socketId"] == socket_id), None)

    if not jogador:
        return {"valida": False, "erro": "Jogador não faz parte da partida."}
        
    jogador_da_vez = partida["jogadores"][partida["turno_index"]]
    if jogador_da_vez["socketId"] != socket_id:
        return {"valida": False, "erro": "Não é a sua vez de jogar!"}
    
    carta_mesa = partida["cartaMesa"]
    penalidade = partida.get("penalidade_acumulada", 0)
    try:
        carta_jogador = jogador["mao"][carta_index]
    except IndexError:
        return {"valida": False, "erro": "Índice de carta inválido."}

    if validar_jogada(carta_jogador, carta_mesa, penalidade):
        carta_removida = jogador["mao"][carta_index]

        is_curinga = (carta_removida['cor'] == 'Curinga')
        valor_jogado = carta_removida['valor']
        
        # Encontra todas as cartas de mesmo valor na mão
        cartas_iguais_idx = [i for i, c in enumerate(jogador["mao"]) if c['valor'] == valor_jogado]
        qtde_jogada = len(cartas_iguais_idx) if not is_curinga else 1

        if is_curinga:
            if not cor_escolhida:
                return {"valida": False, "erro": "Cor do curinga não escolhida"}
            carta_removida['cor_escolhida'] = cor_escolhida
            carta_removida['cor_display'] = carta_removida['cor']
            carta_removida['cor'] = carta_removida['cor_escolhida']
            carta_removida['cor_original'] = 'Curinga'
            jogador["mao"].pop(carta_index)
        else:
            # Remove todas do mesmo valor de trás pra frente
            for i in reversed(cartas_iguais_idx):
                jogador["mao"].pop(i)
                
            if qtde_jogada > 1:
                await sio.emit("mensagem_jogo", {"msg": f"🔥 {jogador['usuarioId']} COMBOU {qtde_jogada} cartas de valor '{valor_jogado}' de uma vez!"}, room=partida_id)

        partida["cartaMesa"] = carta_removida

        if carta_removida['valor'] == 'Inverter':
            if qtde_jogada % 2 != 0:
                partida["sentido_jogo"] *= -1

        # Lógica de Pular
        passo = 1 + qtde_jogada if carta_removida['valor'] == 'Pular' else 1
        
        # Lógica de Penalidade (+2 / +4) ACUMULATIVA
        if carta_removida['valor'] == '+2': 
            partida['penalidade_acumulada'] += (2 * qtde_jogada)
            await sio.emit("mensagem_jogo", {"msg": f"⚠️ Penalidade acumulada: {partida['penalidade_acumulada']} cartas! Próximo defende ou come!"}, room=partida_id)
        elif carta_removida['valor'] == '+4': 
            partida['penalidade_acumulada'] += (4 * qtde_jogada)
            await sio.emit("mensagem_jogo", {"msg": f"🌈 Penalidade BRUTAL: {partida['penalidade_acumulada']} cartas!"}, room=partida_id)

        partida["turno_index"] = (partida["turno_index"] + (passo * partida["sentido_jogo"])) % len(partida["jogadores"])
        partida["ultimo_turno_horario"] = time.time()

        try:
            proximo_jogador = partida["jogadores"][partida["turno_index"]]["usuarioId"]
            status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"])} for j in partida["jogadores"]]
            
            log(f"[{partida_id}] Emitindo jogadaAceita para o jogador {jogador['usuarioId']} e proximo é {proximo_jogador}")
            await sio.emit("mensagem_jogo", {"msg": f"🃏 {jogador['usuarioId']} jogou {carta_removida['valor']} {carta_removida['cor']}"}, room=partida_id)
            await sio.emit("jogadaAceita", {
                "jogador": jogador["usuarioId"],
                "carta": carta_removida,
                "proximoTurno": proximo_jogador,
                "oponentes": status_jogadores,
                "penalidade_acumulada": partida.get("penalidade_acumulada", 0)
            }, room=partida_id)

            await sio.emit("atualizarMao", {"mao": jogador["mao"]}, to=socket_id)

            # Checa vitória e encerra
            if len(jogador["mao"]) == 0:
                await finalizar_partida(partida, jogador)
                
            return {"valida": True}
        except Exception as e:
            log(f"!!! ERRO FATAL AO EMITIR JOGADA ACEITA: {e}")
            import traceback
            traceback.print_exc()
            return {"valida": False, "erro": "Erro interno no servidor ao processar jogada."}
    else:
        return {"valida": False, "erro": "Jogada ilegal perante as regras!"}

@sio.on("jogarCarta")
async def jogar_carta(sid, data):
    log(f"[{sid}] Recebeu tentar jogar carta: {data}")
    partida_id = data.get("partidaId")
    carta_index = data.get("cartaIndex")
    cor_escolhida = data.get("corEscolhida")
    
    try:
        resultado = await processar_jogada(partida_id, sid, carta_index, cor_escolhida)
        log(f"[{sid}] Resultado da jogada: {resultado}")
        if resultado and not resultado.get("valida"):
            log(f"[{sid}] Jogada inválida, enviando resposta erro: {resultado.get('erro')}")
            await sio.emit("jogadaInvalida", {"mensagem": resultado.get("erro", "Erro na jogada")}, to=sid)
    except Exception as e:
        log(f"!!! ERRO em jogar_carta: {e}")
        import traceback
        traceback.print_exc()
        await sio.emit("jogadaInvalida", {"mensagem": "Erro interno do servidor!"}, to=sid)

@sio.on("comprarCartaAqui")
async def comprar_carta_aqui(sid, data):
    partida_id = data.get("partidaId")
    if partida_id not in partidas: return
    
    partida = partidas[partida_id]
    jogador_da_vez = partida["jogadores"][partida["turno_index"]]
    
    if jogador_da_vez["socketId"] != sid:
        await sio.emit("jogadaInvalida", {"mensagem": "Não é a sua vez de comprar!"}, to=sid)
        return
        
    baralho = partida["baralho"]
    penalidade = partida.get("penalidade_acumulada", 0)
    
    if penalidade > 0:
        for _ in range(penalidade):
            if len(baralho) == 0:
                baralho = gerar_baralho()
                partida["baralho"] = baralho
            jogador_da_vez["mao"].append(baralho.pop())
        partida["penalidade_acumulada"] = 0
        await sio.emit("mensagem_jogo", {"msg": f"🤷‍♂️ {jogador_da_vez['usuarioId']} engoliu {penalidade} cartas e passou a vez."}, room=partida_id)
        await sio.emit("atualizarMao", {"mao": jogador_da_vez["mao"]}, to=sid)
    else:
        if len(baralho) == 0:
            baralho = gerar_baralho()
            partida["baralho"] = baralho
        nova_carta = baralho.pop()
        jogador_da_vez["mao"].append(nova_carta)
        await sio.emit("mensagem_jogo", {"msg": f"🤷‍♂️ {jogador_da_vez['usuarioId']} comprou uma carta e passou a vez."}, room=partida_id)
        await sio.emit("suaNovaCarta", {"carta": nova_carta}, to=sid)
    
    # Passa o turno
    partida["turno_index"] = (partida["turno_index"] + partida["sentido_jogo"]) % len(partida["jogadores"])
    partida["ultimo_turno_horario"] = time.time()
    proximo_jogador = partida["jogadores"][partida["turno_index"]]["usuarioId"]
    status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"])} for j in partida["jogadores"]]

    await sio.emit("jogadaAceita", {
        "jogador": jogador_da_vez["usuarioId"],
        "carta": partida["cartaMesa"],  # Mesa não muda
        "proximoTurno": proximo_jogador,
        "oponentes": status_jogadores,
        "penalidade_acumulada": 0
    }, room=partida_id)

async def finalizar_partida(partida, jogador_vencedor):
    aposta_vencedor = float(jogador_vencedor.get("aposta", 1.0))
    taxa = aposta_vencedor * 4 * 0.05
    premio = (aposta_vencedor * 4) - taxa
    vencedor_id = jogador_vencedor["usuarioId"]
    partida_id = partida["id"]

    log(f"🏆 Partida {partida_id} Vencida por: {vencedor_id} | Prêmio: R$ {premio:.2f}")

    # Só tenta creditar no banco se não for Bot do Sistema
    if jogador_vencedor.get("is_real", False):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (vencedor_id,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE id = ?", (premio, user['id']))
            cursor.execute("INSERT INTO transacoes (usuario_id, valor, tipo) VALUES (?, ?, ?)", (user['id'], premio, 'Premio'))
            conn.commit()
        conn.close()
    elif jogador_vencedor.get("is_user_bot", False):
        # Crédito para o dono do bot
        bot_owner_email = jogador_vencedor.get("owner_email")
        bot_id = jogador_vencedor.get("bot_id")
        log(f"🤖 Bot do Usuário {vencedor_id} (Dono: {bot_owner_email}) venceu! Creditando...")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE bots SET saldo = saldo + ? WHERE id = ?", (premio, bot_id))
        conn.commit()
        conn.close()
    else:
        log(f"🤖 O BOT do Sistema {vencedor_id} venceu! O dinheiro ficará para a plataforma.")

    await sio.emit("fimDeJogo", {
        "vencedor": vencedor_id,
        "premio_total": premio
    }, room=partida_id)
    
    # Limpa a sala para evitar vazamento de memória e recepção de eventos de partidas antigas
    for j in partida["jogadores"]:
        if not j.get("is_bot", False):
            try:
                await sio.leave_room(j["socketId"], partida_id)
            except:
                pass

    partidas.pop(partida_id, None)
@sio.on("forcarAutoPlay")
async def force_autoplay(sid, data):
    partida_id = data.get("partidaId")
    if partida_id not in partidas: return
    
    partida = partidas[partida_id]
    jogador = next((j for j in partida["jogadores"] if j["socketId"] == sid), None)
    if not jogador: return
    
    # Se eh o turno dele, o servidor roda a logica do bot instantaneamente
    jogador_da_vez = partida["jogadores"][partida["turno_index"]]
    if jogador_da_vez["socketId"] == sid:
        await forcar_jogada_bot(partida_id, jogador)

async def monitorar_bots_usuarios():
    log("🤖 Monitor de Bots de Usuários Iniciado!")
    while True:
        await asyncio.sleep(5)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bots WHERE status = 'Ativo'")
            bots_ativos = cursor.fetchall()
            conn.close()

            for bot in bots_ativos:
                # Verifica se o bot já está em alguma fila ou partida
                ja_jogando = False
                for aposta, fila in filas_espera.items():
                    if any(j.get("bot_id") == bot['id'] for j in fila):
                        ja_jogando = True
                        break
                
                if not ja_jogando:
                    for pid, p in partidas.items():
                        if any(j.get("bot_id") == bot['id'] for j in p["jogadores"]):
                            ja_jogando = True
                            break
                
                if ja_jogando:
                    continue

                # Verifica Stop Loss / Stop Win
                if bot['saldo'] <= bot['stop_loss'] or bot['saldo'] >= bot['stop_win']:
                    motivo = "Stop Loss atingido" if bot['saldo'] <= bot['stop_loss'] else "Stop Win atingido"
                    log(f"🛑 Bot {bot['nome']} atingiu limites (Saldo: {bot['saldo']}). Motivo: {motivo}")
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE bots SET status = 'Parado', motivo_status = ? WHERE id = ?", (motivo, bot['id']))
                    conn.commit()
                    conn.close()
                    continue

                # Tenta entrar na fila se tiver saldo para aposta
                custo_aposta = float(bot['valor_aposta'] if bot['valor_aposta'] is not None else 1.0)
                if bot['saldo'] >= custo_aposta:
                    conn = get_db()
                    cursor = conn.cursor()
                    # Deduz aposta do saldo do bot
                    cursor.execute("UPDATE bots SET saldo = saldo - ? WHERE id = ?", (custo_aposta, bot['id']))
                    conn.commit()
                    conn.close()

                    # Simula entrada na fila
                    jogador_bot = {
                        "socketId": f"USER_BOT_{bot['id']}",
                        "usuarioId": f"{bot['nome']} (Bot)",
                        "mao": [],
                        "is_bot": True,
                        "is_user_bot": True,  # Flag para identificar bot de usuário
                        "owner_email": bot['usuario_email'],
                        "bot_id": bot['id'],
                        "aposta": custo_aposta,
                        "is_real": False,
                        "avatar_seed": f"user_bot_{bot['nome']}" # Pode ser diferente
                    }
                    
                    if custo_aposta not in filas_espera: filas_espera[custo_aposta] = []
                    filas_espera[custo_aposta].append(jogador_bot)
                    log(f"🤖 Bot '{bot['nome']}' do usuário {bot['usuario_email']} entrou na fila de R$ {custo_aposta}")

                    # Se for o primeiro, inicia o timer
                    if len(filas_espera[custo_aposta]) == 1:
                        if custo_aposta in fila_tasks and not fila_tasks[custo_aposta].done():
                            fila_tasks[custo_aposta].cancel()
                        fila_tasks[custo_aposta] = asyncio.create_task(check_matchmaking_timeout(custo_aposta))

                    # Se já tem 4, inicia
                    if len(filas_espera[custo_aposta]) >= 4:
                        if custo_aposta in fila_tasks and not fila_tasks[custo_aposta].done():
                            fila_tasks[custo_aposta].cancel()
                        await iniciar_partida_pronta(custo_aposta)

        except Exception as e:
            log(f"❌ Erro no monitor de bots: {e}")
            import traceback
            traceback.print_exc()

