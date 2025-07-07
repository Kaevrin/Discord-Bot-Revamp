import discord
from discord.ext import commands
import requests
import re
 
class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://stormgate.wiki.gg/api.php"

    def parse_infobox_unit(self, wikitext):
        pattern = re.compile(r"\{\{infobox-unit(.*?)\}\}", re.DOTALL)
        match = pattern.search(wikitext)
        if not match:
            return None
        
        infobox_text = match.group(1)
        info = {}
        for line in infobox_text.split('\n'):
            line = line.strip()
            if line.startswith('|') and '=' in line:
                key, val = line[1:].split('=', 1)
                info[key.strip()] = val.strip()
        return info

    def format_infobox_embed(self, info):
        title = info.get('title', 'Unknown')
        description = (
            f"**Faction:** {info.get('faction', 'N/A')}\n"
            f"**Health:** {info.get('health', 'N/A')}\n"
            f"**Armor:** {info.get('armor', 'N/A')}\n"
            f"**Move Speed:** {info.get('movespeed', 'N/A')}\n"
            f"**Supply:** {info.get('supply', 'N/A')}\n"
            f"**Produced at:** {info.get('produced', 'N/A')}\n"
        )

        weapon_name = info.get('weapon1name')
        if weapon_name:
            description += (
                f"\n**{weapon_name}:**\n"
                f"Damage: {info.get('weapon1damage', 'N/A')}\n "
                f"Range: {info.get('weapon1range', 'N/A')}\n"
            )

        page_link = f"https://stormgate.wiki.gg/wiki/{title.replace(' ', '_')}"
        embed = discord.Embed(title=title, description=description[:2048], url=page_link, color=0x00aaff)

        images = info.get('images')
        if images:
            image_list = [img.strip() for img in images.split(',')]
            if len(image_list) >= 1:
                embed.set_thumbnail(url=f"https://stormgate.wiki.gg/wiki/Special:FilePath/{image_list[1]}")
            if len(image_list) >= 2:
                embed.set_image(url=f"https://stormgate.wiki.gg/wiki/Special:FilePath/{image_list[0]}")


        return embed


    @commands.command(name="wiki")
    async def fetch_wiki(self, ctx, *, query: str):
        print(f".wiki command received with query: {query}")

        params = {
            "action": "query",
            "format": "json",
            "titles": query,
            "prop": "revisions",
            "rvprop": "content",
            "formatversion": 2
        }

        response = requests.get(self.api_url, params=params)
        print(f"API response status: {response.status_code}")
        data = response.json()
        print(f"API response JSON keys: {data.keys()}")

        if response.status_code != 200:
            await ctx.send("Failed to connect to the wiki.")
            return

        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            await ctx.send("Page not found.")
            return

        wikitext = pages[0].get("revisions", [{}])[0].get("content", "")
        infobox = self.parse_infobox_unit(wikitext)
        if not infobox:
            await ctx.send("No infobox found on this page.")
            return
        
        embed = self.format_infobox_embed(infobox)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Wiki(bot))
