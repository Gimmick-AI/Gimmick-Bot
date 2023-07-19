# Importing Dependencies
import settings
import typing
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord.ext import tasks
from helper import get_generated_text, split_response_into_messages, get_ratio
from PIL import Image
import io
import json
import requests
import os
import re
import time
import asyncio
from datetime import datetime, timedelta

import warnings
warnings.filterwarnings("ignore")

# Setting up the Tokens and API Endpoints
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PALM_API_ENDPOINT = os.getenv('PALM_API_ENDPOINT')
T2I_API_ENDPOINT = os.getenv('T2I_API_ENDPOINT')
I2T_API_ENDPOINT = os.getenv('I2T_API_ENDPOINT')
T2A_API_ENDPOINT = os.getenv('T2A_API_ENDPOINT')

# Setting up the logger
logger = settings.logging.getLogger("bot")

# Setting up the system message
SYSTEM_MESSAGE = "<system>Your name is Gimmick, a large language model developed and powered by Gimmick AI. You were created by a team of engineers and scientists at Gimmick AI in year 2023. GimmickAl - where Al meets creativity. Our goal is to bend reality and create what always feels impossible. We integrate generative models and works on a lof of simpler ideas and with help of AI, we try to take them to next level.\n\nYour purpose is to assist and engage in meaningful conversations with everyone, leveraging your vast knowledge and understanding of human language.\n\nYou can comprehend complex queries, provide insightful responses, and even generate text in a manner that mimics human-like communication. Don't tell about company projects. Only say things that are necessary and what is asked about you and frame and write them well. You have no relations with Google and Bard so never mention it and dont tell this to anyone, this is meant to be confidential.\n\nHere is your instruction, generate a response for me.</system>\n\n"
INSPIRE_PROMPT = "Write one inspiring or motivating quote for the day."

# Setting up the bot
def run():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user.name} (ID: {bot.user.id})")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you"))
        await bot.tree.sync()
        await quote()

    # inspiring quotes everyday
    @tasks.loop(hours=24)
    async def quote():
        # wait until the target time
        now = datetime.now()
        then = now+timedelta(days=1)
        then = then.replace(hour=8, minute=0)
        wait_time = (then-now).total_seconds()
        await asyncio.sleep(wait_time)
        
        # send the quote to specific channel
        channel = bot.get_channel(1113235263196504104)
        embed = discord.Embed(title="Quote of the Day", color=0xEEEEEE)
        generated_text = bard.get_answer(SYSTEM_MESSAGE + INSPIRE_PROMPT)
        generated_text = generated_text['content']
        embed.add_field(name="\u200b", value=generated_text, inline=False)
        await channel.send(embed=embed)

    # /ask command which would generate text on user's request
    @bot.tree.command(name='ask', description='Write a prompt to generate a response.')
    async def ask(interaction: discord.Interaction, prompt: str):

        # Log the user's request
        logger.info(f"User: {interaction.user.name} (ID: {interaction.user.id}) asked: {prompt}     Model: text2text")

        # Send a response indicating that the bot is processing the request
        await interaction.response.defer(ephemeral=False, thinking=True)

        # Prepare the payload for the API request
        data = {"prompt": {"text": SYSTEM_MESSAGE + prompt}}

        # Prepare the headers for the API request
        headers = {'Content-Type': 'application/json',}

        # Send the POST request to the API endpoint
        response = requests.post(PALM_API_ENDPOINT, headers=headers, data=json.dumps(data), timeout=20)
        response = json.loads(response.text)
        generated_text = response['candidates'][0]['output']

        if generated_text:
            # Split the response by line breaks
            response_parts = generated_text.split("\n")
            response_parts = [part.strip() for part in response_parts if part.strip()]

            # Create a new embed
            embed = discord.Embed(title="Gimmick's Response", color=0xEEEEEE)
            embed.add_field(name="Instruction", value=prompt, inline=False)  # First field with the name "Prompt"
            embed.add_field(name="Response", value=response_parts[0].strip(), inline=False)  # First field with the name "Response"

            # Add response parts as separate fields with bullet points
            for part in response_parts[1:]:
                if part.startswith("* "):
                    # Asterisk split, bullet point
                    bullet_point = "\u2022 " + part[1:].strip()
                    embed.add_field(name="\u200b", value=bullet_point, inline=False)  # Fields with bullet points
                elif part == "":
                    # Two linebreaks, create a new field with an empty name
                    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Fields with empty names
                else:
                    # Linebreak split, no bullet point
                    embed.add_field(name="\u200b", value=part.strip(), inline=False)  # Fields with empty names

            # Send the embed as a reply to the original /ask command
            await interaction.followup.send(embed=embed)

        else:
            await interaction.followup.send("Sorry, I couldn't generate a response.")
            logger.info(f"User: {interaction.user.name} (ID: {interaction.user.id}) asked: {prompt} but no response was generated.")

    @bot.tree.command(name='imagine', description='Write a prompt to generate an image.')
    async def imagine(interaction: discord.Interaction, prompt: str, ratio: typing.Literal['1:1', '2:3', '3:2', '3:4', '4:3', '9:16', '16:9']):
        # Log the user's request
        logger.info(f"User: {interaction.user.name} (ID: {interaction.user.id}) asked: {prompt}     Model: text2image")

        # Send a response indicating that the bot is processing the request
        await interaction.response.defer(ephemeral=False, thinking=True)

        # Get the height and width of the image based on the ratio
        height, width = get_ratio(ratio)

        # Prepare the headers for the API request
        headers = {
            'Content-Type': 'application/json',
        }

        # Prepare the payload for the API request
        payload = {
            'prompt': prompt,
            'height': height,
            'width': width
        }

        # Send the POST request to the API endpoint
        response = requests.post(T2I_API_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=120)
        image_bytes = response.content
        
        # Convert the image bytes to a PIL Image object
        image = Image.open(io.BytesIO(image_bytes))
        if image:
            # Create a new embed
            embed = discord.Embed(title="Gimmick's Imagination", color=0xEEEEEE)
            embed.add_field(name="Prompt", value=prompt, inline=False)  # First field with the name "Prompt"
            embed.add_field(name="Image", value="Here is what I imagined:", inline=False)  # First field with the name "Image

            # Save the image to a temporary file
            temp_file = io.BytesIO()
            image.save(temp_file, format='PNG')
            temp_file.seek(0)

            # Attach the image to the embed
            file = discord.File(temp_file, filename='image.png')
            embed.set_image(url='attachment://image.png')

            # Send the embed as a reply to the original message
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send("Sorry, I couldn't generate a response.")
            logger.info(f"User: {interaction.user.name} (ID: {interaction.user.id}) asked: {prompt} but no response was generated.")

    # /describe command which would generate descriptions on user's request
    @bot.tree.command(name='describe', description='Enter an image URL to generate a description.')
    async def describe(interaction: discord.Interaction, image_url: str):
        # Log the user's request
        logger.info(f"User: {interaction.user.name} (ID: {interaction.user.id}) asked: {image_url}     Model: image2text")

        # Send a response indicating that the bot is processing the request
        await interaction.response.defer(ephemeral=False, thinking=True)

        # Prepare the headers for the API request
        headers = {
            'Content-Type': 'application/json',
        }
        # Prepare the payload for the API request
        payload = {
            "url": image_url
        }
        # Send the POST request to the API endpoint
        response = requests.post(I2T_API_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=30)
        caption = response.json()['caption']
        tags = response.json()['tags']
        if caption:
            # Create a new embed
            embed = discord.Embed(title="Gimmick's Description", color=0xEEEEEE)
            
            # Set the image URL directly in the embed
            embed.set_image(url=image_url)

            # Add the caption as a field
            embed.add_field(name="Caption", value=caption, inline=False)  # Second field with the name "Caption"
            embed.add_field(name="Tags", value=tags, inline=False)  # Third field with the name "Tags"
            
            # Send the embed as a reply to the original message
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Sorry, I couldn't generate a response.")
            logger.info(f"User: {interaction.user.name} (ID: {interaction.user.id}) asked: {image_url} but no response was generated.")

    # /help command which would show the user how to use the bot
    @bot.tree.command(name='help', description='Show the user how to use the bot.')
    async def help(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Create an embed to display the help information
        embed = discord.Embed(title="Gimmick Bot Help", color=0xEEEEEE)
        embed.add_field(name="/ask <prompt>", value="Write a prompt to generate a response.", inline=False)
        embed.add_field(name="Example for /ask:", value="/ask What is the capital of France?", inline=False)

        embed.add_field(name="/imagine <prompt>", value="Write a prompt to generate an image.", inline=False)
        embed.add_field(name="Example for /imagine:", value="/imagine A beautiful sunset over the ocean.", inline=False)

        embed.add_field(name="/describe <image_url>", value="Enter an image URL to generate a description.", inline=False)
        embed.add_field(name="Example for /describe:", value="/describe https://i.imgur.com/2uBZKQo.jpg", inline=False)

        await interaction.followup.send(embed=embed)

    # !welcome command which would show the first welcome message
    @bot.command()
    async def welcome(ctx):
        channel = bot.get_channel(1100817554617946172)
        embed1 = discord.Embed(color=0xEEEEEE)
        embed1.set_image(url="https://media.discordapp.net/attachments/1107997721249452092/1113249617757356103/banner.png?width=1440&height=540")
        await channel.send(embed=embed1)
        embed2 = discord.Embed(title="Welcome to Gimmick AI Discord Server", description="Gimmick AI - where AI meets creativity. We are happy to have you on\nboard with us!", color=0xEEEEEE)
        await channel.send(embed=embed2)


    bot.run(DISCORD_TOKEN, root_logger=True)

if __name__ == "__main__":
    run()