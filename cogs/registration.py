import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import re
import asyncio
import io
from typing import Optional

# ============ GLOBAL AYARLAR ============
# Rol ID'leri
UNREGISTERED_ROLE_ID = 1428496119213588521  # Kayıtsız üye rolü
REGISTERED_ROLE_ID = 1029089740022095973    # Kayıtlı üye rolü
NITRO_BOOSTER_ROLE_ID = 1030490914411511869  # Nitro Booster rolü (korunur)
YK_UYELERI_ROLE_ID = 1029089731314720798  # YK Üyeleri rolü - ID'yi güncelleyin
YK_ADAYLARI_ROLE_ID = 1412843482980290711  # YK Adayları rolü - ID'yi güncelleyin

# Kanal ID'leri
LOG_CHANNEL_ID = 1431398643273039934         # Genel log kanalı
REGISTRATION_LOG_CHANNEL_ID = 1459636312519872553  # Kayıt denemesi log kanalı
TICKET_LOG_CHANNEL_ID = 1364306112022839436  # Ticket transcript log kanalı
TICKET_CATEGORY_ID = 1364301691637338132     # Ticket kategorisi
ROLE_SELECTION_CHANNEL_ID = 1432764482547089570  # Rol alma kanalı

# Yetki
OWNER_ID = 315888596437696522  # Bot sahibinin ID'si

# =========================================

# Yetkilendirme kontrolü
def check_registration_permission(member: discord.Member) -> bool:
    """
    Manuel kayıt yetkisini kontrol eder.
    YK Üyeleri, YK Adayları ve Yöneticiler kayıt yapabilir.
    """
    # Yönetici kontrolü
    if member.guild_permissions.administrator:
        return True
    
    # Rol bazlı kontrol
    role_ids = [role.id for role in member.roles]
    
    # YK Üyeleri veya YK Adayları rolü varsa izin ver
    if YK_UYELERI_ROLE_ID in role_ids or YK_ADAYLARI_ROLE_ID in role_ids:
        return True
    
    return False

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

async def check_name_in_database(name: str) -> bool:
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
    
    async def log_registration_attempt(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        age_str: str, 
        success: bool, 
        reason: str = None
    ):
        """Kayıt denemesini log kanalına gönderir"""
        try:
            guild = interaction.guild
            log_channel = guild.get_channel(REGISTRATION_LOG_CHANNEL_ID)
            
            if not log_channel:
                print(f"[UYARI] Kayıt log kanalı bulunamadı! Kanal ID: {REGISTRATION_LOG_CHANNEL_ID}")
                return
            
            # Embed oluştur
            if success:
                embed = discord.Embed(
                    title="✅ Başarılı Kayıt Denemesi",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
            else:
                embed = discord.Embed(
                    title="❌ Başarısız Kayıt Denemesi",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
            
            # Kullanıcı bilgileri
            embed.add_field(
                name="👤 Kullanıcı Bilgileri",
                value=(
                    f"**Kullanıcı:** {interaction.user.mention}\n"
                    f"**Kullanıcı Adı:** {interaction.user.name}\n"
                    f"**Kullanıcı ID:** `{interaction.user.id}`"
                ),
                inline=False
            )
            
            # Denenen bilgiler
            embed.add_field(
                name="📝 Denenen Bilgiler",
                value=(
                    f"**İsim:** {name}\n"
                    f"**Yaş:** {age_str}"
                ),
                inline=False
            )
            
            # Başarısızlık nedeni
            if not success and reason:
                embed.add_field(
                    name="⚠️ Başarısızlık Nedeni",
                    value=reason,
                    inline=False
                )
            
            embed.set_footer(
                text="HydRaboN Kayıt Sistemi",
                icon_url=guild.icon.url if guild.icon else None
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"[HATA] Kayıt denemesi loglanırken hata: {type(e).__name__}: {e}")
    
    async def on_submit(self, interaction: discord.Interaction):
        """Modal submit edildiğinde çalışır"""
        await interaction.response.defer(ephemeral=True)
        
        name = self.name_input.value.strip()
        age_str = self.age_input.value.strip()
        
        # Yaş kontrolü
        try:
            age = int(age_str)
            if age < 13 or age > 99:
                # Başarısız - Geçersiz yaş aralığı
                await self.log_registration_attempt(
                    interaction, name, age_str, False, 
                    "Yaş 13-99 aralığı dışında"
                )
                return await interaction.followup.send(
                    "❌ Yaş 13-99 arasında olmalıdır!",
                    ephemeral=True
                )
        except ValueError:
            # Başarısız - Yaş formatı hatalı
            await self.log_registration_attempt(
                interaction, name, age_str, False, 
                "Geçersiz yaş formatı (sayı değil)"
            )
            return await interaction.followup.send(
                "❌ Lütfen geçerli bir yaş giriniz!",
                ephemeral=True
            )
        
        # İsim formatı kontrolü (sadece harf ve boşluk)
        if not re.match(r'^[a-zA-ZğüşöçıİĞÜŞÖÇ\s]+$', name):
            # Başarısız - İsim formatı hatalı
            await self.log_registration_attempt(
                interaction, name, age_str, False, 
                "İsimde geçersiz karakterler var (sadece harf ve boşluk kullanılabilir)"
            )
            return await interaction.followup.send(
                "❌ İsim sadece harflerden oluşmalıdır!",
                ephemeral=True
            )
        
        # İsim veritabanında var mı kontrol et
        name_valid = await check_name_in_database(name)
        
        if not name_valid:
            # Başarısız - İsim veritabanında yok
            await self.log_registration_attempt(
                interaction, name, age_str, False, 
                "İsim veritabanında bulunamadı (geçersiz isim)"
            )
            return await interaction.followup.send(
                "❌ Lütfen geçerli bir isim giriniz!",
                ephemeral=True
            )
        
        # Başarılı - Tüm kontroller geçti
        await self.log_registration_attempt(
            interaction, name, age_str, True
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
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message
    
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
        self.message = None
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
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
                    title="🔒 Destek Ticket'ı Kapatıldı (Manuel)",
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
                    value=f"**Yetkili:** {interaction.user.mention} ({interaction.user})",
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
        # Embed'i güncelle
        embed = discord.Embed(
            title="✅ İşlem İptal Edildi",
            description="Ticket kapatma işlemi iptal edildi.",
            color=discord.Color.green()
        )
        
        # Butonları devre dışı bırak
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


async def _close_manual_ticket(
    channel: discord.TextChannel,
    guild: discord.Guild,
    member: discord.Member,
    formatted_name: str,
    age: int,
    show_age_text: str,
):
    """Manuel kayıt sonrası ticket'ı kapatır ve transcript kaydeder."""
    try:
        closing_embed = discord.Embed(
            title="🔒 Ticket Kapatılıyor",
            description="Ticket 5 saniye içinde kapatılacak.",
            color=discord.Color.orange(),
        )
        await channel.send(embed=closing_embed)
        await asyncio.sleep(5)

        # Transcript kaydet
        try:
            log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
            if log_channel:
                messages = []
                async for msg in channel.history(limit=None, oldest_first=True):
                    timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    content = msg.content or "[Embed/Attachment]"
                    messages.append(f"[{timestamp}] {msg.author}: {content}")

                transcript = "\n".join(messages)
                transcript_file = io.BytesIO(transcript.encode("utf-8"))
                transcript_file.seek(0)

                transcript_embed = discord.Embed(
                    title="📝 Destek Ticket'ı Kapatıldı (Otomatik)",
                    description=f"**Ticket:** {channel.name}\n**Sebep:** Manuel kayıt tamamlandı",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow(),
                )
                transcript_embed.add_field(
                    name="👤 Kullanıcı",
                    value=f"{member.mention} (`{member.id}`)",
                    inline=False,
                )
                transcript_embed.add_field(
                    name="📋 Kayıt Bilgileri",
                    value=f"**İsim:** {formatted_name}\n**Yaş:** {age}\n**Yaş Durumu:** {show_age_text}",
                    inline=False,
                )
                await log_channel.send(
                    embed=transcript_embed,
                    file=discord.File(
                        transcript_file,
                        filename=f"transcript-{channel.name}.txt",
                    ),
                )
        except Exception as e:
            print(f"[HATA] Ticket transcript kaydedilirken hata: {type(e).__name__}: {e}")

        await channel.delete(reason="Manuel kayıt tamamlandı - Otomatik kapatma")

    except Exception as e:
        print(f"[HATA] Ticket kapatılırken hata: {type(e).__name__}: {e}")


class ManualTicketRoleSelectView(discord.ui.View):
    """Manuel kayıt sonrası ticket kanalında bildirim rolü seçim view'ı"""

    _ROLES = {
        1207713855854223391: "🎉 Etkinlik Bildirim",
        1207713907498688512: "🎁 Çekiliş Bildirim",
        1207713950742085643: "❓ Günün Sorusu Bildirim",
    }

    def __init__(
        self,
        bot: commands.Bot,
        member: discord.Member,
        channel: discord.TextChannel,
        formatted_name: str,
        age: int,
        show_age_text: str,
    ):
        super().__init__(timeout=86400)
        self.bot = bot
        self.member = member
        self.channel = channel
        self.formatted_name = formatted_name
        self.age = age
        self.show_age_text = show_age_text
        self.selected_roles: set = set()
        self.message = None

    async def on_timeout(self):
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except Exception:
                pass
        try:
            await _close_manual_ticket(
                self.channel, self.channel.guild, self.member,
                self.formatted_name, self.age, self.show_age_text,
            )
        except Exception as e:
            print(f"[HATA] Timeout'ta ticket kapatılırken hata: {type(e).__name__}: {e}")

    @discord.ui.button(label="🎉 Etkinlik", style=discord.ButtonStyle.secondary, row=0)
    async def event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, 1207713855854223391, button)

    @discord.ui.button(label="🎁 Çekiliş", style=discord.ButtonStyle.secondary, row=0)
    async def giveaway_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, 1207713907498688512, button)

    @discord.ui.button(label="❓ Günün Sorusu", style=discord.ButtonStyle.secondary, row=0)
    async def qotd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, 1207713950742085643, button)

    @discord.ui.button(label="✅ Tamamla", style=discord.ButtonStyle.success, row=1)
    async def complete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()

        for role_id in self.selected_roles:
            try:
                role = interaction.guild.get_role(role_id)
                if role:
                    await self.member.add_roles(role, reason="Manuel kayıt - bildirim rolü seçimi")
            except Exception as e:
                print(f"[HATA] Bildirim rolü eklenirken hata (Rol ID: {role_id}): {e}")

        role_names = [
            interaction.guild.get_role(rid).name
            for rid in self.selected_roles
            if interaction.guild.get_role(rid)
        ]
        done_embed = discord.Embed(
            title="✅ Rol Seçimi Tamamlandı",
            description=(
                f"**Seçilen Roller:** {', '.join(role_names) if role_names else 'Yok'}\n\n"
                "Ticket kapatılıyor..."
            ),
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=done_embed, view=None)
        await _close_manual_ticket(
            self.channel, interaction.guild, self.member,
            self.formatted_name, self.age, self.show_age_text,
        )

    async def _toggle_role(
        self,
        interaction: discord.Interaction,
        role_id: int,
        button: discord.ui.Button,
    ):
        if role_id in self.selected_roles:
            self.selected_roles.remove(role_id)
            button.style = discord.ButtonStyle.secondary
        else:
            self.selected_roles.add(role_id)
            button.style = discord.ButtonStyle.primary

        embed = discord.Embed(
            title="🔔 Bildirim Rollerini Seçin",
            description=(
                f"{self.member.mention}, almak istediğin bildirim rollerini seç.\n"
                "Seçtikten sonra **Tamamla** butonuna tıkla.\n\n"
                f"**Seçilen Roller:** {len(self.selected_roles)}/3"
            ),
            color=discord.Color.blue(),
        )
        await interaction.response.edit_message(embed=embed, view=self)


class ManualRegistrationModal(discord.ui.Modal, title="Manuel Kayıt Formu"):
    """Yetkililerin manuel kayıt için kullanacağı form"""
    
    name_input = discord.ui.TextInput(
        label="İsim",
        placeholder="Kullanıcının ismini giriniz",
        min_length=2,
        max_length=50,
        required=True,
        style=discord.TextStyle.short
    )
    
    age_input = discord.ui.TextInput(
        label="Yaş",
        placeholder="Kullanıcının yaşını giriniz (13-99)",
        min_length=1,
        max_length=2,
        required=True,
        style=discord.TextStyle.short
    )
    
    show_age_input = discord.ui.TextInput(
        label="İsmin yanında yaş gözüksün mü?",
        placeholder="Evet veya Hayır yazınız",
        min_length=3,
        max_length=5,
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot: commands.Bot, member: discord.Member, default_name: str, default_age: int, default_show_age: bool, ticket_view):
        super().__init__()
        self.bot = bot
        self.member = member
        self.ticket_view = ticket_view
        
        # Default değerleri ayarla
        self.name_input.default = default_name
        self.age_input.default = str(default_age)
        self.show_age_input.default = "Evet" if default_show_age else "Hayır"
    
    async def on_submit(self, interaction: discord.Interaction):
        """Modal submit edildiğinde kayıt işlemini gerçekleştir"""
        await interaction.response.defer(ephemeral=True)
        
        name = self.name_input.value.strip()
        age_str = self.age_input.value.strip()
        show_age_str = self.show_age_input.value.strip().lower()
        
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
        
        # Yaş görünürlüğünü parse et
        if show_age_str in ["evet", "e", "yes", "y"]:
            show_age = True
            show_age_text = "✅ Evet"
        else:
            show_age = False
            show_age_text = "❌ Hayır"
        
        try:
            guild = interaction.guild
            
            # İsmi formatla
            formatted_name = turkish_title_case(name)
            
            # Nickname'i ayarla (yaş görünürlüğüne göre)
            if show_age:
                new_nickname = f"{formatted_name} | {age}"
            else:
                new_nickname = formatted_name
            
            # Rolleri al
            unregistered_role = guild.get_role(UNREGISTERED_ROLE_ID)
            registered_role = guild.get_role(REGISTERED_ROLE_ID)
            
            if not registered_role:
                return await interaction.followup.send(
                    "❌ Kayıtlı rolü bulunamadı!",
                    ephemeral=True
                )
            
            # Kayıtsız rolünü kaldır
            if unregistered_role and unregistered_role in self.member.roles:
                await self.member.remove_roles(unregistered_role, reason=f"Manuel kayıt - Yetkili: {interaction.user}")
            
            # Kayıtlı rolünü ver
            await self.member.add_roles(registered_role, reason=f"Manuel kayıt - Yetkili: {interaction.user}")
            
            # Nickname'i ayarla
            try:
                await self.member.edit(nick=new_nickname, reason="Kayıt işlemi")
            except discord.Forbidden:
                print(f"[UYARI] {self.member} için nickname ayarlanamadı (yetki yok)")
            
            # İstatistikleri kaydet
            try:
                stats_cog = self.bot.get_cog("RegistrationStats")
                if stats_cog:
                    await stats_cog.add_registration(
                        user_id=str(self.member.id),
                        username=str(self.member),
                        name=formatted_name,
                        age=age,
                        show_age=show_age
                    )
            except Exception as e:
                print(f"[HATA] İstatistik veritabanına kaydedilirken hata: {type(e).__name__}: {e}")
            
            # Başarı mesajı
            success_embed = discord.Embed(
                title="✅ Kayıt Başarılı",
                description=(
                    f"**Kullanıcı:** {self.member.mention}\n"
                    f"**İsim:** {formatted_name}\n"
                    f"**Yaş:** {age}\n"
                    f"**Yaş Durumu:** {show_age_text}\n"
                    f"**Nickname:** {new_nickname}\n"
                    f"**Kayıt Eden:** {interaction.user.mention}"
                ),
                color=discord.Color.green()
            )
            
            # Ticket kanalına mesaj gönder
            await interaction.channel.send(embed=success_embed)
            
            # Yetkili'ye ephemeral mesaj
            await interaction.followup.send(
                "✅ Kullanıcı başarıyla kaydedildi!",
                ephemeral=True
            )
            
            # Log kanalına bildirim gönder
            try:
                log_channel = guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="✅ Manuel Kayıt",
                        description=f"{self.member.mention} manuel olarak kaydedildi!",
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
                        value=f"**İsim:** {formatted_name}\n**Yaş:** {age}\n**Yaş Durumu:** {show_age_text}\n**Yeni Nickname:** {new_nickname}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="👮 Yetkili",
                        value=f"**Kaydeden:** {interaction.user.mention}\n**ID:** `{interaction.user.id}`",
                        inline=False
                    )
                    log_embed.add_field(
                        name="🎭 Rol Değişiklikleri",
                        value=f"**Verilen:** <@&{REGISTERED_ROLE_ID}>\n**Alınan:** <@&{UNREGISTERED_ROLE_ID}>",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=self.member.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Manuel Kayıt Sistemi", icon_url=guild.icon.url if guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Log kanalına mesaj gönderilirken hata: {type(e).__name__}: {e}")
            
            # Hoş geldin mesajı gönder
            try:
                welcome_cog = self.bot.get_cog("Welcome")
                if welcome_cog:
                    await welcome_cog.send_welcome_message(self.member)
            except Exception as e:
                print(f"[HATA] Hoş geldin mesajı gönderilirken hata: {type(e).__name__}: {e}")
            
            # Manuel kayıt butonunu devre dışı bırak
            try:
                for item in self.ticket_view.children:
                    if isinstance(item, discord.ui.Button) and item.custom_id == "manual_register_button":
                        item.disabled = True
                        item.label = "Kayıt Tamamlandı"
                
                # Orijinal ticket mesajını güncelle
                async for message in interaction.channel.history(limit=10, oldest_first=True):
                    if message.author == self.bot.user and len(message.embeds) > 0:
                        if message.embeds[0].title == "🎫 Kayıt Destek Talebi":
                            await message.edit(view=self.ticket_view)
                            break
            except Exception as e:
                print(f"[HATA] Ticket mesajı güncellenirken hata: {type(e).__name__}: {e}")
            
            # Ticket kanalında direkt rol seçimi göster
            try:
                role_select_embed = discord.Embed(
                    title="🔔 Bildirim Rollerini Seçin",
                    description=(
                        f"{self.member.mention}, almak istediğin bildirim rollerini seç.\n"
                        "Seçtikten sonra **Tamamla** butonuna tıkla.\n\n"
                        "**Seçilen Roller:** 0/3"
                    ),
                    color=discord.Color.blue(),
                )
                role_select_embed.set_footer(
                    text="24 saat içinde işlem yapılmazsa ticket otomatik kapanacak"
                )
                view = ManualTicketRoleSelectView(
                    bot=self.bot,
                    member=self.member,
                    channel=interaction.channel,
                    formatted_name=formatted_name,
                    age=age,
                    show_age_text=show_age_text,
                )
                msg = await interaction.channel.send(embed=role_select_embed, view=view)
                view.message = msg
            except Exception as e:
                print(f"[HATA] Rol seçimi embed'i gönderilirken hata: {type(e).__name__}: {e}")
                try:
                    await _close_manual_ticket(
                        interaction.channel, guild, self.member,
                        formatted_name, age, show_age_text,
                    )
                except Exception as close_err:
                    print(f"[HATA] Ticket kapatılırken hata: {type(close_err).__name__}: {close_err}")
            
        except Exception as e:
            print(f"[HATA] Manuel kayıt hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                f"❌ Kayıt sırasında bir hata oluştu: {str(e)}",
                ephemeral=True
            )


class TicketControlView(discord.ui.View):
    """Ticket kontrol butonları"""
    
    def __init__(self, bot: commands.Bot = None, member: discord.Member = None, name: str = None, age: int = None, show_age: bool = None):
        super().__init__(timeout=None)  # Kalıcı buton
        self.bot = bot
        self.member = member
        self.name = name
        self.age = age
        self.show_age = show_age
    
    @discord.ui.button(
        label="Manuel Kayıt",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="manual_register_button",
        row=0
    )
    async def manual_register(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manuel kayıt butonu - Formu aç"""
        try:
            # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
            if not check_registration_permission(interaction.user):
                return await interaction.response.send_message(
                    "❌ Bu işlem için yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                    ephemeral=True
                )
            
            # Kayıt bilgilerinin olup olmadığını kontrol et
            if not all([self.bot, self.member, self.name, self.age is not None, self.show_age is not None]):
                return await interaction.response.send_message(
                    "❌ Kayıt bilgileri bulunamadı! Lütfen /kayit komutunu kullanın.",
                    ephemeral=True
                )
            
            # Manuel kayıt modalını aç (kullanıcının girdiği bilgilerle dolu)
            modal = ManualRegistrationModal(
                bot=self.bot,
                member=self.member,
                default_name=self.name,
                default_age=self.age,
                default_show_age=self.show_age,
                ticket_view=self
            )
            await interaction.response.send_modal(modal)
                
        except Exception as e:
            print(f"[HATA] Manuel kayıt butonu hatası: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Bir hata oluştu. Lütfen tekrar deneyiniz.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya manuel kayıt hatası mesajı gönderilemedi!")
    
    @discord.ui.button(
        label="Ticket'ı Kapat",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket_button",
        row=0
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ticket kapatma butonu"""
        try:
            # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
            if not check_registration_permission(interaction.user):
                return await interaction.response.send_message(
                    "❌ Bu işlem için yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
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
            view.message = await interaction.original_response()
            
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
    
    show_age_input = discord.ui.TextInput(
        label="İsmimin yanında yaşım gözüksün mü?",
        placeholder="Evet veya Hayır yazınız",
        min_length=3,
        max_length=5,
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot: commands.Bot, origin_view=None, origin_message=None):
        super().__init__()
        self.bot = bot
        self.origin_view = origin_view
        self.origin_message = origin_message
    
    async def disable_origin_buttons(self, error_message: str = None):
        """Orijinal mesajdaki butonları devre dışı bırakır"""
        if self.origin_view and self.origin_message:
            try:
                for item in self.origin_view.children:
                    item.disabled = True
                
                if error_message:
                    disabled_embed = discord.Embed(
                        title="❌ İşlem Başarısız",
                        description=error_message,
                        color=discord.Color.red()
                    )
                else:
                    disabled_embed = discord.Embed(
                        title="✅ Destek Talebi Oluşturuldu",
                        description="Destek talebiniz başarıyla oluşturuldu. Ticket kanalınızı kontrol edin.",
                        color=discord.Color.green()
                    )
                
                await self.origin_message.edit(embed=disabled_embed, view=self.origin_view)
                self.origin_view.stop()
            except Exception as e:
                print(f"[HATA] Orijinal mesaj güncellenirken hata: {type(e).__name__}: {e}")
    
    async def log_manual_registration_attempt(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        age_str: str, 
        show_age_str: str,
        success: bool,
        reason: str = None
    ):
        """Manuel kayıt denemesini log kanalına gönderir"""
        try:
            guild = interaction.guild
            log_channel = guild.get_channel(REGISTRATION_LOG_CHANNEL_ID)
            
            if not log_channel:
                print(f"[UYARI] Kayıt log kanalı bulunamadı! Kanal ID: {REGISTRATION_LOG_CHANNEL_ID}")
                return
            
            # Embed oluştur
            if success:
                embed = discord.Embed(
                    title="📋 Manuel Kayıt Talebi (Ticket Oluşturuldu)",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
            else:
                embed = discord.Embed(
                    title="❌ Başarısız Manuel Kayıt Talebi",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
            
            # Kullanıcı bilgileri
            embed.add_field(
                name="👤 Kullanıcı Bilgileri",
                value=(
                    f"**Kullanıcı:** {interaction.user.mention}\n"
                    f"**Kullanıcı Adı:** {interaction.user.name}\n"
                    f"**Kullanıcı ID:** `{interaction.user.id}`"
                ),
                inline=False
            )
            
            # Denenen bilgiler
            embed.add_field(
                name="📝 Denenen Bilgiler",
                value=(
                    f"**İsim:** {name}\n"
                    f"**Yaş:** {age_str}\n"
                    f"**Yaş Görünürlüğü:** {show_age_str}"
                ),
                inline=False
            )
            
            # Başarısızlık nedeni veya başarı mesajı
            if success:
                embed.add_field(
                    name="ℹ️ Durum",
                    value="Manuel kayıt için ticket oluşturuldu. Yetkili onayı bekleniyor.",
                    inline=False
                )
            elif reason:
                embed.add_field(
                    name="⚠️ Başarısızlık Nedeni",
                    value=reason,
                    inline=False
                )
            
            embed.set_footer(
                text="HydRaboN Manuel Kayıt Sistemi",
                icon_url=guild.icon.url if guild.icon else None
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"[HATA] Manuel kayıt denemesi loglanırken hata: {type(e).__name__}: {e}")
    
    async def on_submit(self, interaction: discord.Interaction):
        """Modal submit edildiğinde ticket oluştur"""
        await interaction.response.defer(ephemeral=True)
        
        name = self.name_input.value.strip()
        age_str = self.age_input.value.strip()
        show_age_str = self.show_age_input.value.strip().lower()
        
        # Yaş görünürlüğünü parse et
        if show_age_str in ["evet", "e", "yes", "y"]:
            show_age = True
            show_age_text = "✅ Evet"
        else:
            show_age = False
            show_age_text = "❌ Hayır"
        
        try:
            # Yaş doğrulaması
            try:
                age = int(age_str)
                if age < 13 or age > 99:
                    # Başarısız - Geçersiz yaş aralığı
                    await self.log_manual_registration_attempt(
                        interaction, name, age_str, show_age_str, False,
                        "Yaş 13-99 aralığı dışında (Manuel kayıt talebi)"
                    )
                    await self.disable_origin_buttons("Geçersiz yaş! Lütfen 13-99 arası bir yaş giriniz.")
                    return await interaction.followup.send(
                        "❌ Geçersiz yaş! Lütfen 13-99 arası bir yaş giriniz.",
                        ephemeral=True
                    )
            except ValueError:
                # Başarısız - Yaş formatı hatalı
                await self.log_manual_registration_attempt(
                    interaction, name, age_str, show_age_str, False,
                    "Geçersiz yaş formatı (Manuel kayıt talebi)"
                )
                await self.disable_origin_buttons("Geçersiz yaş formatı! Lütfen sadece sayı giriniz.")
                return await interaction.followup.send(
                    "❌ Geçersiz yaş formatı! Lütfen sadece sayı giriniz.",
                    ephemeral=True
                )

            # İsim format kontrolü (sadece harf ve boşluk)
            if not re.match(r'^[a-zA-ZğüşöçıİĞÜŞÖÇ\s]+$', name):
                await self.log_manual_registration_attempt(
                    interaction, name, age_str, show_age_str, False,
                    "İsimde geçersiz karakterler var (Manuel kayıt talebi)"
                )
                await self.disable_origin_buttons("Geçersiz isim formatı! İsim sadece harflerden oluşmalıdır.")
                return await interaction.followup.send(
                    "❌ İsim sadece harflerden oluşmalıdır!",
                    ephemeral=True
                )

            # İsim veritabanında var mı kontrol et - varsa otomatik kayıt yap
            name_valid = await check_name_in_database(name)

            if name_valid:
                # İsim veritabanında bulundu - otomatik kayıt akışını başlat
                # Kayıt log'unu gönder (otomatik kayıt olarak)
                try:
                    log_channel = interaction.guild.get_channel(REGISTRATION_LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="✅ Yetkili Çağır → Otomatik Kayıt",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        log_embed.add_field(
                            name="👤 Kullanıcı Bilgileri",
                            value=(
                                f"**Kullanıcı:** {interaction.user.mention}\n"
                                f"**Kullanıcı Adı:** {interaction.user.name}\n"
                                f"**Kullanıcı ID:** `{interaction.user.id}`"
                            ),
                            inline=False
                        )
                        log_embed.add_field(
                            name="📝 Kayıt Bilgileri",
                            value=(
                                f"**İsim:** {name}\n"
                                f"**Yaş:** {age_str}\n"
                                f"**Yaş Görünürlüğü:** {show_age_text}"
                            ),
                            inline=False
                        )
                        log_embed.add_field(
                            name="ℹ️ Durum",
                            value="İsim veritabanında bulundu. Yetkili çağır yerine otomatik kayıt başlatıldı.",
                            inline=False
                        )
                        log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                        log_embed.set_footer(
                            text="HydRaboN Kayıt Sistemi",
                            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                        )
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"[HATA] Otomatik kayıt log'u gönderilirken hata: {type(e).__name__}: {e}")

                member = interaction.user
                formatted_name = turkish_title_case(name)

                # Bildirim rolleri sorusunu göster (show_age zaten modaldan alındı)
                embed = discord.Embed(
                    title="✅ İsim Doğrulandı - Otomatik Kayıt",
                    description=(
                        f"**İsminiz veritabanında bulundu!** Otomatik kayıt yapılıyor.\n\n"
                        f"**İsim:** {formatted_name}\n"
                        f"**Yaş:** {age}\n"
                        f"**Yaş Görünürlüğü:** {show_age_text}\n\n"
                        "🔔 **Bildirim rolleri almak ister misiniz?**\n\n"
                        "Bildirim rolleri alarak:\n"
                        "• 🎉 Etkinliklerden\n"
                        "• 🎁 Çekiliş duyurularından\n"
                        "• ❓ Günün sorusu kanalından\n"
                        "haberdar olabilirsiniz."
                    ),
                    color=discord.Color.green()
                )
                embed.set_footer(text="İsterseniz rolleri daha sonra da alabilirsiniz")

                view = NotificationRoleConfirmView(self.bot, member, name, age, show_age)
                message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                view.message = message

                # Orijinal mesajdaki butonları güncelle
                if self.origin_view and self.origin_message:
                    try:
                        for item in self.origin_view.children:
                            item.disabled = True
                        success_embed = discord.Embed(
                            title="✅ Otomatik Kayıt Başlatıldı",
                            description="İsminiz veritabanında bulundu, otomatik kayıt işlemi başlatıldı.",
                            color=discord.Color.green()
                        )
                        await self.origin_message.edit(embed=success_embed, view=self.origin_view)
                        self.origin_view.stop()
                    except Exception as e:
                        print(f"[HATA] Orijinal mesaj güncellenirken hata: {type(e).__name__}: {e}")

                return

            # İsim veritabanında bulunamadı - ticket akışına devam et

            # Kategoriyi al
            category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                print(f"[HATA] Ticket kategorisi bulunamadı! Kategori ID: {TICKET_CATEGORY_ID}")
                await self.disable_origin_buttons("Sistem hatası oluştu. Lütfen yetkililere bildirin.")
                return await interaction.followup.send(
                    "❌ Sistem hatası: Ticket kategorisi bulunamadı. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # Kullanıcının zaten bir açık ticket'ı olup olmadığını kontrol et
            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    # Kullanıcının bu kanala erişimi varsa, zaten bir ticket'ı var demektir
                    permissions = channel.permissions_for(interaction.user)
                    if permissions.read_messages and (channel.id != 1364306040727933017 and channel.id != 1364306112022839436):
                        await self.disable_origin_buttons(f"Zaten açık bir destek talebiniz var: {channel.name}")
                        return await interaction.followup.send(
                            f"❌ Zaten açık bir destek talebiniz bulunmaktadır: {channel.mention}\n"
                            "Lütfen mevcut talebinizi tamamlayın veya kapatın.",
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
            
            # YK Üyeleri ve YK Adayları rollerini ekle
            if YK_UYELERI_ROLE_ID != 0:
                yk_uyeleri_role = interaction.guild.get_role(YK_UYELERI_ROLE_ID)
                if yk_uyeleri_role:
                    overwrites[yk_uyeleri_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    )
            
            if YK_ADAYLARI_ROLE_ID != 0:
                yk_adaylari_role = interaction.guild.get_role(YK_ADAYLARI_ROLE_ID)
                if yk_adaylari_role:
                    overwrites[yk_adaylari_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    )
            
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
                    f"**Yaş:** {age}\n"
                    f"**Yaş Görünürlüğü:** {show_age_text}\n\n"
                    "Yetkililere bildirim gönderildi. Lütfen bekleyin."
                ),
                color=discord.Color.orange()
            )
            embed.add_field(
                name="🎭 Kayıt Sonrası Alınabilecek Roller",
                value=(
                    "🎉 **Etkinlik Bildirim** - Sunucu etkinliklerinden haberdar olun\n"
                    "🎁 **Çekiliş Bildirim** - <#1029089842119852114> kanalından haberdar olun\n"
                    "❓ **Günün Sorusu Bildirim** - <#1202362927248846878> kanalından haberdar olun\n\n"
                    f"💡 Kaydınız onaylandıktan sonra <#{ROLE_SELECTION_CHANNEL_ID}> kanalından rolleri alabilirsiniz."
                ),
                inline=False
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Kayıt Destek Sistemi")
            embed.timestamp = discord.utils.utcnow()
            
            # Ticket kontrol view'ı ile gönder (manuel kayıt butonu ekli)
            view = TicketControlView(self.bot, interaction.user, name, age, show_age)
            await ticket_channel.send(
                content=f"{interaction.user.mention}",
                embed=embed,
                view=view
            )
            
            # Başarılı - Ticket oluşturuldu, kayıt log kanalına yaz
            await self.log_manual_registration_attempt(
                interaction, name, age_str, show_age_str, True
            )
            
            # Kullanıcıya başarı mesajı
            await interaction.followup.send(
                f"✅ Destek talebiniz oluşturuldu! {ticket_channel.mention} kanalını kontrol edin.",
                ephemeral=True
            )
            
            # Orijinal onay mesajındaki butonları devre dışı bırak
            await self.disable_origin_buttons()
            
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
                        value=f"**Kanal:** {ticket_channel.mention}\n**İsim:** {name}\n**Yaş:** {age}\n**Yaş Görünürlüğü:** {show_age_text}",
                        inline=False
                    )
                    log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Destek Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Genel log kanalına ticket oluşturma mesajı gönderilirken hata: {type(e).__name__}: {e}")
            
        except discord.Forbidden:
            print(f"[HATA] Ticket kanalı oluşturma yetkisi yok!")
            await self.disable_origin_buttons("Sistem hatası: Yetki eksikliği.")
            await interaction.followup.send(
                "❌ Ticket kanalı oluşturma yetkim yok. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
        except Exception as e:
            print(f"[HATA] Ticket oluşturulurken hata: {type(e).__name__}: {e}")
            await self.disable_origin_buttons("Ticket oluşturulurken bir hata oluştu.")
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


class AgeResetTicketControlView(discord.ui.View):
    """Yaş sıfırlama ticket kontrol butonları (Onay/Ret)"""
    
    def __init__(self, bot: commands.Bot, user_id: int, current_name: str, current_age: int, requested_age: str):
        super().__init__(timeout=None)  # Kalıcı buton
        self.bot = bot
        self.user_id = user_id
        self.current_name = current_name
        self.current_age = current_age
        self.requested_age = requested_age
    
    @discord.ui.button(
        label="Onayla",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="age_reset_approve"
    )
    async def approve_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaş sıfırlama talebini onayla"""
        # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
        if not check_registration_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu işlem için yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            
            if not member:
                return await interaction.followup.send(
                    "❌ Kullanıcı sunucuda bulunamadı!",
                    ephemeral=True
                )
            
            # Yeni yaş bilgisi var mı kontrol et
            if self.requested_age and self.requested_age.strip():
                try:
                    new_age = int(self.requested_age.strip())
                    if new_age < 13 or new_age > 99:
                        return await interaction.followup.send(
                            "❌ Talep edilen yaş geçerli değil (13-99 arası olmalı)!",
                            ephemeral=True
                        )
                except ValueError:
                    return await interaction.followup.send(
                        "❌ Talep edilen yaş geçerli bir sayı değil!",
                        ephemeral=True
                    )
            else:
                # Yaş belirtilmemişse yetkili kendisi girmeli
                return await interaction.followup.send(
                    "❌ Yeni yaş bilgisi belirtilmemiş! Lütfen kullanıcıya doğru yaşı sorup `/kayit` komutuyla manuel olarak güncelleyin.",
                    ephemeral=True
                )
            
            # Veritabanını güncelle
            stats_cog = self.bot.get_cog("RegistrationStats")
            if not stats_cog:
                return await interaction.followup.send(
                    "❌ İstatistik sistemi bulunamadı!",
                    ephemeral=True
                )
            
            # Kullanıcı bilgilerini al
            user_info = await stats_cog.get_user_info(str(self.user_id))
            if not user_info:
                return await interaction.followup.send(
                    "❌ Kullanıcının kayıt bilgisi bulunamadı!",
                    ephemeral=True
                )
            
            name, old_age, registered_at, show_age = user_info
            
            # Yaşı güncelle - veritabanında
            success = await stats_cog.update_user_age(str(self.user_id), new_age)
            
            if not success:
                return await interaction.followup.send(
                    "❌ Veritabanı güncellenirken hata oluştu!",
                    ephemeral=True
                )
            
            # Nickname'i güncelle
            formatted_name = turkish_title_case(name)
            if show_age:
                new_nickname = f"{formatted_name} | {new_age}"
            else:
                new_nickname = formatted_name
            
            try:
                await member.edit(nick=new_nickname, reason=f"Yaş sıfırlama onayı - {interaction.user}")
            except Exception as e:
                print(f"[HATA] Nickname güncellenirken hata: {e}")
            
            # Kullanıcıya DM gönder
            try:
                dm_embed = discord.Embed(
                    title="✅ Yaş Sıfırlama Talebiniz Onaylandı",
                    description=(
                        f"Yaş sıfırlama talebiniz yetkili tarafından onaylandı.\n\n"
                        f"**Eski Yaş:** {self.current_age}\n"
                        f"**Yeni Yaş:** {new_age}\n"
                        f"**Onaylayan Yetkili:** {interaction.user.mention}\n\n"
                        f"Yaşınız başarıyla güncellendi."
                    ),
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                dm_embed.set_footer(text="HydRaboN Yaş Sıfırlama Sistemi")
                await member.send(embed=dm_embed)
            except:
                pass
            
            # Ticket kanalına onay mesajı gönder
            channel_embed = discord.Embed(
                title="✅ Yaş Sıfırlama Talebi Onaylandı",
                description=(
                    f"**Onaylayan Yetkili:** {interaction.user.mention}\n"
                    f"**Kullanıcı:** <@{self.user_id}>\n\n"
                    f"**Eski Yaş:** {self.current_age}\n"
                    f"**Yeni Yaş:** {new_age}\n\n"
                    "Kullanıcının yaşı başarıyla güncellendi.\n"
                    "Bu ticket 10 saniye içinde otomatik olarak kapatılacaktır."
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await interaction.channel.send(embed=channel_embed)
            
            # Log kanalına bildirim
            try:
                log_channel = guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="✅ Yaş Sıfırlama Talebi Onaylandı",
                        description=f"<@{self.user_id}> kullanıcısının yaş sıfırlama talebi onaylandı.",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(
                        name="👤 Kullanıcı",
                        value=f"**ID:** `{self.user_id}`\n**İsim:** {name}",
                        inline=False
                    )
                    log_embed.add_field(
                        name="🔄 Yaş Değişikliği",
                        value=f"**Eski Yaş:** {self.current_age}\n**Yeni Yaş:** {new_age}",
                        inline=True
                    )
                    log_embed.add_field(
                        name="👮 Onaylayan",
                        value=f"{interaction.user.mention}\n**Tag:** {interaction.user}",
                        inline=True
                    )
                    log_embed.set_footer(text="HydRaboN Yaş Sıfırlama Sistemi")
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Log kanalına mesaj gönderilirken hata: {e}")
            
            await interaction.followup.send(
                "✅ Yaş sıfırlama talebi onaylandı ve kullanıcının yaşı güncellendi!",
                ephemeral=True
            )
            
            # Butonları devre dışı bırak
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            # 10 saniye sonra ticket'ı kapat
            import asyncio
            await asyncio.sleep(10)
            try:
                await interaction.channel.delete(reason=f"Yaş sıfırlama onaylandı - {interaction.user}")
            except:
                print("[HATA] Ticket kanalı silinemedi!")
            
        except Exception as e:
            print(f"[HATA] Yaş sıfırlama onaylanırken hata: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Yaş güncellenirken bir hata oluştu!",
                ephemeral=True
            )
    
    @discord.ui.button(
        label="Reddet",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="age_reset_reject"
    )
    async def reject_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaş sıfırlama talebini reddet"""
        # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
        if not check_registration_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu işlem için yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                ephemeral=True
            )
        
        # Red sebebi modal'ı
        class RejectReasonModal(discord.ui.Modal, title="Red Sebebi"):
            reason_input = discord.ui.TextInput(
                label="Red Sebebi",
                placeholder="Neden reddedildiğini açıklayın",
                min_length=5,
                max_length=500,
                required=True,
                style=discord.TextStyle.paragraph
            )
            
            def __init__(self, parent_view):
                super().__init__()
                self.parent_view = parent_view
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.defer(ephemeral=True)
                
                reason = self.reason_input.value.strip()
                
                try:
                    guild = modal_interaction.guild
                    member = guild.get_member(self.parent_view.user_id)
                    
                    # Kullanıcıya DM gönder
                    if member:
                        try:
                            dm_embed = discord.Embed(
                                title="❌ Yaş Sıfırlama Talebiniz Reddedildi",
                                description=(
                                    f"Yaş sıfırlama talebiniz yetkili tarafından reddedildi.\n\n"
                                    f"**Red Sebebi:**\n{reason}\n\n"
                                    f"**Reddeden Yetkili:** {modal_interaction.user.mention}\n\n"
                                    "Daha fazla bilgi için yetkililere ulaşabilirsiniz."
                                ),
                                color=discord.Color.red(),
                                timestamp=discord.utils.utcnow()
                            )
                            dm_embed.set_footer(text="HydRaboN Yaş Sıfırlama Sistemi")
                            await member.send(embed=dm_embed)
                        except:
                            pass
                    
                    # Ticket kanalına red mesajı gönder
                    channel_embed = discord.Embed(
                        title="❌ Yaş Sıfırlama Talebi Reddedildi",
                        description=(
                            f"**Reddeden Yetkili:** {modal_interaction.user.mention}\n"
                            f"**Kullanıcı:** <@{self.parent_view.user_id}>\n\n"
                            f"**Red Sebebi:**\n{reason}\n\n"
                            "Bu ticket 10 saniye içinde otomatik olarak kapatılacaktır."
                        ),
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    await modal_interaction.channel.send(embed=channel_embed)
                    
                    # Log kanalına bildirim
                    try:
                        log_channel = guild.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            log_embed = discord.Embed(
                                title="❌ Yaş Sıfırlama Talebi Reddedildi",
                                description=f"<@{self.parent_view.user_id}> kullanıcısının yaş sıfırlama talebi reddedildi.",
                                color=discord.Color.red(),
                                timestamp=discord.utils.utcnow()
                            )
                            log_embed.add_field(
                                name="👤 Kullanıcı",
                                value=f"**ID:** `{self.parent_view.user_id}`",
                                inline=False
                            )
                            log_embed.add_field(
                                name="📋 Red Sebebi",
                                value=reason,
                                inline=False
                            )
                            log_embed.add_field(
                                name="👮 Reddeden",
                                value=f"{modal_interaction.user.mention}\n**Tag:** {modal_interaction.user}",
                                inline=False
                            )
                            log_embed.set_footer(text="HydRaboN Yaş Sıfırlama Sistemi")
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        print(f"[HATA] Log kanalına mesaj gönderilirken hata: {e}")
                    
                    await modal_interaction.followup.send(
                        "✅ Yaş sıfırlama talebi reddedildi ve kullanıcıya bildirim gönderildi!",
                        ephemeral=True
                    )
                    
                    # Butonları devre dışı bırak
                    for item in self.parent_view.children:
                        item.disabled = True
                    await modal_interaction.message.edit(view=self.parent_view)
                    
                    # 10 saniye sonra ticket'ı kapat
                    import asyncio
                    await asyncio.sleep(10)
                    try:
                        await modal_interaction.channel.delete(reason=f"Yaş sıfırlama reddedildi - {modal_interaction.user}")
                    except:
                        print("[HATA] Ticket kanalı silinemedi!")
                    
                except Exception as e:
                    print(f"[HATA] Yaş sıfırlama reddedilirken hata: {type(e).__name__}: {e}")
                    await modal_interaction.followup.send(
                        "❌ İşlem sırasında bir hata oluştu!",
                        ephemeral=True
                    )
        
        # Modal'ı göster
        try:
            modal = RejectReasonModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[HATA] Red modal açılırken hata: {e}")
            await interaction.response.send_message(
                "❌ Form açılırken bir hata oluştu!",
                ephemeral=True
            )


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
        placeholder="Yeni yaşınızı giriniz.",
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
            
            # Kullanıcının zaten bir açık ticket'ı olup olmadığını kontrol et
            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    # Kullanıcının bu kanala erişimi varsa, zaten bir ticket'ı var demektir
                    permissions = channel.permissions_for(interaction.user)
                    if permissions.read_messages:
                        return await interaction.followup.send(
                            f"❌ Zaten açık bir destek talebiniz bulunmaktadır: {channel.mention}\n"
                            "Lütfen mevcut talebinizi tamamlayın veya kapatın.",
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
            
            # YK Üyeleri ve YK Adayları rollerini ekle
            if YK_UYELERI_ROLE_ID != 0:
                yk_uyeleri_role = interaction.guild.get_role(YK_UYELERI_ROLE_ID)
                if yk_uyeleri_role:
                    overwrites[yk_uyeleri_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    )
            
            if YK_ADAYLARI_ROLE_ID != 0:
                yk_adaylari_role = interaction.guild.get_role(YK_ADAYLARI_ROLE_ID)
                if yk_adaylari_role:
                    overwrites[yk_adaylari_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    )
            
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
            
            # Yaş sıfırlama özel kontrol view'ı ile gönder (Onay/Ret butonları)
            view = AgeResetTicketControlView(
                bot=self.bot,
                user_id=interaction.user.id,
                current_name=self.current_name,
                current_age=self.current_age,
                requested_age=new_age
            )
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
        self.message = None
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
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
        # Embed'i güncelle
        embed = discord.Embed(
            title="✅ İşlem İptal Edildi",
            description="Yaş sıfırlama işleminiz iptal edildi.",
            color=discord.Color.green()
        )
        
        # Butonları devre dışı bırak
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class NotificationRoleSelectView(discord.ui.View):
    """Bildirim rolleri seçim menüsü"""
    
    def __init__(self, bot: commands.Bot, member: discord.Member, name: str, age: int, show_age: bool):
        super().__init__(timeout=60)
        self.bot = bot
        self.member = member
        self.message = None
        self.name = name
        self.age = age
        self.show_age = show_age
        
        # Rol ID'leri
        self.notification_roles = {
            1207713855854223391: "🎉 Etkinlik Bildirim",
            1207713907498688512: "🎁 Çekiliş Bildirim",
            1207713950742085643: "❓ Günün Sorusu Bildirim"
        }
        
        # Seçilen rolleri takip et
        self.selected_roles = set()
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="🎉 Etkinlik", style=discord.ButtonStyle.secondary, row=0)
    async def event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Etkinlik bildirim rolü butonuna basıldığında"""
        role_id = 1207713855854223391
        await self.toggle_role(interaction, role_id, button)
    
    @discord.ui.button(label="🎁 Çekiliş", style=discord.ButtonStyle.secondary, row=0)
    async def giveaway_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Çekiliş bildirim rolü butonuna basıldığında"""
        role_id = 1207713907498688512
        await self.toggle_role(interaction, role_id, button)
    
    @discord.ui.button(label="❓ Günün Sorusu", style=discord.ButtonStyle.secondary, row=0)
    async def qotd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Günün sorusu bildirim rolü butonuna basıldığında"""
        role_id = 1207713950742085643
        await self.toggle_role(interaction, role_id, button)
    
    @discord.ui.button(label="✅ Tamamla", style=discord.ButtonStyle.success, row=1)
    async def complete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Tamamla butonuna basıldığında"""
        # Seçilen rol ID'lerini listeye çevir
        selected_role_ids = list(self.selected_roles)
        
        # Kayıt işlemini tamamla
        age_view = AgeVisibilityView(self.bot, self.member, self.name, self.age)
        age_view.show_age = self.show_age
        await age_view.complete_registration(interaction, selected_role_ids)
    
    async def toggle_role(self, interaction: discord.Interaction, role_id: int, button: discord.ui.Button):
        """Rol seçimini toggle et"""
        if role_id in self.selected_roles:
            # Rolü kaldır
            self.selected_roles.remove(role_id)
            button.style = discord.ButtonStyle.secondary
        else:
            # Rolü ekle
            self.selected_roles.add(role_id)
            button.style = discord.ButtonStyle.primary
        
        # Embed'i güncelle
        embed = discord.Embed(
            title="🔔 Bildirim Rollerini Seçin",
            description=(
                "Aşağıdaki butonlarla almak istediğiniz bildirim rollerini seçebilirsiniz.\n"
                "Seçtikten sonra **Tamamla** butonuna tıklayın.\n\n"
                f"**Seçilen Roller:** {len(self.selected_roles)}/3"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


class NotificationRoleConfirmView(discord.ui.View):
    """Bildirim rolleri onay view'ı"""
    
    def __init__(self, bot: commands.Bot, member: discord.Member, name: str, age: int, show_age: bool):
        super().__init__(timeout=60)
        self.bot = bot
        self.member = member
        self.name = name
        self.age = age
        self.show_age = show_age
        self.message = None
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="Evet", style=discord.ButtonStyle.success, emoji="✅")
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Evet butonuna basıldığında rol seçim menüsünü göster"""
        embed = discord.Embed(
            title="🔔 Bildirim Rollerini Seçin",
            description=(
                "Aşağıdaki butonlarla almak istediğiniz bildirim rollerini seçebilirsiniz.\n"
                "Seçtikten sonra **Tamamla** butonuna tıklayın.\n\n"
                "**Seçilen Roller:** 0/3"
            ),
            color=discord.Color.blue()
        )
        
        view = NotificationRoleSelectView(self.bot, self.member, self.name, self.age, self.show_age)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Hayır", style=discord.ButtonStyle.secondary, emoji="❌")
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Hayır butonuna basıldığında direkt kayıt tamamla"""
        age_view = AgeVisibilityView(self.bot, self.member, self.name, self.age)
        age_view.show_age = self.show_age
        await age_view.complete_registration(interaction, selected_roles=None)


class AgeVisibilityView(discord.ui.View):
    """Yaş görünürlüğü seçim butonu"""
    
    def __init__(self, bot: commands.Bot, member: discord.Member, name: str, age: int):
        super().__init__(timeout=60)  # 60 saniye timeout
        self.bot = bot
        self.member = member
        self.name = name
        self.age = age
        self.show_age = None  # Kullanıcının seçimi
        self.message = None
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="Yaşımı Göster", style=discord.ButtonStyle.success, emoji="✅")
    async def show_age_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaşı göster butonuna basıldığında"""
        self.show_age = True
        await self.ask_notification_roles(interaction)
    
    @discord.ui.button(label="Yaşımı Gizle", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def hide_age_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yaşı gizle butonuna basıldığında"""
        self.show_age = False
        await self.ask_notification_roles(interaction)
    
    async def ask_notification_roles(self, interaction: discord.Interaction):
        """Bildirim rolleri sorgusunu göster"""
        embed = discord.Embed(
            title="🔔 Bildirim Rolleri",
            description=(
                "**Etkinliklerden, çekilişlerden ve günün sorularından haberdar olmak ister misiniz?**\n\n"
                "Bildirim rolleri alarak:\n"
                "• 🎉 Etkinliklerden\n"
                "• 🎁 Çekiliş duyurularından\n"
                "• ❓ Günün sorusu kanalından\n"
                "haberdar olabilirsiniz.\n\n"
                "Rolleri almak ister misiniz?"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="İsterseniz rolleri daha sonra da alabilirsiniz")
        
        view = NotificationRoleConfirmView(self.bot, self.member, self.name, self.age, self.show_age)
        view.message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def complete_registration(self, interaction: discord.Interaction, selected_roles: list = None):
        """Kayıt işlemini tamamla"""
        # Not: Burada defer kullanmıyoruz çünkü embed'i güncelleyeceğiz
        
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
                error_embed = discord.Embed(
                    title="❌ Sistem Hatası",
                    description="Kayıt işlemi sırasında bir hata oluştu. Lütfen yetkililere bildirin.",
                    color=discord.Color.red()
                )
                return await interaction.response.edit_message(embed=error_embed, view=None)
            
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
                error_embed = discord.Embed(
                    title="❌ Sistem Hatası",
                    description="Kayıt işlemi sırasında bir hata oluştu. Lütfen yetkililere bildirin.",
                    color=discord.Color.red()
                )
                return await interaction.response.edit_message(embed=error_embed, view=None)
            
            # İsmi değiştir
            try:
                await self.member.edit(nick=new_nickname, reason="Kayıt işlemi")
            except Exception as e:
                print(f"[HATA] İsim değiştirilirken hata: {e}")
            
            # Bildirim rollerini ver (eğer seçildiyse)
            if selected_roles:
                for role_id in selected_roles:
                    try:
                        role = guild.get_role(role_id)
                        if role:
                            await self.member.add_roles(role, reason="Kayıt sırasında bildirim rolü seçimi")
                    except Exception as e:
                        print(f"[HATA] Bildirim rolü eklenirken hata (Rol ID: {role_id}): {e}")
            
            # Kullanıcıya başarı mesajı gönder
            visibility_status = "Görünür" if self.show_age else "Gizli"
            
            description = f"**İsim:** {formatted_name}\n**Yaş:** {self.age}\n**Yaş Durumu:** {visibility_status}\n**Yeni İsim:** {new_nickname}"
            
            if selected_roles:
                role_names = []
                for role_id in selected_roles:
                    role = guild.get_role(role_id)
                    if role:
                        role_names.append(role.name)
                if role_names:
                    description += f"\n**Bildirim Rolleri:** {', '.join(role_names)}"
            
            success_embed = discord.Embed(
                title="✅ Kayıt Başarılı!",
                description=description,
                color=discord.Color.green()
            )
            success_embed.set_footer(text="Yaş görünürlüğünü ve rolleri /kayit-ayarlari komutuyla değiştirebilirsiniz.")
            
            # Mevcut embed'i güncelle (view'ı kaldır)
            await interaction.response.edit_message(embed=success_embed, view=None)
            
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
                    
                    # Rol değişiklikleri
                    role_changes = f"**Verilen:** <@&{REGISTERED_ROLE_ID}>\n**Alınan:** <@&{UNREGISTERED_ROLE_ID}>"
                    if selected_roles:
                        role_mentions = " ".join([f"<@&{role_id}>" for role_id in selected_roles])
                        role_changes += f"\n**Bildirim Rolleri:** {role_mentions}"
                    
                    log_embed.add_field(
                        name="🎭 Rol Değişiklikleri",
                        value=role_changes,
                        inline=False
                    )
                    log_embed.set_thumbnail(url=self.member.display_avatar.url)
                    log_embed.set_footer(text="HydRaboN Kayıt Sistemi", icon_url=guild.icon.url if guild.icon else None)
                    
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Log kanalına mesaj gönderilirken hata: {type(e).__name__}: {e}")
            
            # Hoş geldin mesajı gönder
            try:
                welcome_cog = self.bot.get_cog("Welcome")
                if welcome_cog:
                    await welcome_cog.send_welcome_message(self.member)
            except Exception as e:
                print(f"[HATA] Hoş geldin mesajı gönderilirken hata: {type(e).__name__}: {e}")
                
        except Exception as e:
            print(f"[HATA] Beklenmeyen kayıt hatası: {type(e).__name__}: {e}")
            error_embed = discord.Embed(
                title="❌ Beklenmeyen Hata",
                description="Kayıt işlemi sırasında beklenmeyen bir hata oluştu. Lütfen yetkililere bildirin.",
                color=discord.Color.red()
            )
            try:
                await interaction.response.edit_message(embed=error_embed, view=None)
            except:
                # Eğer zaten response edildiyse followup kullan
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        
        self.stop()


class NewAccountSupportView(discord.ui.View):
    """Yeni hesaplar için yetkili çağırma butonu"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)  # 5 dakika timeout - kullanıcıya formu doldurması için yeterli süre
        self.bot = bot
        self.message = None
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="Yetkili Çağır", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yetkili çağır butonuna basıldığında modal aç"""
        try:
            modal = SupportTicketModal(self.bot, origin_view=self, origin_message=self.message)
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
        super().__init__(timeout=300)  # 5 dakika timeout - kullanıcıya formu doldurması için yeterli süre
        self.bot = bot
        self.message = None
    
    async def on_timeout(self):
        """Timeout olduğunda butonları devre dışı bırak"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="Evet", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Evet butonuna basıldığında modal aç"""
        try:
            modal = SupportTicketModal(self.bot, origin_view=self, origin_message=self.message)
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
        # Embed'i güncelle
        embed = discord.Embed(
            title="✅ İşlem İptal Edildi",
            description="Yetkili çağırma işleminiz iptal edildi.",
            color=discord.Color.green()
        )
        
        # Butonları devre dışı bırak
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
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
            
            # Hesap yaşı kontrolü (14 gün)
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
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                view.message = await interaction.original_response()
                return
            
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
            member = interaction.user
            
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
            view.message = await interaction.original_response()
            
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
        name="kayit-embed",
        description="Kayıt embed'ini belirtilen kanala gönderir"
    )
    @app_commands.default_permissions(administrator=True)
    async def send_registration_embed(
        self,
        interaction: discord.Interaction,
        kanal: Optional[discord.TextChannel] = None
    ):
        """Kayıt embed'ini gönderir"""
        
        # Owner kontrolü
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message(
                "❌ Bu komutu kullanma yetkiniz bulunmamaktadır.",
                ephemeral=True
            )
        
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
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1362825668965957845/1459650495890329833/a2.png?ex=69640cf5&is=6962bb75&hm=0690e7e22e7f4e78cd5298e00eeb298d8cfae9668c88a92764bd9b44320b39a3&=&format=webp&quality=lossless")
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
        name="kayit-sifirla",
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
        
        # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
        if not check_registration_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu komutu kullanma yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                ephemeral=True
            )
        
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
        
        # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
        if not check_registration_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu komutu kullanma yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                ephemeral=True
            )
        
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
            
            # Anasayfaya dönüş view'ı
            class BackToSettingsView(discord.ui.View):
                def __init__(self, bot, stats_cog, member, name, age, current_show_age):
                    super().__init__(timeout=300)
                    self.bot = bot
                    self.stats_cog = stats_cog
                    self.member = member
                    self.name = name
                    self.age = age
                    self.current_show_age = current_show_age
                    self.message = None
                
                async def on_timeout(self):
                    """Timeout olduğunda butonları devre dışı bırak"""
                    if self.message:
                        try:
                            for item in self.children:
                                item.disabled = True
                            await self.message.edit(view=self)
                        except:
                            pass
                
                @discord.ui.button(label="Ana Sayfaya Dön", style=discord.ButtonStyle.primary, emoji="🏠")
                async def back_to_home(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Ana ayarlar sayfasına dön"""
                    # interaction.user her seferinde Discord'dan gelen güncel member verisini taşır
                    main_view = RegistrationSettingsView(
                        self.bot, self.stats_cog, interaction.user,
                        self.name, self.age, self.current_show_age, self.message
                    )
                    embed = main_view.create_main_embed()
                    await interaction.response.edit_message(embed=embed, view=main_view)
            
            # Rol yönetimi için geri dönüş view'ı
            class RoleManageViewWithBack(discord.ui.View):
                def __init__(self, member, bot, stats_cog, name, age, current_show_age):
                    super().__init__(timeout=300)
                    self.member = member
                    self.bot = bot
                    self.stats_cog = stats_cog
                    self.name = name
                    self.age = age
                    self.current_show_age = current_show_age
                    self.message = None
                    self.add_item(RoleManageSelect(member, self))
                
                async def on_timeout(self):
                    """Timeout olduğunda butonları devre dışı bırak"""
                    if self.message:
                        try:
                            for item in self.children:
                                item.disabled = True
                            await self.message.edit(view=self)
                        except:
                            pass
                
                @discord.ui.button(label="Ana Sayfaya Dön", style=discord.ButtonStyle.secondary, emoji="🏠", row=1)
                async def back_to_home(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Ana ayarlar sayfasına dön"""
                    # interaction.user her seferinde Discord'dan gelen güncel member verisini taşır
                    main_view = RegistrationSettingsView(
                        self.bot, self.stats_cog, interaction.user,
                        self.name, self.age, self.current_show_age, self.message
                    )
                    embed = main_view.create_main_embed()
                    await interaction.response.edit_message(embed=embed, view=main_view)
            
            # Yaş sıfırlama onay view'ı geri dönüş ile
            class AgeResetConfirmWithBackView(discord.ui.View):
                def __init__(self, bot, current_name, current_age, stats_cog, member, current_show_age):
                    super().__init__(timeout=300)
                    self.bot = bot
                    self.current_name = current_name
                    self.current_age = current_age
                    self.stats_cog = stats_cog
                    self.member = member
                    self.current_show_age = current_show_age
                    self.message = None
                
                async def on_timeout(self):
                    """Timeout olduğunda butonları devre dışı bırak"""
                    if self.message:
                        try:
                            for item in self.children:
                                item.disabled = True
                            await self.message.edit(view=self)
                        except:
                            pass
                
                @discord.ui.button(label="Evet, Ticket Aç", style=discord.ButtonStyle.danger, emoji="✅", row=0)
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
                
                @discord.ui.button(label="Hayır, İptal Et", style=discord.ButtonStyle.secondary, emoji="❌", row=0)
                async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Yaş sıfırlama iptal edildi"""
                    embed = discord.Embed(
                        title="✅ İşlem İptal Edildi",
                        description="Yaş sıfırlama işleminiz iptal edildi.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Ana sayfaya dönmek için aşağıdaki butona tıklayın")
                    
                    # Geri dön view'ı
                    back_view = BackToSettingsView(
                        self.bot, self.stats_cog, self.member,
                        self.current_name, self.current_age, self.current_show_age
                    )
                    back_view.message = self.message
                    await interaction.response.edit_message(embed=embed, view=back_view)
                
                @discord.ui.button(label="Ana Sayfaya Dön", style=discord.ButtonStyle.primary, emoji="🏠", row=1)
                async def back_to_home(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Ana ayarlar sayfasına dön"""
                    main_view = RegistrationSettingsView(
                        self.bot, self.stats_cog, self.member,
                        self.current_name, self.current_age, self.current_show_age, self.message
                    )
                    embed = main_view.create_main_embed()
                    await interaction.response.edit_message(embed=embed, view=main_view)
            
            # Rol düzenleme select menu
            class RoleManageSelect(discord.ui.Select):
                def __init__(self, member: discord.Member, parent_view):
                    self.member = member
                    self.parent_view = parent_view
                    
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
                    await interaction.response.defer()

                    try:
                        # Her interaction Discord'dan güncel member verisi getirir;
                        # self.member eski interaction'dan kalmış olabilir.
                        member = interaction.user

                        # Seçilen rol ID'leri
                        selected_role_ids = [int(value) for value in self.values]

                        # Sadece seçilen rolleri toggle et
                        added_roles = []
                        removed_roles = []

                        # Sadece seçilen roller üzerinde işlem yap
                        for role_id in selected_role_ids:
                            role = member.guild.get_role(role_id)
                            if not role:
                                continue

                            has_role = role in member.roles

                            if has_role:
                                # Rol kullanıcıda var, kaldır (toggle)
                                try:
                                    await member.remove_roles(role, reason="Kullanıcı rol yönetimi - toggle")
                                    removed_roles.append(role.name)
                                except Exception as e:
                                    print(f"[HATA] Rol kaldırılırken hata ({role.name}): {e}")
                            else:
                                # Rol kullanıcıda yok, ekle (toggle)
                                try:
                                    await member.add_roles(role, reason="Kullanıcı rol yönetimi - toggle")
                                    added_roles.append(role.name)
                                except Exception as e:
                                    print(f"[HATA] Rol eklenirken hata ({role.name}): {e}")
                        
                        # Sonuç mesajı
                        result_parts = []
                        if added_roles:
                            result_parts.append(f"**Eklenen Roller:** {', '.join(added_roles)}")
                        if removed_roles:
                            result_parts.append(f"**Kaldırılan Roller:** {', '.join(removed_roles)}")
                        
                        if not result_parts:
                            result_msg = "Herhangi bir değişiklik yapılmadı."
                            embed_color = discord.Color.orange()
                        else:
                            result_msg = "\n\n".join(result_parts)
                            embed_color = discord.Color.green()
                        
                        embed = discord.Embed(
                            title="✅ Roller Güncellendi!",
                            description=result_msg,
                            color=embed_color
                        )
                        embed.set_footer(text="Ana sayfaya dönmek için aşağıdaki butona tıklayın")
                        
                        # Geri dön view'ı
                        back_view = BackToSettingsView(
                            self.parent_view.bot,
                            self.parent_view.stats_cog,
                            interaction.user,
                            self.parent_view.name,
                            self.parent_view.age,
                            self.parent_view.current_show_age
                        )
                        back_view.message = self.parent_view.message
                        await interaction.edit_original_response(embed=embed, view=back_view)
                        
                    except Exception as e:
                        print(f"[HATA] Rol yönetimi hatası: {e}")
                        await interaction.followup.send(
                            "❌ Roller güncellenirken bir hata oluştu!",
                            ephemeral=True
                        )
            
            # Ana ayarlar view'ı
            class RegistrationSettingsView(discord.ui.View):
                def __init__(self, bot, stats_cog, member, name, age, current_show_age, message=None):
                    super().__init__(timeout=300)  # 5 dakika
                    self.bot = bot
                    self.stats_cog = stats_cog
                    self.member = member
                    self.name = name
                    self.age = age
                    self.current_show_age = current_show_age
                    self.message = message
                
                async def on_timeout(self):
                    """Timeout olduğunda butonları devre dışı bırak"""
                    if self.message:
                        try:
                            for item in self.children:
                                item.disabled = True
                            
                            # Timeout mesajını embed'e ekle
                            embed = self.message.embeds[0] if self.message.embeds else discord.Embed(
                                title="⚙️ Kayıt Ayarları",
                                description="⏱️ Oturum süresi doldu. Yeni bir ayar yapmak için `/kayit-ayarlari` komutunu tekrar kullanın.",
                                color=discord.Color.grayed_out()
                            )
                            embed.set_footer(text="⏱️ Bu oturum sona erdi")
                            
                            await self.message.edit(embed=embed, view=self)
                        except Exception as e:
                            print(f"[HATA] Timeout mesajı güncellenirken hata: {e}")
                
                def create_main_embed(self):
                    """Ana sayfa embed'ini oluştur"""
                    current_status = "Görünür ✅" if self.current_show_age else "Gizli 👁️"
                    
                    embed = discord.Embed(
                        title="⚙️ Kayıt Ayarları",
                        description=(
                            f"**Kayıt Bilgileriniz:**\n"
                            f"• İsim: {self.name}\n"
                            f"• Yaş: {self.age}\n"
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
                        ).format(self.name, self.age),
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="Aşağıdaki butonları kullanarak ayarlarınızı değiştirebilirsiniz")
                    return embed
                
                @discord.ui.button(label="Yaşımı Göster", style=discord.ButtonStyle.success, emoji="✅", row=0)
                async def show_age(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_age(interaction, True)
                
                @discord.ui.button(label="Yaşımı Gizle", style=discord.ButtonStyle.secondary, emoji="👁️", row=0)
                async def hide_age(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_age(interaction, False)

                @discord.ui.button(label="Yaşımı Sıfırla", style=discord.ButtonStyle.danger, emoji="🔄", row=0)
                async def reset_age(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Yaş sıfırlama onay sayfasını göster"""
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
                        
                        # Yaş sıfırlama view'ını ana view ile bağla
                        confirm_view = AgeResetConfirmWithBackView(
                            self.bot, self.name, self.age,
                            self.stats_cog, self.member, self.current_show_age
                        )
                        confirm_view.message = self.message
                        await interaction.response.edit_message(embed=embed, view=confirm_view)
                        
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
                                "• Menüden değiştirmek istediğiniz rolleri seçin\n"
                                "• Seçtiğiniz rol varsa kaldırılır, yoksa eklenir\n"
                                "• Hiçbir rol seçmezseniz hiçbir değişiklik yapılmaz\n\n"
                                "✅ = Şu anda aktif\n"
                                "❌ = Şu anda pasif"
                            ),
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text="Değişiklikler anında uygulanacaktır")
                        
                        # interaction.user Discord'dan gelen güncel member verisini taşır;
                        # self.member eski interaction'dan kalıp stale olabilir
                        role_view = RoleManageViewWithBack(
                            interaction.user,
                            self.bot, self.stats_cog, self.name, self.age, self.current_show_age
                        )
                        role_view.message = self.message
                        await interaction.response.edit_message(embed=embed, view=role_view)
                        
                    except Exception as e:
                        print(f"[HATA] Rol yönetim menüsü açılırken hata: {e}")
                        await interaction.response.send_message(
                            "❌ Rol yönetim menüsü açılırken bir hata oluştu!",
                            ephemeral=True
                        )
                
                async def toggle_age(self, interaction: discord.Interaction, show_age: bool):
                    await interaction.response.defer()
                    
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
                        
                        # Ayarı güncelle
                        self.current_show_age = show_age
                        visibility_status = "Görünür ✅" if show_age else "Gizli 👁️"
                        action_text = "gösterilecek" if show_age else "gizlenecek"
                        
                        # Onay sayfası
                        embed = discord.Embed(
                            title="✅ Yaş Görünürlüğü Güncellendi!",
                            description=f"Yaş görünürlüğünüz başarıyla değiştirildi.",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Yeni Durum", value=visibility_status, inline=True)
                        embed.add_field(name="Yeni İsim", value=new_nickname, inline=True)
                        embed.add_field(
                            name="📝 Bilgi",
                            value=f"Artık yaşınız kullanıcı adınızda {action_text}.",
                            inline=False
                        )
                        embed.set_footer(text="Ana sayfaya dönmek için aşağıdaki butona tıklayın")
                        
                        # Geri dön view'ı
                        back_view = BackToSettingsView(
                            self.bot, self.stats_cog, self.member,
                            self.name, self.age, self.current_show_age
                        )
                        back_view.message = self.message
                        await interaction.edit_original_response(embed=embed, view=back_view)
                        
                    except Exception as e:
                        print(f"[HATA] Yaş görünürlüğü değiştirme hatası: {e}")
                        await interaction.followup.send(
                            "❌ Beklenmeyen bir hata oluştu.",
                            ephemeral=True
                        )
            
            view = RegistrationSettingsView(self.bot, stats_cog, interaction.user, name, age, show_age)
            embed = view.create_main_embed()
            
            message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            view.message = message
            
        except Exception as e:
            print(f"[HATA] Kayıt ayarları hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="isim-kontrol",
        description="Veritabanında isim kontrolü yapar"
    )
    @app_commands.default_permissions(administrator=True)
    async def check_name(
        self,
        interaction: discord.Interaction,
        isim: str
    ):
        """Veritabanında ismin var olup olmadığını kontrol eder"""
        
        # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
        if not check_registration_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu komutu kullanma yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # İsmi normalleştir
            normalized_name = normalize_turkish(isim.strip())
            name_parts = normalized_name.split()
            
            # Veritabanında kontrol
            results = {}
            async with aiosqlite.connect("names.db") as db:
                for part in name_parts:
                    cursor = await db.execute(
                        "SELECT name FROM names WHERE name_norm_tr = ? LIMIT 1",
                        (part,)
                    )
                    result = await cursor.fetchone()
                    results[part] = result is not None
            
            # Sonuç embed'i oluştur
            all_found = all(results.values())
            
            embed = discord.Embed(
                title="🔍 İsim Kontrol Sonucu",
                color=discord.Color.green() if all_found else discord.Color.red()
            )
            
            embed.add_field(
                name="📝 Kontrol Edilen İsim",
                value=f"`{isim.strip()}`",
                inline=False
            )
            
            # Her bir isim parçası için sonuç
            if len(name_parts) > 1:
                parts_status = []
                for part, found in results.items():
                    status = "✅ Bulundu" if found else "❌ Bulunamadı"
                    parts_status.append(f"**{turkish_title_case(part)}**: {status}")
                
                embed.add_field(
                    name="🔎 Parçalar",
                    value="\n".join(parts_status),
                    inline=False
                )
            
            # Genel durum
            if all_found:
                embed.add_field(
                    name="✅ Durum",
                    value="Tüm isim parçaları veritabanında mevcut.",
                    inline=False
                )
            else:
                missing_parts = [turkish_title_case(part) for part, found in results.items() if not found]
                embed.add_field(
                    name="❌ Durum",
                    value=f"Şu parçalar veritabanında bulunamadı: {', '.join(missing_parts)}",
                    inline=False
                )
            
            embed.set_footer(text=f"Kontrol eden: {interaction.user.name}")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"[HATA] İsim kontrol hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ İsim kontrolü sırasında bir hata oluştu.",
                ephemeral=True
            )


    @app_commands.command(
        name="isim-ekle",
        description="Veritabanına yeni isim(ler) ekler (virgülle ayırarak birden fazla isim girilebilir)"
    )
    @app_commands.default_permissions(administrator=True)
    async def add_name(
        self,
        interaction: discord.Interaction,
        isimler: str
    ):
        """İsim veritabanına yeni kayıt ekler"""

        # Yetkilendirme kontrolü (YK Üyeleri, YK Adayları ve Yöneticiler)
        if not check_registration_permission(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu komutu kullanma yetkiniz bulunmamaktadır! (YK Üyeleri, YK Adayları veya Yönetici yetkisi gereklidir)",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # Virgülle ayrılmış isimleri parçala
        raw_names = [n.strip() for n in isimler.split(",") if n.strip()]

        if not raw_names:
            return await interaction.followup.send(
                "❌ Geçerli bir isim girilmedi.",
                ephemeral=True
            )

        if len(raw_names) > 20:
            return await interaction.followup.send(
                "❌ Tek seferde en fazla 20 isim eklenebilir.",
                ephemeral=True
            )

        # Format kontrolü: sadece harf ve boşluk
        invalid_names = [
            n for n in raw_names
            if not re.match(r'^[a-zA-ZğüşöçıİĞÜŞÖÇ\s]+$', n)
        ]
        if invalid_names:
            return await interaction.followup.send(
                f"❌ Geçersiz karakter içeren isimler: {', '.join(f'`{n}`' for n in invalid_names)}\n"
                "İsimler sadece harflerden oluşmalıdır.",
                ephemeral=True
            )

        added: list[str] = []
        skipped: list[str] = []

        try:
            async with aiosqlite.connect("names.db") as db:
                for name in raw_names:
                    formatted = turkish_title_case(name)
                    normalized = normalize_turkish(name)

                    cursor = await db.execute(
                        "SELECT 1 FROM names WHERE name_norm_tr = ? LIMIT 1",
                        (normalized,)
                    )
                    if await cursor.fetchone():
                        skipped.append(formatted)
                    else:
                        await db.execute(
                            "INSERT INTO names (name, name_norm_tr) VALUES (?, ?)",
                            (formatted, normalized)
                        )
                        added.append(formatted)

                await db.commit()
        except Exception as e:
            print(f"[HATA] İsim ekleme hatası: {type(e).__name__}: {e}")
            return await interaction.followup.send(
                "❌ Veritabanına yazılırken bir hata oluştu.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📝 İsim Ekleme Sonucu",
            color=discord.Color.green() if added else discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        if added:
            embed.add_field(
                name=f"✅ Eklenen İsimler ({len(added)})",
                value=", ".join(f"`{n}`" for n in added),
                inline=False
            )
        if skipped:
            embed.add_field(
                name=f"⚠️ Zaten Mevcut ({len(skipped)})",
                value=", ".join(f"`{n}`" for n in skipped),
                inline=False
            )

        embed.set_footer(text=f"İşlem yapan: {interaction.user.name}")
        await interaction.followup.send(embed=embed, ephemeral=True)

        # Log kanalına bildir (sadece yeni isim eklendiyse)
        if not added:
            return
        try:
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="📝 Veritabanına İsim Eklendi",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                log_embed.add_field(
                    name=f"➕ Eklenen İsimler ({len(added)})",
                    value=", ".join(f"`{n}`" for n in added),
                    inline=False
                )
                log_embed.add_field(
                    name="👮 İşlem Yapan",
                    value=f"{interaction.user.mention} (`{interaction.user.id}`)",
                    inline=False
                )
                log_embed.set_footer(
                    text="HydRaboN İsim Veritabanı",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                )
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"[HATA] Log kanalına isim ekleme mesajı gönderilirken hata: {type(e).__name__}: {e}")


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(Registration(bot))

