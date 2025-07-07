import discord
from discord.ext import commands
import aiohttp

class Untappedgg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base = "https://api.stormgate.untapped.gg/api/v1"

    async def fetch_json(self, endpoint: str, params: dict = None):
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    @commands.command(name="top10", help="Fetch the top 10 ranked 1v1 players from Untapped.gg")
    async def top10(self, ctx):
        players = await self.fetch_json("leaderboard", {"match_mode": "ranked_1v1"})

        if not players:
            await ctx.send("❌ Failed to fetch leaderboard data from Untapped.gg.")
            return

        top_players = players[:10]
        lines = []
        for i, p in enumerate(top_players, 1):
            name = p.get("playerName", "Unknown")
            race = p.get("race", "Unknown").capitalize()
            mmr = p.get("mmr", "N/A")
            wins = p.get("wins", 0)
            losses = p.get("losses", 0)
            ties = p.get("ties", 0)
            total = wins + losses + ties
            winrate = f"{wins/total*100:.1f}%" if total > 0 else "N/A"

            lines.append(
                f"**{i}. {name}** ({race}) | **MMR:** {mmr} | "
                f"**W:** {wins} **L:** {losses} | **WR:** {winrate}"
            )

        embed = discord.Embed(
            title="🏆 Top 10 Ranked 1v1",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Data from Untapped.gg • Updated every minute")
        await ctx.send(embed=embed)

    @commands.command(name="search", help="Look up a Stormgate player by display name")
    async def search_player(self, ctx, *, player_name: str):
        await ctx.typing()

        players = await self.fetch_json("players", {"q": player_name})
        if not players:
            await ctx.send(f"No players found matching '{player_name}'.")
            return

        first = players[0]
        name = first.get("playerName", "Unknown")

        ranks_1v1 = first.get("ranks", {}).get("ranked_1v1", {})
        if not ranks_1v1:
            await ctx.send(f"No ranked 1v1 stats found for {name}.")
            return

        # Build a description showing all factions with data
        desc_lines = []
        for faction, stats in ranks_1v1.items():
            mmr = stats.get("mmr", "N/A")
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            ties = stats.get("ties", 0)
            league = stats.get("league", "N/A").capitalize()
            total = wins + losses + ties
            winrate = f"{wins/total*100:.1f}%" if total > 0 else "N/A"

            desc_lines.append(
                f"**{faction.capitalize()}** - MMR: {mmr}, League: {league}\n"
                f"Record: {wins}W / {losses}L / {ties}T | Win Rate: {winrate}\n"
            )

        embed = discord.Embed(
            title=f"📊 Player Profile: {name}",
            description="\n".join(desc_lines),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Data from Untapped.gg")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Untappedgg(bot))
