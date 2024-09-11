#botตรวจจับคำหยาบและสแปมข้อความ

import discord
from discord.ext import commands
import os
import re
from dotenv import load_dotenv
from sever import server_on

# โหลดข้อมูลจากไฟล์ .env เช่น Token และ API Key ต่าง ๆ
load_dotenv()

# ดึง Token ของบอทจาก .env
spam_bot_token = os.getenv('SPAM_BOT_TOKEN')

# คำหยาบที่ต้องการตรวจจับ
bad_words = [
    "อีดอก", "อีเหี้ย", "อีสัตว์", "อีควาย", "อีตอแหล", "ไอ้ระยำ", "ไอ้เบื๊อก", "เฮงซวย",
    "ผู้หญิงต่ำๆ", "มารศาสนา", "หน้าเปรต", "มึง", "กู", "ไอเหี้ย", "ไอสัตว์", "สัส",
    "ไอ้สัส", "อีควาย", "อีหน้าหี", "ควย", "เวร", "อีควาย", "ทำเหี้ยไร", "อีดอกทอง", "อีดอก"
]

# เพิ่มรูปแบบการตรวจจับคำหยาบภาษาอังกฤษทุกคำโดยใช้ regex
bad_word_patterns = [r"\b{}\b".format(re.escape(word)) for word in bad_words]
bad_word_patterns.append(r"\b\w+\b")  # ตรวจจับคำภาษาอังกฤษทุกคำ

# คำสั่งที่ใช้ในการสร้างบอท
intents = discord.Intents.default()
intents.message_content = True  # เปิดใช้งานการเข้าถึงเนื้อหาข้อความ
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ฟังก์ชันตรวจจับข้อความไม่เหมาะสม
@bot.event
async def on_message(message):
    if message.author.bot and message.author != bot.user:
        return  # ข้ามข้อความจากบอทอื่น

    try:
        # ตรวจสอบว่าเป็นแอดมินหรือไม่ (ยศ 'Bot' หรือ 'Admin' ไม่ได้รับผลกระทบใดๆ)
        if any(role.name in ['Bot', '🔧Admin'] for role in message.author.roles):
            return

        # ตรวจจับคำหยาบ
        for pattern in bad_word_patterns:
            if re.search(pattern, message.content.lower()):
                print(f"Bad word detected: {message.content}")
                await message.delete()
                embed = discord.Embed(
                    title="⚠️ การเตือนการใช้คำหยาบ",
                    description=f"{message.author.mention} โปรดหลีกเลี่ยงการใช้คำหยาบคาย!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed, delete_after=5)
                try:
                    await message.author.send("โปรดหลีกเลี่ยงการใช้คำหยาบคายในเซิร์ฟเวอร์ของเรา.")
                except discord.Forbidden:
                    print(f"Failed to send DM to {message.author}.")
                break  # ออกจากลูปหลังจากลบข้อความแล้ว

        # ตรวจจับสแปม (ถ้าผู้ใช้ส่งข้อความเกิน 10 ข้อความในระยะเวลาสั้น ๆ)
        user_messages = [msg async for msg in message.channel.history(limit=10) if msg.author == message.author]
        if len(user_messages) >= 10:
            await message.delete()
            embed = discord.Embed(
                title="🚫 การเตือนการส่งข้อความรัว",
                description=f"{message.author.mention} กรุณาหยุดส่งข้อความรัวๆ ครับ/ค่ะ!",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed, delete_after=5)
            try:
                await message.author.send("กรุณาหยุดส่งข้อความรัวๆ ครับ/ค่ะ!")
            except discord.Forbidden:
                print(f"Failed to send DM to {message.author}.")

        # ตรวจจับภาพโป๊เปลือย (ตรวจสอบเบื้องต้นโดยใช้ชื่อไฟล์)
        if message.attachments:
            for attachment in message.attachments:
                if any(word in attachment.filename.lower() for word in ['porn', 'nude', 'sex']):
                    await message.delete()
                    embed = discord.Embed(
                        title="🚫 การเตือนการส่งภาพไม่เหมาะสม",
                        description=f"{message.author.mention} ห้ามส่งภาพโป๊เปลือย!",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed, delete_after=5)
                    try:
                        await message.author.send("คุณถูกตักเตือนเนื่องจากส่งภาพไม่เหมาะสม กรุณาปฏิบัติตามกฎของเซิร์ฟเวอร์.")
                    except discord.Forbidden:
                        print(f"Failed to send DM to {message.author}.")

    except Exception as e:
        print(f"Error: {e}")
        # ส่งข้อความถึงแอดมินเพื่อแจ้งว่าเกิดข้อผิดพลาด
        admin_channel = bot.get_channel(123456789012345678)  # ใส่ Channel ID ที่แอดมินใช้งาน
        await admin_channel.send(f"⚠️ เกิดข้อผิดพลาด: {e}")

    await bot.process_commands(message)

# ฟังก์ชันที่ทำงานเมื่อบอทพร้อมใช้งาน
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("Bot is ready!")

# ฟังก์ชันจัดการข้อผิดพลาดเพื่อกู้คืนการทำงาน
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"An error occurred in event: {event}")
    # พยายามส่งข้อความแจ้งให้แอดมินทราบ
    admin_channel = bot.get_channel(123456789012345678)  # ใส่ Channel ID ที่แอดมินใช้งาน
    await admin_channel.send(f"⚠️ เกิดข้อผิดพลาดใน event: {event}")


server_on()

# เริ่มต้นบอทด้วย Token ที่ตั้งไว้
bot.run(spam_bot_token)
