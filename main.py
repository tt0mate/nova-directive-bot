import discord
import json
import os
import math
import asyncio
import asyncpg
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
db_pool = None

FICHA_PADRAO = {
    'hp_atual': 100,
    'hp_max': 100,
    'energia_atual': 100,
    'energia_max': 100,
    'sanidade_atual': 100,
    'sanidade_max': 100,
    'nome': None,
    'imagem': None,
    'cor': None
}

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
    await db_pool.execute('''
        CREATE TABLE IF NOT EXISTS fichas (
            user_id TEXT PRIMARY KEY,
            data JSONB NOT NULL
        )
    ''')

async def get_ficha(user_id):
    uid = str(user_id)
    row = await db_pool.fetchrow('SELECT data FROM fichas WHERE user_id = $1', uid)
    if row is None:
        ficha = dict(FICHA_PADRAO)
    else:
        ficha = dict(row['data'])
    for campo, valor in FICHA_PADRAO.items():
        if campo not in ficha:
            ficha[campo] = valor
    return ficha

async def save_ficha(user_id, ficha):
    uid = str(user_id)
    await db_pool.execute(
        '''
        INSERT INTO fichas (user_id, data) VALUES ($1, $2::jsonb)
        ON CONFLICT (user_id) DO UPDATE SET data = $2::jsonb
        ''',
        uid, json.dumps(ficha)
    )

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

def parse_cor(texto):
    texto = texto.strip().lstrip('#')
    try:
        return int(texto, 16), None
    except ValueError:
        return None, 'Cor inválida. Use formato hex, ex: `FF0000` ou `#FF0000`.'

async def resolver_alvo(message, parts, index=1):
    if message.mentions:
        m = message.mentions[0]
        return str(m.id), m.display_name, None
    if len(parts) > index:
        try:
            uid = int(parts[index])
            membro = message.guild.get_member(uid)
            nome = membro.display_name if membro else str(uid)
            return str(uid), nome, None
        except ValueError:
            pass
    return None, None, '❌ Informe um @usuario ou ID válido.'

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="✅ Sistema de Fichas Ativo"
        )
    )

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.content.startswith('&'):
        return

    parts = message.content.strip().split()
    cmd = parts[0].lower()

    # ─── COMANDOS DE JOGADOR ───────────────────────────────────────────────────

    if cmd == '&ficha':
        ficha = await get_ficha(message.author.id)

        nome = ficha.get('nome') or message.author.display_name
        imagem = ficha.get('imagem') or message.author.display_avatar.url

        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        en_barra, en_pct = gerar_barra(ficha['energia_atual'], ficha['energia_max'])
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        dor = status_dor(ficha['hp_atual'], ficha['hp_max'])

        if ficha.get('cor') is not None:
            cor = ficha['cor']
        else:
            hp_pct_real = (ficha['hp_atual'] / ficha['hp_max'] * 100) if ficha['hp_max'] > 0 else 0
            if ficha['hp_atual'] < 0:
                cor = 0x1a1a2e
            elif hp_pct_real < 30:
                cor = 0xe74c3c
            elif hp_pct_real < 50:
                cor = 0xe67e22
            elif hp_pct_real < 70:
                cor = 0xf1c40f
            else:
                cor = 0x2ecc71

        embed = discord.Embed(title=f"🧾 Ficha de Operador: {nome}", color=cor)
        embed.set_thumbnail(url=imagem)
        embed.add_field(
            name="❤️ HP",
            value=f"`{ficha['hp_atual']}/{ficha['hp_max']}`\n⟦{hp_barra}⟧ • {hp_pct}%\n{dor}",
            inline=False
        )
        embed.add_field(
            name="⚡ Energia Espiritual",
            value=f"`{ficha['energia_atual']}/{ficha['energia_max']}`\n⟦{en_barra}⟧ • {en_pct}%",
            inline=True
        )
        embed.add_field(
            name="🧠 Sanidade",
            value=f"`{ficha['sanidade_atual']}/{ficha['sanidade_max']}`\n⟦{san_barra}⟧ • {san_pct}%",
            inline=True
        )
        embed.set_footer(text="Sistema de Fichas • RPG")
        await message.channel.send(embed=embed)

    elif cmd == '&hpdescontar':
        valor, erro = parse_valor(parts, 1)
        if erro:
            await message.channel.send(f'❌ {erro}\nUso: `&hpdescontar <valor>`')
            return
        if valor <= 0:
            await message.channel.send('❌ O valor precisa ser positivo.')
            return
        ficha = await get_ficha(message.author.id)
        hp_min = -(ficha['hp_max'] / 2)
        ficha['hp_atual'] = max(hp_min, ficha['hp_atual'] - valor)
        await save_ficha(message.author.id, ficha)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        dor = status_dor(ficha['hp_atual'], ficha['hp_max'])
        await message.channel.send(
            f"❤️ **HP:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%\n{dor}"
        )

    elif cmd == '&energiausar':
        valor, erro = parse_valor(parts, 1)
        if erro:
            await message.channel.send(f'❌ {erro}\nUso: `&energiausar <valor>`')
            return
        if valor <= 0:
            await message.channel.send('❌ O valor precisa ser positivo.')
            return
        ficha = await get_ficha(message.author.id)
        ficha['energia_atual'] = max(0, ficha['energia_atual'] - valor)
        await save_ficha(message.author.id, ficha)
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
        if valor <= 0:
            await message.channel.send('❌ O valor precisa ser positivo.')
            return
        ficha = await get_ficha(message.author.id)
        ficha['sanidade_atual'] = max(0, ficha['sanidade_atual'] - valor)
        await save_ficha(message.author.id, ficha)
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        await message.channel.send(
            f"🧠 **Sanidade:** {ficha['sanidade_atual']}/{ficha['sanidade_max']}\n"
            f"⟦{san_barra}⟧ • {san_pct}%"
        )

    elif cmd == '&mudarcor':
        if len(parts) < 2:
            await message.channel.send('Uso: `&mudarcor #RRGGBB` (sua cor) ou `&mudarcor @usuario/ID #RRGGBB` (admin)')
            return

        if len(parts) == 2:
            uid = str(message.author.id)
            nome_alvo = message.author.display_name
            cor, erro_cor = parse_cor(parts[1])
        else:
            uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
            if erro:
                await message.channel.send(erro)
                return
            if uid != str(message.author.id) and not is_admin(message.author):
                await message.channel.send('❌ Você só pode mudar a cor da sua própria ficha.')
                return
            cor, erro_cor = parse_cor(parts[-1])

        if erro_cor:
            await message.channel.send(f'❌ {erro_cor}')
            return
        ficha = await get_ficha(uid)
        ficha['cor'] = cor
        await save_ficha(uid, ficha)
        embed_preview = discord.Embed(
            title=f"✅ Cor da ficha de **{nome_alvo}** atualizada!",
            color=cor
        )
        await message.channel.send(embed=embed_preview)

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
            "🎨 **`&mudarcor #RRGGBB`**\n"
            "Muda a cor do embed da sua própria ficha.\n"
            "→ Exemplo: `&mudarcor #FF0000`\n\n"
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
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Todos os comandos aceitam **@menção ou ID** do jogador.\n\n"
            "❤️ **`&sethpmax @usuario/ID <valor>`**\n"
            "Define o HP máximo de um jogador.\n"
            "→ Exemplo: `&sethpmax @Jogador 150`\n\n"
            "❤️ **`&hpadd @usuario/ID <valor>`**\n"
            "Cura HP de um jogador (não ultrapassa o máximo).\n"
            "→ Exemplo: `&hpadd @Jogador 30`\n\n"
            "❤️ **`&removehpmax @usuario/ID <valor>`**\n"
            "Reduz o HP máximo de um jogador permanentemente.\n"
            "→ Exemplo: `&removehpmax @Jogador 20`\n\n"
            "❤️ **`&sethp @usuario/ID <valor>`**\n"
            "Define o HP atual de um jogador diretamente.\n"
            "→ Exemplo: `&sethp @Jogador 50`\n\n"
            "⚡ **`&setenergiamax @usuario/ID <valor>`**\n"
            "Define a energia máxima de um jogador.\n"
            "→ Exemplo: `&setenergiamax @Jogador 120`\n\n"
            "⚡ **`&energiaadd @usuario/ID <valor>`**\n"
            "Recupera energia de um jogador.\n"
            "→ Exemplo: `&energiaadd @Jogador 40`\n\n"
            "🧠 **`&setsanidademax @usuario/ID <valor>`**\n"
            "Define a sanidade máxima de um jogador.\n"
            "→ Exemplo: `&setsanidademax @Jogador 100`\n\n"
            "🧠 **`&sanidadeadd @usuario/ID <valor>`**\n"
            "Recupera sanidade de um jogador.\n"
            "→ Exemplo: `&sanidadeadd @Jogador 25`\n\n"
            "🖼️ **`&mudarimagem @usuario/ID`** *(anexe uma imagem)*\n"
            "Muda a imagem da ficha de um jogador.\n"
            "→ Exemplo: `&mudarimagem @Jogador` + anexar imagem\n\n"
            "✏️ **`&mudarnome @usuario/ID novo nome`**\n"
            "Muda o nome exibido na ficha de um jogador.\n"
            "→ Exemplo: `&mudarnome @Jogador Kira Yamato`\n\n"
            "🎨 **`&mudarcor @usuario/ID #RRGGBB`**\n"
            "Muda a cor da ficha de qualquer jogador.\n"
            "→ Exemplo: `&mudarcor @Jogador #00FF00`\n\n"
            "✨ **`&heall @usuario/ID`**\n"
            "Cura HP, Energia e Sanidade de um jogador ao máximo.\n"
            "→ Exemplo: `&heall @Jogador`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.channel.send(ajuda_adm)

    # ─── COMANDOS DE ADMIN ─────────────────────────────────────────────────────

    elif cmd == '&sethpmax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['hp_max'] = valor
        ficha['hp_atual'] = min(ficha['hp_atual'], valor)
        await save_ficha(uid, ficha)
        await message.channel.send(f'✅ HP máximo de **{nome_alvo}** definido para **{valor}**.')

    elif cmd == '&hpadd':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['hp_atual'] = min(ficha['hp_max'], ficha['hp_atual'] + valor)
        await save_ficha(uid, ficha)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        await message.channel.send(
            f"✅ **HP de {nome_alvo}:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%"
        )

    elif cmd == '&removehpmax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['hp_max'] = max(1, ficha['hp_max'] - valor)
        ficha['hp_atual'] = min(ficha['hp_atual'], ficha['hp_max'])
        await save_ficha(uid, ficha)
        await message.channel.send(f'✅ HP máximo de **{nome_alvo}** reduzido para **{ficha["hp_max"]}**.')

    elif cmd == '&sethp':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        hp_min = -(ficha['hp_max'] / 2)
        ficha['hp_atual'] = max(hp_min, min(ficha['hp_max'], valor))
        await save_ficha(uid, ficha)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        dor = status_dor(ficha['hp_atual'], ficha['hp_max'])
        await message.channel.send(
            f"✅ **HP de {nome_alvo}:** {ficha['hp_atual']}/{ficha['hp_max']}\n"
            f"⟦{hp_barra}⟧ • {hp_pct}%\n{dor}"
        )

    elif cmd == '&setenergiamax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['energia_max'] = valor
        ficha['energia_atual'] = min(ficha['energia_atual'], valor)
        await save_ficha(uid, ficha)
        await message.channel.send(f'✅ Energia máxima de **{nome_alvo}** definida para **{valor}**.')

    elif cmd == '&energiaadd':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['energia_atual'] = min(ficha['energia_max'], ficha['energia_atual'] + valor)
        await save_ficha(uid, ficha)
        en_barra, en_pct = gerar_barra(ficha['energia_atual'], ficha['energia_max'])
        await message.channel.send(
            f"✅ **Energia de {nome_alvo}:** {ficha['energia_atual']}/{ficha['energia_max']}\n"
            f"⟦{en_barra}⟧ • {en_pct}%"
        )

    elif cmd == '&setsanidademax':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['sanidade_max'] = valor
        ficha['sanidade_atual'] = min(ficha['sanidade_atual'], valor)
        await save_ficha(uid, ficha)
        await message.channel.send(f'✅ Sanidade máxima de **{nome_alvo}** definida para **{valor}**.')

    elif cmd == '&sanidadeadd':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        valor, erro_v = parse_valor(parts, -1)
        if erro_v:
            await message.channel.send(f'❌ {erro_v}')
            return
        ficha = await get_ficha(uid)
        ficha['sanidade_atual'] = min(ficha['sanidade_max'], ficha['sanidade_atual'] + valor)
        await save_ficha(uid, ficha)
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        await message.channel.send(
            f"✅ **Sanidade de {nome_alvo}:** {ficha['sanidade_atual']}/{ficha['sanidade_max']}\n"
            f"⟦{san_barra}⟧ • {san_pct}%"
        )

    elif cmd == '&heall':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        ficha = await get_ficha(uid)
        ficha['hp_atual'] = ficha['hp_max']
        ficha['energia_atual'] = ficha['energia_max']
        ficha['sanidade_atual'] = ficha['sanidade_max']
        await save_ficha(uid, ficha)
        hp_barra, hp_pct = gerar_barra(ficha['hp_atual'], ficha['hp_max'])
        en_barra, en_pct = gerar_barra(ficha['energia_atual'], ficha['energia_max'])
        san_barra, san_pct = gerar_barra(ficha['sanidade_atual'], ficha['sanidade_max'])
        embed = discord.Embed(
            title=f"✨ {nome_alvo} foi completamente curado!",
            color=0x2ecc71
        )
        embed.add_field(
            name="❤️ HP",
            value=f"`{ficha['hp_atual']}/{ficha['hp_max']}`\n⟦{hp_barra}⟧ • {hp_pct}%",
            inline=False
        )
        embed.add_field(
            name="⚡ Energia",
            value=f"`{ficha['energia_atual']}/{ficha['energia_max']}`\n⟦{en_barra}⟧ • {en_pct}%",
            inline=True
        )
        embed.add_field(
            name="🧠 Sanidade",
            value=f"`{ficha['sanidade_atual']}/{ficha['sanidade_max']}`\n⟦{san_barra}⟧ • {san_pct}%",
            inline=True
        )
        await message.channel.send(embed=embed)

    elif cmd == '&mudarimagem':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if not message.attachments:
            await message.channel.send('❌ Anexe uma imagem junto ao comando.\nUso: `&mudarimagem @usuario/ID` + imagem anexada')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        imagem_url = message.attachments[0].url
        ficha = await get_ficha(uid)
        ficha['imagem'] = imagem_url
        await save_ficha(uid, ficha)
        await message.channel.send(f'✅ Imagem da ficha de **{nome_alvo}** atualizada!')

    elif cmd == '&mudarnome':
        if not is_admin(message.author):
            await message.channel.send('❌ Apenas administradores podem usar este comando.')
            return
        if len(parts) < 3:
            await message.channel.send('Uso: `&mudarnome @usuario/ID novo nome`')
            return
        uid, nome_alvo, erro = await resolver_alvo(message, parts, 1)
        if erro:
            await message.channel.send(erro)
            return
        novo_nome = ' '.join(parts[2:])
        if not novo_nome.strip():
            await message.channel.send('❌ Informe um nome válido.')
            return
        ficha = await get_ficha(uid)
        ficha['nome'] = novo_nome.strip()
        await save_ficha(uid, ficha)
        await message.channel.send(f'✅ Nome de **{nome_alvo}** na ficha alterado para **{novo_nome.strip()}**.')

async def health_check(request):
    return web.Response(text='OK')

async def start_web():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await init_db()
    async with client:
        await asyncio.gather(
            start_web(),
            client.start(os.getenv('DISCORD_TOKEN'))
        )

asyncio.run(main())
