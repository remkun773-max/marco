import os
import discord
from anthropic import AsyncAnthropic

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
SYSTEM = os.getenv(
    "BOT_SYSTEM",
    "คุณคือผู้ช่วยในเซิร์ฟเวอร์ Discord ตอบเป็นภาษาเดียวกับผู้ใช้ กระชับ เป็นมิตร",
)
MAX_HISTORY = 10  # จำนวนข้อความล่าสุดที่จำต่อห้อง

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
ai = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
history = {}  # channel_id -> [{"role": ..., "content": ...}]


def chunks(text, size=1900):
    for i in range(0, len(text), size):
        yield text[i : i + size]


@client.event
async def on_ready():
    print(f"บอทออนไลน์แล้ว: {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return
    is_dm = isinstance(message.channel, discord.DMChannel)
    if not is_dm and client.user not in message.mentions:
        return  # ตอบเฉพาะตอนถูก @mention หรือแชตส่วนตัว

    text = (
        message.content.replace(f"<@{client.user.id}>", "")
        .replace(f"<@!{client.user.id}>", "")
        .strip()
    ) or "สวัสดี"

    h = history.setdefault(message.channel.id, [])
    h.append({"role": "user", "content": f"{message.author.display_name}: {text}"})
    del h[:-MAX_HISTORY]
    while h and h[0]["role"] != "user":
        h.pop(0)

    async with message.channel.typing():
        try:
            r = await ai.messages.create(
                model=MODEL, max_tokens=800, system=SYSTEM, messages=h
            )
            reply = "".join(b.text for b in r.content if b.type == "text") or "..."
        except Exception as e:
            print("error:", e)
            h.pop()
            await message.reply("ขออภัย มีข้อผิดพลาด ลองใหม่อีกครั้งนะ")
            return

    h.append({"role": "assistant", "content": reply})
    first = True
    for part in chunks(reply):
        if first:
            await message.reply(part)
            first = False
        else:
            await message.channel.send(part)


client.run(DISCORD_TOKEN)
