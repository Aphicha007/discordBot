#botยืนยันตัวตน

import discord
from discord.ext import commands
import pandas as pd
import os
import random
from dotenv import load_dotenv
from sever import server_on

# โหลดข้อมูลจากไฟล์ .env เพื่อเก็บ Token
load_dotenv()
bot_token = os.getenv('DISCORD_BOT_TOKEN')

# ตรวจสอบว่ามีการโหลดโทเค็น
if bot_token is None:
    raise ValueError("ไม่พบโทเค็นในไฟล์ .env กรุณาตรวจสอบว่าชื่อตัวแปรในไฟล์ .env ถูกต้องและไฟล์อยู่ในไดเรกทอรีเดียวกันกับสคริปต์")

# โหลดข้อมูลจากไฟล์ Excel โดยระบุให้เลือกเฉพาะคอลัมน์ที่เกี่ยวข้อง
try:
    df = pd.read_excel('รายชื่อนักเรียนทั้งหมด.xlsx', usecols=["รหัสบัตรนักเรียน", "ชื่อ - สกุล", "ชั้น", "สถานะการลงทะเบียน", "ID 8 หลัก"])
except FileNotFoundError:
    raise FileNotFoundError("ไม่พบไฟล์ Excel กรุณาตรวจสอบชื่อไฟล์และตำแหน่งที่ตั้งของไฟล์")
except ValueError as e:
    raise ValueError(f"เกิดข้อผิดพลาดในการโหลดไฟล์ Excel: {str(e)}")

# พิมพ์ข้อมูลทั้งหมดเพื่อการตรวจสอบ
print(df)

# ตั้งค่าการทำงานของบอท
intents = discord.Intents.default()
intents.message_content = True  # เปิดใช้งาน message content intent
intents.members = True  # เปิดใช้งาน members intent
bot = commands.Bot(command_prefix="!", intents=intents)

# ฟังก์ชันที่ทำงานเมื่อบอทพร้อมใช้งาน
@bot.event
async def on_ready():
    try:
        print(f"Logged in as {bot.user} in {bot.guilds[0].name}")
        
        # ดึงข้อมูล Channel ID ของช่องที่ต้องการให้บอทส่งข้อความ
        channel = bot.get_channel(1276825799441387583)  # แทนที่ด้วย Channel ID ที่ถูกต้อง
        if channel is not None:
            # ส่งข้อความไปยังช่องที่กำหนดพร้อมกับปุ่มยืนยันตัวตน
            await channel.send("กดปุ่มด้านล่างเพื่อยืนยันตัวตน:", view=VerifyButton())
            print(f"Message sent to channel: {channel.name}")
        else:
            # ถ้าไม่พบช่องที่กำหนด ให้พิมพ์ข้อความแจ้งเตือนในคอนโซล
            print("ไม่พบช่องที่กำหนด ตรวจสอบ Channel ID")
    except IndexError:
        print("ไม่พบ Guild หรือ Channel ในเซิร์ฟเวอร์ กรุณาตรวจสอบว่าบอทได้เข้าร่วมเซิร์ฟเวอร์แล้ว")
    except Exception as e:
        print(f"Error in on_ready: {str(e)}")

# ฟังก์ชันที่ทำงานเมื่อมีสมาชิกใหม่เข้ามาในเซิร์ฟเวอร์
@bot.event
async def on_member_join(member):
    try:
        # ตรวจสอบว่าผู้ใช้ได้ลงทะเบียนแล้วหรือไม่
        student = df[df['ชื่อ - สกุล'].str.contains(member.display_name)]
        
        if student.empty or not student.iloc[0]['สถานะการลงทะเบียน']:
            # ส่งข้อความแจ้งเตือนผู้ใช้งานใหม่พร้อมกับปุ่มยืนยันตัวตน
            channel = bot.get_channel(1276825799441387583)  # แทนที่ด้วย Channel ID ที่ถูกต้อง
            if channel is not None:
                await channel.send(f"{member.mention} กรุณายืนยันตัวตนโดยการกดปุ่มด้านล่าง:", view=VerifyButton())
                print(f"Verification prompt sent to {member.display_name}")
    except Exception as e:
        print(f"Error in on_member_join: {str(e)}")

# สร้างคลาส VerificationModal สำหรับการสร้างฟอร์มยืนยันตัวตน
class VerificationModal(discord.ui.Modal, title="ยืนยันตัวตนสำหรับนักเรียนสะเดาขรรค์ชัย"):
    name = discord.ui.TextInput(
        label="ชื่อ - สกุล", 
        placeholder="กรอกชื่อของคุณ (ตัวอย่าง: นายปิกาจู ใส่ไข่ดาว, นางสาวไหมพรหม พงศ์พิทัก)"
    )
    student_id = discord.ui.TextInput(
        label="รหัสบัตรนักเรียน", 
        placeholder="กรอกรหัสนักเรียน (ตัวอย่าง: 65-00000)"
    )

    def generate_id(self):
        existing_ids = df['ID 8 หลัก'].dropna().astype(str).tolist()  # เอาเฉพาะ ID ที่มีอยู่แล้วในไฟล์ Excel
        while True:
            new_id = str(random.randint(10000000, 99999999))  # สร้าง ID 8 หลักแบบสุ่ม
            if new_id not in existing_ids:  # ตรวจสอบว่า ID ไม่ซ้ำ
                return new_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            name = self.name.value.strip()  # ลบช่องว่างที่ต้นและท้าย
            student_id = self.student_id.value.strip()  # ลบช่องว่างที่ต้นและท้าย

            print(f"Name input: {name}")  # พิมพ์ชื่อที่กรอกมา
            print(f"Student ID input: {student_id}")  # พิมพ์รหัสที่กรอกมา

            # ค้นหาชื่อและรหัสที่ตรงกันในไฟล์ Excel
            student = df[(df['ชื่อ - สกุล'].str.strip() == name) & (df['รหัสบัตรนักเรียน'].str.strip() == student_id)]
            
            if not student.empty:
                if student.iloc[0]['สถานะการลงทะเบียน']:
                    await interaction.response.send_message("คุณได้ลงทะเบียนไปแล้ว ไม่สามารถลงทะเบียนซ้ำได้", ephemeral=True)
                else:
                    class_section = student.iloc[0]['ชั้น']
                    role = discord.utils.get(interaction.guild.roles, name=class_section)
                    student_role = discord.utils.get(interaction.guild.roles, name="🎓 Student")  # ค้นหา role "🎓 Student"
                    new_id = self.generate_id()  # สร้าง ID 8 หลักใหม่
                    print(f"Role found: {role.name if role else 'None'}")  # พิมพ์บทบาทที่พบ

                    if role and student_role:
                        member = interaction.user
                        await member.add_roles(role)  # เพิ่มบทบาทตามชั้นเรียน
                        await member.add_roles(student_role)  # เพิ่มบทบาท "🎓 Student"
                        df.loc[(df['ชื่อ - สกุล'].str.strip() == name) & (df['รหัสบัตรนักเรียน'].str.strip() == student_id), ['สถานะการลงทะเบียน', 'ID 8 หลัก']] = [True, new_id]
                        df.to_excel('รายชื่อนักเรียนทั้งหมด.xlsx', index=False)
                        await interaction.response.send_message(f"ยืนยันสำเร็จ! คุณได้รับบทบาท {class_section} และ 🎓 Student พร้อม ID: {new_id} ห้ามเผยแพร่ให้ใครรู้นะจุ๊ๆๆ", ephemeral=True)
                    else:
                        await interaction.response.send_message("ไม่พบบทบาทที่ตรงกับข้อมูลของคุณ", ephemeral=True)
            else:
                print("Student not found in Excel")  # ถ้าไม่พบชื่อหรือรหัสในไฟล์ Excel
                await interaction.response.send_message("ข้อมูลไม่ถูกต้อง กรุณาลองใหม่", ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)
            print(f"Error in on_submit: {str(e)}")
        finally:
            # ลบปุ่มหลังจากทำการยืนยันเสร็จ
            await interaction.message.edit(view=None)

# ฟังก์ชันตรวจสอบ ID 8 หลัก ของผู้ใช้งานที่ถูกแท็ก
@bot.command(name='เช็คid')
@commands.has_role('🔧Admin')
async def check_id(ctx, member: discord.Member):
    try:
        # ค้นหาข้อมูลของสมาชิกที่ได้รับการแท็ก โดยใช้ชื่อของสมาชิกที่ถูกแท็ก
        student = df[df['ชื่อ - สกุล'].str.contains(member.display_name)]
        
        if not student.empty:
            student_id_8_digits = student.iloc[0]['ID 8 หลัก']
            await ctx.send(f"ID 8 หลักของผู้ใช้ {member.mention} คือ: {student_id_8_digits}", delete_after=10)  # ข้อความจะหายไปหลัง 10 วินาที
        else:
            await ctx.send("ไม่พบข้อมูลที่ตรงกับผู้ใช้ที่ระบุ กรุณาตรวจสอบและลองอีกครั้ง", delete_after=10)
    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {str(e)}", delete_after=10)
        print(f"Error in check_id: {str(e)}")

# ฟังก์ชันตรวจสอบ ID 8 หลัก โดยเฉพาะบทบาท 🔧Admin เท่านั้นที่ใช้ได้
@bot.command(name='ตรวจสอบID')
@commands.has_role('🔧Admin')
async def check_id_by_8_digits(ctx, student_id: str):
    try:
        # ค้นหา ID 8 หลักที่ตรงกันในไฟล์ Excel
        student = df[df['ID 8 หลัก'].astype(str) == student_id]
        
        if not student.empty:
            name = student.iloc[0]['ชื่อ - สกุล']
            student_card_id = student.iloc[0]['รหัสบัตรนักเรียน']
            class_section = student.iloc[0]['ชั้น']
            await ctx.send(f"พบข้อมูล: \nชื่อ - สกุล: {name}\nรหัสบัตรนักเรียน: {student_card_id}\nชั้น: {class_section}", delete_after=10)  # ข้อความจะหายไปหลัง 10 วินาที
        else:
            await ctx.send("ไม่พบข้อมูลที่ตรงกับ ID 8 หลักที่ให้มา กรุณาตรวจสอบและลองอีกครั้ง", delete_after=10)
    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {str(e)}", delete_after=10)
        print(f"Error in check_id_by_8_digits: {str(e)}")

# ฟังก์ชันสำหรับการเริ่มกระบวนการยืนยันตัวตนด้วยคำสั่ง !ยืนยัน
@bot.command(name='ยืนยัน')
async def verify_command(ctx):
    try:
        # ส่งฟอร์มยืนยันตัวตน (Verification Modal) ให้กับผู้ใช้งานที่เรียกใช้คำสั่ง
        modal = VerificationModal()
        await ctx.send("กรุณากรอกข้อมูลเพื่อยืนยันตัวตน:", view=VerifyButton())
        await ctx.author.send_modal(modal)
    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {str(e)}")
        print(f"Error in verify_command: {str(e)}")

# สร้างคลาสใหม่สำหรับปุ่มยืนยันตัวตนและปุ่มผู้เข้าร่วม
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="ยืนยันตัวตนสำหรับนักเรียนสะเดาขรรค์ชัย", style=discord.ButtonStyle.primary)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("Verify Button clicked")
        modal = VerificationModal()  # สร้าง modal สำหรับการยืนยันตัวตน
        await interaction.response.send_modal(modal)  # ใช้ interaction ในการส่ง modal


    @discord.ui.button(label="🔅ผู้เข้าร่วม", style=discord.ButtonStyle.secondary)
    async def participant_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("Participant Button clicked")
        try:
            participant_role = discord.utils.get(interaction.guild.roles, name="🔅ผู้เข้าร่วม")  # ค้นหา role "🔅ผู้เข้าร่วม"
            if participant_role:
                member = interaction.user
                await member.add_roles(participant_role)  # เพิ่มบทบาท "🔅ผู้เข้าร่วม"
                await interaction.response.send_message(f"ยืนยันสำเร็จ! คุณได้รับบทบาท 🔅ผู้เข้าร่วม", ephemeral=True)
            else:
                await interaction.response.send_message("ไม่พบบทบาทที่ตรงกับข้อมูลของคุณ", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)
            print(f"Error in participant_button: {str(e)}")
        finally:
            # ลบปุ่มหลังจากที่ได้มอบบทบาทแล้ว
            await interaction.message.edit(view=None)

server_on()

# รันบอทด้วยโทเค็นที่ได้รับจาก .env
bot.run(bot_token)
