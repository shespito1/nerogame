# -*- coding: utf-8 -*-
with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

new_code = '''        carta_removida = jogador["mao"][carta_index]

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

        passo = 1 + qtde_jogada if carta_removida['valor'] == 'Pular' else 1

        qtde_comprar = 0
        if carta_removida['valor'] == '+2': qtde_comprar = 2 * qtde_jogada
        elif carta_removida['valor'] == '+4': qtde_comprar = 4 * qtde_jogada

        if qtde_comprar > 0:
            vitima_index = (partida["turno_index"] + (1 * partida["sentido_jogo"])) % len(partida["jogadores"])
            vitima = partida["jogadores"][vitima_index]
            for _ in range(qtde_comprar):
                if len(partida["baralho"]) == 0:
                    partida["baralho"] = gerar_baralho()
                nova_carta = partida["baralho"].pop()
                vitima["mao"].append(nova_carta)
                if not vitima.get("is_bot", False):
                    await sio.emit("suaNovaCarta", {"carta": nova_carta}, to=vitima["socketId"])

            await sio.emit("mensagem_jogo", {"msg": f"😢 {vitima['usuarioId']} engoliu {qtde_comprar} cartas da penalidade!"}, room=partida_id)
            passo = 1 + qtde_jogada if carta_removida['valor'] in ['+2', '+4'] else passo'''

text = re.sub(r'        carta_removida = jogador\["mao"\]\[carta_index\].*?passo = 2 # Pula a vez da vítima', new_code, text, flags=re.DOTALL)

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patched " + str("OK" if new_code in text else "FAILED"))
