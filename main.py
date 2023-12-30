from apscheduler.schedulers.asyncio import AsyncIOScheduler
import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

import requests
import json
from flask import Flask, jsonify
from discord import Embed, SyncWebhook


from aiohttp import ClientSession
from discord import Webhook


from datetime import datetime, timedelta

load_dotenv()

token = os.getenv('TOKEN')
webhook_url = os.getenv('WEBHOOK_URL')
webhook_url_dev = os.getenv('WEBHOOK_URL_DEV')


webhook = SyncWebhook.from_url(webhook_url_dev)


def get_remaining_time(start_time):
    try:
        now = datetime.utcnow()
        start_time = datetime.fromtimestamp(start_time)
        remaining_time = start_time - now
        if remaining_time < timedelta(seconds=0):
            return "Contest started!"
        return f"{remaining_time.seconds} seconds remaining"
    except Exception as e:
        print(f"Error calculating remaining time: {e}")
        return "Error retrieving contest information."


scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('interval', seconds=1)
async def update_contests():
    embed = fetch_and_display_contests()
    if isinstance(embed, str):
        await webhook.send(content=embed)
    else:
        for contest in embed.fields:
            contest.value = get_remaining_time(
                datetime.fromtimestamp(start_time))
        await webhook.edit_message(embed=embed, original_message=message)


# Codeforces API URL
API_URL = "https://codeforces.com/api/contest.list?gym=false&showUnofficial=false"

app = Flask(__name__)


def get_upcoming_contests():
    api_url = 'https://codeforces.com/api/contest.list'
    params = {'gym': False}

    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()

        upcoming_contests = []
        for contest in data['result']:
            if contest['phase'] == 'BEFORE':
                upcoming_contests.append(contest)

        return upcoming_contests
    else:
        return {'error': 'Failed to fetch upcoming contests from Codeforces API'}


def fetch_and_display_contests():
    response = requests.get(API_URL).json()
    # with open("codeforces_response.json", "a") as f:
    #   f.write(json.dumps(response))
    contests = response["result"]

    upcoming_contests = [c for c in contests if c["phase"] == "BEFORE"]

    if not upcoming_contests:
        return "No upcoming contests found."

    embed = Embed(title="Upcoming Codeforces Contests", color=0x00FF00)

    for contest in upcoming_contests:
        name = contest["name"]
        start_time = contest["startTimeSeconds"]
        remaining_time = get_remaining_time(start_time)

        from datetime import datetime
        start_time_formatted = datetime.fromtimestamp(
            start_time).strftime("%d-%b-%Y %H:%M:%S")

        embed.add_field(
            name=name, value=f"Starts at {start_time_formatted}", inline=False)

    return embed


if __name__ == '__main__':
    intents = discord.Intents.default()
    intents.message_content = True
    intents.messages = True
    intents.guilds = True

    bot = commands.Bot(command_prefix='!', intents=intents)

    rank_emoji_map = {
        "newbie": ":small_red_triangle_down:",
        "master": "<:master_emoji:9876543210>",
    }

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')

# bot event on message
    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        await bot.process_commands(message)

    @bot.command(name='rating')
    async def rating(ctx, message):
        user_handle = message
        api_response = requests.get(
            f"https://codeforces.com/api/user.info?handles={user_handle}")
        data = api_response.json()

        print(data)

        # Create the card embed
        embed = discord.Embed(
            title="Codeforces User Rating",
            color=discord.Color.blue()  # Customize card color
        )

        user_data = data['result'][0]
        # Set a default emoji if rank not found
        rank_emoji = rank_emoji_map.get(
            user_data["rank"], "<:default_emoji:0000000000>")
        # Set user avatar (optional)
        embed.set_thumbnail(url="https://pngtree.com/freepng/vector-link-icon_3785569.html")
        embed.add_field(name="Username",
                        value=user_data["handle"], inline=True)
        embed.add_field(name="Rating", value=user_data["rating"], inline=False)
        embed.add_field(name="Rank", value=rank_emoji, inline=False)
        embed.add_field(name="Max Rating",
                        value=user_data["maxRating"], inline=False)
        # Add more fields as needed

        # Store the card embed in the context
        ctx.bot.context_embed = embed
        card_embed = ctx.bot.context_embed
        await ctx.send(embed=card_embed)

    @bot.command(name='e')
    async def respond_with_emoji(ctx, emoji_id):
        emoji_list = ctx.guild.emojis
        print(emoji_list)
        emoji = await ctx.guild.fetch_emoji(emoji_id)

        embed = discord.Embed(
            title=f"Emoji Information",
            description=f"Emoji Name: {emoji.name}\nEmoji ID: {emoji.id}",
            color=0x00ff00  # You can customize the color
        )

        embed.set_thumbnail(url=emoji.url)  # Display the emoji as a thumbnail

        await ctx.send(embed=embed)

    @bot.command(name='cal')
    async def cal(ctx):
        embed = fetch_and_display_contests()

        if isinstance(embed, str):
            await ctx.send(embed)
        else:
            webhook = SyncWebhook.from_url(webhook_url_dev)
            message = webhook.send(embed=embed)
            for contest in embed.fields:
                contest.value = get_remaining_time(
                    datetime.fromtimestamp(start_time))
            await webhook.edit_message(embed=embed, original_message=message)
    bot.run(token)
    app.run(debug=True)
    scheduler.start()
