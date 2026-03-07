# -*- coding: utf-8 -*-
with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# To be absolutely sure, let's log the actual error if validation fails in auto-play
text = text.replace('await processar_jogada(partida_id, jogador["socketId"], carta_index, cor)', 'res = await processar_jogada(partida_id, jogador["socketId"], carta_index, cor)\n        if not res.get("valida"):\n            print(f"AUTO-PLAY ERRO: {res}")')

text = text.replace('await processar_jogada(partida_id, jogador["socketId"], carta_index, cor_nova)', 'res2 = await processar_jogada(partida_id, jogador["socketId"], carta_index, cor_nova)\n            if not res2.get("valida"):\n                print(f"AUTO-PLAY COMPRA ERRO: {res2}")')

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(text)
