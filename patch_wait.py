import re

with open('socket_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = '''async def check_matchmaking_timeout(aposta):
    import time
    import random
    import asyncio
    
    # Aguarda o limite pro bot entrar (10 seg)
    await asyncio.sleep(10)
    
    fila = filas_espera.get(aposta, [])
    if 0 < len(fila) < 4:
        print(f"? Tempo limite da fila R$ {aposta:.2f} atingido. Adicionando {4 - len(fila)} BOTS...")
        falta = 4 - len(fila)
        nomes_reais_bots = ["Miguel", "Arthur", "Gael", "Theo", "Heitor", "Ravi", "Davi", "Bernardo", "Noah", "Gabriel", "Samuel", "Pedro", "Antonio", "Joao", "Isaac", "Helena", "Alice", "Laura", "Maria", "Sophia", "Manuela", "Maite", "Liz", "Cecilia", "Isabella", "Luisa", "Valentina"]
        for _ in range(falta):
            nome_bot = random.choice(nomes_reais_bots)
            bot_id = f"BOT_{random.randint(1000, 9999)}"
            bot_jogador = {"socketId": bot_id, "usuarioId": nome_bot, "mao": [], "is_bot": True, "aposta": aposta}
            fila.append(bot_jogador)
            
        await iniciar_partida_pronta(aposta)'''

text = re.sub(r'async def check_matchmaking_timeout\(aposta\):.*?await iniciar_partida_pronta\(aposta\)', replacement, text, flags=re.DOTALL)

with open('socket_handler.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("PATCHED WAIT")
