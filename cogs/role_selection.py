import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

# ============ GLOBAL AYARLAR ============
# Rol ID'leri
ETKINLIK_BILDIRIM_ROLE_ID = 1207713855854223391  # Etkinlik Bildirim rolü
CEKILIS_BILDIRIM_ROLE_ID = 1207713907498688512   # Çekiliş Bildirim rolü
GUNUN_SORUSU_BILDIRIM_ROLE_ID = 1207713950742085643  # Günün Sorusu Bildirim rolü

# Kanal ID'si
ROLE_SELECTION_CHANNEL_ID = 1432764482547089570  # Rol alma kanalı

# Yetki
OWNER_ID = 315888596437696522  # Bot sahibinin ID'si
# =========================================


class RoleSelectionView(discord.ui.View):
    """Rol alma butonu view"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Kalıcı buton
    
    @discord.ui.button(
        label="Etkinlik Bildirim",
        style=discord.ButtonStyle.primary,
        emoji="🎉",
        custom_id="role_select_etkinlik",
        row=0
    )
    async def etkinlik_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Etkinlik Bildirim rolünü toggle eder"""
        await self.toggle_role(interaction, ETKINLIK_BILDIRIM_ROLE_ID, "Etkinlik Bildirim")
    
    @discord.ui.button(
        label="Çekiliş Bildirim",
        style=discord.ButtonStyle.success,
        emoji="🎁",
        custom_id="role_select_cekilis",
        row=0
    )
    async def cekilis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Çekiliş Bildirim rolünü toggle eder"""
        await self.toggle_role(interaction, CEKILIS_BILDIRIM_ROLE_ID, "Çekiliş Bildirim")
    
    @discord.ui.button(
        label="Günün Sorusu Bildirim",
        style=discord.ButtonStyle.secondary,
        emoji="❓",
        custom_id="role_select_gunun_sorusu",
        row=0
    )
    async def gunun_sorusu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Günün Sorusu Bildirim rolünü toggle eder"""
        await self.toggle_role(interaction, GUNUN_SORUSU_BILDIRIM_ROLE_ID, "Günün Sorusu Bildirim")
    
    async def toggle_role(self, interaction: discord.Interaction, role_id: int, role_name: str):
        """Belirtilen rolü kullanıcıya ekler veya kaldırır"""
        try:
            member = interaction.user
            guild = interaction.guild
            role = guild.get_role(role_id)
            
            if not role:
                print(f"[HATA] Rol bulunamadı! Rol ID: {role_id}")
                return await interaction.response.send_message(
                    f"❌ {role_name} rolü bulunamadı! Lütfen yetkililere bildirin.",
                    ephemeral=True
                )
            
            # Kullanıcının rolü var mı kontrol et
            if role in member.roles:
                # Rolü kaldır
                try:
                    await member.remove_roles(role, reason="Kullanıcı rol yönetimi")
                    embed = discord.Embed(
                        title="✅ Rol Kaldırıldı",
                        description=f"**{role.name}** rolü başarıyla kaldırıldı.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    print(f"[HATA] Rol kaldırma yetkisi yok! Hedef: {member}")
                    await interaction.response.send_message(
                        "❌ Rol kaldırma yetkim yok! Bot rolü hedef rolden daha üstte olmalı.",
                        ephemeral=True
                    )
                except Exception as e:
                    print(f"[HATA] Rol kaldırılırken hata: {type(e).__name__}: {e}")
                    await interaction.response.send_message(
                        "❌ Rol kaldırılırken bir hata oluştu.",
                        ephemeral=True
                    )
            else:
                # Rolü ekle
                try:
                    await member.add_roles(role, reason="Kullanıcı rol yönetimi")
                    embed = discord.Embed(
                        title="✅ Rol Eklendi",
                        description=f"**{role.name}** rolü başarıyla eklendi.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    print(f"[HATA] Rol ekleme yetkisi yok! Hedef: {member}")
                    await interaction.response.send_message(
                        "❌ Rol ekleme yetkim yok! Bot rolü hedef rolden daha üstte olmalı.",
                        ephemeral=True
                    )
                except Exception as e:
                    print(f"[HATA] Rol eklenirken hata: {type(e).__name__}: {e}")
                    await interaction.response.send_message(
                        "❌ Rol eklenirken bir hata oluştu.",
                        ephemeral=True
                    )
        
        except Exception as e:
            print(f"[HATA] Rol toggle hatası: {type(e).__name__}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Beklenmeyen bir hata oluştu.",
                    ephemeral=True
                )
            except:
                print("[HATA] Kullanıcıya hata mesajı gönderilemedi!")


class RoleSelection(commands.Cog):
    """Rol alma sistemi cog'u"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot hazır olduğunda persistent view'ı ekle"""
        self.bot.add_view(RoleSelectionView())
    
    @app_commands.command(
        name="rol-embed",
        description="Rol alma embed'ini belirtilen kanala gönderir"
    )
    @app_commands.default_permissions(administrator=True)
    async def send_role_selection_embed(
        self,
        interaction: discord.Interaction,
        kanal: Optional[discord.TextChannel] = None
    ):
        """Rol alma embed'ini gönderir"""
        
        # Owner kontrolü
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message(
                "❌ Bu komutu kullanma yetkiniz bulunmamaktadır.",
                ephemeral=True
            )
        
        target_channel = kanal or interaction.channel
        
        # Embed oluştur
        embed = discord.Embed(
            title="🎭 Rol Alma Paneli",
            description=(
                "Aşağıdaki butonlara tıklayarak bildirim rollerinizi alabilir veya kaldırabilirsiniz.\n\n"
                "**Kullanılabilir Roller:**\n\n"
                "🎉 **Etkinlik Bildirim**\n"
                "• Sunucudaki etkinlik duyurularından haberdar olun\n\n"
                "🎁 **Çekiliş Bildirim**\n"
                "• Düzenlenen çekilişlerden haberdar olun\n\n"
                "❓ **Günün Sorusu Bildirim**\n"
                "• Günün sorusu etkinliklerinden haberdar olun\n\n"
                "💡 *Bir role sahipseniz, butona tekrar tıklayarak rolü kaldırabilirsiniz.*"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{interaction.guild.name} - Rol Alma Sistemi")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Butonları ekle
        view = RoleSelectionView()
        
        try:
            await target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Rol alma embed'i {target_channel.mention} kanalına gönderildi!",
                ephemeral=True
            )
        except discord.Forbidden:
            print(f"[HATA] Rol embed'i gönderilemedi! {target_channel.name} kanalına mesaj gönderme yetkisi yok.")
            await interaction.response.send_message(
                "❌ Bu kanala mesaj gönderme yetkim yok!",
                ephemeral=True
            )
        except Exception as e:
            print(f"[HATA] Rol embed'i gönderilirken beklenmeyen hata: {type(e).__name__}: {e}")
            await interaction.response.send_message(
                "❌ Beklenmeyen bir hata oluştu. Lütfen yetkililere bildirin.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(RoleSelection(bot))

