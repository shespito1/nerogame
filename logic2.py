with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

text = re.sub(r'cartaCuringaIndex:\s*null', 'cartaCuringaIndex: null,\n        autoPlay: false', text)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
