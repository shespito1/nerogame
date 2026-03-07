# -*- coding: utf-8 -*-
with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Add to CSS:
css = '''    <style>
        @keyframes recebeCartas {
            0% { transform: scale(1); box-shadow: 0 0 0px rgba(255, 255, 0, 0); }
            50% { transform: scale(1.3); box-shadow: 0 0 20px rgba(255, 255, 0, 0.8); background-color: rgba(255, 255, 0, 0.3); }
            100% { transform: scale(1); box-shadow: 0 0 0px rgba(255, 255, 0, 0); }
        }
        .animar-recebe-cartas {
            animation: recebeCartas 1s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }'''
text = re.sub(r'    <style>', css, text)

new_watch = '''    watch: {
        oponentes: {
            handler(newVal, oldVal) {
                if(!oldVal) return;
                newVal.forEach(newOp => {
                    const oldOp = oldVal.find(o => o.id === newOp.id);
                    if(oldOp && newOp.cartas > oldOp.cartas) {
                        const diff = newOp.cartas - oldOp.cartas;
                        // Encontra o elemento no DOM
                        this.(() => {
                            const el = document.getElementById('oponente-' + newOp.id);
                            if(el) {
                                // Mostra tooltip e pisca
                                const flot = document.createElement('div');
                                flot.innerText = "+" + diff + " 🃏";
                                flot.style.position = "absolute";
                                flot.style.color = "#ffeb3b";
                                flot.style.fontWeight = "bold";
                                flot.style.fontSize = "22px";
                                flot.style.top = "-25px";
                                flot.style.right = "-15px";
                                flot.style.textShadow = "2px 2px 4px #000";
                                flot.style.zIndex = "9999";
                                flot.style.transition = "all 1s ease-out";
                                el.appendChild(flot);
                                
                                el.classList.remove('animar-recebe-cartas');
                                void el.offsetWidth; // trigger reflow
                                el.classList.add('animar-recebe-cartas');
                                
                                setTimeout(() => {
                                    flot.style.top = "-60px";
                                    flot.style.opacity = "0";
                                }, 50);
                                setTimeout(() => {
                                    if(el.contains(flot)) el.removeChild(flot);
                                }, 1000);
                            }
                        });
                    }
                });
            },
            deep: true
        },
        turnoAtual(newVal) {'''
text = re.sub(r'    watch: \{\s*turnoAtual\(newVal\) \{', new_watch, text)

# Add IDs to opponents 
text = text.replace('class="oponente" :class="{ \'oponente-ativo\': op.id === turnoAtual }"', ':id="\'oponente-\' + op.id" class="oponente" :class="{ \'oponente-ativo\': op.id === turnoAtual }"')

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Frontend OK")
