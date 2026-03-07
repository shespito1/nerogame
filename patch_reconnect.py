import re

with open('socket_handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

reconnect_handler = """@sio.on("entrarFila")
async def entrar_fila(sid, data):"""

new_reconnect = """@sio.on("verificarReconexao")
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
                status_jogadores = [{"id": j["usuarioId"], "cartas": len(j["mao"])} for j in partida["jogadores"]]
                
                # Manda o estado atualizado pro jogador
                print(f"🔄 Jogador {usuario_id} reconectado à partida {partida_id}")
                await sio.emit("partidaIniciada", {
                    "partidaId": partida_id,
                    "suaMao": jogador["mao"],
                    "cartaMesa": partida["cartaMesa"],
                    "turnoAtual": partida["jogadores"][partida["turno_index"]]["usuarioId"],
                    "oponentes": status_jogadores
                }, to=sid)
                
                # Avisa aos outros
                await sio.emit("mensagem_jogo", {"msg": f"🔄 {usuario_id} voltou e assumiu o controle!"}, room=partida_id)
                return
    
    # Se não achou na partida
    await sio.emit("reconexaoFalha", {}, to=sid)


@sio.on("entrarFila")
async def entrar_fila(sid, data):"""

content = content.replace(reconnect_handler, new_reconnect)

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added verificarReconexao logic")
