import re
with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = '''            await sio.emit("jogadaAceita", {
                "jogador": jogador["usuarioId"],
                "carta": carta_removida,
                "proximoTurno": proximo_jogador,
                "oponentes": status_jogadores
            }, room=partida_id)

            await sio.emit("atualizarMao", {"mao": jogador["mao"]}, to=socket_id)'''

if 'await sio.emit("atualizarMao", {"mao": jogador["mao"]}, to=socket_id)' not in text:
    text = re.sub(r'await sio\.emit\("jogadaAceita", \{\s*"jogador": jogador\["usuarioId"\],\s*"carta": carta_removida,\s*"proximoTurno": proximo_jogador,\s*"oponentes": status_jogadores\s*\}, room=partida_id\)', replacement, text, flags=re.DOTALL)

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(text)
