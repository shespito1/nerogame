# -*- coding: utf-8 -*-
with open("socket_handler.py", "r", encoding="utf-8") as f:
    text = f.read()

melhor_carta_logic = """
def escolher_melhor_carta_index(mao, carta_mesa):
    validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa)]
    if not validas: return None
    normais = [i for i in validas if mao[i]["cor"] != "Curinga"]
    if normais:
        especiais = [i for i in normais if mao[i]["valor"] in ["+2", "Inverter", "Pular"]]
        if especiais: return especiais[0]
        return normais[0]
    return validas[0]
"""

if "escolher_melhor_carta_index" not in text:
    text = text.replace("def validar_jogada(carta_jogador, carta_mesa):", melhor_carta_logic + "\ndef validar_jogada(carta_jogador, carta_mesa):")

text = text.replace("cartas_validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa)]\n    if cartas_validas:\n        import random\n        carta_index = cartas_validas[0]", "carta_index = escolher_melhor_carta_index(mao, carta_mesa)\n    if carta_index is not None:\n        import random")

text = text.replace("cartas_validas = [i for i, c in enumerate(mao) if validar_jogada(c, carta_mesa)]\n\n        if cartas_validas:\n            carta_index = cartas_validas[0]", "carta_index = escolher_melhor_carta_index(mao, carta_mesa)\n        if carta_index is not None:")

with open("socket_handler.py", "w", encoding="utf-8") as f:
    f.write(text)

