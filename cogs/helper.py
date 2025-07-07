import discord
from discord.ext import commands

class help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.text_channel_text = []
        


    async def send_to_all(self,msg):
        for text_channel in self.text_channel_text:
            await text_channel.send(msg)

    @commands.command(name="help")
    async def custom_help(self, ctx):
        embed = discord.Embed(
            title="📘 Available Commands",
            description="Here are the commands you can use:",
            color=discord.Color.blurple()
        )

        for command in self.bot.commands:
            if not command.hidden:
                name = f"!{command.name}"
                help_text = command.help or "No description."
                embed.add_field(name=name, value=help_text, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="cooked")
    async def cooked(self, ctx):
        try:
            with open('./images/cooked.jpg', 'rb') as f:
                picture = discord.File(f, filename="cooked.jpg")
                
                embed = discord.Embed(
                    #title="You just got cooked!",
                    color=discord.Color.orange()
                )
                embed.set_image(url="attachment://cooked.jpg")

                await ctx.send(embed=embed, file=picture)

        except Exception as e:
            print(e)
            await ctx.send("Something went wrong while trying to cook.")
            
async def setup(bot):
    await bot.add_cog(help(bot))