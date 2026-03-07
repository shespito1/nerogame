with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

ui_html = '''        </div>
    </div>

    <!-- BOT AUTO TOGGLE -->
    <div v-if="estado === 'JOGO'" style="position: absolute; top: 10px; right: 20px; background: rgba(0,0,0,0.8); padding: 8px 12px; border-radius: 8px; z-index: 9999; border: 1px solid #4a5568;">
        <label style="color: #63b3ed; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">
            <input type="checkbox" v-model="autoPlay" style="width: 18px; height: 18px; cursor: pointer;" />
            AUTO JOGAR
        </label>
    </div>'''

text = re.sub(r'    <!-- BOT AUTO TOGGLE -->.*?</div>', ui_html, text, flags=re.DOTALL)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
