import re

with open('socket_handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the entering queue player to have 'is_real': True
old_entrar_fila = 'jogador = {"socketId": sid, "usuarioId": usuario_id, "mao": [], "is_bot": False, "aposta": aposta}'
new_entrar_fila = 'jogador = {"socketId": sid, "usuarioId": usuario_id, "mao": [], "is_bot": False, "aposta": aposta, "is_real": True}'
content = content.replace(old_entrar_fila, new_entrar_fila)

# 2. Update the payout logic to use 'is_real'
old_payout = 'if not jogador_vencedor.get("is_bot", False):'
new_payout = 'if jogador_vencedor.get("is_real", False):'
content = content.replace(old_payout, new_payout)

# 3. Add check in bot_play_task to stop if player reclaimed control
old_bot_task = """        if jogador_da_vez["socketId"] != bot_jogador["socketId"]:
            continue

        await asyncio.sleep(random.uniform(1.5, 3.0))"""

new_bot_task = """        if jogador_da_vez["socketId"] != bot_jogador["socketId"]:
            continue

        # Se o jogador recuperou o controle (is_bot = False), o bot para de jogar por ele
        if not bot_jogador.get("is_bot", False):
            break

        await asyncio.sleep(random.uniform(1.5, 3.0))"""
content = content.replace(old_bot_task, new_bot_task)

# 4. Add the toggle endpoint (minimizar/deixar no background)
endpoint = """@sio.on("deixarPartidaEmBackground")
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


@sio.on("entrarFila")"""

content = content.replace('@sio.on("entrarFila")', endpoint)


with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Backend features for background playing updated!")
