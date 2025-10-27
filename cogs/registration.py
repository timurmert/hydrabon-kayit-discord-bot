import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import re
from typing import Optional

# ============ GLOBAL AYARLAR ============
# Rol ID'leri
UNREGISTERED_ROLE_ID = 1428496119213588521  # Kayıtsız üye rolü
REGISTERED_ROLE_ID = 1029089740022095973    # Kayıtlı üye rolü
NITRO_BOOSTER_ROLE_ID = 1030490914411511869  # Nitro Booster rolü (korunur)

# Kanal ID'leri
LOG_CHANNEL_ID = 1431398643273039934         # Genel log kanalı
TICKET_LOG_CHANNEL_ID = 1364306112022839436  # Ticket transcript log kanalı
TICKET_CATEGORY_ID = 1364301691637338132     # Ticket kategorisi
REQUIRED_VOICE_CHANNEL_ID = 1428811752232976566  # Kayıt için gerekli ses kanalı

# =========================================

# Türkçe karakter normalleştirme
def normalize_turkish(text: str) -> str:
    """Türkçe karakterleri normalize eder (küçük harf)"""
    tr_map = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")
    return text.translate(tr_map).lower()

def turkish_title_case(text: str) -> str:
    """Türkçe karakterlere uygun şekilde her kelimenin baş harfini büyütür"""
    # Türkçe karakter dönüşüm haritaları
    lower_map = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")
    upper_map = str.maketrans("iığüşöç", "İIĞÜŞÖÇ")
    
    words = text.split()
    result_words = []
    
    for word in words:
        if len(word) > 0:
            # İlk karakteri büyük harfe çevir (Türkçe uyumlu)
            first_char = word[0].translate(upper_map).upper()
            # Geri kalan karakterleri küçük harfe çevir (Türkçe uyumlu)
            rest_chars = word[1:].translate(lower_map).lower()
            result_words.append(first_char + rest_chars)
    
    return " ".join(result_words)

class RegistrationModal(discord.ui.Modal, title="Kayıt Formu"):
    """Kayıt için modal (pop-up) formu"""
    
    name_input = discord.ui.TextInput(
        label="İsim",
        placeholder="Lütfen gerçek isminizi giriniz",
        min_length=2,
        max_length=50,
        required=True,
        style=discord.TextStyle.short
    )
    
    age_input = discord.ui.TextInput(
        label="Yaş",
        placeholder="Yaşınızı giriniz (13-99)",
        min_length=2,
        max_length=2,
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        """Modal submit edildiğinde çalışır"""
        await interaction.response.defer(ephemeral=True)
        
        name = self.name_input.value.strip()
        age_str = self.age_input.value.strip()
        
        # Yaş kontrolü
        try:
            age = int(age_str)
            if age < 13 or age > 99:
                return await interaction.followup.send(
                    "❌ Yaş 13-99 arasında olmalıdır!",
                    ephemeral=True
                )
        except ValueError:
            return await interaction.followup.send(
                "❌ Lütfen geçerli bir yaş giriniz!",
                ephemeral=True
            )
        
        # İsim formatı kontrolü (sadece harf ve boşluk)
        if not re.match(r'^[a-zA-ZğüşöçıİĞÜŞÖÇ\s]+$', name):
            return await interaction.followup.send(
                "❌ İsim sadece harflerden oluşmalıdır!",
                ephemeral=True
            )
        
        # İsim veritabanında var mı kontrol et
        name_valid = await self.check_name_in_database(name)
        
        if not name_valid:
            return await interaction.followup.send(
                "❌ Lütfen geçerli bir isim giriniz!",
                ephemeral=True
            )
        
        # Bilgiler doğru - Yaş görünürlüğü sorusu göster
        member = interaction.user
        formatted_name = turkish_title_case(name)
        
        embed = discord.Embed(
            title="👁️ Yaş Görünürlüğü Ayarı",
            description=(
                f"**Kayıt bilgileriniz doğrulandı!**\n\n"
                f"**İsim:** {formatted_name}\n"
                f"**Yaş:** {age}\n\n"
                "🎭 **Kullanıcı adınızda yaşınız görünsün mü?**\n\n"
                "• **Yaşımı Göster:** İsminiz `" + f"{formatted_name} | {age}" + "` şeklinde görünür\n"
                "• **Yaşımı Gizle:** İsminiz sadece `" + f"{formatted_name}" + "` şeklinde görünür\n\n"
                "💡 *Bu ayarı daha sonra /kayit-ayarlari komutuyla değiştirebilirsiniz.*"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Lütfen aşağıdaki butonlardan birini seçiniz")
        
        view = AgeVisibilityView(self.bot, member, name, age)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    async def check_name_in_database(self, name: str) -> bool:
        """İsmin veritabanında olup olmadığını kontrol eder"""
        try:
            normalized = normalize_turkish(name)
            
            # Birleşik isimler için kontrol (örn: "Ahmet Mehmet")
            name_parts = normalized.split()
            
            async with aiosqlite.connect("names.db") as db:
                # Her isim parçasını kontrol et
                for part in name_parts:
                    cursor = await db.execute(
                        "SELECT 1 FROM names WHERE name_norm_tr = ? LIMIT 1",
                        (part,)
                    )
                    result = await cursor.fetchone()
                    
                    # Eğer herhangi bir parça bulunamazsa False döndür
                    if result is None:
                        return False
            
            # Tüm parçalar bulunduysa True döndür
            return True
        except Exception as e:
            print(f"[HATA] Veritabanı kontrol hatası: {type(e).__name__}: {e}")
            # Hata durumunda güvenlik için False döndür
            return False
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Modal hata durumunda"""
        print(f"[HATA] Modal hatası: {type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu. Lütfen tekrar deneyiniz.",
                ephemeral=True
            )
        except:
            # Eğer followup da gönderilemezse
            print("[HATA] Kullanıcıya hata mesajı gönderilemedi!")


class TicketCloseConfirmView(discord.ui.View):
    """Ticket kapatma onay view"""
    
    def __init__(self):
        super().__init__(timeout=30)  # 30 saniye timeout
    
    @discord.ui.button(label="Evet, Kapat", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kapatma onaylandı"""
        await interaction.response.defer()
        
        try:
            channel = interaction.channel
            guild = interaction.guild
            
            # Türkiye saat dilimi
            import pytz
            turkey_tz = pytz.timezone("Europe/Istanbul")
            
            # Kanal mesajlarını topla (transcript)
            messages = []
            async for message in channel.history(limit=100, oldest_first=True):
                # UTC'den Türkiye saatine çevir
                timestamp_utc = message.created_at
                timestamp_turkey = timestamp_utc.astimezone(turkey_tz)
                timestamp = timestamp_turkey.strftime("%d.%m.%Y %H:%M:%S")
                content = message.content if message.content else "*[Embed veya Dosya]*"
                messages.append(f"[{timestamp}] {message.author}: {content}")
            
            # Transcript'i oluştur
            transcript = "\n".join(messages)
            
            # Ticket log kanalına gönder
            log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
            if log_channel:
                # Log embed'i
                log_embed = discord.Embed(
                    title="🔒 Destek Ticket'ı Kapatıldı",
                    description=f"**#{channel.name}** ticket'ı kapatıldı.",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                log_embed.add_field(
                    name="📊 Ticket Bilgileri",
                    value=f"**Kanal:** {channel.name}\n**Kanal ID:** `{channel.id}`\n**Mesaj Sayısı:** {len(messages)}",
                    inline=False
                )
                log_embed.add_field(
                    name="👤 İşlem Yapan",
                    value=f"**Yetkili:** {interaction.user.mention}\n**Tag:** {interaction.user}",
                    inline=False
                )
                log_embed.set_footer(text="HydRaboN Ticket Sistemi", icon_url=guild.icon.url if guild.icon else None)
                
                # Transcript dosya olarak ekle
                if transcript:
                    import io
                    transcript_file = discord.File(
                        io.BytesIO(transcript.encode('utf-8')),
                        filename=f"ticket-{channel.name}-transcript.txt"
                    )
                    await log_channel.send(embed=log_embed, file=transcript_file)
                else:
                    await log_channel.send(embed=log_embed)
            else:
                print(f"[HATA] Ticket log kanalı bulunamadı! Kanal ID: {TICKET_LOG_CHANNEL_ID}")
            
            # Kapatılıyor mesajı
            closing_embed = discord.Embed(
                title="🔒 Ticket Kapatılıyor",
                description="Bu kanal 5 saniye içinde silinecek...",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=closing_embed)
            
            # 5 saniye bekle
            import asyncio
            await asyncio.sleep(5)
            
            # Kanalı sil
            await channel.delete(reason=f"Ticket kapatıldı - {interaction.user}")
            
        except discord.Forbidden:
            print(f"[HATA] Ticket kapatma yetkisi yok!")
            await interaction.followup.send(
                "❌ Kanalı silme yetkim yok!",
                ephemeral=True
            )
        except Exception as e:
            print(f"[HATA] Ticket kapatılırken hata: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Ticket kapatılırken bir hata oluştu.",
                ephemeral=True
            )
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kapatma iptal edildi"""
        await interaction.response.send_message(
            "✅ Ticket kapatma işlemi iptal edildi.",
            ephemeral=True
        )
        self.stop()


class TicketControlView(discord.ui.View):
    """Ticket kontrol butonları"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Kalıcı buton
    
    @discord.ui.button(
        label="Ticket'ı Kapat",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ticket kapatma butonu"""
        try:
            # Yönetici kontrolü
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(
                    "❌ Bu işlem için yönetici yetkisi gereklidir!",
                    ephemeral=True
                )
            
            # Onay mesajı
            embed = discord.Embed(
                title="⚠️ Ticket Kapatma Onayı",
                description=(
                    "Bu ticket'ı kapatmak istediğinize emin misiniz?\n\n"
                    "• Tüm mesajlar log kanalına kaydedilecek\n"
                    "• Kanal 5 saniye içinde silinecek\n"
                    "• Bu işlem geri alınamaz!"
                ),
                color=discord.Color.orange()
            )
            
            view = TicketCloseConfirmView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"[HATA] Ticket kapatma butonu hatası: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya ticket kapatma hatası mesajı gönderilemedi!")


class SupportTicketModal(discord.ui.Modal, title="Destek Talebi"):
    """Yetkili çağırma için modal"""
    
    name_input = discord.ui.TextInput(
        label="İsim",
        placeholder="İsminizi giriniz",
        min_length=2,
        max_length=50,
        required=True,
        style=discord.TextStyle.short
    )
    
    age_input = discord.ui.TextInput(
        label="Yaş",
        placeholder="Yaşınızı giriniz",
        min_length=1,
        max_length=2,
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        """Modal submit edildiğinde ticket oluştur"""
        await interaction.response.defer(ephemeral=True)
        
        name = self.name_input.value.strip()
        age_str = self.age_input.value.strip()
        
        try:
            # Kategoriyi al
            category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                print(f"[HATA] Ticket kategorisi bulunamadı! Kategori ID: {TICKET_CATEGORY_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası: Ticket kategorisi bulunamadı. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # Ticket kanalı adı
            ticket_name = f"kayıt-{interaction.user.name}-{interaction.user.discriminator}"
            
            # Sadece kullanıcı ve yöneticiler görebilsin
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True
                )
            }
            
            # Ticket kanalı oluştur
            ticket_channel = await category.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                reason=f"Kayıt destek talebi - {interaction.user}"
            )
            
            # Ticket bilgi embed'i
            embed = discord.Embed(
                title="🎫 Kayıt Destek Talebi",
                description=(
                    f"**Kullanıcı:** {interaction.user.mention}\n"
                    f"**Kullanıcı ID:** {interaction.user.id}\n"
                    f"**İsim:** {name}\n"
                    f"**Yaş:** {age_str}\n\n"
                    "Yetkililere bildirim gönderildi. Lütfen bekleyin."
                ),
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Kayıt Destek Sistemi")
            embed.timestamp = discord.utils.utcnow()
            
            # Ticket kontrol view'ı ile gönder
            view = TicketControlView()
            await ticket_channel.send(
                content=f"{interaction.user.mention}",
                embed=embed,
                view=view
            )
            
            # Kullanıcıya başarı mesajı
            await interaction.followup.send(
                f"✅ Destek talebiniz oluşturuldu! {ticket_channel.mention} kanalını kontrol edin.",
                ephemeral=True
            )
            
            # Genel log kanalına bildirim gönder
            try:
                log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🎫 Yeni Destek Ticket'ı Oluşturuldu",
                        description=f"{interaction.user.mention} yeni bir destek talebi oluşturdu.",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(
                        name="👤 Kullanıcı Bilgileri",
                        value=f"**Kullanıcı:** {interaction.user.mention}\n**ID:** `{interaction.user.id}`\n**Tag:** {interaction.user}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="📋 Ticket Bilgileri",
                        value=f"**Kanal:** {ticket_channel.mention}\n**İsim:** {name}\n**Yaş:** {age_str}",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Destek Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Genel log kanalına ticket oluşturma mesajı gönderilirken hata: {type(e).__name__}: {e}")
            
        except discord.Forbidden:
            print(f"[HATA] Ticket kanalı oluşturma yetkisi yok!")
            await interaction.followup.send(
                "❌ Ticket kanalı oluşturma yetkim yok. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
        except Exception as e:
            print(f"[HATA] Ticket oluşturulurken hata: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Ticket oluşturulurken bir hata oluştu. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Modal hata durumunda"""
        print(f"[HATA] Ticket modal hatası: {type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu. Lütfen tekrar deneyiniz.",
                ephemeral=True
            )
        except:
            print("[HATA] Kullanıcıya ticket modal hatası mesajı gönderilemedi!")


class AgeResetTicketModal(discord.ui.Modal, title="Yaş Sıfırlama Talebi"):
    """Yaş sıfırlama için ticket modal"""
    
    reason_input = discord.ui.TextInput(
        label="Sebep",
        placeholder="Yaşınızı neden sıfırlamak istiyorsunuz?",
        min_length=10,
        max_length=500,
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    new_age_input = discord.ui.TextInput(
        label="Yeni Yaş (Opsiyonel)",
        placeholder="Eğer biliyorsanız doğru yaşınızı giriniz",
        min_length=0,
        max_length=2,
        required=False,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot: commands.Bot, current_name: str, current_age: int):
        super().__init__()
        self.bot = bot
        self.current_name = current_name
        self.current_age = current_age
    
    async def on_submit(self, interaction: discord.Interaction):
        """Modal submit edildiğinde ticket oluştur"""
        await interaction.response.defer(ephemeral=True)
        
        reason = self.reason_input.value.strip()
        new_age = self.new_age_input.value.strip()
        
        try:
            # Kategoriyi al
            category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                print(f"[HATA] Ticket kategorisi bulunamadı! Kategori ID: {TICKET_CATEGORY_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası: Ticket kategorisi bulunamadı. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # Ticket kanalı adı
            ticket_name = f"yaş-sıfırlama-{interaction.user.name}-{interaction.user.discriminator}"
            
            # Sadece kullanıcı ve yöneticiler görebilsin
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True
                )
            }
            
            # Ticket kanalı oluştur
            ticket_channel = await category.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                reason=f"Yaş sıfırlama talebi - {interaction.user}"
            )
            
            # Ticket bilgi embed'i
            embed = discord.Embed(
                title="🔄 Yaş Sıfırlama Talebi",
                description=(
                    f"**Kullanıcı:** {interaction.user.mention}\n"
                    f"**Kullanıcı ID:** {interaction.user.id}\n\n"
                    f"**Mevcut İsim:** {self.current_name}\n"
                    f"**Mevcut Yaş:** {self.current_age}\n"
                    f"**Talep Edilen Yeni Yaş:** {new_age if new_age else 'Belirtilmedi'}\n\n"
                    f"**Sebep:**\n{reason}\n\n"
                    "Yetkililere bildirim gönderildi. Lütfen bekleyin."
                ),
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Yaş Sıfırlama Sistemi")
            embed.timestamp = discord.utils.utcnow()
            
            # Ticket kontrol view'ı ile gönder
            view = TicketControlView()
            await ticket_channel.send(
                content=f"{interaction.user.mention}",
                embed=embed,
                view=view
            )
            
            # Kullanıcıya başarı mesajı
            await interaction.followup.send(
                f"✅ Yaş sıfırlama talebiniz oluşturuldu! {ticket_channel.mention} kanalını kontrol edin.",
                ephemeral=True
            )
            
            # Genel log kanalına bildirim gönder
            try:
                log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🔄 Yeni Yaş Sıfırlama Ticket'ı Oluşturuldu",
                        description=f"{interaction.user.mention} yaş sıfırlama talebi oluşturdu.",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(
                        name="👤 Kullanıcı Bilgileri",
                        value=f"**Kullanıcı:** {interaction.user.mention}\n**ID:** `{interaction.user.id}`\n**Tag:** {interaction.user}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="📋 Ticket Bilgileri",
                        value=f"**Kanal:** {ticket_channel.mention}\n**Mevcut Yaş:** {self.current_age}\n**Talep Edilen Yaş:** {new_age if new_age else 'Belirtilmedi'}",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Yaş Sıfırlama Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Genel log kanalına yaş sıfırlama ticket mesajı gönderilirken hata: {type(e).__name__}: {e}")
            
        except discord.Forbidden:
            print(f"[HATA] Ticket kanalı oluşturma yetkisi yok!")
            await interaction.followup.send(
                "❌ Ticket kanalı oluşturma yetkim yok. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
        except Exception as e:
            print(f"[HATA] Yaş sıfırlama ticket'ı oluşturulurken hata: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Ticket oluşturulurken bir hata oluştu. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Modal hata durumunda"""
        print(f"[HATA] Yaş sıfırlama modal hatası: {type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu. Lütfen tekrar deneyiniz.",
                ephemeral=True
            )
        except:
            print("[HATA] Kullanıcıya yaş sıfırlama modal hatası mesajı gönderilemedi!")


class AgeResetConfirmView(discord.ui.View):
    """Yaş sıfırlama onay view"""
    
    def __init__(self, bot: commands.Bot, current_name: str, current_age: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.current_name = current_name
        self.current_age = current_age
    
    @discord.ui.button(label="Evet, Ticket Aç", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaş sıfırlama ticket'ı açmayı onayla"""
        try:
            modal = AgeResetTicketModal(self.bot, self.current_name, self.current_age)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[HATA] Yaş sıfırlama modal açılırken hata: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Form açılırken bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya modal açma hatası mesajı gönderilemedi!")
    
    @discord.ui.button(label="Hayır, İptal Et", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaş sıfırlama iptal edildi"""
        await interaction.response.send_message(
            "✅ Yaş sıfırlama işlemi iptal edildi.",
            ephemeral=True
        )
        self.stop()


class AgeVisibilityView(discord.ui.View):
    """Yaş görünürlüğü seçim butonu"""
    
    def __init__(self, bot: commands.Bot, member: discord.Member, name: str, age: int):
        super().__init__(timeout=60)  # 60 saniye timeout
        self.bot = bot
        self.member = member
        self.name = name
        self.age = age
        self.show_age = None  # Kullanıcının seçimi
    
    @discord.ui.button(label="Yaşımı Göster", style=discord.ButtonStyle.success, emoji="✅")
    async def show_age_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaşı göster butonuna basıldığında"""
        self.show_age = True
        await self.complete_registration(interaction)
    
    @discord.ui.button(label="Yaşımı Gizle", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def hide_age_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaşı gizle butonuna basıldığında"""
        self.show_age = False
        await self.complete_registration(interaction)
    
    async def complete_registration(self, interaction: discord.Interaction):
        """Kayıt işlemini tamamla"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = interaction.guild
            
            # İsmi formatla
            formatted_name = turkish_title_case(self.name)
            
            # Nickname'i ayarla (yaş görünürlüğüne göre)
            if self.show_age:
                new_nickname = f"{formatted_name} | {self.age}"
            else:
                new_nickname = formatted_name
            
            # Rolleri al
            unregistered_role = guild.get_role(UNREGISTERED_ROLE_ID)
            registered_role = guild.get_role(REGISTERED_ROLE_ID)
            
            if not registered_role:
                print(f"[HATA] Kayıtlı rolü bulunamadı! Rol ID: {REGISTERED_ROLE_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası oluştu. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # Kayıtsız rolünü kaldır
            try:
                if unregistered_role and unregistered_role in self.member.roles:
                    await self.member.remove_roles(unregistered_role, reason="Kayıt işlemi")
            except Exception as e:
                print(f"[HATA] Kayıtsız rolü kaldırılırken hata: {e}")
            
            # Kayıtlı rolünü ver
            try:
                await self.member.add_roles(registered_role, reason="Kayıt işlemi")
            except Exception as e:
                print(f"[HATA] Rol verilirken hata: {e}")
                return await interaction.followup.send(
                    "❌ Sistem hatası oluştu. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # İsmi değiştir
            try:
                await self.member.edit(nick=new_nickname, reason="Kayıt işlemi")
            except Exception as e:
                print(f"[HATA] İsim değiştirilirken hata: {e}")
            
            # Kullanıcıya başarı mesajı gönder
            visibility_status = "Görünür" if self.show_age else "Gizli"
            embed = discord.Embed(
                title="✅ Kayıt Başarılı!",
                description=f"**İsim:** {formatted_name}\n**Yaş:** {self.age}\n**Yaş Durumu:** {visibility_status}\n**Yeni İsim:** {new_nickname}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Yaş görünürlüğünü /kayit-ayarlari komutuyla değiştirebilirsiniz.")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # İstatistik veritabanına kaydet
            try:
                stats_cog = self.bot.get_cog("RegistrationStats")
                if stats_cog:
                    await stats_cog.add_registration(
                        user_id=str(self.member.id),
                        username=str(self.member),
                        name=formatted_name,
                        age=self.age,
                        show_age=self.show_age
                    )
            except Exception as e:
                print(f"[HATA] İstatistik veritabanına kaydedilirken hata: {type(e).__name__}: {e}")
            
            # Log kanalına bildirim gönder
            try:
                log_channel = guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="✅ Yeni Kayıt",
                        description=f"{self.member.mention} başarıyla kayıt oldu!",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(
                        name="👤 Kullanıcı Bilgileri",
                        value=f"**Kullanıcı:** {self.member.mention}\n**ID:** `{self.member.id}`\n**Tag:** {self.member}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="📋 Kayıt Bilgileri",
                        value=f"**İsim:** {formatted_name}\n**Yaş:** {self.age}\n**Yaş Durumu:** {visibility_status}\n**Yeni Nickname:** {new_nickname}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="🎭 Rol Değişiklikleri",
                        value=f"**Verilen:** <@&{REGISTERED_ROLE_ID}>\n**Alınan:** <@&{UNREGISTERED_ROLE_ID}>",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=self.member.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Kayıt Sistemi", icon_url=guild.icon.url if guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Log kanalına mesaj gönderilirken hata: {type(e).__name__}: {e}")
                
        except Exception as e:
            print(f"[HATA] Beklenmeyen kayıt hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
        
        self.stop()


class NewAccountSupportView(discord.ui.View):
    """Yeni hesaplar için yetkili çağırma butonu"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)  # 60 saniye timeout
        self.bot = bot
    
    @discord.ui.button(label="Yetkili Çağır", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yetkili çağır butonuna basıldığında modal aç"""
        try:
            modal = SupportTicketModal(self.bot)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[HATA] Destek modal açılırken hata: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Form açılırken bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya destek modal hatası mesajı gönderilemedi!")


class SupportConfirmView(discord.ui.View):
    """Yetkili çağırma onay butonu"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)  # 60 saniye timeout
        self.bot = bot
    
    @discord.ui.button(label="Evet", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Evet butonuna basıldığında modal aç"""
        try:
            modal = SupportTicketModal(self.bot)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[HATA] Destek modal açılırken hata: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Form açılırken bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya destek modal hatası mesajı gönderilemedi!")
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """İptal butonuna basıldığında"""
        await interaction.response.send_message(
            "✅ İşlem iptal edildi.",
            ephemeral=True
        )
        self.stop()


class RegistrationButton(discord.ui.View):
    """Kayıt butonu view"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)  # Kalıcı buton
        self.bot = bot
        
        # Butonları manuel olarak sıralı ekle
        # 1. Kayıt Ol butonu (Yeşil)
        register_btn = discord.ui.Button(
            label="Kayıt Ol",
            style=discord.ButtonStyle.success,
            emoji="📝",
            custom_id="registration_button",
            row=0
        )
        register_btn.callback = self.register_button_callback
        self.add_item(register_btn)

        # 2. Yetkili Çağır butonu (Gri)
        support_btn = discord.ui.Button(
            label="Yetkili Çağır",
            style=discord.ButtonStyle.danger,
            emoji="⚠️",
            custom_id="support_button",
            row=0
        )
        support_btn.callback = self.support_button_callback
        self.add_item(support_btn)
        
        # 3. Web Sitemiz butonu
        self.add_item(discord.ui.Button(
            label="Web Sitemiz",
            emoji="🌐",
            style=discord.ButtonStyle.link,
            url="https://hydrabon.com/",
            row=0
        ))
        
    async def register_button_callback(self, interaction: discord.Interaction):
        """Kayıt Ol butonuna tıklandığında"""
        try:
            member = interaction.user
            
            # Kullanıcının ses kanalında olup olmadığını kontrol et
            # Kullanıcı herhangi bir ses kanalında mı?
            if not member.voice or not member.voice.channel:
                return await interaction.response.send_message(
                    "❌ Kayıt olabilmek için önce <#1428811752232976566> ses kanalına katılmalısınız!",
                    ephemeral=True
                )
            
            # Kullanıcı doğru ses kanalında mı?
            if member.voice.channel.id != REQUIRED_VOICE_CHANNEL_ID:
                return await interaction.response.send_message(
                    "❌ Kayıt olabilmek için <#1428811752232976566> ses kanalında olmalısınız!",
                    ephemeral=True
                )
            
            # Ses kanalı kontrolü geçtikten sonra hesap yaşı kontrolü (14 gün)
            account_age = discord.utils.utcnow() - member.created_at
            if account_age.days < 14:
                # Hesap 14 günden yeni - Manuel kayıt için ticket açmaya yönlendir
                embed = discord.Embed(
                    title="⏰ Hesap Yaşı Yetersiz",
                    description=(
                        "❌ **Otomatik kayıt olamazsınız!**\n\n"
                        f"Discord hesabınız **{account_age.days} gün** önce oluşturulmuş.\n"
                        f"Otomatik kayıt olabilmek için hesabınızın en az **14 gün** eski olması gerekmektedir.\n\n"
                        f"⏳ **Kalan Süre:** {14 - account_age.days} gün\n\n"
                        "🎫 **Manuel Kayıt İçin:**\n"
                        "Eğer özel bir durumunuz varsa veya manuel kayıt olmak istiyorsanız, "
                        "aşağıdaki **Yetkili Çağır** butonuna tıklayarak destek talebi oluşturabilirsiniz. "
                        "Yetkili ekibimiz sizinle ilgilenecektir."
                    ),
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Hesap Oluşturulma: {member.created_at.strftime('%d.%m.%Y')}")
                
                view = NewAccountSupportView(self.bot)
                return await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            # Tüm kontroller geçti - Kayıt modal'ını aç
            modal = RegistrationModal(self.bot)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[HATA] Kayıt butonu hatası: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Kayıt formu açılırken bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya buton hatası mesajı gönderilemedi!")
    
    async def support_button_callback(self, interaction: discord.Interaction):
        """Yetkili Çağır butonuna tıklandığında"""
        try:
            embed = discord.Embed(
                title="⚠️ Yetkili Çağırma",
                description=(
                    "📢 **Dikkat!**\n\n"
                    "Bu özellik sadece kayıt sırasında **gerçekten bir hata** aldıysanız kullanılmalıdır.\n\n"
                    "Yetkililere destek talebi göndermek istediğinize emin misiniz?"
                ),
                color=discord.Color.orange()
            )
            
            view = SupportConfirmView(self.bot)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"[HATA] Destek butonu hatası: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya destek butonu hatası mesajı gönderilemedi!")


class Registration(commands.Cog):
    """Kayıt sistemi cog'u"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot hazır olduğunda persistent view'ları ekle"""
        self.bot.add_view(RegistrationButton(self.bot))
        self.bot.add_view(TicketControlView())
    
    @app_commands.command(
        name="kayit_embed",
        description="Kayıt embed'ini belirtilen kanala gönderir"
    )
    @app_commands.default_permissions(administrator=True)
    async def send_registration_embed(
        self,
        interaction: discord.Interaction,
        kanal: Optional[discord.TextChannel] = None
    ):
        """Kayıt embed'ini gönderir"""
        
        target_channel = kanal or interaction.channel
        
        # Embed oluştur
        embed = discord.Embed(
            title="<:yazisiz_ana_logo:1394693679935000667> HydRaboN'a Hoş Geldiniz! <:yazisiz_ana_logo:1394693679935000667>",
            description=(
                "❓ [Biz Kimiz?](https://hydrabon.com/)\n\n"
                "• Kayıt olmak için aşağıdaki **Kayıt Ol** butonuna tıklayınız.\n"
                "• Açılacak formda **gerçek** isminizi ve yaşınızı giriniz.\n"
                "• Lütfen **geçerli** bir isim ve yaş girdiğinizden emin olunuz.\n\n"
                "⚠️ Geçerli bilgiler girmenize rağmen hata alıyorsanız **'Yetkili Çağır'** butonuna tıklayarak destek alabilirsiniz."
            ),
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_footer(text=f"{interaction.guild.name} - Kayıt Sistemi")
        
        # Butonu ekle
        view = RegistrationButton(self.bot)
        
        try:
            await target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Kayıt embed'i {target_channel.mention} kanalına gönderildi!",
                ephemeral=True
            )
        except discord.Forbidden:
            print(f"[HATA] Kayıt embed'i gönderilemedi! {target_channel.name} kanalına mesaj gönderme yetkisi yok.")
            await interaction.response.send_message(
                "❌ Bu kanala mesaj gönderme yetkim yok!",
                ephemeral=True
            )
        except Exception as e:
            print(f"[HATA] Kayıt embed'i gönderilirken beklenmeyen hata: {type(e).__name__}: {e}")
            await interaction.response.send_message(
                "❌ Beklenmeyen bir hata oluştu. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="kayit",
        description="Manuel olarak kullanıcı kaydı yapar (Acil durumlar için)"
    )
    @app_commands.default_permissions(administrator=True)
    async def manual_registration(
        self,
        interaction: discord.Interaction,
        kullanici: discord.Member,
        isim: str,
        yas: int
    ):
        """Manuel kayıt işlemi yapar"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Yaş kontrolü
            if yas < 13 or yas > 99:
                return await interaction.followup.send(
                    "❌ Yaş 13-99 arasında olmalıdır!",
                    ephemeral=True
                )
            
            # İsim formatı kontrolü (sadece harf ve boşluk)
            if not re.match(r'^[a-zA-ZğüşöçıİĞÜŞÖÇ\s]+$', isim):
                return await interaction.followup.send(
                    "❌ İsim sadece harflerden oluşmalıdır!",
                    ephemeral=True
                )
            
            # İsmi formatla: Her kelimenin baş harfini büyük yap (Türkçe uyumlu)
            formatted_name = turkish_title_case(isim)
            
            # Yeni nickname: İsim | Yaş
            new_nickname = f"{formatted_name} | {yas}"
            
            # Rolleri al
            guild = interaction.guild
            unregistered_role = guild.get_role(UNREGISTERED_ROLE_ID)
            registered_role = guild.get_role(REGISTERED_ROLE_ID)
            
            if not registered_role:
                print(f"[HATA] Kayıtlı rolü bulunamadı! Rol ID: {REGISTERED_ROLE_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası: Kayıtlı rolü bulunamadı!",
                    ephemeral=True
                )
            
            # Kayıtsız rolünü kaldır
            try:
                if unregistered_role and unregistered_role in kullanici.roles:
                    await kullanici.remove_roles(unregistered_role, reason=f"Manuel kayıt - {interaction.user}")
            except discord.Forbidden:
                print(f"[HATA] Rol kaldırma yetkisi yok! Hedef: {kullanici}")
            except Exception as e:
                print(f"[HATA] Rol kaldırılırken hata: {type(e).__name__}: {e}")
            
            # Kayıtlı rolünü ver
            try:
                await kullanici.add_roles(registered_role, reason=f"Manuel kayıt - {interaction.user}")
            except discord.Forbidden:
                print(f"[HATA] Rol verme yetkisi yok! Bot rolü, hedef rolden daha üstte olmalı.")
                return await interaction.followup.send(
                    "❌ Rol verme yetkim yok! Bot rolü hedef rolden daha üstte olmalı.",
                    ephemeral=True
                )
            except Exception as e:
                print(f"[HATA] Rol verilirken hata: {type(e).__name__}: {e}")
                return await interaction.followup.send(
                    "❌ Rol verilirken bir hata oluştu.",
                    ephemeral=True
                )
            
            # İsmi değiştir
            try:
                await kullanici.edit(nick=new_nickname, reason=f"Manuel kayıt - {interaction.user}")
            except discord.Forbidden:
                print(f"[HATA] İsim değiştirme yetkisi yok! Bot rolü hedef kullanıcıdan daha üstte olmalı.")
                # İsim değiştirilemese de kayıt devam etsin
            except Exception as e:
                print(f"[HATA] İsim değiştirilirken hata: {type(e).__name__}: {e}")
                # İsim değiştirilemese de kayıt devam etsin
            
            # İstatistik veritabanına kaydet (manuel kayıt - yaş varsayılan olarak görünür)
            try:
                stats_cog = self.bot.get_cog("RegistrationStats")
                if stats_cog:
                    await stats_cog.add_registration(
                        user_id=str(kullanici.id),
                        username=str(kullanici),
                        name=formatted_name,
                        age=yas,
                        show_age=True  # Manuel kayıtlarda yaş varsayılan olarak görünür
                    )
            except Exception as e:
                print(f"[HATA] İstatistik veritabanına kaydedilirken hata: {type(e).__name__}: {e}")
            
            # Başarılı mesajı
            embed = discord.Embed(
                title="✅ Manuel Kayıt Başarılı!",
                description=f"{kullanici.mention} kullanıcısı manuel olarak kayıt edildi.",
                color=discord.Color.green()
            )
            embed.add_field(name="İşlem Yapan", value=interaction.user.mention, inline=True)
            embed.add_field(name="Kayıt Edilen", value=kullanici.mention, inline=True)
            embed.add_field(name="İsim", value=formatted_name, inline=True)
            embed.add_field(name="Yaş", value=str(yas), inline=True)
            embed.add_field(name="Yeni Nickname", value=new_nickname, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log kanalına bildirim gönder
            try:
                log_channel = guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="📝 Manuel Kayıt",
                        description=f"{kullanici.mention} manuel olarak kayıt edildi.",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(
                        name="👤 Kayıt Edilen Kullanıcı",
                        value=f"**Kullanıcı:** {kullanici.mention}\n**ID:** `{kullanici.id}`\n**Tag:** {kullanici}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="📋 Kayıt Bilgileri",
                        value=f"**İsim:** {formatted_name}\n**Yaş:** {yas}\n**Yeni Nickname:** {new_nickname}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="🎭 Rol Değişiklikleri",
                        value=f"**Verilen:** <@&{REGISTERED_ROLE_ID}>\n**Alınan:** <@&{UNREGISTERED_ROLE_ID}>",
                        inline=False
                    )
                    log_embed.add_field(
                        name="⚙️ İşlem Bilgileri",
                        value=f"**İşlemi Yapan:** {interaction.user.mention}\n**İşlem Türü:** Manuel Kayıt\n**Komut:** `/kayit`",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=kullanici.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Manuel Kayıt Sistemi", icon_url=guild.icon.url if guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Log kanalına manuel kayıt mesajı gönderilirken hata: {type(e).__name__}: {e}")
            
        except Exception as e:
            print(f"[HATA] Manuel kayıt hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="kayit_sifirla",
        description="Seçilen kullanıcının kaydını sıfırlar"
    )
    @app_commands.default_permissions(administrator=True)
    async def reset_registration(
        self,
        interaction: discord.Interaction,
        kullanici: discord.Member,
        sebep: str
    ):
        """Kullanıcının kaydını sıfırlar"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Kayıtsız rolünü al
            unregistered_role = interaction.guild.get_role(UNREGISTERED_ROLE_ID)
            
            if not unregistered_role:
                print(f"[HATA] Kayıtsız rolü bulunamadı! Rol ID: {UNREGISTERED_ROLE_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası: Kayıtsız rolü bulunamadı!",
                    ephemeral=True
                )
            
            # Rolleri filtrele (@everyone ve Nitro Booster hariç)
            user_roles = [
                role for role in kullanici.roles 
                if role.name != "@everyone" and role.id != NITRO_BOOSTER_ROLE_ID
            ]
            
            # Tüm rolleri kaldır
            if user_roles:
                try:
                    await kullanici.remove_roles(*user_roles, reason=f"Kayıt sıfırlama - {interaction.user}")
                except discord.Forbidden:
                    print(f"[HATA] Rol kaldırma yetkisi yok! Hedef: {kullanici}")
                    return await interaction.followup.send(
                        "❌ Yeterli yetkim yok! Bot rolü hedef kullanıcıdan daha üstte olmalı.",
                        ephemeral=True
                    )
                except Exception as e:
                    print(f"[HATA] Roller kaldırılırken hata: {type(e).__name__}: {e}")
                    return await interaction.followup.send(
                        "❌ Roller kaldırılırken bir hata oluştu.",
                        ephemeral=True
                    )
            
            # Kayıtsız rolünü ver
            try:
                await kullanici.add_roles(unregistered_role, reason=f"Kayıt sıfırlama - {interaction.user}")
            except discord.Forbidden:
                print(f"[HATA] Rol verme yetkisi yok! Hedef: {kullanici}")
                return await interaction.followup.send(
                    "❌ Rol verme yetkisi yok!",
                    ephemeral=True
                )
            except Exception as e:
                print(f"[HATA] Rol verilirken hata: {type(e).__name__}: {e}")
                return await interaction.followup.send(
                    "❌ Rol verilirken bir hata oluştu.",
                    ephemeral=True
                )
            
            # Kullanıcının ismini sıfırla (nickname'i kaldır)
            try:
                await kullanici.edit(nick=None, reason=f"Kayıt sıfırlama - {interaction.user}")
            except discord.Forbidden:
                print(f"[HATA] İsim sıfırlama yetkisi yok! Hedef: {kullanici}")
                # İsim sıfırlanamazsa uyarı ver ama devam et
                await interaction.followup.send(
                    f"⚠️ {kullanici.mention} kullanıcısının kaydı sıfırlandı ancak isim değiştirilemedi (yetki hatası).",
                    ephemeral=True
                )
                return
            except Exception as e:
                print(f"[HATA] İsim sıfırlanırken hata: {type(e).__name__}: {e}")
                # İsim sıfırlanamazsa uyarı ver ama devam et
                await interaction.followup.send(
                    f"⚠️ {kullanici.mention} kullanıcısının kaydı sıfırlandı ancak isim sıfırlanamadı.",
                    ephemeral=True
                )
                return
            
            # Başarılı mesajı
            embed = discord.Embed(
                title="✅ Kayıt Sıfırlandı",
                description=f"{kullanici.mention} kullanıcısının kaydı başarıyla sıfırlandı.",
                color=discord.Color.green()
            )
            embed.add_field(name="İşlem Yapan", value=interaction.user.mention, inline=True)
            embed.add_field(name="Hedef Kullanıcı", value=kullanici.mention, inline=True)
            embed.add_field(name="Sebep", value=sebep, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Genel log kanalına bildirim gönder
            try:
                log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🔄 Kayıt Sıfırlandı",
                        description=f"{kullanici.mention} kullanıcısının kaydı sıfırlandı.",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(
                        name="👤 Hedef Kullanıcı",
                        value=f"**Kullanıcı:** {kullanici.mention}\n**ID:** `{kullanici.id}`\n**Tag:** {kullanici}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="⚙️ İşlem Bilgileri",
                        value=f"**İşlemi Yapan:** {interaction.user.mention}\n**Kaldırılan Rol Sayısı:** {len(user_roles)}\n**Verilen Rol:** <@&{UNREGISTERED_ROLE_ID}>\n**Sebep:** {sebep}",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=kullanici.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Kayıt Sıfırlama", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Genel log kanalına kayıt sıfırlama mesajı gönderilirken hata: {type(e).__name__}: {e}")
            
        except Exception as e:
            print(f"[HATA] Kayıt sıfırlama hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="kayit-goruntule",
        description="Belirtilen kullanıcının kayıt bilgilerini görüntüler"
    )
    @app_commands.default_permissions(administrator=True)
    async def view_registration_info(
        self,
        interaction: discord.Interaction,
        kullanici: discord.Member
    ):
        """Kullanıcının kayıt bilgilerini görüntüler (isim, yaş, kayıt tarihi vb.)"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            stats_cog = self.bot.get_cog("RegistrationStats")
            if not stats_cog:
                return await interaction.followup.send(
                    "❌ İstatistik sistemi bulunamadı!",
                    ephemeral=True
                )
            
            # Kullanıcı bilgilerini al
            user_info = await stats_cog.get_user_info(str(kullanici.id))
            
            if not user_info:
                return await interaction.followup.send(
                    f"❌ {kullanici.mention} için kayıt bilgisi bulunamadı!\n\n"
                    "Bu kullanıcı henüz kayıt olmamış olabilir veya kayıt verileri silinmiş olabilir.",
                    ephemeral=True
                )
            
            name, age, registered_at, show_age = user_info
            
            # Türkiye saat dilimine çevir
            import pytz
            import datetime
            
            # registered_at string ise datetime'a çevir
            if isinstance(registered_at, str):
                registered_at = datetime.datetime.fromisoformat(registered_at)
            
            turkey_tz = pytz.timezone("Europe/Istanbul")
            if registered_at.tzinfo is None:
                registered_at = turkey_tz.localize(registered_at)
            else:
                registered_at = registered_at.astimezone(turkey_tz)
            
            # Hesap yaşı hesapla
            account_age = discord.utils.utcnow() - kullanici.created_at
            
            # Sunucuya katılma süresi
            join_age = discord.utils.utcnow() - kullanici.joined_at if kullanici.joined_at else None
            
            visibility_status = "Görünür ✅" if show_age else "Gizli 👁️"
            current_nickname = kullanici.display_name
            
            embed = discord.Embed(
                title="📋 Kullanıcı Kayıt Bilgileri",
                description=f"{kullanici.mention} kullanıcısının detaylı kayıt bilgileri",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # Discord Hesap Bilgileri
            account_info = (
                f"**Kullanıcı:** {kullanici.mention}\n"
                f"**ID:** `{kullanici.id}`\n"
                f"**Tag:** {kullanici}\n"
                f"**Hesap Oluşturma:** {kullanici.created_at.strftime('%d.%m.%Y')}\n"
                f"**Hesap Yaşı:** {account_age.days} gün"
            )
            if join_age:
                account_info += f"\n**Sunucuya Katılma:** {join_age.days} gün önce"
            
            embed.add_field(
                name="👤 Discord Bilgileri",
                value=account_info,
                inline=False
            )
            
            # Kayıt Bilgileri
            embed.add_field(
                name="📝 Kayıt Bilgileri",
                value=(
                    f"**Kayıtlı İsim:** {name}\n"
                    f"**Yaş:** {age}\n"
                    f"**Yaş Görünürlüğü:** {visibility_status}\n"
                    f"**Mevcut Nickname:** {current_nickname}\n"
                    f"**Kayıt Tarihi:** {registered_at.strftime('%d.%m.%Y %H:%M')}"
                ),
                inline=False
            )
            
            # Rol Bilgileri
            role_count = len(kullanici.roles) - 1  # @everyone hariç
            embed.add_field(
                name="🎭 Rol Bilgisi",
                value=f"**Toplam Rol Sayısı:** {role_count}",
                inline=True
            )
            
            embed.set_thumbnail(url=kullanici.display_avatar.url)
            embed.set_footer(text="HydRaboN Kayıt Bilgileri", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"[HATA] Kayıt bilgisi görüntüleme hatası: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="kayit-ayarlari",
        description="Kayıt ayarlarınızı düzenleyin (yaş görünürlüğü, rol yönetimi)"
    )
    async def age_settings(
        self,
        interaction: discord.Interaction
    ):
        """Kayıt ayarlarını yönet"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            stats_cog = self.bot.get_cog("RegistrationStats")
            if not stats_cog:
                return await interaction.followup.send(
                    "❌ İstatistik sistemi bulunamadı!",
                    ephemeral=True
                )
            
            # Kullanıcı bilgilerini al
            user_info = await stats_cog.get_user_info(str(interaction.user.id))
            
            if not user_info:
                return await interaction.followup.send(
                    "❌ Kayıt bilginiz bulunamadı! Önce kayıt olmalısınız.",
                    ephemeral=True
                )
            
            name, age, registered_at, show_age = user_info
            current_status = "Görünür ✅" if show_age else "Gizli 👁️"
            
            # Rol düzenleme select menu
            class RoleManageSelect(discord.ui.Select):
                def __init__(self, member: discord.Member):
                    self.member = member
                    
                    # Yönetilebilir rol ID'leri
                    self.manageable_role_ids = [
                        1207713855854223391,
                        1207713907498688512,
                        1207713950742085643
                    ]
                    
                    # Seçenekleri oluştur
                    options = []
                    for role_id in self.manageable_role_ids:
                        role = member.guild.get_role(role_id)
                        if role:
                            # Kullanıcının bu rolü var mı kontrol et
                            has_role = role in member.roles
                            options.append(
                                discord.SelectOption(
                                    label=role.name,
                                    value=str(role_id),
                                    description=f"{'✅ Aktif' if has_role else '❌ Pasif'}",
                                    emoji="✅" if has_role else "❌"
                                )
                            )
                    
                    super().__init__(
                        placeholder="Düzenlemek istediğiniz rolleri seçin...",
                        min_values=0,
                        max_values=len(options),
                        options=options,
                        custom_id="role_manage_select"
                    )
                
                async def callback(self, interaction: discord.Interaction):
                    await interaction.response.defer(ephemeral=True)
                    
                    try:
                        # Seçilen rol ID'leri
                        selected_role_ids = [int(value) for value in self.values]
                        
                        # Mevcut roller ile karşılaştır
                        added_roles = []
                        removed_roles = []
                        
                        for role_id in self.manageable_role_ids:
                            role = self.member.guild.get_role(role_id)
                            if not role:
                                continue
                            
                            has_role = role in self.member.roles
                            should_have = role_id in selected_role_ids
                            
                            if should_have and not has_role:
                                # Rol verilecek
                                try:
                                    await self.member.add_roles(role, reason="Kullanıcı rol yönetimi")
                                    added_roles.append(role.name)
                                except Exception as e:
                                    print(f"[HATA] Rol eklenirken hata ({role.name}): {e}")
                            elif not should_have and has_role:
                                # Rol alınacak
                                try:
                                    await self.member.remove_roles(role, reason="Kullanıcı rol yönetimi")
                                    removed_roles.append(role.name)
                                except Exception as e:
                                    print(f"[HATA] Rol kaldırılırken hata ({role.name}): {e}")
                        
                        # Sonuç mesajı
                        result_parts = []
                        if added_roles:
                            result_parts.append(f"**Eklenen Roller:** {', '.join(added_roles)}")
                        if removed_roles:
                            result_parts.append(f"**Kaldırılan Roller:** {', '.join(removed_roles)}")
                        
                        if not result_parts:
                            result_msg = "Herhangi bir değişiklik yapılmadı."
                        else:
                            result_msg = "\n".join(result_parts)
                        
                        embed = discord.Embed(
                            title="✅ Roller Güncellendi!",
                            description=result_msg,
                            color=discord.Color.green()
                        )
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        
                    except Exception as e:
                        print(f"[HATA] Rol yönetimi hatası: {e}")
                        await interaction.followup.send(
                            "❌ Roller güncellenirken bir hata oluştu!",
                            ephemeral=True
                        )
            
            class RoleManageView(discord.ui.View):
                def __init__(self, member: discord.Member):
                    super().__init__(timeout=60)
                    self.add_item(RoleManageSelect(member))
            
            # Ana ayarlar view'ı
            class RegistrationSettingsView(discord.ui.View):
                def __init__(self, bot, stats_cog, member, name, age, current_show_age):
                    super().__init__(timeout=60)
                    self.bot = bot
                    self.stats_cog = stats_cog
                    self.member = member
                    self.name = name
                    self.age = age
                    self.current_show_age = current_show_age
                
                @discord.ui.button(label="Yaşımı Göster", style=discord.ButtonStyle.success, emoji="✅", row=0)
                async def show_age(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_age(interaction, True)
                
                @discord.ui.button(label="Yaşımı Gizle", style=discord.ButtonStyle.secondary, emoji="👁️", row=0)
                async def hide_age(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_age(interaction, False)

                @discord.ui.button(label="Yaşımı Sıfırla", style=discord.ButtonStyle.danger, emoji="🔄", row=0)
                async def reset_age(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Yaş sıfırlama onay sorusu göster"""
                    try:
                        embed = discord.Embed(
                            title="⚠️ Yaş Sıfırlama Onayı",
                            description=(
                                "**Yaşınızı sıfırlamak için yetkili desteği gereklidir.**\n\n"
                                "Bu işlem için bir destek ticket'ı açılacaktır. Ticket'ta:\n"
                                "• Yaşınızı neden sıfırlamak istediğinizi belirtmeniz\n"
                                "• Doğru yaşınızı (biliyorsanız) girmeniz\n"
                                "gerekecektir.\n\n"
                                "Yetkililerin onayı sonrasında yaşınız güncellenecektir.\n\n"
                                "**Devam etmek istiyor musunuz?**"
                            ),
                            color=discord.Color.orange()
                        )
                        embed.set_footer(text="Ticket açılması durumunda yetkililere bildirim gönderilecektir")
                        
                        confirm_view = AgeResetConfirmView(self.bot, self.name, self.age)
                        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
                        
                    except Exception as e:
                        print(f"[HATA] Yaş sıfırlama onay mesajı gösterilirken hata: {e}")
                        await interaction.response.send_message(
                            "❌ Bir hata oluştu. Lütfen tekrar deneyiniz.",
                            ephemeral=True
                        )
                
                @discord.ui.button(label="Rolleri Düzenle", style=discord.ButtonStyle.primary, emoji="🎭", row=1)
                async def manage_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Rol yönetim menüsünü aç"""
                    try:
                        embed = discord.Embed(
                            title="🎭 Rol Yönetimi",
                            description=(
                                "Aşağıdaki menüden düzenlemek istediğiniz rolleri seçebilirsiniz.\n\n"
                                "**Nasıl Kullanılır:**\n"
                                "• Menüden istediğiniz rolleri seçin\n"
                                "• Seçtiğiniz roller size **eklenecek**\n"
                                "• Seçmediğiniz roller **kaldırılacak**\n"
                                "• Hiçbir rol seçmezseniz tüm roller kaldırılır\n\n"
                                "✅ = Şu anda aktif\n"
                                "❌ = Şu anda pasif"
                            ),
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text="Değişiklikler anında uygulanacaktır")
                        
                        role_view = RoleManageView(self.member)
                        await interaction.response.send_message(embed=embed, view=role_view, ephemeral=True)
                        
                    except Exception as e:
                        print(f"[HATA] Rol yönetim menüsü açılırken hata: {e}")
                        await interaction.response.send_message(
                            "❌ Rol yönetim menüsü açılırken bir hata oluştu!",
                            ephemeral=True
                        )
                
                async def toggle_age(self, interaction: discord.Interaction, show_age: bool):
                    await interaction.response.defer(ephemeral=True)
                    
                    try:
                        # Veritabanını güncelle
                        success = await self.stats_cog.update_age_visibility(str(self.member.id), show_age)
                        
                        if not success:
                            return await interaction.followup.send(
                                "❌ Ayar güncellenirken bir hata oluştu!",
                                ephemeral=True
                            )
                        
                        # Nickname'i güncelle
                        formatted_name = turkish_title_case(self.name)
                        if show_age:
                            new_nickname = f"{formatted_name} | {self.age}"
                        else:
                            new_nickname = formatted_name
                        
                        try:
                            await self.member.edit(nick=new_nickname, reason=f"Yaş görünürlüğü değiştirildi")
                        except Exception as e:
                            print(f"[HATA] Nickname değiştirilirken hata: {e}")
                        
                        visibility_status = "Görünür ✅" if show_age else "Gizli 👁️"
                        
                        embed = discord.Embed(
                            title="✅ Yaş Görünürlüğü Güncellendi!",
                            description=f"Yaş görünürlüğünüz başarıyla değiştirildi.",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Yeni Durum", value=visibility_status, inline=True)
                        embed.add_field(name="Yeni İsim", value=new_nickname, inline=True)
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        self.stop()
                        
                    except Exception as e:
                        print(f"[HATA] Yaş görünürlüğü değiştirme hatası: {e}")
                        await interaction.followup.send(
                            "❌ Beklenmeyen bir hata oluştu.",
                            ephemeral=True
                        )
            
            embed = discord.Embed(
                title="⚙️ Kayıt Ayarları",
                description=(
                    f"**Kayıt Bilgileriniz:**\n"
                    f"• İsim: {name}\n"
                    f"• Yaş: {age}\n"
                    f"• Yaş Durumu: {current_status}\n\n"
                    "**Kullanılabilir Ayarlar:**\n\n"
                    "🔸 **Yaş Görünürlüğü**\n"
                    "• Yaşınızın kullanıcı adınızda görünmesini ayarlayın\n"
                    "• Göster: `{0} | {1}` formatında\n"
                    "• Gizle: `{0}` formatında\n\n"
                    "🔸 **Rol Yönetimi**\n"
                    "• İstediğiniz rolleri kendiniz ekleyip kaldırabilirsiniz\n"
                    "• Rollerinizi dilediğiniz gibi özelleştirin\n\n"
                    "🔸 **Yaş Sıfırlama**\n"
                    "• Yanlış yaş girildiyse yetkili desteği ile düzeltilebilir\n"
                    "• Ticket açılarak değişiklik talebinde bulunabilirsiniz"
                ).format(name, age),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Aşağıdaki butonları kullanarak ayarlarınızı değiştirebilirsiniz")
            
            view = RegistrationSettingsView(self.bot, stats_cog, interaction.user, name, age, show_age)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"[HATA] Kayıt ayarları hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(Registration(bot))

