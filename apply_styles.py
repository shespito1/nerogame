import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_styles = '''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&family=Rowdies:wght@400;700&display=swap');

        body { 
            font-family: 'Baloo 2', display, sans-serif; 
            background: radial-gradient(circle at center, #1b533a 0%, #0d2e1c 100%); 
            color: white; 
            margin: 0; 
            padding: 0; 
            min-height: 100vh;
        }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }

        h1 { 
            text-align: center; color: #f1c40f; font-family: 'Rowdies', cursive; 
            text-shadow: 2px 2px 0 #000; margin-bottom: 20px;
        }

        .stats { 
            display: flex; justify-content: space-around; font-size: 20px; font-weight: bold; 
            color: #63b3ed; margin-bottom: 20px; text-transform: uppercase;
            background: rgba(0,0,0,0.35); padding: 15px 25px; border-radius: 12px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.05);
        }

        .log { 
            background: rgba(0,0,0,0.5); padding: 15px; height: 120px; overflow-y: scroll; 
            border-radius: 8px; font-family: 'Consolas', monospace; font-size: 13px; color: #4ade80; 
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        }
        
        .card { 
            background: rgba(20, 30, 25, 0.6); padding: 30px; border-radius: 16px; 
            text-align: center; margin-bottom: 20px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05);
            backdrop-filter: blur(8px);
        }

        button { 
            background: linear-gradient(135deg, #f6d365 0%, #ffb347 100%); 
            color: #744210; border: none; padding: 15px 35px; font-size: 20px; border-radius: 50px; 
            cursor: pointer; font-weight: 800; font-family: 'Baloo 2', cursive;
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-transform: uppercase; margin-top: 15px;
        }
        button:hover { transform: scale(1.05) translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        button:disabled { filter: grayscale(1); cursor: not-allowed; transform: none; }

        /* MESA E OPONENTES */
        .mesa-container { display: flex; justify-content: space-evenly; align-items: center; margin: 20px 0; gap: 40px; }
        
        .oponentes { display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; }
        .oponente { 
            display: inline-flex; flex-direction: column; align-items: center; justify-content: center;
            min-width: 90px; padding: 12px; background: rgba(0,0,0,0.5); margin: 5px; 
            border-radius: 12px; font-size: 14px; border: 2px solid transparent; transition: 0.3s;
            position: relative;
        }
        .oponente span { color: white !important; }
        .oponente-nome { font-weight: bold; margin-bottom: 5px; color: #e2e8f0; }
        .oponente-cartas { 
            background: #4a5568; color: white; padding: 4px 10px; 
            border-radius: 20px; font-size: 16px; font-weight: bold;
            border: 1px solid rgba(255,255,255,0.2); 
            margin-top: 5px;
        }
        .oponente-ativo { 
            border: 2px solid #fbd38d; box-shadow: 0 0 20px rgba(251, 211, 141, 0.4); 
            background: rgba(251, 211, 141, 0.15); transform: translateY(-5px);
        }

        .mesa { background: rgba(0,0,0,0.3); padding: 20px; border-radius: 8px; text-align: center; }

        .mao-container { margin-top: 20px; text-align: center; padding: 15px; border-radius: 12px;}
        .meu-turno { border: 2px dashed #48bb78; background: rgba(72, 187, 120, 0.1); }
        .mao { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 10px; }

        /* CARTAS DE UNO */
        .carta { 
            position: relative; display: inline-flex; justify-content: center; align-items: center; 
            width: 75px; height: 115px; border-radius: 8px; margin: 8px; 
            font-size: 34px; font-weight: 700; font-family: 'Rowdies', cursive;
            color: white; cursor: pointer; user-select: none; 
            border: 4px solid white; text-align: center; 
            text-shadow: 2px 2px 0px rgba(0,0,0,0.5); 
            box-shadow: 2px 5px 12px rgba(0,0,0,0.4), inset 0 0 0 3px rgba(0,0,0,0.1); 
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            background-color: #333; overflow: hidden;
            line-height: normal;
        }
        .carta::before {
            content: ''; position: absolute; top: -10%; left: -10%; right: -10%; bottom: -10%;
            background: rgba(255,255,255,0.15); border-radius: 50%;
            transform: rotate(-25deg) scale(0.85); z-index: 0; pointer-events: none;
        }
        .carta span { position: relative; z-index: 1; pointer-events: none; }
        
        .carta:hover { 
            transform: translateY(-15px) scale(1.1) rotate(-2deg); 
            z-index: 20; box-shadow: 5px 15px 25px rgba(0,0,0,0.5); 
        }

        .carta-mesa { transform: scale(1.4); pointer-events: none; box-shadow: 0 10px 30px rgba(0,0,0,0.6); margin: 30px; }
        
        /* Cores reais do UNO */
        .Vermelho { background: linear-gradient(135deg, #f56462 0%, #d82b28 100%); }
        .Azul { background: linear-gradient(135deg, #0099ff 0%, #0056cc 100%); }
        .Verde { background: linear-gradient(135deg, #2ecc71 0%, #158b44 100%); }
        .Amarelo { background: linear-gradient(135deg, #ffda33 0%, #e0a300 100%); color: white; }
        .Amarelo span { text-shadow: 2px 2px 0px rgba(0,0,0,0.3); }
        .Curinga { background: conic-gradient(from 45deg, #f56462 0% 25%, #0099ff 25% 50%, #2ecc71 50% 75%, #ffda33 75% 100%); }
        .Curinga::before { background: rgba(0,0,0,0.3); }

        /* Animações */
        @keyframes drawCard { 
            0% { opacity: 0; transform: translateY(50px) scale(0.5) rotate(10deg); } 
            100% { opacity: 1; transform: translateY(0) scale(1) rotate(0deg); } 
        }
        .carta-animada { animation: drawCard 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
    </style>
'''

# Replace old style
html = re.sub(r'<style>.*?</style>', new_styles, html, flags=re.DOTALL)

# Wrap card values in span for z-index
html = html.replace('{{ carta.valor }}', '<span>{{ carta.valor }}</span>')
html = html.replace('{{ cartaMesa.valor }}', '<span>{{ cartaMesa.valor }}</span>')
html = html.replace('class="carta"', 'class="carta carta-animada"')

# Fix opponents html correctly
old_opponents = """                <div v-for="op in getOponentes()" :key="op.id" class="oponente" :class="{ 'oponente-ativo': op.id === turnoAtual }">
                    <span>{{ op.id }}</span><br>
                    🎴 {{ op.cartas }} cartas
                    <span v-if="op.id === turnoAtual" style="position:absolute; right: -25px; font-size: 20px;">👈</span>
                </div>"""

new_opponents = """                <div v-for="op in getOponentes()" :key="op.id" class="oponente" :class="{ 'oponente-ativo': op.id === turnoAtual }">
                    <span class="oponente-nome">🤖 {{ op.id }}</span>
                    <span class="oponente-cartas">🃏 {{ op.cartas }} cartas</span>
                </div>"""

html = html.replace(old_opponents, new_opponents)

# Fix mesa html to not use inner BR and extra span for color, just use the card look
old_mesa = """                <div v-if="cartaMesa" class="carta-mesa" :class="cartaMesa.cor">
                    <span>{{ cartaMesa.valor }}</span><br>
                    <span style="font-size: 12px; font-weight: normal;">{{ cartaMesa.cor }}</span>
                </div>"""

new_mesa = """                <div v-if="cartaMesa" class="carta carta-mesa" :class="cartaMesa.cor">
                    <span>{{ cartaMesa.valor }}</span>
                </div>"""

html = html.replace(old_mesa, new_mesa)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
