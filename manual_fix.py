import sys
with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
fixed = re.sub(
    r'print\(f\"\[\{partida_id\}\] Emitindo jogadaAceita para o jogador \{jogador\[\'usuarioId\'\]\} e proximo.*?\{proximo_jogador\}\"\).*?await sio\.emit\(\"jogadaAceita\", \{',
    'print(f"[{partida_id}] Emitindo jogadaAceita para o jogador {jogador[\'usuarioId\']} e proximo é {proximo_jogador}")\n            await sio.emit("jogadaAceita", {',
    text, flags=re.DOTALL
)

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(fixed)
