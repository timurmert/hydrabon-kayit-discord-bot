import os
import datetime
import pytz
import pkgutil
import importlib
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

turkey_tz = pytz.timezone("Europe/Istanbul")

load_dotenv()
TOKEN = os.getenv("TOKEN")
SERVER_BRAND = "HydRaboN" # Sunucu ismi. Bot içerisinde sunucu ismi olarak kullanılmasını istediğin isim.
COMMAND_PREFIX = "" # Sunucu içi bot prefix'i. Not: Slash komutları kullanıldığı için bu çok da önemli değil.
OWNER_ID = 315888596437696522 # Bot sahibinin ID'si. Yapımcı ya da bakımından sorumlu tepe kişinin.
STREAM_URL = "https://www.twitch.tv/mrpresidentnotsjanymore" # Bot yayında gözüküyor kısmı için bir yönlendirme linki. Twitch veya YouTube linki olabilir.

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = False  # Ses kanalı devre dışı

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# ==== EVENTS ====
@bot.event
async def on_ready():
    print("=" * 50)
    print("🌟 Discord Bot Başlatıldı")
    print(f"🤖 Bot: {bot.user} (ID: {bot.user.id})")
    print(f"⏰ Zaman: {datetime.datetime.now(turkey_tz).strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"🌐 Sunucu Sayısı: {len(bot.guilds)} | 👥 Kullanıcı: {len(bot.users)}")
    print("=" * 50)

    # Uptime bilgisi
    if not hasattr(bot, "start_time"):
        bot.start_time = datetime.datetime.now(turkey_tz)

    # Yayın olarak durum ayarı – marka/sunucu adı değişkeninden gelir
    try:
        await bot.change_presence(
            activity=discord.Streaming(
                name=f"{SERVER_BRAND}",
                url=f"{STREAM_URL}"
            )
        )
        print("🎮 Durum ayarlandı.")
    except Exception as e:
        print(f"⚠️ Durum ayarlanamadı: {e}")

    # Slash komutlarını senkronize et
    try:
        print("⚙️ Global slash komutları senkronize ediliyor...")
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} global komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Slash komut senkronizasyon hatası: {e}")

# ==== ADMIN GROUP ====
admin_group = app_commands.Group(
    name="admin",
    description="Yönetici komutları",
    default_permissions=discord.Permissions(administrator=True),
)
bot.tree.add_command(admin_group) # Sadece bu kullanıcı yönetici komutlarını çalıştırabilir

def _owner_guard(user_id: int) -> bool:
    return user_id == OWNER_ID

@admin_group.command(name="sync", description="Slash komutlarını senkronize eder")
@app_commands.default_permissions(administrator=True)
async def admin_sync(interaction: discord.Interaction):
    if not _owner_guard(interaction.user.id):
        return await interaction.response.send_message(
            "Bu komutu kullanma yetkiniz bulunmamaktadır.", ephemeral=True
        )
    try:
        await bot.tree.sync()
        await bot.tree.sync(guild=interaction.guild)
        await interaction.response.send_message("Slash komutları senkronize edildi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Komut senkronizasyonu sırasında hata: {e}", ephemeral=True)

@admin_group.command(name="load", description="Belirtilen modülü (cog) yükler")
@app_commands.default_permissions(administrator=True)
async def admin_load(interaction: discord.Interaction, extension: str):
    if not _owner_guard(interaction.user.id):
        return await interaction.response.send_message(
            "Bu komutu kullanma yetkiniz bulunmamaktadır.", ephemeral=True
        )
    try:
        await bot.load_extension(f"cogs.{extension}")
        await interaction.response.send_message(f"`{extension}` yüklendi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"`{extension}` yüklenirken hata: {e}", ephemeral=True)

@admin_group.command(name="unload", description="Belirtilen modülü (cog) kaldırır")
@app_commands.default_permissions(administrator=True)
async def admin_unload(interaction: discord.Interaction, extension: str):
    if not _owner_guard(interaction.user.id):
        return await interaction.response.send_message(
            "Bu komutu kullanma yetkiniz bulunmamaktadır.", ephemeral=True
        )
    try:
        await bot.unload_extension(f"cogs.{extension}")
        await interaction.response.send_message(f"`{extension}` kaldırıldı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"`{extension}` kaldırılırken hata: {e}", ephemeral=True)

@admin_group.command(name="reload", description="Belirtilen modülü (cog) yeniden yükler")
@app_commands.default_permissions(administrator=True)
async def admin_reload(interaction: discord.Interaction, extension: str):
    if not _owner_guard(interaction.user.id):
        return await interaction.response.send_message(
            "Bu komutu kullanma yetkiniz bulunmamaktadır.", ephemeral=True
        )
    try:
        await bot.reload_extension(f"cogs.{extension}")
        await interaction.response.send_message(f"`{extension}` yeniden yüklendi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"`{extension}` yeniden yüklenirken hata: {e}", ephemeral=True)

# ==== COG DISCOVERY ====
async def load_extensions():

    print("📦 Cog'lar yükleniyor...")
    successful, total = 0, 0
    try:
        import cogs
        for modinfo in pkgutil.iter_modules(cogs.__path__):
            name = modinfo.name
            total += 1
            ext = f"cogs.{name}"
            try:
                await bot.load_extension(ext)
                print(f"✅ {ext}")
                successful += 1
            except Exception as e:
                print(f"❌ {ext} yüklenemedi: {e}")
    except Exception as e:
        print(f"⚠️ Cog keşfi yapılamadı (cogs paketi var mı?): {e}")
    print(f"📊 Yükleme Sonucu: {successful}/{total} başarılı")

# ==== ENTRYPOINT ====
async def main():
    if not TOKEN:
        raise RuntimeError("TOKEN .env içinde tanımlı değil.")
    print("=" * 50)
    print(f"🌟 {SERVER_BRAND} Bot Başlatılıyor...")
    print(f"⏰ Başlangıç: {datetime.datetime.now(turkey_tz).strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    async with bot:
        await load_extensions()
        print("🔗 Discord'a bağlanılıyor...")
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
