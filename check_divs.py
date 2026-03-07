with open('public/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

div_count = 0
for i, line in enumerate(lines):
    div_count += line.count('<div')
    div_count += line.count('< div')
    div_count -= line.count('</div')
    if div_count < 0:
        print(f"Negative div count at line {i+1}: {line.strip()}")
        # don't break, maybe it gets balanced later?
print("Final count:", div_count)
