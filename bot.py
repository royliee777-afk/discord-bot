import discord
from discord.ext import commands
from discord import app_commands
import os, json, re, ast, operator, unicodedata, random
from datetime import date, timedelta
from dotenv import load_dotenv
from keep_alive import keep_alive

# ================= ENV =================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ================= CONFIG =================
STREAK_CHANNEL = "‧₊˚✧daily-streak✧˚₊‧"
LOG_THREAD_NAME = "Log pelanggaran"
DATA_FILE = "streak.json"
MOD_ROLE_NAME = "Mod"

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA =================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"users": {}, "message_id": None}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= MATEMATIKA =================
OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def hitung(expr):
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return OPS[type(node.op)](_eval(node.operand))
        raise ValueError
    return _eval(ast.parse(expr, mode="eval").body)

# ================= KATA KASAR =================
KATA_KASAR = [
    "kontol","anjing","bangsat","memek","asu",
    "ngentot","jancok","peler"
]

def normalize(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z]", "", t)

def ada_kasar(text):
    n = normalize(text)
    return any(k in n for k in KATA_KASAR)

# ================= DAILY STREAK (SORTED) =================
def build_streak_text(guild):
    users = []

    for m in guild.members:
        if m.bot or m.id == OWNER_ID:
            continue

        uid = str(m.id)
        user_data = data["users"].get(uid, {"streak": 0})
        users.append((m.display_name, user_data["streak"]))

    # 🔥 URUTKAN DARI STREAK TERBESAR
    users.sort(key=lambda x: x[1], reverse=True)

    lines = ["**Daily Streak 🔥**"]
    for name, streak in users:
        lines.append(f"{name}:{streak}")

    return "\n".join(lines)

async def update_streak(guild):
    channel = discord.utils.get(guild.text_channels, name=STREAK_CHANNEL)
    if not channel:
        return

    text = build_streak_text(guild)

    try:
        if data.get("message_id"):
            msg = await channel.fetch_message(data["message_id"])
            await msg.edit(content=text)
            return
    except:
        pass

    msg = await channel.send(text)
    data["message_id"] = msg.id
    save()

# ================= EVENTS =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"ONLINE: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild = message.guild
    uid = str(message.author.id)

    # ===== KATA KASAR =====
    if ada_kasar(message.content):
        await message.delete()
        if message.author.id != OWNER_ID:
            until = discord.utils.utcnow() + timedelta(minutes=2, seconds=30)
            await message.author.timeout(until)

            thread = discord.utils.get(message.channel.threads, name=LOG_THREAD_NAME)
            if not thread:
                thread = await message.channel.create_thread(
                    name=LOG_THREAD_NAME,
                    type=discord.ChannelType.public_thread
                )

            await thread.send(
                f"{message.author.display_name} timeout 2 menit 30 detik (kata kasar)"
            )
        return

    # ===== MATEMATIKA =====
    if message.content.lower().startswith("bro "):
        soal = message.content[4:].strip()

        if not re.fullmatch(r"[0-9+\-*/(). %*]+", soal):
            await message.channel.send("Bro, gua ga ngerti itu 😅")
            return

        try:
            await message.channel.send(
                f"Bro, jawabannya {hitung(soal)} 😎"
            )
        except:
            await message.channel.send("Bro, gua ga ngerti itu 😅")
        return

    # ===== DAILY STREAK =====
    if message.author.id == OWNER_ID:
        return

    today = str(date.today())
    data["users"].setdefault(uid, {"streak": 0, "last_date": None})

    if data["users"][uid]["last_date"] == today:
        return

    data["users"][uid]["streak"] += 1
    data["users"][uid]["last_date"] = today
    save()

    await message.channel.send(
        f"Hai {message.author.display_name}, streak kamu sekarang {data['users'][uid]['streak']} 🔥"
    )

    await update_streak(guild)

# ================= SLASH COMMAND =================
@bot.tree.command(name="jokes")
async def jokes(interaction: discord.Interaction):
    S = ["Bapak","Wi wok de tok","Reynard","Ayah","Kevin","Nathan"]
    P = ["kehilangan","mencari","mukul","menjual","melihat"]
    O = ["remote","sendal","kunci","motor","HP"]
    K = [
        "karena kebanyakan mikir",
        "karena kurang tidur",
        "karena kebanyakan kopi",
        "karena lupa hari"
    ]
    emoji = ["😂","🤣","😆","🔥","💀"]

    await interaction.response.send_message(
        f"{random.choice(S)} {random.choice(P)} {random.choice(O)} {random.choice(K)} {random.choice(emoji)}"
    )

@bot.tree.command(name="tambah_streak")
async def tambah_streak(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌", ephemeral=True)

    uid = str(member.id)
    data["users"].setdefault(uid, {"streak": 0, "last_date": None})
    data["users"][uid]["streak"] += 1
    save()
    await update_streak(interaction.guild)
    await interaction.response.send_message("✅ Streak ditambah")

@bot.tree.command(name="kurang_streak")
async def kurang_streak(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌", ephemeral=True)

    uid = str(member.id)
    if uid in data["users"] and data["users"][uid]["streak"] > 0:
        data["users"][uid]["streak"] -= 1
        save()

    await update_streak(interaction.guild)
    await interaction.response.send_message("✅ Streak dikurang")

@bot.tree.command(name="timeout")
async def timeout(interaction: discord.Interaction, member: discord.Member, menit: int, detik: int, alasan: str):
    is_owner = interaction.user.id == OWNER_ID
    is_mod = any(r.name == MOD_ROLE_NAME for r in interaction.user.roles)

    if not is_owner and not is_mod:
        return await interaction.response.send_message("❌", ephemeral=True)

    until = discord.utils.utcnow() + timedelta(minutes=menit, seconds=detik)
    await member.timeout(until)

    await interaction.response.send_message(
        f"{member.display_name} Timeout: {menit} menit {detik} detik\nAlasan: {alasan}"
    )

@bot.tree.command(name="hapus_timeout")
async def hapus_timeout(interaction: discord.Interaction, member: discord.Member):
    is_owner = interaction.user.id == OWNER_ID
    is_mod = any(r.name == MOD_ROLE_NAME for r in interaction.user.roles)

    if not is_owner and not is_mod:
        return await interaction.response.send_message("❌", ephemeral=True)

    await member.timeout(None)
    await interaction.response.send_message("✅ Timeout dihapus")

# ================= RUN =================
keep_alive()
bot.run(TOKEN)
