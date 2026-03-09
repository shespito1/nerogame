import socketio
import time
import random
import asyncio
from database import get_db

# Criação do servidor Socket.IO (Assíncrono para aguentar muitos jogadores)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"🎮 Novo jogador conectou na fazenda! ID da sessão: {sid}")
    # Inicia o monitor de bots se ainda não estiver rodando (usamos uma flag global)
    if not hasattr(sio, 'bot_monitor_started'):
        sio.bot_monitor_started = True
        asyncio.create_task(monitorar_bots_usuarios())

@sio.event
async def disconnect(sid):
    print(f"❌ Jogador desconectou: {sid}")
    
    # Se o jogador estiver em uma partida, transforma ele em BOT
    for partida_id, partida in partidas.items():
        for jogador in partida["jogadores"]:
            if jogador.get("socketId") == sid and not jogador.get("is_bot", False):
                jogador["is_bot"] = True
                print(f"🤖 Jogador {jogador['usuarioId']} ({sid}) caiu. Auto-play ativado na partida {partida_id}!")
                # Avise os outros na sala e comece a tarefa de bot para ele
                asyncio.create_task(sio.emit("mensagem_jogo", {"msg": f"🔌 {jogador['usuarioId']} caiu da partida e agora está no modo automático!"}, room=partida_id))
                asyncio.create_task(bot_play_task(partida_id, jogador))
                break

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
        print(f"🌾 Fazendeiro {farmer_id} começou a trabalhar para {email}!")
        
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
    
    print(f"🎒 {email} colheu múltiplos itens: {itens_ganhos}")
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
            return carta_jogador['valor'] == '+4'
        return False

    if carta_jogador['cor'] == 'Curinga': return True
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
            print(f"[{partida_id}] Bot loop check confirmou o turno: {bot_jogador['usuarioId']}")

            # Se o jogador recuperou o controle (is_bot = False), o bot para de jogar por ele
            if not bot_jogador.get("is_bot", False):
                print(f"[{partida_id}] Bot {bot_jogador['usuarioId']} finalizou pq is_bot=False")
                break
        if partida_id not in partidas: break

        carta_mesa = partida["cartaMesa"]
        mao = bot_jogador["mao"]
        penalidade = partida.get("penalidade_acumulada", 0)

        if len(mao) == 0: break
        
        print(f"[{partida_id}] Turno do Mebot {bot_jogador['usuarioId']} - mesa: {carta_mesa} (Penalidade: {penalidade})")

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
            print(f"ERRO NO BOT {bot_jogador['usuarioId']}: {bot_err}")
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
            print(f"⏳ Tempo limite da fila R$ {aposta:.2f} atingido. Adicionando {4 - len(fila)} BOTS...")
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
        print("💥 ERRO no matchmaking:", e)
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
        print(f"Matchmaking: Filtrado por dono, faltam {falta} jogadores. Completando com bots do sistema...")
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
                print(f"📡 Enviando estado da partida {partida_id} para {usuario_id}. Oponentes: {[s['id'] for s in status_jogadores]}")
                
                # Manda o estado atualizado pro jogador
                print(f"🔄 Jogador {usuario_id} reconectado/assumiu partida {partida_id}")
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
                print(f"🤖 {usuario_id} minimizou a partida! Bot assumiu.")
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
                print(f"🔄 {usuario_id} removido de outra fila antes de entrar na de R$ {aposta:.2f}")

    # Impede entrar na fila se já estiver em partida
    for pid, p in partidas.items():
        if any(jog["usuarioId"] == usuario_id for jog in p["jogadores"]):
            print(f"⚠️ {usuario_id} já está em uma partida ativa ({pid}). Impedindo nova fila.")
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
    print(f"➡️ {usuario_id} entrou na fila de R$ {aposta:.2f} (Total: {len(filas_espera[aposta])})")

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
            
            print(f"[{partida_id}] Emitindo jogadaAceita para o jogador {jogador['usuarioId']} e proximo é {proximo_jogador}")
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
            print(f"!!! ERRO FATAL AO EMITIR JOGADA ACEITA: {e}")
            import traceback
            traceback.print_exc()
            return {"valida": False, "erro": "Erro interno no servidor ao processar jogada."}
    else:
        return {"valida": False, "erro": "Jogada ilegal perante as regras!"}

@sio.on("jogarCarta")
async def jogar_carta(sid, data):
    print(f"[{sid}] Recebeu tentar jogar carta: {data}")
    partida_id = data.get("partidaId")
    carta_index = data.get("cartaIndex")
    cor_escolhida = data.get("corEscolhida")
    
    try:
        resultado = await processar_jogada(partida_id, sid, carta_index, cor_escolhida)
        print(f"[{sid}] Resultado da jogada: {resultado}")
        if resultado and not resultado.get("valida"):
            print(f"[{sid}] Jogada inválida, enviando resposta erro: {resultado.get('erro')}")
            await sio.emit("jogadaInvalida", {"mensagem": resultado.get("erro", "Erro na jogada")}, to=sid)
    except Exception as e:
        print(f"!!! ERRO em jogar_carta: {e}")
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

    print(f"🏆 Partida {partida_id} Vencida por: {vencedor_id} | Prêmio: R$ {premio:.2f}")

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
        print(f"🤖 Bot do Usuário {vencedor_id} (Dono: {bot_owner_email}) venceu! Creditando...")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE bots SET saldo = saldo + ? WHERE id = ?", (premio, bot_id))
        conn.commit()
        conn.close()
    else:
        print(f"🤖 O BOT do Sistema {vencedor_id} venceu! O dinheiro ficará para a plataforma.")

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
    print("🤖 Monitor de Bots de Usuários Iniciado!")
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
                    print(f"🛑 Bot {bot['nome']} atingiu limites (Saldo: {bot['saldo']}). Motivo: {motivo}")
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
                    print(f"🤖 Bot '{bot['nome']}' do usuário {bot['usuario_email']} entrou na fila de R$ {custo_aposta}")

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
            print(f"❌ Erro no monitor de bots: {e}")
            import traceback
            traceback.print_exc()

