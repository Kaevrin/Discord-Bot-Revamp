# This program made by Shaymon Madrid with help from online resources such as videos, source code examples, and documentation files. 

import discord
from discord.ext import commands
from discord import Intents, Client, Message
import os
import asyncio
from dotenv import load_dotenv

#Important information being loaded
load_dotenv()
TOKEN = os.getenv('discord_token')
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)
admin = [127558963662159872, 448886759749713939]

@bot.command(name="reload")
async def reload(ctx):
    if ctx.author.id in admin:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.unload_extension(f'cogs.{filename[:-3]}')
                print(f'Unloaded: {filename}')
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded: {filename}")

async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'Loaded: {filename}')
    print("Cogs loaded")

async def main():
    await load()
    await bot.start(TOKEN)

asyncio.run(main())