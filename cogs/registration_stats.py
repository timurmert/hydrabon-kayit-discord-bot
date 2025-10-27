from discord.ext import commands, tasks
import aiosqlite
import datetime
import pytz

# Türkiye saat dilimi
TURKEY_TZ = pytz.timezone("Europe/Istanbul")

class RegistrationStats(commands.Cog):
    """Kayıt istatistikleri sistemi - Sadece veritabanı kaydı"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "registration_stats.db"
    
    async def cog_load(self):
        """Cog yüklendiğinde veritabanını hazırla"""
        await self.setup_database()
        self.cleanup_old_records.start()  # Temizleme görevini başlat
    
    async def cog_unload(self):
        """Cog kaldırıldığında temizleme görevini durdur"""
        self.cleanup_old_records.cancel()
    
    async def setup_database(self):
        """Veritabanını oluştur"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS registrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        registered_at TIMESTAMP NOT NULL,
                        show_age BOOLEAN DEFAULT 1
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_registered_at 
                    ON registrations(registered_at)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_id 
                    ON registrations(user_id)
                """)
                
                # Eski kayıtlara show_age kolonu ekle (eğer yoksa)
                try:
                    await db.execute("ALTER TABLE registrations ADD COLUMN show_age BOOLEAN DEFAULT 1")
                    await db.commit()
                except:
                    pass  # Kolon zaten varsa hata verir, görmezden gel
                
                await db.commit()
        except Exception as e:
            print(f"[HATA] Veritabanı oluşturulurken hata: {type(e).__name__}: {e}")
    
    async def add_registration(self, user_id: str, username: str, name: str, age: int, show_age: bool = True):
        """Yeni kayıt ekle"""
        try:
            now = datetime.datetime.now(TURKEY_TZ)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO registrations (user_id, username, name, age, registered_at, show_age)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, name, age, now, show_age))
                await db.commit()
        except Exception as e:
            print(f"[HATA] Kayıt eklenirken hata: {type(e).__name__}: {e}")
    
    async def get_user_info(self, user_id: str):
        """Kullanıcının kayıt bilgilerini getir"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT name, age, registered_at, show_age
                    FROM registrations
                    WHERE user_id = ?
                    ORDER BY registered_at DESC
                    LIMIT 1
                """, (user_id,))
                result = await cursor.fetchone()
                return result
        except Exception as e:
            print(f"[HATA] Kullanıcı bilgisi alınırken hata: {type(e).__name__}: {e}")
            return None
    
    async def update_age_visibility(self, user_id: str, show_age: bool):
        """Kullanıcının yaş görünürlüğünü güncelle"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE registrations
                    SET show_age = ?
                    WHERE user_id = ?
                    AND id = (SELECT id FROM registrations WHERE user_id = ? ORDER BY registered_at DESC LIMIT 1)
                """, (show_age, user_id, user_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"[HATA] Yaş görünürlüğü güncellenirken hata: {type(e).__name__}: {e}")
            return False
    
    async def update_user_age(self, user_id: str, new_age: int):
        """Kullanıcının yaşını güncelle (Yaş sıfırlama için)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE registrations
                    SET age = ?
                    WHERE user_id = ?
                    AND id = (SELECT id FROM registrations WHERE user_id = ? ORDER BY registered_at DESC LIMIT 1)
                """, (new_age, user_id, user_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"[HATA] Yaş güncellenirken hata: {type(e).__name__}: {e}")
            return False
    
    @tasks.loop(hours=24)
    async def cleanup_old_records(self):
        """2 haftadan eski kayıtları sil"""
        try:
            now = datetime.datetime.now(TURKEY_TZ)
            two_weeks_ago = now - datetime.timedelta(days=14)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM registrations 
                    WHERE registered_at < ?
                """, (two_weeks_ago,))
                await db.commit()
        except Exception as e:
            print(f"[HATA] Eski kayıtlar silinirken hata: {type(e).__name__}: {e}")
    
    @cleanup_old_records.before_loop
    async def before_cleanup(self):
        """Bot hazır olana kadar bekle"""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(RegistrationStats(bot))

