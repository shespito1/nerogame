old = """@sio.event
async def disconnect(sid):
    print(f"❌ Jogador desconectou: {sid}")

# ======================================================="""

new = """@sio.event
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

# ======================================================="""

with open('socket_handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

if old in content:
    with open('socket_handler.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(old, new))
    print("Patched successfully!")
else:
    print("Old string not found in socket_handler.py.")