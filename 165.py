import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import InputStream, InputAudioStream
from yt_dlp import YoutubeDL

# ================= CONFIG ==================
API_ID = 29799310
API_HASH = "3336adf6895c1d55e88873cef51dfb25"
BOT_TOKEN = "8268848983:AAGePVO0P1cUVd6-0iGbbPIdKskJfEt7d4Q"
SESSION_STRING = "YOUR_USER_SESSION_STRING"
DOWNLOAD_PATH = "downloads"
os.makedirs(DOWNLOAD_PATH, exist_ok=True)
# ===========================================

bot = Client("vc_bot", bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
vc = PyTgCalls(userbot)

queue = []
is_playing = False
current_chat_id = None
current_song = None
current_msg_id = None
song_start_time = None
song_duration = None  # seconds

# ---------------- Functions ----------------
def add_to_queue(song_name: str):
    queue.append(song_name)

def get_next_song():
    if queue:
        return queue.pop(0)
    return None

def download_song(query: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=True)["entries"][0]
        file_path = ydl.prepare_filename(info)
        title = info.get("title", query)
        duration = info.get("duration", 180)
    return file_path, title, duration

def progress_bar(elapsed, total, length=20):
    filled = int(length * elapsed / total)
    bar = "█" * filled + "░" * (length - filled)
    return bar

def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{int(s):02d}"

# ---------------- Buttons -----------------
def get_control_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏯ Pause/Resume", callback_data="pause_resume"),
            InlineKeyboardButton("⏭ Skip", callback_data="skip"),
            InlineKeyboardButton("⏹ Stop", callback_data="stop")
        ],
        [
            InlineKeyboardButton("📜 Queue", callback_data="show_queue")
        ]
    ])

# ---------------- Bot Commands -------------
@bot.on_message(filters.command("play") & filters.group)
async def play(_, message):
    global current_chat_id, current_msg_id
    if len(message.command) < 2:
        await message.reply_text("❌ သီချင်းနာမည်ထည့်ပါ `/play <song>`")
        return
    song_name = " ".join(message.command[1:])
    add_to_queue(song_name)
    current_chat_id = message.chat.id
    status_msg = await message.reply_text(
        f"🎵 **{song_name}** added to queue!\n🎹 Control playback with buttons below.",
        reply_markup=get_control_buttons()
    )
    current_msg_id = status_msg.message_id

# ---------------- Button Callbacks ----------
@bot.on_callback_query()
async def callbacks(_, query):
    global is_playing, current_song, song_start_time
    try:
        if query.data == "skip":
            if queue:
                next_song = get_next_song()
                current_song = next_song
                await query.message.edit_text(f"⏭ Skipped! Now Playing: **{next_song}**", reply_markup=get_control_buttons())
                is_playing = False
            else:
                await query.message.edit_text("❌ Queue is empty.", reply_markup=get_control_buttons())
        elif query.data == "stop":
            queue.clear()
            is_playing = False
            current_song = None
            await query.message.edit_text("⏹ Playback stopped and queue cleared!", reply_markup=get_control_buttons())
        elif query.data == "pause_resume":
            if vc.is_connected:
                try:
                    await vc.pause_stream(current_chat_id)
                    await query.message.edit_text(f"⏸ Paused: {current_song}", reply_markup=get_control_buttons())
                except:
                    await vc.resume_stream(current_chat_id)
                    await query.message.edit_text(f"▶️ Resumed: {current_song}", reply_markup=get_control_buttons())
        elif query.data == "show_queue":
            if queue:
                q_text = "\n".join([f"🎶 {i+1}. {s}" for i, s in enumerate(queue)])
                await query.answer(f"📜 Queue:\n{q_text}", show_alert=True)
            else:
                await query.answer("📜 Queue is empty!", show_alert=True)
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}", reply_markup=get_control_buttons())

# ---------------- VC Player with Graphical Progress -----------------
async def play_queue():
    global is_playing, current_song, song_start_time, song_duration
    while True:
        if not is_playing and queue and current_chat_id:
            song = get_next_song()
            current_song = song
            file_path, title, duration = download_song(song)
            song_duration = duration
            song_start_time = time.time()
            print(f"🎵 Playing {title} in VC...")
            is_playing = True
            vc.join_group_call(current_chat_id, InputStream(InputAudioStream(file_path)))

            # Update progress every 5 seconds
            while is_playing and (time.time() - song_start_time) < song_duration:
                elapsed = int(time.time() - song_start_time)
                remaining = song_duration - elapsed
                bar = progress_bar(elapsed, song_duration)
                try:
                    await bot.edit_message_text(
                        current_chat_id,
                        current_msg_id,
                        f"🎶 Now Playing: **{title}**\n⏱ {format_time(elapsed)}/{format_time(song_duration)} | Remaining: {format_time(remaining)}\n[{bar}]",
                        reply_markup=get_control_buttons()
                    )
                except:
                    pass
                await asyncio.sleep(5)
            is_playing = False
        await asyncio.sleep(2)

# ---------------- Main ---------------------
async def main():
    await bot.start()
    await userbot.start()
    await vc.start()
    print("🎶 Modern VC Music Bot with Graphical Progress & Remaining Time started.")
    await play_queue()

asyncio.run(main())