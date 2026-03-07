import re

def fix():
    with open('socket_handler.py', 'r', encoding='utf-8') as f:
        code = f.read()

    new_prefix = '''        prefixos = ["Alex", "Dani", "Gabi", "Mari", "Luiz", "Feli", "Brun", "Carl", "Vito", "Pedr", "Rafa", "Thia", "Guil", "Fern", "Leti", "Cami", "Juli", "Arth", "Bern", "Mich", "Davi", "Heit", "Math", "Luca", "Nico", "Enzo", "Yuri", "Kaua", "Igor", "Caio", "Kevi", "Will", "Ruan", "Vini", "Levi", "Theo", "Gael", "Migu", "Roge", "Dieg", "Andr", "Bata", "Silv", "Sant", "Melo", "Cost", "Lima", "Mora", "Gome", "Pere", "Ribe", "Mart", "Carv", "Alme", "Lope", "Soar", "Viei", "Mont", "Rodr", "Cunh", "Mede", "Nune", "Roch", "Frei", "Corr", "Mour", "Nasc", "Amar", "Card", "Teix", "Mach", "Tava", "Pint", "Agui", "Xavi", "Ramo", "Fari", "Borg", "Pinh", "Dias", "Brit", "Neve", "Maci", "Mati", "Vare", "Leal", "Vale", "Bast", "Texe", "Camp", "Mell", "Blan", "Garc", "Duar", "Figu", "Font", "Pess", "Fons", "Sale", "Band"]
            nomes_inteiros = ['Miguel', 'Arthur', 'Gael', 'Theo', 'Heitor', 'Ravi', 'Davi', 'Bernardo', 'Noah', 'Gabriel', 'Samuel', 'Pedro', 'Antonio', 'Joao', 'Isaac', 'Helena', 'Alice', 'Laura', 'Maria', 'Sophia', 'Manuela', 'Maite', 'Liz', 'Cecilia', 'Isabella', 'Luisa', 'Valentina', 'Heloisa', 'Julia', 'Livia', 'Lorena', 'Elisa', 'Giovanna', 'Matheus', 'Lucas', 'Nicolas', 'Joaquim', 'Henrique', 'Lorenzo', 'Benjamin', 'Thiago', 'Victor', 'Leonardo', 'Eduardo', 'Daniel', 'Vinicius', 'Francisco', 'Diego', 'Felipe', 'Carlos', 'Andre', 'Renato', 'Rodrigo', 'Fernando', 'Ricardo', 'Marcelo', 'Bruno', 'Caique', 'Igor', 'Breno', 'Alexandre', 'Caio', 'Douglas', 'Marcos', 'Rui', 'Hugo', 'Gustavo', 'Guilherme', 'Rafael', 'Otavio', 'Paulo', 'Jose', 'Julio', 'Roberto', 'Amanda', 'Beatriz', 'Bruna', 'Camila', 'Carolina', 'Leticia', 'Natalia', 'Larissa', 'Thais', 'Aline', 'Milena', 'Mariana', 'Fernanda', 'Vanessa', 'Gabriela', 'Juliana', 'Renata', 'Jessica', 'Vitoria', 'Patricia', 'Priscila', 'Tatiana', 'Daniela', 'Monica', 'Erica', 'Sabrina', 'Alessandra', 'Raquel', 'Mirella', 'Viviane', 'darkaco', 'detonatromba', 'matador_noob', 'ze_da_manga', 'sarrada_br', 'xX_matador_Xx', 'bala_tensa', 'pai_ta_on', 'mae_ta_on', 'goku_careca', 'careca_tv', 'tiringa', 'zeca_urubu', 'calvo_aos_20', 'jogador_caro', 'amassa_nozes', 'chupa_cabra', 'corta_giro', 'grau_e_corte', 'mandrake', 'cria_de_favela', 'noob_master', 'ping_999', 'so_capa', 'rei_do_gado', 'cachorro_louco', 'pao_de_batata', 'bolacha_br', 'toca_do_tatu', 'lobo_solitario', 'gato_net', 'robozao', 'deusa_gamer', 'imperador', 'cavaleiro_br', 'ninja_suave', 'assassino_br', 'bruxo_br', 'lenda_viva', 'mito_ofc', 'coringa_louco', 'peppa_pig', 'shaolin_matador', 'cabeca_de_gelo', 'bota_fogo', 'tio_patinhas', 'nego_ney', 'vidaloka', 'perna_longa', 'tropa_do_buxa', 'pro_player', 'ze_droguinha', 'mestre_yoda', 'anao_bombado']

            for _ in range(falta):
                tipo = random.random()
                if tipo < 0.33:
                    nome_bot = f"{random.choice(nomes_inteiros)}"
                elif tipo < 0.66:
                    nome_bot = f"{random.choice(prefixos)}"
                else:
                    numero = str(random.randint(0, 99)).zfill(2)
                    nome_bot = f"{random.choice(prefixos)}{numero}"

                bot_id = f"BOT_{random.randint(1000, 9999)}"
                bot_jogador = {"socketId": bot_id, "usuarioId": nome_bot, "mao": [], "is_bot": True, "aposta": aposta, "is_real": False}
                fila.append(bot_jogador)

            await iniciar_partida_pronta(aposta)'''

    code = re.sub(r'prefixos = \["Alex", "Dani", "Gabi", "Mari"\].*?await iniciar_partida_pronta\(aposta\)', new_prefix, code, flags=re.DOTALL)

    with open('socket_handler.py', 'w', encoding='utf-8') as f:
        f.write(code)

if __name__ == '__main__':
    fix()
