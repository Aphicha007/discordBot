import discord
from discord.ext import commands, tasks
from discord import PCMVolumeTransformer
import yt_dlp as youtube_dl
import requests
import re
import asyncio  
import os
from dotenv import load_dotenv
from sever import server_on

# โหลดข้อมูลจากไฟล์ .env เพื่อเก็บ Token และ API Key
load_dotenv()

# ดึง Token ของบอทใหม่จาก .env
bot_token_new = os.getenv('DISCORD_BOT_TOKEN_NEW')

# ดึง YouTube API Key จาก .env
youtube_api_key = os.getenv('YOUTUBE_API_KEY')

# ตรวจสอบว่ามีการโหลดโทเค็นและ API Key หรือไม่
if bot_token_new is None or youtube_api_key is None:
    raise ValueError("ไม่พบโทเค็นหรือ YouTube API Key ในไฟล์ .env กรุณาตรวจสอบว่าชื่อตัวแปรในไฟล์ .env ถูกต้องและไฟล์อยู่ในไดเรกทอรีเดียวกันกับสคริปต์.")

# ตั้งค่าการทำงานของบอท
intents = discord.Intents.default()  # เปิดใช้งาน intents พื้นฐาน
intents.message_content = True  # เปิดใช้งานการรับข้อความ
bot = commands.Bot(command_prefix="!", intents=intents)  # สร้างอินสแตนซ์ของบอทด้วยคำสั่ง prefix "!"

# ฟังก์ชันที่ทำงานเมื่อบอทพร้อมใช้งาน
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} in {bot.guilds[0].name}")  # แสดงข้อความเมื่อบอทออนไลน์และเชื่อมต่อกับเซิร์ฟเวอร์
    check_inactivity.start()  # เริ่มต้นการตรวจสอบการไม่ใช้งานของบอท

queue = []  # คิวเพลง
current_track_index = 0  # ตำแหน่งของเพลงในคิว
voice_client = None  # ตัวแปรเก็บการเชื่อมต่อเสียง
volume = 0.5  # ระดับเสียงเริ่มต้น (50%)
inactive_timeout = 180  # ระยะเวลาที่บอทจะออกจากช่องหากไม่มีการใช้งาน (วินาที)
last_command_time = None  # เวลาในการรับคำสั่งล่าสุด

# สร้างปุ่มควบคุมเพลง
class MusicControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏮ เพลงก่อนหน้า", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await previous(interaction)

    @discord.ui.button(label="⏯ หยุด/เล่น", style=discord.ButtonStyle.success)
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global voice_client
        if voice_client.is_playing():
            voice_client.pause()  # หยุดเล่นเพลงชั่วคราว
            await interaction.response.send_message("หยุดเล่นเพลง!", ephemeral=True)
        elif voice_client.is_paused():
            voice_client.resume()  # เล่นเพลงต่อจากที่หยุด
            await interaction.response.send_message("เล่นเพลงต่อ!", ephemeral=True)

    @discord.ui.button(label="⏹ หยุดและออกจากช่องเสียง", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global voice_client
        if voice_client is not None and voice_client.is_connected():
            await voice_client.disconnect()  # ออกจากช่องเสียง
            await interaction.response.send_message("บอทออกจากช่องเสียงแล้ว!", ephemeral=True)
        else:
            await interaction.response.send_message("บอทไม่ได้เชื่อมต่อกับช่องเสียง.", ephemeral=True)

    @discord.ui.button(label="⏭ เพลงถัดไป", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await skip(interaction)

    @discord.ui.button(label="🔊 เพิ่มเสียง", style=discord.ButtonStyle.secondary)
    async def volume_up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await volume_up(interaction)

    @discord.ui.button(label="🔉 ลดเสียง", style=discord.ButtonStyle.secondary)
    async def volume_down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await volume_down(interaction)
    
    @discord.ui.button(label="📋 ดูคิวเพลง", style=discord.ButtonStyle.secondary)
    async def view_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await manage_queue(interaction)  # เรียกฟังก์ชัน manage_queue เพื่อแสดงคิวเพลง

# ฟังก์ชันอัปเดต Embed สำหรับการเล่นเพลง
async def update_embed(ctx, title, duration=None, thumbnail_url=None):
    embed = discord.Embed(
        title="กำลังเล่นเพลง - Playing Music",
        description=title,
        color=discord.Color.blue()
    )
    embed.add_field(name="🎵 คิวเพลง", value=f"คิวที่ : {current_track_index + 1}/{len(queue)}", inline=True)
    if duration:
        embed.add_field(name="⏱ เวลาเพลงทั้งหมด", value=f"{duration}", inline=True)
    embed.add_field(name="🔊 ระดับเสียง", value=f"Volume : {int(volume * 100)}%", inline=True)
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
        embed.set_image(url=thumbnail_url)  # ใช้รูปที่เป็น thumbnail สำหรับ embed

    view = MusicControls()
    
    # หากเป็นการอัปเดตจาก interaction เช่นการลบเพลง
    if isinstance(ctx, discord.Interaction):
        await ctx.edit_original_response(embed=embed, view=view)
    else:  # หากเป็นการอัปเดตจาก command เช่น play
        await ctx.send(embed=embed, view=view)

# คำสั่งเล่นเพลง
@bot.command(name='play')
async def play(ctx, *, query: str):
    global voice_client, last_command_time, current_track_index

    if ctx.author.voice is None:
        await ctx.send("กรุณาเข้าร่วมช่องเสียงก่อน!")
        return

    voice_channel = ctx.author.voice.channel

    # ตรวจสอบว่า voice_client มีการเชื่อมต่อกับช่องเสียงอยู่หรือไม่
    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    url, title, duration, thumbnail_url = await search_youtube(query)
    if url is None:
        await ctx.send("ไม่พบวิดีโอ.")
        return

    queue.append((url, title, duration, thumbnail_url))
    print(f"เพิ่มเพลงเข้าคิว: {title}")

    last_command_time = asyncio.get_event_loop().time()

    if not voice_client.is_playing():
        current_track_index = len(queue) - 1  # อัปเดตตำแหน่งปัจจุบันเมื่อเล่นเพลง
        await play_track(ctx, queue[current_track_index])


# ฟังก์ชันค้นหา YouTube
async def search_youtube(query):
    if re.match(r'^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$', query):
        return query, query, None, None  # ถ้าเป็นลิงก์ตรงอยู่แล้ว ให้คืนค่าทั้งลิงก์และลิงก์เป็นชื่อเพลง
    
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={query}&key={youtube_api_key}"
    response = requests.get(search_url)
    results = response.json()

    if results['items']:
        video_id = results['items'][0]['id']['videoId']
        title = results['items'][0]['snippet']['title']
        thumbnail_url = results['items'][0]['snippet']['thumbnails']['high']['url']  # ใช้ภาพที่มีคุณภาพสูงขึ้น
        duration = "ไม่ทราบ"  # สามารถใช้ YouTube Data API v3 เพื่อดึงข้อมูล duration ได้ถ้าต้องการ
        return f"https://www.youtube.com/watch?v={video_id}", title, duration, thumbnail_url
    else:
        return None, None, None, None

# ฟังก์ชันเล่นเพลงถัดไป
async def play_next(ctx):
    global current_track_index, last_command_time

    if current_track_index < len(queue) - 1:
        current_track_index += 1  # ไปยังเพลงถัดไปในคิว
        await play_track(ctx, queue[current_track_index])
    else:
        await ctx.send("ไม่มีเพลงในคิวแล้ว!")  # แจ้งว่าไม่มีเพลงในคิว

    last_command_time = asyncio.get_event_loop().time()

# ฟังก์ชันเล่นเพลงที่เลือกจากคิว
async def play_track(ctx, track):
    global voice_client, volume, last_command_time

    url, title, duration, thumbnail_url = track

    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'quiet': True
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']

        voice_client.stop()  # หยุดเพลงที่กำลังเล่นอยู่
        voice_client.play(PCMVolumeTransformer(discord.FFmpegPCMAudio(url2, executable="ffmpeg", before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn'), volume=volume))

        await update_embed(ctx, title, duration, thumbnail_url)

        last_command_time = asyncio.get_event_loop().time()

    except Exception as e:
        await ctx.send(f"⚠️ ไม่สามารถเล่นเพลงได้: {str(e)}")  # แจ้งเมื่อเกิดข้อผิดพลาดในการเล่นเพลง
        print(f"เกิดข้อผิดพลาดขณะพยายามเล่นเพลง: {str(e)}")

# ฟังก์ชันจัดการคิวเพลง
async def manage_queue(interaction):
    queue_list = ""
    for i, (_, title, _, _) in enumerate(queue):
        queue_list += f"{i + 1}. {title}\n"  # สร้างรายการเพลงในคิว

    embed = discord.Embed(
        title="จัดการคิวเพลง",
        description=queue_list if queue_list else "คิวว่าง!",
        color=discord.Color.green()
    )

    view = ManageQueueView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)  # ส่งข้อความแบบ ephemeral (เฉพาะผู้ใช้งานเห็น)

# สร้างการจัดการคิวเพลง
class ManageQueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🔄 รีเฟรช", style=discord.ButtonStyle.secondary, custom_id="refresh"))  # ปุ่มรีเฟรชคิวเพลง

# คำสั่งลบเพลงจากคิว
@bot.command(name='remove')
async def remove_from_queue(ctx, index: int):
    global current_track_index
    
    if index - 1 < 0 or index - 1 >= len(queue):
        await ctx.send("หมายเลขที่ระบุไม่ถูกต้อง!")
    else:
        removed_song = queue.pop(index - 1)
        await ctx.send(f"ลบเพลง {removed_song[1]} ออกจากคิวแล้ว.")
        
        # ปรับ current_track_index เพื่อให้ตรงกับเพลงปัจจุบันหลังจากลบเพลง
        if current_track_index >= len(queue):
            current_track_index = len(queue) - 1
            
        # อัปเดต Embed หลังจากลบเพลงแล้ว
        if queue:
            await update_embed(ctx, queue[current_track_index][1])
        else:
            await ctx.send("คิวว่างแล้ว ไม่มีเพลงในคิวที่จะเล่นต่อ")

# คำสั่งย้ายตำแหน่งเพลงในคิว
@bot.command(name='move')
async def move_song(ctx, old_index: int, new_index: int):
    if old_index - 1 < 0 or old_index - 1 >= len(queue) or new_index - 1 < 0 or new_index - 1 >= len(queue):
        await ctx.send("หมายเลขที่ระบุไม่ถูกต้อง!")
    else:
        song = queue.pop(old_index - 1)
        queue.insert(new_index - 1, song)
        await ctx.send(f"ย้ายเพลง {song[1]} จากตำแหน่ง {old_index} ไปยัง {new_index} แล้ว.")
        await manage_queue(ctx)  # อัปเดตการแสดงผลคิวเมื่อเพลงถูกย้าย

# คำสั่งหยุดเล่นเพลงและล้างคิว
@bot.command(name='stop')
async def stop(ctx):
    global queue, current_track_index, voice_client

    if voice_client is not None and voice_client.is_connected():
        await voice_client.disconnect()  # บอทออกจากช่องเสียง

    queue = []  # ล้างคิวเพลงทั้งหมด
    current_track_index = 0
    await ctx.send("หยุดเพลงและล้างคิวแล้ว!")

# คำสั่งออกจากช่องเสียง
@bot.command(name='leave')
async def leave(ctx):
    global voice_client
    if voice_client is not None and voice_client.is_connected():
        await voice_client.disconnect()  # บอทออกจากช่องเสียง
        await ctx.send("บอทออกจากช่องเสียงแล้ว!")
    else:
        await ctx.send("บอทไม่ได้อยู่ในช่องเสียง")

# คำสั่งเล่นเพลงถัดไป
@bot.command(name='next')
async def next(ctx):
    await play_next(ctx)  # เล่นเพลงถัดไปในคิว

# คำสั่งเล่นเพลงก่อนหน้า
@bot.command(name='previous')
async def previous(ctx):
    global current_track_index

    if current_track_index > 0:
        current_track_index -= 1  # ย้อนกลับไปยังเพลงก่อนหน้าในคิว
        await play_track(ctx, queue[current_track_index])
    else:
        await ctx.send("ไม่มีเพลงก่อนหน้าในคิว")

# ฟังก์ชันข้ามเพลงถัดไปในคิว
async def skip(interaction):
    global current_track_index

    if current_track_index < len(queue) - 1:
        current_track_index += 1  # ไปยังเพลงถัดไปในคิว
        await play_track(interaction, queue[current_track_index])
    else:
        await interaction.response.send_message("ไม่มีเพลงถัดไปในคิว", ephemeral=True)

# คำสั่งเพิ่มระดับเสียง
async def volume_up(interaction):
    global volume
    if voice_client and voice_client.source:
        volume = min(volume + 0.1, 1.0)  # เพิ่มระดับเสียง (สูงสุด 100%)
        voice_client.source.volume = volume
        await interaction.response.send_message(f"🔊 เพิ่มระดับเสียงเป็น {int(volume * 100)}%")
        await update_embed(interaction, queue[current_track_index][1])

# คำสั่งลดระดับเสียง
async def volume_down(interaction):
    global volume
    if voice_client and voice_client.source:
        volume = max(volume - 0.1, 0.0)  # ลดระดับเสียง (ต่ำสุด 0%)
        voice_client.source.volume = volume
        await interaction.response.send_message(f"🔉 ลดระดับเสียงเป็น {int(volume * 100)}%")
        await update_embed(interaction, queue[current_track_index][1])

# ฟังก์ชันตรวจสอบการไม่ใช้งานของบอท
@tasks.loop(seconds=60)
async def check_inactivity():
    global voice_client, last_command_time
    current_time = asyncio.get_event_loop().time()

    if voice_client is not None:
        # ตรวจสอบว่ามีการเล่นเพลงอยู่หรือไม่
        if voice_client.is_playing():
            last_command_time = current_time  # ถ้าเล่นเพลงอยู่ให้รีเซ็ตเวลา
        elif (current_time - last_command_time) > inactive_timeout:
            if voice_client.is_connected():
                await voice_client.disconnect()  # บอทออกจากช่องเสียงเนื่องจากไม่มีการใช้งาน
                print("บอทออกจากช่องเสียงเนื่องจากไม่มีการใช้งาน")
            

server_on()

# เริ่มรันบอทด้วย token ที่ได้รับ
bot.run(bot_token_new)
