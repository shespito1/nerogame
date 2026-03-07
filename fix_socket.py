with open('socket_handler.py', 'r', encoding='utf-8') as f:
    c = f.read()

import re
match = re.search(r'carta_removida = jogador\["mao"\].pop\(carta_index\).*?erro": "Cor do curinga não escolhida"\}', c, re.DOTALL)
if match:
    new_str = '''carta_removida = jogador["mao"][carta_index]
        
        # Se for curinga
        if carta_removida['cor'] == 'Curinga':
            if not cor_escolhida:
                return {"valida": False, "erro": "Cor do curinga não escolhida"}
        
        jogador["mao"].pop(carta_index)'''
    c = c.replace(match.group(0), new_str)
    with open('socket_handler.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Fixed pop bug!')
