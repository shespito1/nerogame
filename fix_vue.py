import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

bad_vue_button = r'<button v-for="\(valor, index\) in opcoesAposta" :key="valor".*?</button>'

clean_buttons = """
            <button v-for="(valor, index) in opcoesAposta" :key="valor"
                style="margin: 0; font-size: 24px; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.3); border-radius: 8px;"
                :style="{ background: ['linear-gradient(135deg, #f56565, #c53030)', 'linear-gradient(135deg, #4299e1, #2b6cb0)', 'linear-gradient(135deg, #48bb78, #2f855a)'][index % 3] }"
                @click="pagarEEntrarNaFila(valor)">
                R$ {{ valor.toFixed(2).replace('.', ',') }}
            </button>
"""

text = re.sub(bad_vue_button, clean_buttons, text, flags=re.DOTALL)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Vue syntax fixed.")