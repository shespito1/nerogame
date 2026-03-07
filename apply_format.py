import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    data = f.read()

data = re.sub(r'\{\{\s*cartaMesa\.valor\s*\}\}', '{{ formatValor(cartaMesa.valor) }}', data)
data = re.sub(r'\{\{\s*carta\.valor\s*\}\}', '{{ formatValor(carta.valor) }}', data)
data = data.replace(':data-valor=\"cartaMesa.valor\"', ':data-valor=\"formatValor(cartaMesa.valor)\"')
data = data.replace(':data-valor=\"carta.valor\"', ':data-valor=\"formatValor(carta.valor)\"')

method_str = '''methods: {
        formatValor(val) {
            if (val === "Pular") return "Ø";
            if (val === "Inverter") return "??";
            return val;
        },'''

if 'formatValor(' not in data:
    data = data.replace('methods: {', method_str)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(data)
print('Done!')
