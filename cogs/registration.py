import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import re
from typing import Optional

# Türkçe karakter normalleştirme
def normalize_turkish(text: str) -> str:
    """Türkçe karakterleri normalize eder (küçük harf)"""
    tr_map = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")
    return text.translate(tr_map).lower()

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
        
        # Başarılı kayıt - İşlemleri başlat
        member = interaction.user
        guild = interaction.guild
        
        # Rol ID'leri
        UNREGISTERED_ROLE_ID = 1428496119213588521  # Alınacak rol
        REGISTERED_ROLE_ID = 1029089740022095973    # Verilecek rol
        LOG_CHANNEL_ID = 1365956201539571835        # Log kanalı
        
        # Yeni nickname: İsim | Yaş
        new_nickname = f"{name} | {age}"
        
        try:
            # Rolleri al
            unregistered_role = guild.get_role(UNREGISTERED_ROLE_ID)
            registered_role = guild.get_role(REGISTERED_ROLE_ID)
            
            # Rol kontrolü
            if not registered_role:
                print(f"[HATA] Kayıtlı rolü bulunamadı! Rol ID: {REGISTERED_ROLE_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası oluştu. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # Kayıtsız rolünü kaldır
            try:
                if unregistered_role and unregistered_role in member.roles:
                    await member.remove_roles(unregistered_role, reason="Kayıt işlemi")
            except discord.Forbidden:
                print(f"[HATA] Kayıtsız rolü kaldırma yetkisi yok! Rol: {unregistered_role.name if unregistered_role else 'Bulunamadı'}")
            except Exception as e:
                print(f"[HATA] Kayıtsız rolü kaldırılırken hata: {e}")
            
            # Kayıtlı rolünü ver
            try:
                await member.add_roles(registered_role, reason="Kayıt işlemi")
            except discord.Forbidden:
                print(f"[HATA] Rol verme yetkisi yok! Bot rolü, hedef rolden daha üstte olmalı. Rol: {registered_role.name}")
                return await interaction.followup.send(
                    "❌ Sistem hatası oluştu. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            except Exception as e:
                print(f"[HATA] Rol verilirken hata: {e}")
                return await interaction.followup.send(
                    "❌ Sistem hatası oluştu. Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # İsmi değiştir
            try:
                await member.edit(nick=new_nickname, reason="Kayıt işlemi")
            except discord.Forbidden:
                print(f"[HATA] İsim değiştirme yetkisi yok! Bot rolü hedef kullanıcıdan daha üstte olmalı.")
                # İsim değiştirilemese de kayıt devam etsin
            except Exception as e:
                print(f"[HATA] İsim değiştirilirken hata: {e}")
                # İsim değiştirilemese de kayıt devam etsin
            
            # Kullanıcıya başarı mesajı gönder
            embed = discord.Embed(
                title="✅ Kayıt Başarılı!",
                description=f"**İsim:** {name}\n**Yaş:** {age}\n**Yeni İsim:** {new_nickname}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Kayıt olan: {member.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # İstatistik veritabanına kaydet
            try:
                stats_cog = self.bot.get_cog("RegistrationStats")
                if stats_cog:
                    await stats_cog.add_registration(
                        user_id=str(member.id),
                        username=str(member),
                        name=name,
                        age=age
                    )
            except Exception as e:
                print(f"[HATA] İstatistik veritabanına kaydedilirken hata: {type(e).__name__}: {e}")
            
            # Log kanalına bildirim gönder
            try:
                log_channel = guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="📝 Yeni Kayıt",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(name="Kullanıcı", value=f"{member.mention} ({member.id})", inline=False)
                    log_embed.add_field(name="İsim", value=name, inline=True)
                    log_embed.add_field(name="Yaş", value=str(age), inline=True)
                    log_embed.add_field(name="Yeni İsim", value=new_nickname, inline=False)
                    log_embed.set_thumbnail(url=member.display_avatar.url)
                    log_embed.set_footer(text=f"Kayıt Sistemi")
                    
                    await log_channel.send(embed=log_embed)
                else:
                    print(f"[HATA] Log kanalı bulunamadı! Kanal ID: {LOG_CHANNEL_ID}")
            except discord.Forbidden:
                print(f"[HATA] Log kanalına mesaj gönderme yetkisi yok!")
            except Exception as e:
                print(f"[HATA] Log kanalına mesaj gönderilirken hata: {e}")
                
        except Exception as e:
            print(f"[HATA] Beklenmeyen kayıt hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu. Lütfen yetkililere bildirin.",
                ephemeral=True
            )
    
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
        
        LOG_CHANNEL_ID = 1364306112022839436
        
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
            
            # Log kanalına gönder
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                # Log embed'i
                log_embed = discord.Embed(
                    title="🔒 Ticket Kapatıldı",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                log_embed.add_field(name="Kanal", value=channel.name, inline=True)
                log_embed.add_field(name="Kapatan", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="Mesaj Sayısı", value=str(len(messages)), inline=True)
                
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
                print(f"[HATA] Log kanalı bulunamadı! Kanal ID: {LOG_CHANNEL_ID}")
            
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
        
        TICKET_CATEGORY_ID = 1364301691637338132
        
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
    
    @discord.ui.button(
        label="Kayıt Ol",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="registration_button",
        row=0
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kayıt Ol butonuna tıklandığında"""
        try:
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
    
    @discord.ui.button(
        label="Web Sitemiz",
        style=discord.ButtonStyle.link,
        emoji="🌐",
        url="https://hydrabon.com/",
        row=0
    )
    async def website_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Web sitesi butonu - Link butonu olduğu için bu fonksiyon çağrılmaz"""
        pass
    
    @discord.ui.button(
        label="Yetkili Çağır",
        style=discord.ButtonStyle.secondary,
        emoji="⚠️",
        custom_id="support_button",
        row=0
    )
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            title="🎉 Hoş Geldiniz!",
            description=(
                "**Sunucumuza hoş geldiniz!**\n\n"
                "Kayıt olmak için aşağıdaki **Kayıt Ol** butonuna tıklayınız.\n"
                "Açılacak formda gerçek isminizi ve yaşınızı giriniz.\n\n"
                "**Not:** Girdiğiniz isim geçerli bir Türkçe isim olmalıdır."
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
        name="kayit_sifirla",
        description="Seçilen kullanıcının kaydını sıfırlar"
    )
    @app_commands.default_permissions(administrator=True)
    async def reset_registration(
        self,
        interaction: discord.Interaction,
        kullanici: discord.Member
    ):
        """Kullanıcının kaydını sıfırlar"""
        
        await interaction.response.defer(ephemeral=True)
        
        UNREGISTERED_ROLE_ID = 1428496119213588521  # Verilecek rol
        
        try:
            # Kayıtsız rolünü al
            unregistered_role = interaction.guild.get_role(UNREGISTERED_ROLE_ID)
            
            if not unregistered_role:
                print(f"[HATA] Kayıtsız rolü bulunamadı! Rol ID: {UNREGISTERED_ROLE_ID}")
                return await interaction.followup.send(
                    "❌ Sistem hatası: Kayıtsız rolü bulunamadı!",
                    ephemeral=True
                )
            
            # Botun kendi rolünü kontrol et (everyone hariç)
            user_roles = [role for role in kullanici.roles if role.name != "@everyone"]
            
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
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"[HATA] Kayıt sıfırlama hatası: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Beklenmeyen bir hata oluştu.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(Registration(bot))

