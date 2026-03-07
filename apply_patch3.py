import re

new_text = '''filas_espera = {}
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


def escolher_melhor_carta_index(mao, carta_mesa):
    validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa)]
    if not validas: return None
    normais = [i for i in validas if mao[i]["cor"] != "Curinga"]
    if normais:
        especiais = [i for i in normais if mao[i]["valor"] in ["+2", "Inverter", "Pular"]]
        if especiais: return especiais[0]
        return normais[0]
    return validas[0]

def validar_jogada(carta_jogador, carta_mesa):
    if carta_jogador['cor'] == 'Curinga': return True
    if carta_jogador['cor'] == carta_mesa['cor']: return True
    if str(carta_jogador['valor']) == str(carta_mesa['valor']): return True
    return False

async def bot_play_task(partida_id, bot_jogador):
    import time
    import random
    import asyncio
    while partida_id in partidas:
        await asyncio.sleep(1)
        if partida_id not in partidas: break
        partida = partidas[partida_id]

        jogador_da_vez = partida["jogadores"][partida["turno_index"]]
        if jogador_da_vez["socketId"] != bot_jogador["socketId"]:
            continue

        await asyncio.sleep(random.uniform(1.5, 3.0))
        if partida_id not in partidas: break

        carta_mesa = partida["cartaMesa"]
        mao = bot_jogador["mao"]

        if len(mao) == 0: break

        cartas_validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa)]
        if cartas_validas:
            carta_index = cartas_validas[0]
            cor_bot = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if mao[carta_index]['cor'] == 'Curinga' else None
            await processar_jogada(partida_id, bot_jogador["socketId"], carta_index, cor_bot)
        else:
            if len(partida["baralho"]) == 0:
                partida["baralho"] = gerar_baralho()
            nova_carta = partida["baralho"].pop()
            bot_jogador["mao"].append(nova_carta)

            if validar_jogada(nova_carta, carta_mesa):
                carta_index = len(bot_jogador["mao"]) - 1
                await sio.emit("mensagem_jogo", {"msg": f"{bot_jogador['usuarioId']} comprou uma carta e a usou!"}, room=partida_id)
                cor_bot_nova = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if nova_carta['cor'] == 'Curinga' else None
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

async def check_matchmaking_timeout(aposta):
    import time
    import random
    import asyncio
    await asyncio.sleep(10)
    fila = filas_espera.get(aposta, [])
    if 0 < len(fila) < 4:
        falta = 4 - len(fila)
        nomes_reais_bots = ["Miguel", "Arthur", "Gael", "Theo", "Heitor", "Ravi", "Davi", "Bernardo", "Noah", "Gabriel", "Samuel", "Pedro", "Antonio", "Joao", "Isaac", "Helena", "Alice", "Laura", "Maria", "Sophia", "Manuela", "Maite", "Liz", "Cecilia", "Isabella", "Luisa", "Valentina"]
        for _ in range(falta):
            nome_bot = random.choice(nomes_reais_bots)
            bot_id = f"BOT_{random.randint(1000, 9999)}"
            bot_jogador = {"socketId": bot_id, "usuarioId": nome_bot, "mao": [], "is_bot": True, "aposta": aposta}
            fila.append(bot_jogador)
        await iniciar_partida_pronta(aposta)

async def forcar_jogada_bot(partida_id, jogador):
    import time
    import random
    import asyncio
    partida = partidas.get(partida_id)
    if not partida: return
    await sio.emit("mensagem_jogo", {"msg": f"⏳ Tempo esgotado para {jogador['usuarioId']}! O sistema jogou..."}, room=partida_id)
    carta_mesa = partida["cartaMesa"]
    mao = jogador["mao"]
    if not mao: return

    carta_index = escolher_melhor_carta_index(mao, carta_mesa)
    if carta_index is not None:
        cor = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if mao[carta_index]['cor'] == 'Curinga' else None
        await processar_jogada(partida_id, jogador["socketId"], carta_index, cor)
    else:
        if len(partida["baralho"]) == 0:
            partida["baralho"] = gerar_baralho()
        nova_carta = partida["baralho"].pop()
        jogador["mao"].append(nova_carta)
        if not jogador.get("is_bot", False):
            await sio.emit("suaNovaCarta", {"carta": nova_carta}, to=jogador["socketId"])
        
        if validar_jogada(nova_carta, carta_mesa):
            c_idx = len(jogador["mao"]) - 1
            c_nova = random.choice(['Vermelho', 'Azul', 'Verde', 'Amarelo']) if nova_carta['cor'] == 'Curinga' else None
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
                "oponentes": status_jogadores
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
        if tempo_agora - ultimo_turno >= 14:
            await forcar_jogada_bot(partida_id, jogador_da_vez)
            if partida_id in partidas:
                partidas[partida_id]["ultimo_turno_horario"] = time.time() + 2

async def iniciar_partida_pronta(aposta):
    global partida_id_counter
    import time
    import random
    import asyncio
    fila = filas_espera.get(aposta, [])
    jogadores_da_vez = [fila.pop(0) for _ in range(4)]
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
        "ultimo_turno_horario": time.time()
    }

    status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"])} for j in jogadores_da_vez]
    
    for jog in jogadores_da_vez:
        if not jog.get("is_bot", False):
            await sio.enter_room(jog["socketId"], partida_id)
            await sio.emit("partidaIniciada", {
                "partidaId": partida_id,
                "suaMao": jog["mao"],
                "cartaMesa": carta_mesa,
                "turnoAtual": jogadores_da_vez[0]["usuarioId"],
                "oponentes": status_jogadores
            }, to=jog["socketId"])
        else:
            asyncio.create_task(bot_play_task(partida_id, jog))

    asyncio.create_task(user_timeout_task(partida_id))

@sio.on("entrarFila")
async def entrar_fila(sid, data):
    import asyncio
    global partida_id_counter
    usuario_id = data.get("usuarioId")
    aposta = float(data.get("aposta", 1.0))

    jogador = {"socketId": sid, "usuarioId": usuario_id, "mao": [], "is_bot": False, "aposta": aposta}
    
    if aposta not in filas_espera: filas_espera[aposta] = []
    
    filas_espera[aposta].append(jogador)
    print(f"[{usuario_id}] entrou na fila do UNO apostando R$ {aposta:.2f}. Total na fila desta aposta: {len(filas_espera[aposta])}")
    
    if aposta == 50.00:
        if len(filas_espera[aposta]) >= 4:
            await iniciar_partida_pronta(aposta)
        return

    if len(filas_espera[aposta]) == 1:
        if aposta in fila_tasks and not fila_tasks[aposta].done():
            fila_tasks[aposta].cancel()
        fila_tasks[aposta] = asyncio.create_task(check_matchmaking_timeout(aposta))

    if len(filas_espera[aposta]) >= 4:
        if aposta in fila_tasks and not fila_tasks[aposta].done():
            fila_tasks[aposta].cancel()
        await iniciar_partida_pronta(aposta)

async def processar_jogada(partida_id, socket_id, carta_index, cor_escolhida=None):'''

with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = re.sub(r'fila_espera = \[\].*?a=None\):', new_text, text2, flags=re.DOTALL)
with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(text2)
