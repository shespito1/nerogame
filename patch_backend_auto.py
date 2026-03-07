# -*- coding: utf-8 -*-
with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

handler_logic = '''
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

'''

if 'def force_autoplay' not in text:
    text += handler_logic

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(text)
