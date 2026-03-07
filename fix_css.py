import os
with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(':class="cartaMesa.cor"', ':class="[cartaMesa.cor, cartaMesa.cor_escolhida ? \'Cor-\'+cartaMesa.cor_escolhida : \'\']"')
text = text.replace(':class="carta.cor"', ':class="[carta.cor, carta.cor_escolhida ? \'Cor-\'+carta.cor_escolhida : \'\']"')

new_css = '''/* CORES REALISTAS */
        .Cor-Vermelho { background: linear-gradient(135deg, #ff5555 0%, #cc0000 100%) !important; color: white !important; }
        .Cor-Azul { background: linear-gradient(135deg, #5555ff 0%, #0000cc 100%) !important; color: white !important; }
        .Cor-Verde { background: linear-gradient(135deg, #55ff55 0%, #00aa00 100%) !important; color: white !important; }
        .Cor-Amarelo { background: linear-gradient(135deg, #ffff55 0%, #d4aa00 100%) !important; color: white !important; }
        .Cor-Amarelo span, .Cor-Amarelo::after, .Cor-Amarelo .bottom-corner { text-shadow: 2px 2px 0px rgba(0,0,0,0.4) !important; }
'''
if 'Cor-Vermelho' not in text:
    text = text.replace('/* CORES REALISTAS */', new_css)
text = text.replace('<h3>🎨 Escolha a Cor Curinga!</h3>', '<h3>🎨</h3>')

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done frontend updates.')
