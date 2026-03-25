import discord
import aiohttp
from dotenv import load_dotenv
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('&hello'):
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(webhook_url, session=session)
                await webhook.send('Hello!')
        else:
            await message.channel.send('Webhook não configurado!')

token = os.getenv('DISCORD_TOKEN')
if not token:
    print('Error: DISCORD_TOKEN environment variable not set.')
else:
    client.run(token)
