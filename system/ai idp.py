import discord
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO

# === CONFIGURATION ===
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN'

# Channels
SCRIM_WATCH_CHANNEL_ID = 111111111111111111  # Scrim submissions
SCRIM_POST_CHANNEL_ID = 222222222222222222   # Scrim results

TOURNAMENT_WATCH_CHANNEL_ID = 333333333333333333  # Tournament submissions
TOURNAMENT_POST_CHANNEL_ID = 444444444444444444   # Tournament results

GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY'
SCRIM_MOD_ROLE_ID = 555555555555555555  # Role allowed to submit

# === Initialize Gemini AI ===
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("Gemini 1.5 Pro")

# === Initialize Discord Client ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


def extract_scrim_idp(image_url=None, text_input=None):
    prompt = (
        "You are an expert BGMI Scrim Room ID and Password extractor. "
        "Only extract and return the Room ID and Password from the input. "
        "Return exactly in this format:\n\nRoom ID: 1234567\nPassword: abc123\n\n"
        "If no valid Room ID or Password is found, reply ONLY with: No IDP found."
    )
    try:
        if image_url:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            result = gemini_model.generate_content([prompt, image])
        elif text_input:
            result = gemini_model.generate_content([prompt + "\n\nContent:\n" + text_input])
        else:
            return "No input provided."
        return result.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


def extract_tournament_idp(image_url=None, text_input=None):
    prompt = (
        "You are an expert BGMI Tournament Room ID and Password extractor. "
        "Only extract and return the Room ID and Password from the input. "
        "Return exactly in this format:\n\nRoom ID: 1234567\nPassword: abc123\n\n"
        "If no valid Room ID or Password is found, reply ONLY with: No IDP found."
    )
    try:
        if image_url:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            result = gemini_model.generate_content([prompt, image])
        elif text_input:
            result = gemini_model.generate_content([prompt + "\n\nContent:\n" + text_input])
        else:
            return "No input provided."
        return result.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Only process in the two watch channels
    if message.channel.id not in [SCRIM_WATCH_CHANNEL_ID, TOURNAMENT_WATCH_CHANNEL_ID]:
        return

    guild = message.guild
    member = guild.get_member(message.author.id)
    if member is None:
        await message.channel.send("Error: Could not verify your roles.")
        return

    if SCRIM_MOD_ROLE_ID not in [role.id for role in member.roles]:
        await message.channel.send("Sorry, only members with the 'scrim_mod' role can submit IDPs.")
        return

    # Decide which extractor and post channel to use
    if message.channel.id == SCRIM_WATCH_CHANNEL_ID:
        extractor = extract_scrim_idp
        post_channel_id = SCRIM_POST_CHANNEL_ID
        kind = "Scrim"
    else:
        extractor = extract_tournament_idp
        post_channel_id = TOURNAMENT_POST_CHANNEL_ID
        kind = "Tournament"

    output_channel = client.get_channel(post_channel_id)
    if output_channel is None:
        await message.channel.send("Error: Could not find the output channel.")
        return

    idp_result = None

    # Try attachments (images)
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                await message.channel.send(f"Analyzing {kind} image with Gemini AI...")
                idp_result = extractor(image_url=attachment.url)
                break

    # If no image or no result, try text content
    if idp_result is None and message.content.strip():
        await message.channel.send(f"Analyzing {kind} text with Gemini AI...")
        idp_result = extractor(text_input=message.content)

    if idp_result:
        if "Room ID" in idp_result and "Password" in idp_result:
            await output_channel.send(
                f"**BGMI {kind} Room Details**\n\n{idp_result}\n\nJoin the custom room ASAP before it gets full!"
            )
        elif idp_result == "No IDP found.":
            await message.channel.send(f"No valid Room ID & Password found in your {kind.lower()} submission.")
        else:
            await message.channel.send(f"Error processing your submission: {idp_result}")
    else:
        await message.channel.send("Could not process your submission.")


client.run(DISCORD_TOKEN)
