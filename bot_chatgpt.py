#Botสนทนาและตอบกลับ

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os
import asyncio
import random
import re
from sever import server_on

# โหลดข้อมูลจากไฟล์ .env เช่น Token และ API Key ต่าง ๆ
load_dotenv()

# ดึง Token ของบอทจาก .env
bot_token = os.getenv('DISCORD_BOT_TOKEN_CHATGPT')
openai_api_key = os.getenv('OPENAI_API_KEY')

# สร้าง OpenAI Client
client = AsyncOpenAI(api_key=openai_api_key)

# สร้างอินสแตนซ์ของบอท Discord
intents = discord.Intents.all()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Channel ID ของห้องพิเศษที่ไม่ต้องใช้คำสั่ง "!บอท"
SPECIAL_CHANNEL_ID = 1277250317670678529

# รายการของ Channel IDs ที่อนุญาตให้บอททำงาน โดยต้องใช้คำสั่ง "!บอท"
ALLOWED_CHANNEL_IDS =[
    1276815482569359362,
    1276815598432813078,
    1276816160171753532,
    1276816318913314846,
    1276816482205962240,
    1276816567107326003,
    1276816792236462111,
    1276817099704242229,
    1276817650005053541,
    1276817722868629514,
    1276817799385321473,
    1276818087122964481,
    1276818317407158370,
    1276818448231567361,
    1276818559066181663,
    1276820268345458731,
    1276820442866384998,
    1276820551360315413,
    1276820658994544702,
    1276820766666788925,
    1276820849566945395,
    1276820966562992138,
    1276821034808508427,
    1276821124315090985,
    1276821736553320458,
    1276822486817701958,
    1276822589062385765,
    1276822732000071733,
    1276822805471563846,
    1276822875378155611,
    1276822932609568851,
    1276823035554435073,
    1276823099643396176,
    1276823190748008479,
    1276823379449741333,
    1276823522030649418,
    1276823837815865365,
    1276823989993340949,
    1276824124995534913,
    1276824278372843602,
    1276825442548187157,
    1276825600358613012,
    1276825732785373237,
    1276823755779473409,
    1276823832748883980,
    1276823921928437770,
    1276824076761038869,
    1276824156947611759,
    1276824218855669826,
    1276824328629125162,
    1276824408861966419,
    1276824486737350676,
    1276826172940091463,
    1276826264015077457,
    1276826171954298931,
    1276826354087624744,
    1276826367870369865,
    1276826815125782612,
    1276826891470503956,
    1276826898529517590,
    1276826978582003722,
    1276827005953773578,
    1276827085549342730
]

# กำหนดโฟลเดอร์ที่เก็บไฟล์ PDF ตารางเรียน
PDF_FOLDER_PATH = 'ตารางเรียน'  # ตั้งค่าให้ตรงกับชื่อโฟลเดอร์ของคุณ

# ข้อความสถานะที่หลากหลาย
status_messages = [
    "น้องโกโก้กำลังคิด... 😊",
    "รอสักครู่นะคะ น้องโกโก้กำลังหาคำตอบ... 😌",
    "น้องโกโก้กำลังประมวลผล... 💭",
    "รอแป๊บนะคะ น้องโกโก้กำลังหาคำตอบให้ค่ะ... 🤗"
]

# ฟังก์ชันที่ทำงานเมื่อบอทพร้อมทำงาน
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("น้องโกโก้พร้อมใช้งานในช่องที่อนุญาตแล้วค่ะ!")

# ฟังก์ชันที่ทำงานเมื่อมีข้อความใหม่เข้ามาในช่อง
@bot.event
async def on_message(message):
    # ตรวจสอบว่าข้อความมาจากช่องพิเศษหรือไม่
    if message.channel.id == SPECIAL_CHANNEL_ID:
        command_text = message.content.strip()  # ไม่ต้องใช้คำสั่ง !บอท
    elif message.channel.id in ALLOWED_CHANNEL_IDS and message.content.startswith('!บอท'):
        command_text = message.content[len('!บอท'):].strip()  # ตัด !บอท ออก
    else:
        return

    # ตรวจสอบว่าไม่ใช่ข้อความจากบอทเอง
    if message.author == bot.user:
        return

    # ตรวจสอบคำถามเกี่ยวกับชื่อน้องโกโก้
    if re.search(r'ชื่ออะไร|น้องโกโก้|โกโก้', command_text):
        await message.channel.send("น้องโกโก้ไงคะ ชื่อของหนูคือน้องโกโก้ค่ะ 😊")
        return

    # ตรวจสอบคำขอเกี่ยวกับตารางเรียน
    print(f"Received message: {command_text}")  # Debug
    schedule_requests = re.findall(r'(ม\.\d|ปวช\.\d)/(\d+)', command_text)
    print(f"Schedule requests found: {schedule_requests}")  # Debug

    if schedule_requests:
        for grade, room in schedule_requests:
            print(f"Request received for grade: {grade}, room: {room}")  # Debug
            try:
                # ตรวจสอบความถูกต้องของชั้นปีและห้องเรียน
                valid = False
                if grade in ["ม.1", "ม.2", "ม.3"] and 1 <= int(room) <= 12:
                    valid = True
                elif grade in ["ม.4", "ม.5", "ม.6"] and 1 <= int(room) <= 7:
                    valid = True
                elif grade in ["ปวช.1", "ปวช.2", "ปวช.3"] and 1 <= int(room) <= 2:
                    valid = True

                if valid:
                    # เปลี่ยนชื่อไฟล์ให้ตรงกับรูปแบบ เช่น "ตารางเรียน_ม6_1.pdf"
                    grade_file_name = grade.replace('.', '')  # เอาจุดออกจากชื่อ เช่น ม.6 -> ม6
                    file_name = f'ตารางเรียน_{grade_file_name}_{room}.pdf'
                    pdf_path = os.path.join(PDF_FOLDER_PATH, file_name)
                    print(f"Checking file path: {pdf_path}")  # Debug

                    if os.path.isfile(pdf_path):
                        # ส่งไฟล์ PDF ไปยังช่อง
                        await message.channel.send(f"นี่คือตารางเรียนของ {grade}/{room}:", file=discord.File(pdf_path))
                        print(f"File sent: {pdf_path}")  # Debug
                    else:
                        await message.channel.send(f"ไม่พบตารางเรียนสำหรับ {grade}/{room}ค่ะ.")
                        print(f"File not found: {pdf_path}")  # Debug
                else:
                    await message.channel.send(f"ห้อง {grade}/{room} ไม่ถูกต้อง กรุณาตรวจสอบและลองใหม่อีกครั้งค่ะ.")
                    print(f"Invalid room: {grade}/{room}")  # Debug

            except Exception as e:
                await message.channel.send("เกิดข้อผิดพลาดขณะพยายามดึงข้อมูลตารางเรียน กำลังอยู่ในขั้นตอนการพัฒนา โปรดลองอีกครั้งในภายหลังค่ะ.")
                print(f"Error sending PDF: {e}")

        return

    # เลือกข้อความสถานะแบบสุ่ม
    typing_message = random.choice(status_messages)

    # ส่งข้อความแสดงสถานะการทำงาน
    typing_indicator = asyncio.create_task(message.channel.send(typing_message))

    try:
        # ส่งข้อความไปยัง OpenAI และรับการตอบกลับ
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "คุณเป็นบอทที่น่ารัก กวนๆ สุภาพและเป็นมิตรสำหรับการสนทนาใน Discord."},
                {"role": "user", "content": command_text}
            ]
        )

        reply = response.choices[0].message.content

        # ปรับให้แน่ใจว่าบอทตอบในลักษณะที่เป็นผู้หญิง
        reply = re.sub(r'ค่ะ', reply) 
        
        # ยกเลิก typing indicator ก่อนส่งข้อความ
        typing_indicator.cancel()

        # ส่งการตอบกลับไปยังช่อง
        await message.channel.send(reply)
        print(f"OpenAI response sent: {reply}")  # Debug

    except Exception as e:
        # ยกเลิก typing indicator ถ้ามีข้อผิดพลาด
        typing_indicator.cancel()
        await message.channel.send(f"ขอโทษค่ะ น้องโกโก้มีปัญหาในการตอบคำถาม: {e}")
        print(f"Error handling question from user {message.author.id}: {e}")

    # ประมวลผลคำสั่งอื่น ๆ
    await bot.process_commands(message)

# ฟังก์ชันสำหรับจัดการข้อผิดพลาด
@bot.event
async def on_error(event, *args, **kwargs):
    with open('bot_error.log', 'a', encoding='utf-8') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

# คำสั่งตรวจสอบสถานะการทำงานของบอท
@bot.command(name='check')
async def check(ctx):
    await ctx.send("น้องโกโก้ทำงานปกติค่ะ! 🌟")


server_on()

# เริ่มต้นบอทด้วย Token ที่ตั้งไว้
bot.run(bot_token)
