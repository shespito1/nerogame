import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the bad style block completely
text = re.sub(r'<style>\s*\.uno-menu-card.*?</style>', '', text, flags=re.DOTALL)

# Revert menu card to something simpler
text = re.sub(
    r'<div @click="estado = \'ESCOLHER_APOSTA\'" class="uno-menu-card">.*?</div>\s*</div>\s*</div>',
    """<div @click="estado = 'ESCOLHER_APOSTA'" style="background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%); padding: 30px 20px; border-radius: 12px; cursor: pointer; border: 4px solid white; width: 220px; transition: 0.3s; text-align: center; box-shadow: 0 8px 20px rgba(229, 62, 62, 0.4);" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1.0)'">
                <div style="font-size: 50px; margin-bottom: 5px; transform: rotate(-10deg); text-shadow: 2px 2px 0px rgba(0,0,0,0.5);">🃏</div>
                <h3 style="margin: 0; color: #fbd38d; font-family: 'Rowdies', cursive; font-size: 32px; letter-spacing: 2px; text-shadow: 2px 2px 0px rgba(0,0,0,0.5);">UNO</h3>
                <h4 style="margin: 0; color: white; font-family: 'Baloo 2', cursive; font-weight: 800; font-size: 18px;">ROYALE</h4>
                <p style="color: #fed7d7; font-size: 14px; margin-top: 15px; background: rgba(0,0,0,0.2); padding: 5px; border-radius: 8px;">Aposte as fichas e vença!</p>
            </div>
        </div>
    </div>""",
    text,
    flags=re.DOTALL
)


# Revert botões to simpler UNO colored buttons without missing gap
text = re.sub(
    r'<button v-for="\(valor, index\) in opcoesAposta".*?</button>',
    """<button v-for="(valor, index) in opcoesAposta" :key="valor"
                :style="'margin: 0; font-size: 24px; font-family: \\\'Rowdies\\\', cursive; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.3); background: ' + (['linear-gradient(135deg, #f56565, #c53030)', 'linear-gradient(135deg, #4299e1, #2b6cb0)', 'linear-gradient(135deg, #48bb78, #2f855a)'][index % 3])"
                @click="pagarEEntrarNaFila(valor)">
                R$ {{ valor.toFixed(2).replace('.', ',') }}
            </button>""",
    text,
    flags=re.DOTALL
)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Reverted to safe inline styles.")