import sys

script = '''
import re

with open("socket_handler.py", "r", encoding="utf-8") as f:
    text = f.read()

with open("novo.py", "r", encoding="utf-8") as f:
    novo = f.read()

text = re.sub(r'fila_espera = \[\].*?(?=async def processar_jogada)', novo, text, flags=re.DOTALL)

with open("socket_handler.py", "w", encoding="utf-8") as f:
    f.write(text)

print("foi")
'''
with open("patch.py", "w", encoding="utf-8") as f:
    f.write(script)
