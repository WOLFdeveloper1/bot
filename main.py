import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
from keep_alive import keep_alive

TOKEN = 'MTM4MDEyNjI1NzU0Njc4ODg4Ng.Gq3uPP.JvxO7oPVZ6EpRVbu_wv3y_Pwh2o6Wyy-jKcDIg'
ADMIN_ID = '1325400232267091988'  # Replace with your Discord user ID as a string

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

user_points = {}
points_tracking_enabled = True  # Always enabled in all servers


# Load points from file
def load_points():
    global user_points
    try:
        with open("points.json", "r") as f:
            user_points = json.load(f)
    except FileNotFoundError:
        user_points = {}


# Save points to file
def save_points():
    with open("points.json", "w") as f:
        json.dump(user_points, f)


# Load a key from keys.txt and remove it after use
def get_next_key():
    if not os.path.exists("keys.txt"):
        return None
    with open("keys.txt", "r") as f:
        keys = [line.strip() for line in f if line.strip()]
    if not keys:
        return None
    key = keys[0]
    with open("keys.txt", "w") as f:
        f.writelines(k + '\n' for k in keys[1:])
    return key


@bot.event
async def on_ready():
    print(f'{bot.user} is ready!')
    load_points()
    check_voice_activity.start()


@tasks.loop(minutes=1)
async def check_voice_activity():
    # Tracks all voice channels in every guild the bot is in
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.bot:
                    continue
                uid = str(member.id)
                points_to_add = 0
                if member.voice:
                    if member.voice.self_stream:
                        points_to_add = 1.0
                    elif member.voice.self_deaf:
                        points_to_add = 0.25
                    else:
                        points_to_add = 0.50

                    user_points[uid] = user_points.get(uid, 0) + points_to_add

                    # When a user reaches 100 points, attempt to send a key
                    if user_points[uid] >= 100:
                        key = get_next_key()
                        if key:
                            try:
                                await member.send(
                                    f"🎉 Here's your 1-day WOLVES PVT FREE key:\n`{key}`\n⏰ This key expires in 24 hours!"
                                )
                                user_points[uid] = 0
                            except:
                                pass
                        save_points()


@bot.command()
async def points(ctx):
    """Anyone can check their current points."""
    uid = str(ctx.author.id)
    user_pts = user_points.get(uid, 0)
    await ctx.send(f"📊 You currently have **{user_pts:.2f}** points.")


@bot.command()
async def key(ctx):
    """Anyone can claim a key if they have 100+ points."""
    uid = str(ctx.author.id)
    user_pts = user_points.get(uid, 0)

    if user_pts >= 100:
        key = get_next_key()
        if key:
            try:
                await ctx.author.send(
                    f"🎉 Here's your 1-day WOLVES PVT FREE key:\n`{key}`\n⏰ This key expires in 24 hours!"
                )
                user_points[uid] = 0
                save_points()
                await ctx.send("✅ Key sent to your DMs! Your points have been reset.")
            except discord.Forbidden:
                await ctx.send("❌ I couldn't DM you. Please enable DMs from server members.")
        else:
            await ctx.send("❌ No keys available right now. Please wait for the admin to add more.")
    else:
        needed = 100 - user_pts
        await ctx.send(f"❌ You need **{needed:.2f}** more points to get a key!")


@bot.command()
async def addkeys(ctx):
    """Admin-only: Add multiple keys via DM, one per line."""
    if str(ctx.author.id) != ADMIN_ID:
        await ctx.send("❌ Only the admin can add keys.")
        return

    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("📥 Please use this command in DMs.")
        return

    await ctx.send("📤 Send the keys now (one per line). You have 60 seconds...")

    def check(msg):
        return msg.author == ctx.author and isinstance(msg.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        new_keys = set(line.strip() for line in msg.content.splitlines() if line.strip())

        try:
            with open("keys.txt", "r") as f:
                existing_keys = set(line.strip() for line in f.readlines())
        except FileNotFoundError:
            existing_keys = set()

        updated_keys = existing_keys.union(new_keys)

        with open("keys.txt", "w") as f:
            for key in updated_keys:
                f.write(key + "\n")

        await ctx.send(f"✅ Successfully added {len(new_keys)} new key(s). Total keys: {len(updated_keys)}")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Timeout. Please try `!addkeys` again.")


@bot.command()
async def keysleft(ctx):
    """Admin-only: Show how many keys remain."""
    if str(ctx.author.id) != ADMIN_ID:
        await ctx.send("❌ Only the admin can use this command.")
        return

    try:
        with open("keys.txt", "r") as f:
            keys = [line.strip() for line in f if line.strip()]
        await ctx.send(f"🗝️ Keys available: **{len(keys)}**")
    except FileNotFoundError:
        await ctx.send("🗝️ No keys file found. Admin needs to add keys.")


@bot.command()
async def howtogetkey(ctx):
    """Admin-only: Post an embed explaining how to earn points and get a key."""
    if str(ctx.author.id) != ADMIN_ID:
        await ctx.send("❌ Only the admin can use this command.")
        return

    embed = discord.Embed(
        title="🎯 How to Get Points & Claim a Key",
        description=(
            "Stay active in any voice channel to earn points every minute:\n\n"
            "🎥 **Streaming:** 1.0 point per minute\n"
            "🔊 **Voice Chat (not streaming):** 0.50 points per minute\n"
            "🔇 **Deafened in Voice Chat:** 0.25 points per minute\n\n"
            "🎁 Once you reach **100 points**, use the `!key` command to receive a **1-day WOLVES PVT FREE key** in your DMs!"
        ),
        color=0x00ff00
    )
    await ctx.send(embed=embed)


keep_alive()
bot.run(TOKEN)
