from discord.ext import commands
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
    
    async def delete_user_data(self, user_id: str):
        """Kullanıcının tüm verilerini sil"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM registrations 
                    WHERE user_id = ?
                """, (user_id,))
                deleted_count = cursor.rowcount
                await db.commit()
                return deleted_count
        except Exception as e:
            print(f"[HATA] Kullanıcı verileri silinirken hata: {type(e).__name__}: {e}")
            return 0
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Üye sunucudan çıktığında veritabanından verilerini sil"""
        if member.bot:
            return
        
        user_id = str(member.id)
        await self.delete_user_data(user_id)


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(RegistrationStats(bot))

