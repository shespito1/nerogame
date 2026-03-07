import json

settings_path = r'C:\Users\wesle\AppData\Roaming\Code\User\settings.json'

with open(settings_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

if 'chat.tools.terminal.autoApprove' in data:
    for key in data['chat.tools.terminal.autoApprove']:
        data['chat.tools.terminal.autoApprove'][key] = True

with open(settings_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)
