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
            
            # Kayıtsız rolünü kaldır
            if unregistered_role and unregistered_role in member.roles:
                await member.remove_roles(unregistered_role, reason="Kayıt işlemi")
            
            # Kayıtlı rolünü ver
            if registered_role:
                await member.add_roles(registered_role, reason="Kayıt işlemi")
            
            # İsmi değiştir
            await member.edit(nick=new_nickname, reason="Kayıt işlemi")
            
            # Kullanıcıya başarı mesajı gönder
            embed = discord.Embed(
                title="✅ Kayıt Başarılı!",
                description=f"**İsim:** {name}\n**Yaş:** {age}\n**Yeni İsim:** {new_nickname}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Kayıt olan: {member.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log kanalına bildirim gönder
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
                
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Yeterli yetkim yok! (Rol verme veya isim değiştirme yetkisi)",
                ephemeral=True
            )
        except Exception as e:
            print(f"Kayıt hatası: {e}")
            await interaction.followup.send(
                f"❌ Kayıt sırasında bir hata oluştu: {e}",
                ephemeral=True
            )
    
    async def check_name_in_database(self, name: str) -> bool:
        """İsmin veritabanında olup olmadığını kontrol eder"""
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
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Modal hata durumunda"""
        print(f"Modal hatası: {error}")
        await interaction.followup.send(
            "❌ Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyiniz.",
            ephemeral=True
        )


class RegistrationButton(discord.ui.View):
    """Kayıt butonu view"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)  # Kalıcı buton
        self.bot = bot
    
    @discord.ui.button(
        label="Kayıt Ol",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="registration_button"
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kayıt Ol butonuna tıklandığında"""
        modal = RegistrationModal(self.bot)
        await interaction.response.send_modal(modal)


class Registration(commands.Cog):
    """Kayıt sistemi cog'u"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot hazır olduğunda persistent view'ı ekle"""
        self.bot.add_view(RegistrationButton(self.bot))
        print("✅ Kayıt sistemi yüklendi ve persistent view eklendi")
    
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
            await interaction.response.send_message(
                "❌ Bu kanala mesaj gönderme yetkim yok!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Bir hata oluştu: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(Registration(bot))

