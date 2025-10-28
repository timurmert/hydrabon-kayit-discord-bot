import discord
from discord.ext import commands
import random

# Hoş geldin mesajları - İstediğiniz mesajları ekleyebilirsiniz
# {} yerine kullanıcının adı gelecek
WELCOME_MESSAGES = [
    "Merhaba {}, HydRaboN'a hoş geldin! Seni buraya getiren şey ne oldu?",
    "Hey {}, aramıza hoş geldin. Kendini kısaca tanıtır mısın?",
    "Hey {}, <#1029089842119852114> kanalındaki çekilişlerimize göz attın mı?",
    "Hoş geldin {}, yardıma ihtiyacın varsa, <#1364306040727933017> kanalında yardım alabilirsin!",
    "Hoş geldin {}, burada sana nasıl hitap edilmesini istersin?",
    "{} geldi. Hangi konularda sohbet etmeyi seversin?",
    "Hoş geldin {}, boş zamanlarında neler yaparsın?",
    "{} hoş geldin. Son izlediğin film neydi?",
    "Hoş geldin {}, genelde hangi saatlerde aktifsin?",
    "{} geldi. Üstesinden gelmeye çalıştığın bir konu var mı?",
    "Selam {}, destek taleplerini <#1364306040727933017> kanalında açacağını biliyor muydun?",
    "Selam {} hoş geldin, topluluğumuzda en çok hangi etkinlik ilgini çeker?",
    "Hey {}, <#1029089839859109939> kanalındaki duyurulara göz atmayı unutma!",
    "Hoş geldin {}, burada en çok hangi kısım ilgini çekti?",
    "{} geldi! İlk olarak hangi kanala göz atmayı düşünüyorsun?",
    "{} aramıza katıldı! Sence iyi bir sunucuda olmazsa olmaz şey nedir?",
    "{} hoş geldin. HydRaboN ailesinin işleyişine destek olmak istersen <#1365954137661116446> kanalından başvurunu yapabilirsin!",
    "Hey {}, HydRaboN'a hoş geldin! Gücünü hangi oyunda göstermek istersin?",
    "Merhaba {}, doğru adrestesin! Hangi efsane karakter seni temsil eder?",
    "Hoş geldin {}, HydRaboN'un enerjisine katıldığın için çok mutluyuz! En çok hangi başarılı olman istediğin şey ne?",
    "Selam {}, burası hayallerin gerçeğe dönüştüğü yer! Hangi hayalini bizimle paylaşmak isterdin?",
    "Selam {}, HydRaboN'a hoş geldin! Burada en çok ne öğrenmek/yaşamak istersin?",
    "Hoş geldin {}, ilk mesajını hangi kanala bırakmayı düşünüyorsun?",
    "Merhaba {}, HydRaboN’a adımını attın! Takım ruhunu mu, sohbeti mi daha çok seversin?",
    "Hey {}, buraya katıldığın için mutluyuz! Peki senin süper gücün nedir?",
    "Hoş geldin {}, seni en çok motive eden şey nedir?",
    "{} geldi! Eğer buraya bir özellik eklemek istesen bu özellik ne olurdu?",
    "Hoş geldin {}, HydRaboN’un hangi alanı sana daha çok hitap ediyor?",
    "Hey {}, burada ilk kazanmak istediğin deneyimin ne olmasını istersin?",
    "Hoş geldin {}, eğer sunucuda bir etkinlik düzenlense katılmak istediğin şey ne olurdu?",
    "{} geldi, hoş geldin! En çok hangi oyunda iddialısın?",
    "Hoş geldin {}, toplulukta seni en çok ne mutlu eder?",
    "Selam {}, ilk günden kendini göstermek isteyenlerden misin, yoksa gözlemci olmak isteyenlerden misin?",
    "{} aramıza katıldı! Sence iyi bir ekipte olmazsa olmaz değer nedir?",
    "Hoş geldin {}, bir gün neyi başarmış olmak istersin?",
    "Hey {}, topluluk içinde yeni insanlarla tanışırken ilk sorduğun soru ne olur?",
    "Selam {}, buradaki enerjini hangi emojiyle anlatırsın?",
    "{} geldi! HydRaboN’da unutulmaz bir an yaşasan, bu nasıl bir an olurdu?",
    "Hey {}, aramıza hoş geldin! İlk HydRaboN anın unutulmaz olsun!",
    "Merhaba {}, HydRaboN'un kalbine hoş geldin! Sevdiğin bir şarkıyı bizimle paylaşarak başlamaya ne dersin?",
    "Selam {}, cesurların arasına hoş geldin! Hangi zorluğu aşmayı hedefliyorsun?",
    "Hey {}, HydRaboN'da yeni bir macera başlıyor! Efsane olmaya hazır mısın?",
    "{} geldi ve sunucunun enerjisi bir anda arttı! Yapmaktan en çok keyif aldığın şey ne?",
    "Merhaba {}, hoş geldin! Hangi anı burada ölümsüzleştirmek isterdin?",
    "Selam {}, HydRaboN ruhunu taşıyanların arasında hoş geldin! Kendini 3 kelimeyle anlatır mısın?",
    "{} hoş geldin! Burada sıradanlık yasaktır! Sende hangi yetenek gizli?",
    "Hey {}, geldin ve hikaye şimdi başlıyor! Bir süper gücün olsaydı ne olmasını isterdin?",
    "Hoş geldin {}, burada yıldızlar bile bize bakıyor! En büyük hedefin nedir?",
    "Selam {}, HydRaboN'la yükselmeye hazır mısın? En çok motive eden şey nedir?",
    "{} geldi! HydRaboN bir kişi daha güçlendi! En sevdiğin ilham kaynağın ne?",
    "Merhaba {}, burası seninle daha da güçlendi! Takım çalışmasında kendine ne kadar güvenirsin?",
    "{} hoş geldin! Zafere giden yolda ilk adım buradan başlar! Sence başarı nedir?",
    "Hey {}, hoş geldin! Seni burada tanımak için sabırsızlanıyoruz! Şu an bir yerde olsan, nerede olmak isterdin?",
    "{} geldi! HydRaboN'un yeni yıldızı aramızda! Hayat mottolarından biri ne?",
    "Selam {}, yeni bir hikayeye hoş geldin! Bugün kendine bir söz versen, ne olurdu?",
    "{} hoş geldin! Burada hayaller gerçek oluyor! Bugün bir şeyi değiştirebilseydin ne olurdu?",
    "Hey {}, HydRaboN artık daha da güçlü! İçindeki cevheri ortaya çıkarmaya hazır mısın?",
    "Hoş geldin {}, birlikte zirveyi zorluyoruz! Hayatındaki en büyük ilham kaynağın kim?",
    "{} geldi! HydRaboN ailesi büyüyor! Kendine koyduğun son hedef neydi?",
    "Selam {}, burası enerjini ortaya koyabileceğin yer! Sence hayat bir oyun olsaydı hangi rolde olurdun?",
    "Merhaba {}, hoş geldin! Hangi kahramanla omuz omuza savaşmak isterdin?",
    "{}! HydRaboN'da yeni bir serüven başladı! Hayatında unutamadığın bir anı paylaşır mısın?",
    "Hey {}, hoş geldin! Bugün seni gülümseten bir şey neydi?",
    "Hoş geldin {}, enerjine enerjimizi katmaya geldik! Sence en güçlü yönün hangisi?",
    "{} aramıza katıldı! Birlikte başaracak çok şeyimiz var! Hayatındaki motto nedir?",
    "Selam {}, HydRaboN'la maceraya atılmaya hazır ol! Şu an bir kahraman ismi alsan ne olurdu?",
    "Hoş geldin {}, burada herkes kendi hikayesinin kahramanı! Senin kahramanlık anın neydi?",
    "{} geldi! Şimdi takım tamamlandı! Hayatındaki en büyük hayalini bizimle paylaşmak ister misin?",
    "Hey {}, HydRaboN'a hoş geldin! En çok hangi konuda ilham alırsın?",
    "Selam {}, burası hayallerin gerçeğe döndüğü yer! En çok görmek istediğin yer neresi?",
    "Hoş geldin {}, büyük şeyler küçük adımlarla başlar! Bugün atacağın ilk adım ne olurdu?",
    "{}! Aramıza hoş geldin, burada her gün yeni bir macera! Hangi konuda kendini geliştirmek istersin?",
    "Merhaba {}, HydRaboN sahnesine hoş geldin! Eğer bir kitap yazsan, adı ne olurdu?",
    "{} geldi! Sunucunun havası değişti! Şu anda ruh halini bir renk olarak söylesen, hangi renk olurdu?",
    "Hey {}, hoş geldin! Burada herkes bir yıldız! Parlamak için en çok ne yaparsın?",
    "Hoş geldin {}, HydRaboN'la zirveye koşuyoruz! Başarmak istediğin bir hedef var mı?",
    "{} aramıza katıldı! Cesaretin, buraya geldiğin anda başladı! Hayalini üç kelimeyle anlatır mısın?",
    "Selam {}, HydRaboN'da her adım bir serüven! Bugün hangi yeni şeyi denemek isterdin?",
    "Hoş geldin {}, birlikte unutulmaz anılar biriktireceğiz! Sence hayatın en güzel anı hangi anda gizlidir?",
    "{} geldi! Şimdi sıra sende: Burada ilk ne yaşamak istersin?"
]

class Welcome(commands.Cog):
    """Yeni üye karşılama sistemi"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome_channel_id = 1406431661872124026  # Sohbet-muhabbet kanalı
        self.new_member_role_id = 1428496119213588521  # Yeni üyelere verilecek rol (KAYITSIZ UYE)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Yeni üye sunucuya katıldığında çalışır"""
        
        if member.bot:
            return
        
        guild = member.guild

        # Rol verme
        try:
            role = guild.get_role(self.new_member_role_id)
            if role:
                await member.add_roles(role, reason="Yeni üye otomatik rol")
            else:
                print(f"[HATA] Yeni üye rolü bulunamadı! Rol ID: {self.new_member_role_id}")
        except discord.Forbidden:
            print(f"[HATA] Yeni üyeye rol verme yetkisi yok! Üye: {member}")
        except Exception as e:
            print(f"[HATA] Yeni üyeye rol verilirken hata: {type(e).__name__}: {e}")
        
        # Hoş geldin mesajı gönderme
        try:
            channel = guild.get_channel(self.welcome_channel_id)
            if channel:
                # Rastgele mesaj seç
                message = random.choice(WELCOME_MESSAGES).format(member.mention)
                await channel.send(message)
            else:
                print(f"[HATA] Hoş geldin kanalı bulunamadı! Kanal ID: {self.welcome_channel_id}")
        except discord.Forbidden:
            print(f"[HATA] Hoş geldin kanalına mesaj gönderme yetkisi yok!")
        except Exception as e:
            print(f"[HATA] Hoş geldin mesajı gönderilirken hata: {type(e).__name__}: {e}")


async def setup(bot: commands.Bot):
    """Cog'u yükler"""
    await bot.add_cog(Welcome(bot))

