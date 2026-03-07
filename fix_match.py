import re

def fix():
    with open('socket_handler.py', 'r', encoding='utf-8') as f:
        code = f.read()

    new_code = '''async def check_matchmaking_timeout(aposta):
    import time
    import random
    import traceback
    import asyncio

    try:
        # Aguarda o limite pro bot entrar (10 seg)
        await asyncio.sleep(10)

        fila = filas_espera.get(aposta, [])
        if 0 < len(fila) < 4:
            print(f"⏳ Tempo limite da fila R$ {aposta:.2f} atingido. Adicionando {4 - len(fila)} BOTS...")
            falta = 4 - len(fila)

            prefixos = ["Alex", "Dani", "Gabi", "Mari"]
            nomes_inteiros = ['Miguel', 'Arthur', 'Gael']
            
            for _ in range(falta):
                num = str(random.randint(0, 99)).zfill(2)
                nome_bot = f"{random.choice(prefixos)}{num}"
                bot_id = f"BOT_{random.randint(1000, 9999)}"
                bot_jogador = {"socketId": bot_id, "usuarioId": nome_bot, "mao": [], "is_bot": True, "aposta": aposta, "is_real": False}
                fila.append(bot_jogador)

            await iniciar_partida_pronta(aposta)
    except Exception as e:
        print("💥 ERRO no matchmaking:", e)
        traceback.print_exc()

'''

    code = re.sub(r'async def check_matchmaking_timeout\(aposta\):.*?(?=\nasync def |\ndef )', new_code, code, flags=re.DOTALL)
    
    with open('socket_handler.py', 'w', encoding='utf-8') as f:
        f.write(code)
        
    print("socket_handler.py patched")

    # Patch index.html
    with open('public/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # ensure io connects over same IP/domain
    html = html.replace('io("http://localhost:8000")', 'io()')
    
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
        
    print("public/index.html patched")

if __name__ == '__main__':
    fix()
