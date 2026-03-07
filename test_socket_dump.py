import re
text = open('public/index.html', 'r', encoding='utf-8').read()
match = re.search(r'this\.socket\.on\("jogadaAceita", \(data\) => {.*?\n                  }\);', text, re.DOTALL)
if match:
    print(match.group(0))
else:
    print('Not found')
