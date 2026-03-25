import discord
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
        await message.channel.send('Hello!')

token = os.getenv('DISCORD_TOKEN')
if not token:
    print('Error: DISCORD_TOKEN environment variable not set.')
else:
    client.run(token)
