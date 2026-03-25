import discord
import json
import os
import math
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

DATA_FILE = 'fichas.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_ficha(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            'hp_atual': 100,
            'hp_max': 100,
            'energia_atual': 100,
            'energia_max': 100,
            'sanidade_atual': 100,
            'sanidade_max': 100
        }
    return data[uid]

def gerar_barra(atual, maximo):
    if maximo <= 0:
        return '▁▁▁▁▁', 0
    pct = max(0, min(100, (atual / maximo) * 100))
    pct_arredondada = math.floor(pct / 10) * 10
    blocos_cheios = pct_arredondada // 20
    meio_bloco = (pct_arredondada % 20) // 10
    vazios = 5 - blocos_cheios - meio_bloco
    barra = '█' * blocos_cheios + ('▌' if meio_bloco else '') + '▁' * vazios
    return barra, pct_arredondada

def status_dor(hp_atual, hp_max):
    if hp_max <= 0:
        return '[Condição Estável]'
    hp_min = -(hp_max / 2)
    porcentagem = (hp_atual / hp_max) * 100
    if hp_atual <= hp_min:
        return '[⚠ SINAIS VITAIS EM COLAPSO]'
    elif hp_atual < 0:
        return '[Colapso Mental Iminente 🧠]'
    elif porcentagem < 30:
        return '[ALERTA CRÍTICO ⚠️: Danos Severos]'
    elif porcentagem < 50:
        return '[Alerta: Integridade Comprometida]'
    elif porcentagem < 70:
        return '[Dor Leve]'
    else:
        return '[Condição Estável]'

def is_admin(member):
    return member.guild_permissions.administrator

def parse_valor(parts, index):
    try:
        return int(parts[index]), None
    except (IndexError, ValueError):
        return None, 'Valor inválido ou ausente.'

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if not message.content.startswith('&'):
        return

    data = load_data()
    parts = message.content.strip().split()
    cmd = parts[0].lower()

    # ─── COMANDOS DE JOGADOR ───────────────────────────────────────────────────

    if cmd == '&ficha':
        ficha = get_ficha(data, message.author.id)
        save_data(data)
        nome = message.author.display_name

        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        en_barra, en_pct = gerar_barra(ficha['energia_atual'], ficha['energia_max'])
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        dor = status_dor(ficha['hp_atual'], ficha['hp_max'])

        resposta = (
            f"🧾 **Ficha de Operador: {nome}**\n\n"
            f"❤️ **HP:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%\n"
            f"{dor}\n\n"
            f"⚡ **Energia Espiritual:** {ficha['energia_atual']}/{ficha['energia_max']}\n"
            f"⟦{en_barra}⟧ • {en_pct}%\n\n"
            f"🧠 **Sanidade:** {ficha['sanidade_atual']}/{ficha['sanidade_max']}\n"
            f"⟦{san_barra}⟧ • {san_pct}%"
        )
        await message.channel.send(resposta)

    elif cmd == '&hpdescontar':
        valor, erro = parse_valor(parts, 1)
        if erro:
            await message.channel.send(f'❌ {erro}\nUso: `&hpdescontar <valor>`')
            return
        ficha = get_ficha(data, message.author.id)
        hp_min = -(ficha['hp_max'] / 2)
        ficha['hp_atual'] = max(hp_min, ficha['hp_atual'] - valor)
        save_data(data)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        dor = status_dor(ficha['hp_atual'], ficha['hp_max'])
        await message.channel.send(
            f"❤️ **HP:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%\n"
            f"{dor}"
        )

    elif cmd == '&energiausar':
        valor, erro = parse_valor(parts, 1)
        if erro:
            await message.channel.send(f'❌ {erro}\nUso: `&energiausar <valor>`')
            return
        ficha = get_ficha(data, message.author.id)
        ficha['energia_atual'] = max(0, ficha['energia_atual'] - valor)
        save_data(data)
        en_barra, en_pct = gerar_barra(ficha['energia_atual'], ficha['energia_max'])
        await message.channel.send(
            f"⚡ **Energia Espiritual:** {ficha['energia_atual']}/{ficha['energia_max']}\n"
            f"⟦{en_barra}⟧ • {en_pct}%"
        )

    elif cmd == '&sanidadeperder':
        valor, erro = parse_valor(parts, 1)
        if erro:
            await message.channel.send(f'❌ {erro}\nUso: `&sanidadeperder <valor>`')
            return
        ficha = get_ficha(data, message.author.id)
        ficha['sanidade_atual'] = max(0, ficha['sanidade_atual'] - valor)
        save_data(data)
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        await message.channel.send(
            f"🧠 **Sanidade:** {ficha['sanidade_atual']}/{ficha['sanidade_max']}\n"
            f"⟦{san_barra}⟧ • {san_pct}%"
        )

    elif cmd == '&fichaajuda':
        ajuda = (
            "📖 **Comandos disponíveis para jogadores**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🧾 **`&ficha`**\n"
            "Exibe sua ficha completa com HP, Energia e Sanidade.\n"
            "→ Exemplo: `&ficha`\n\n"
            "❤️ **`&hpdescontar <valor>`**\n"
            "Desconta HP do seu personagem. Não pode passar do limite mínimo.\n"
            "→ Exemplo: `&hpdescontar 20`\n\n"
            "⚡ **`&energiausar <valor>`**\n"
            "Gasta energia espiritual do seu personagem.\n"
            "→ Exemplo: `&energiausar 15`\n\n"
            "🧠 **`&sanidadeperder <valor>`**\n"
            "Reduz a sanidade do seu personagem.\n"
            "→ Exemplo: `&sanidadeperder 10`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Jogadores **não podem se curar sozinhos**. Apenas admins recuperam recursos."
        )
        await message.channel.send(ajuda)

    elif cmd == '&ajudaadm':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        ajuda_adm = (
            "🛡️ **Comandos de Administrador**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❤️ **`&sethpmax @usuario <valor>`**\n"
            "Define o HP máximo de um jogador.\n"
            "→ Exemplo: `&sethpmax @Jogador 150`\n\n"
            "❤️ **`&hpadd @usuario <valor>`**\n"
            "Cura HP de um jogador (não ultrapassa o máximo).\n"
            "→ Exemplo: `&hpadd @Jogador 30`\n\n"
            "❤️ **`&removehpmax @usuario <valor>`**\n"
            "Reduz o HP máximo de um jogador permanentemente.\n"
            "→ Exemplo: `&removehpmax @Jogador 20`\n\n"
            "❤️ **`&sethp @usuario <valor>`**\n"
            "Define o HP atual de um jogador diretamente (debug).\n"
            "→ Exemplo: `&sethp @Jogador 50`\n\n"
            "⚡ **`&setenergiamax @usuario <valor>`**\n"
            "Define a energia máxima de um jogador.\n"
            "→ Exemplo: `&setenergiamax @Jogador 120`\n\n"
            "⚡ **`&energiaadd @usuario <valor>`**\n"
            "Recupera energia de um jogador (não ultrapassa o máximo).\n"
            "→ Exemplo: `&energiaadd @Jogador 40`\n\n"
            "🧠 **`&setsanidademax @usuario <valor>`**\n"
            "Define a sanidade máxima de um jogador.\n"
            "→ Exemplo: `&setsanidademax @Jogador 100`\n\n"
            "🧠 **`&sanidadeadd @usuario <valor>`**\n"
            "Recupera sanidade de um jogador (não ultrapassa o máximo).\n"
            "→ Exemplo: `&sanidadeadd @Jogador 25`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.channel.send(ajuda_adm)

    # ─── COMANDOS DE ADMIN ─────────────────────────────────────────────────────

    elif cmd == '&sethpmax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&sethpmax @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['hp_max'] = valor
        ficha['hp_atual'] = min(ficha['hp_atual'], valor)
        save_data(data)
        await message.channel.send(f'✅ HP máximo de **{alvo.display_name}** definido para **{valor}**.')

    elif cmd == '&hpadd':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&hpadd @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['hp_atual'] = min(ficha['hp_max'], ficha['hp_atual'] + valor)
        save_data(data)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        await message.channel.send(
            f"✅ **HP de {alvo.display_name}:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%"
        )

    elif cmd == '&removehpmax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&removehpmax @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['hp_max'] = max(1, ficha['hp_max'] - valor)
        ficha['hp_atual'] = min(ficha['hp_atual'], ficha['hp_max'])
        save_data(data)
        await message.channel.send(f'✅ HP máximo de **{alvo.display_name}** reduzido para **{ficha["hp_max"]}**.')

    elif cmd == '&sethp':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&sethp @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        hp_min = -(ficha['hp_max'] / 2)
        ficha['hp_atual'] = max(hp_min, min(ficha['hp_max'], valor))
        save_data(data)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        dor = status_dor(ficha['hp_atual'], ficha['hp_max'])
        await message.channel.send(
            f"✅ **HP de {alvo.display_name}:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%\n"
            f"{dor}"
        )

    elif cmd == '&setenergiamax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&setenergiamax @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['energia_max'] = valor
        ficha['energia_atual'] = min(ficha['energia_atual'], valor)
        save_data(data)
        await message.channel.send(f'✅ Energia máxima de **{alvo.display_name}** definida para **{valor}**.')

    elif cmd == '&energiaadd':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&energiaadd @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['energia_atual'] = min(ficha['energia_max'], ficha['energia_atual'] + valor)
        save_data(data)
        en_barra, en_pct = gerar_barra(ficha['energia_atual'], ficha['energia_max'])
        await message.channel.send(
            f"✅ **Energia de {alvo.display_name}:** {ficha['energia_atual']}/{ficha['energia_max']}\n"
            f"⟦{en_barra}⟧ • {en_pct}%"
        )

    elif cmd == '&setsanidademax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&setsanidademax @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['sanidade_max'] = valor
        ficha['sanidade_atual'] = min(ficha['sanidade_atual'], valor)
        save_data(data)
        await message.channel.send(f'✅ Sanidade máxima de **{alvo.display_name}** definida para **{valor}**.')

    elif cmd == '&sanidadeadd':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.mentions:
            await message.channel.send('Uso: `&sanidadeadd @usuario <valor>`')
            return
        valor, erro = parse_valor(parts, -1)
        if erro:
            await message.channel.send(f'❌ {erro}')
            return
        alvo = message.mentions[0]
        ficha = get_ficha(data, alvo.id)
        ficha['sanidade_atual'] = min(ficha['sanidade_max'], ficha['sanidade_atual'] + valor)
        save_data(data)
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        await message.channel.send(
            f"✅ **Sanidade de {alvo.display_name}:** {ficha['sanidade_atual']}/{ficha['sanidade_max']}\n"
            f"⟦{san_barra}⟧ • {san_pct}%"
        )

token = os.getenv('DISCORD_TOKEN')
if not token:
    print('Error: DISCORD_TOKEN environment variable not set.')
else:
    client.run(token)
