with open('public/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The extra lines are approximately from index 251 to 260
# Let's inspect them to be sure
start = 0
end = 0
for i, line in enumerate(lines):
    if '<h3 style="margin: 0; color: #fbd38d; font-family: \'Rowdies\', cursive; font-size: 38px' in line:
        if i > 200:
            start = i
            break

if start > 0:
    for i in range(start, start + 30):
        if '</div>' in lines[i] and '</div>' in lines[i-1] and '</div>' in lines[i-2]:
            end = i
            break

if start > 0 and end > 0:
    print(f"Removing lines from {start} to {end}")
    del lines[start:end+1]
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Done")
else:
    print("Could not find the block to remove")
