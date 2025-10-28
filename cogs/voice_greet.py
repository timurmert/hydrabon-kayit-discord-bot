import discord
from discord.ext import commands
import asyncio
import os

class VoiceGreet(commands.Cog):
    """Ses kanalına giriş yapan kullanıcılara karşılama sesi çalar"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_channel_id = 1428811752232976566  # Bot'un bulunduğu ses kanalı
        self.greeting_sound = "welcome.mp3"  # Çalınacak ses dosyası
        self.playing_lock = asyncio.Lock()  # Aynı anda birden fazla ses çalmasını önler
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Kullanıcı ses kanalına girdiğinde çalışır"""
        
        # Bot'un kendisini kontrol etme
        if member.id == self.bot.user.id:
            return
        
        # Kullanıcı bir kanala katıldı mı?
        if after.channel and not before.channel:
            # Bot'un olduğu kanala katıldı mı?
            if after.channel.id == self.voice_channel_id:
                await self.play_greeting(member, after.channel)
        
        # Kullanıcı kanal değiştirdi mi ve yeni kanal bot'un olduğu kanal mı?
        elif after.channel and before.channel:
            if after.channel.id == self.voice_channel_id and before.channel.id != self.voice_channel_id:
                await self.play_greeting(member, after.channel)
    
    async def play_greeting(self, member: discord.Member, channel: discord.VoiceChannel):
        """Karşılama sesini çalar"""
        
        # Ses dosyası var mı kontrol et
        if not os.path.exists(self.greeting_sound):
            print(f"[HATA] Karşılama ses dosyası bulunamadı: {self.greeting_sound}")
            return
        
        # Lock ile aynı anda birden fazla ses çalmasını önle
        async with self.playing_lock:
            try:
                # Bot'un voice client'ını al
                voice_client = None
                for vc in self.bot.voice_clients:
                    if vc.channel.id == self.voice_channel_id:
                        voice_client = vc
                        break
                
                if not voice_client:
                    print(f"[HATA] Bot ses kanalında değil, karşılama sesi çalınamadı.")
                    return
                
                # Eğer bot şu anda bir şey çalıyorsa bekle
                if voice_client.is_playing():
                    voice_client.stop()
                    await asyncio.sleep(0.5)
                
                # Ses dosyasını çal
                audio_source = discord.FFmpegPCMAudio(self.greeting_sound)
                voice_client.play(
                    audio_source,
                    after=lambda e: print(f"[HATA] Karşılama sesi çalınırken hata: {e}") if e else None
                )
                
            except Exception as e:
                print(f"[HATA] Karşılama sesi çalınırken beklenmeyen hata: {type(e).__name__}: {e}")


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(VoiceGreet(bot))

