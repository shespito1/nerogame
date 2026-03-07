import sys, json

settings_path = r'C:\Users\wesle\AppData\Roaming\Code\User\settings.json'

with open(settings_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Trocar todos os alse dentro de chat.tools.terminal.autoApprove por 	rue
import re

def replacer(match):
    return match.group(0).replace('false', 'true')

text = re.sub(r'"chat\.tools\.terminal\.autoApprove":\s*\{[^\}]+\}', replacer, text, flags=re.DOTALL)

with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(text)
