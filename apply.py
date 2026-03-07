with open('public/index.html', 'r', encoding='utf-8') as f:
    data = f.read()

import re
old = r"if (val === 'Inverter') return '\u21C6';"
new = r"if (val === 'Inverter') return '\u21C6';\n            if (val === 'Curinga') return '\u22C6';"
data = data.replace(old, new)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(data)
print("Updated via file")
