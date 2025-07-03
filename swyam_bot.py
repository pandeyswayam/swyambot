import os
import logging
import replicate
import aiohttp
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# 📥 Load .env
load_dotenv()

# 🔑 Load API keys
TELEGRAM_TOKEN = os.getenv("8132596043:AAENH41SgaOTNF1XOGOISd66KJ5gR4l9xC0") or "8132596043:AAENH41SgaOTNF1XOGOISd66KJ5gR4l9xC0"
REPLICATE_TOKEN = os.getenv("r8_QplU2nMCek0zLHtjZhUGxLhrJiT38NC3QQ4Lw") or "r8_QplU2nMCek0zLHtjZhUGxLhrJiT38NC3QQ4Lw"

# 🔧 Initialize replicate client
client = replicate.Client(api_token=REPLICATE_TOKEN)

# 🖼️ & 🎥 Replicate model names
IMAGE_MODEL = "black-forest-labs/flux-dev"
VIDEO_MODEL = "kwaivgi/kling-v1.6-standard"

# 🧾 Logger
logging.basicConfig(level=logging.INFO)

# 🚀 Start command
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Send me a prompt to generate an image (Flux), "
        "or send an image to animate (Kling)."
    )

# ✍️ Text → Image
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    chat_id = update.effective_chat.id
    await ctx.bot.send_message(chat_id, "🎨 Generating image...")

    try:
        output = client.run(IMAGE_MODEL, input={"prompt": prompt})
        image_url = output[0]
        await ctx.bot.send_photo(chat_id, image_url)
    except Exception as e:
        logging.error("Image generation error: %s", e)
        await ctx.bot.send_message(chat_id, "⚠️ Image generation failed.")

# 📸 Image → Video
async def handle_image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    photo = update.message.photo[-1]

    bio = BytesIO()
    await photo.get_file().download_to_memory(out=bio)
    bio.seek(0)

    await ctx.bot.send_message(chat_id, "⬆️ Uploading image to Replicate...")

    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("file", bio, filename="image.png", content_type="image/png")

            async with session.post(
                "https://dreambooth-api-experimental.replicate.com/v1/upload",
                headers={"Authorization": f"Token {REPLICATE_TOKEN}"},
                data=form
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Upload failed: {await resp.text()}")
                upload_response = await resp.json()
                image_url = upload_response.get("url")

        if not image_url:
            raise Exception("No image URL returned from upload.")

        await ctx.bot.send_message(chat_id, "🎥 Generating video...")

        output = client.run(VIDEO_MODEL, input={"image": image_url, "duration": 5})
        video_url = output[0]
        await ctx.bot.send_video(chat_id, video_url)

    except Exception as e:
        logging.error("Video generation error: %s", e)
        await ctx.bot.send_message(chat_id, f"⚠️ Video generation failed.\n{e}")

# 🏁 Start the bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
