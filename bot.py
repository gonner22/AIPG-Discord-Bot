import discord
from discord.ext import commands, tasks
import requests
import time
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Obtener el token desde la variable de entorno
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Define intents to enable message events
intents = discord.Intents.default()
intents.messages = True

# Create a Discord bot instance
client = commands.Bot(command_prefix="!", intents=intents)

# Function to set a voice channel to private (disconnect for everyone)
async def set_channel_private(category, channel):
    try:
        # Check if the channel is a voice channel and part of the specified category
        if isinstance(channel, discord.VoiceChannel) and channel.category == category:
            # Set permissions to prevent connecting for the default role (everyone)
            await channel.set_permissions(channel.guild.default_role, connect=False)
    except Exception as e:
        print(f"An error occurred while setting channel to private: {e}")

# Function to get or create a voice channel within a category
async def get_or_create_channel(category, channel_name):
    for existing_channel in category.voice_channels:
        existing_name = existing_channel.name.lower().replace(" ", "")
        target_name = channel_name.lower().replace(" ", "")

        # Check if a similar channel already exists
        if existing_name.startswith(target_name):
            return existing_channel

    # If no similar channel found, create a new one
    channel = await category.create_voice_channel(channel_name)
    time.sleep(0.5)
    return channel

# Function to create or update a voice channel's name with specific formatting
async def create_or_update_channel(guild, category, channel_name, stat_value):
    try:
        # Get or create the channel within the specified category
        channel = await get_or_create_channel(category, channel_name)

        # Format the value based on the channel name
        if channel_name.lower() == "supply:":
            formatted_value = "{:,.0f} AIPG".format(stat_value)
        elif channel_name.lower() == "price: $":
            formatted_value = "{:.3f}".format(stat_value)
        elif channel_name.lower() in ["difficulty:", "market cap:", "hashrate:", "block:"]:
            formatted_value = "{:,.0f}".format(stat_value)
        else:
            formatted_value = stat_value

        # Update the channel name with the formatted value
        await channel.edit(name=f"{channel_name} {formatted_value}")

    except Exception as e:
        print(f"An error occurred while updating channel name: {e}")

# Function to update all statistics channels within a guild
async def update_stats_channels(guild):
    try:
        # Fetch server statistics from an external API
        response = requests.get("https://explorer.aipowergrid.io/ext/getsummary")
        data = response.json()

        # Define the category name for statistics channels
        category_name = "Server Stats"
        category = discord.utils.get(guild.categories, name=category_name)

        # If the category doesn't exist, create it
        if not category:
            print(f"Creating category '{category_name}'")
            category = await guild.create_category(category_name)

        # Introduce a delay between creation requests
        time.sleep(0.5)

        # Update or create individual statistics channels
        await create_or_update_channel(guild, category, "Difficulty:", data["difficulty"])
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Hashrate: TH/s", data["hashrate"])
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Block:", data["blockcount"])
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Supply:", data["supply"])
        time.sleep(0.5)
        await create_or_update_channel(guild, category, "Price: $", data["lastPrice"])
        time.sleep(0.5)

        # Calculate market cap and update its channel
        market_cap = data["supply"] * data["lastPrice"]
        formatted_market_cap = "{:,.0f}".format(market_cap)
        await create_or_update_channel(guild, category, "Market Cap: $", formatted_market_cap)

        # Set all channels within the category to private
        for channel in category.voice_channels:
            await set_channel_private(category, channel)

    except Exception as e:
        print(f"An error occurred while updating channels: {e}")

# Define a task to update statistics channels every 5 minutes
@tasks.loop(minutes=5)
async def update_stats_task():
    for guild in client.guilds:
        print(f"Updating stats for guild '{guild.name}'")
        await update_stats_channels(guild)

# Event triggered when the bot is ready
@client.event
async def on_ready():
    print("The bot is ready")
    update_stats_task.start()

# Run the bot with the provided token
client.run(TOKEN)
