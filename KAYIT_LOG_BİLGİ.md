# 📋 Kayıt Log Sistemi

## 📖 Genel Bakış

Bot artık tüm kayıt denemelerini (başarılı veya başarısız) otomatik olarak bir Discord kanalına loglayacaktır. Bu sayede:

- ✅ Başarılı kayıt denemeleri
- ❌ Başarısız kayıt denemeleri ve nedenleri
- 📋 Manuel kayıt talepleri (Ticket sistemi)

gibi tüm kayıt aktiviteleri takip edilebilir.

---

## ⚙️ Kurulum

### 1. Log Kanalı Oluşturma

Discord sunucunuzda kayıt loglarının gönderileceği bir kanal oluşturun:
- Kanal adı örneği: `#kayıt-logları` veya `#registration-logs`
- Kanalın sadece yetkililerin görebileceği şekilde ayarlanması önerilir

### 2. Kanal ID'sini Ayarlama

`cogs/registration.py` dosyasında **18. satırda** şu ayarı bulun:

```python
REGISTRATION_LOG_CHANNEL_ID = 1431398643273039934  # Kayıt denemesi log kanalı (değiştirin!)
```

Bu ID'yi kendi log kanalınızın ID'si ile değiştirin.

#### Discord'da Kanal ID'si Nasıl Alınır?

1. Discord'da **Geliştirici Modu**'nu aktifleştirin:
   - Kullanıcı Ayarları → Gelişmiş → Geliştirici Modu'nu açın

2. Log kanalına sağ tıklayın ve **Kimliği Kopyala** seçeneğine tıklayın

3. Kopyaladığınız ID'yi `REGISTRATION_LOG_CHANNEL_ID` değişkenine yapıştırın

---

## 📊 Log Mesajı Örnekleri

### ✅ Başarılı Kayıt Denemesi

```
✅ Başarılı Kayıt Denemesi

👤 Kullanıcı Bilgileri
Kullanıcı: @KullanıcıAdı
Kullanıcı Adı: KullanıcıAdı
Kullanıcı ID: 123456789012345678

📝 Denenen Bilgiler
İsim: Ahmet
Yaş: 25
```

### ❌ Başarısız Kayıt Denemesi

```
❌ Başarısız Kayıt Denemesi

👤 Kullanıcı Bilgileri
Kullanıcı: @KullanıcıAdı
Kullanıcı Adı: KullanıcıAdı
Kullanıcı ID: 123456789012345678

📝 Denenen Bilgiler
İsim: Test123
Yaş: 25

⚠️ Başarısızlık Nedeni
İsimde geçersiz karakterler var (sadece harf ve boşluk kullanılabilir)
```

### 📋 Manuel Kayıt Talebi (Ticket)

```
📋 Manuel Kayıt Talebi (Ticket Oluşturuldu)

👤 Kullanıcı Bilgileri
Kullanıcı: @KullanıcıAdı
Kullanıcı Adı: KullanıcıAdı
Kullanıcı ID: 123456789012345678

📝 Denenen Bilgiler
İsim: Mehmet
Yaş: 20
Yaş Görünürlüğü: evet

ℹ️ Durum
Manuel kayıt için ticket oluşturuldu. Yetkili onayı bekleniyor.
```

---

## 🔍 Loglanan Başarısızlık Nedenleri

Sistem aşağıdaki durumları otomatik olarak tespit edip loglar:

1. **Yaş 13-99 aralığı dışında**
   - Kullanıcı 13'ten küçük veya 99'dan büyük bir yaş girdiğinde

2. **Geçersiz yaş formatı (sayı değil)**
   - Kullanıcı yaş alanına sayı dışında bir şey yazdığında

3. **İsimde geçersiz karakterler var**
   - İsim alanına sayı, özel karakter veya emoji girildiğinde
   - Sadece Türkçe/İngilizce harfler ve boşluk kabul edilir

4. **İsim veritabanında bulunamadı (geçersiz isim)**
   - Girilen isim bot'un isim veritabanında yoksa

---

## 🛠️ Sorun Giderme

### Log mesajları gelmiyor

1. **Kanal ID'sini kontrol edin:**
   - `cogs/registration.py` dosyasındaki `REGISTRATION_LOG_CHANNEL_ID` değişkeninin doğru olduğundan emin olun

2. **Bot izinlerini kontrol edin:**
   - Bot'un log kanalında "Mesaj Gönder" ve "Embed Bağlantıları Yerleştir" izinlerine sahip olduğundan emin olun

3. **Bot loglarını kontrol edin:**
   - Konsol çıktısında `[UYARI] Kayıt log kanalı bulunamadı!` mesajı varsa kanal ID'si yanlış demektir

### Bot'u yeniden başlatma

Ayarları değiştirdikten sonra bot'u yeniden başlatmayı unutmayın!

---

## 📝 Notlar

- Log mesajları sadece yöneticilerin görebileceği bir kanalda tutulmalıdır
- Bu loglar GDPR/KVKK uyumluluğu açısından düzenli olarak temizlenmelidir
- Loglar kullanıcıların kişisel bilgilerini içerdiği için güvenli bir şekilde saklanmalıdır

---

## 💡 İpuçları

- Log kanalını sadece üst düzey yetkililerin görebileceği şekilde ayarlayın
- Logları düzenli olarak gözden geçirerek şüpheli kayıt denemelerini tespit edebilirsiniz
- Çok sayıda başarısız deneme yapan kullanıcıları takip edebilirsiniz

---

**🎉 Kayıt log sistemi başarıyla kuruldu!**

Herhangi bir sorunuz veya sorununuz varsa lütfen bot geliştiricisine ulaşın.

