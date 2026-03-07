# -*- coding: utf-8 -*-
with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

ui_html = '''        </div>
    </div>

    <!-- BOT AUTO TOGGLE -->
    <div v-if="estado === 'JOGO'" style="position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.8); padding: 8px 12px; border-radius: 8px; z-index: 9999; border: 1px solid #4a5568;">
        <label style="color: #63b3ed; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">
            <input type="checkbox" v-model="autoPlay" style="width: 18px; height: 18px; cursor: pointer;" />
            🤖 BOT AUTO
        </label>
    </div>'''

if 'BOT AUTO' not in text:
    text = text.replace('        </div>\n    </div>\n\n    <div v-if="escolhendoCor"', ui_html + '\n\n    <div v-if="escolhendoCor"')

if 'autoPlay: false' not in text:
    text = text.replace('cartaCuringaIndex: null\n      },', 'cartaCuringaIndex: null,\n        autoPlay: false\n      },')
    text = text.replace('cartaCuringaIndex: null\n    },', 'cartaCuringaIndex: null,\n        autoPlay: false\n    },')

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
