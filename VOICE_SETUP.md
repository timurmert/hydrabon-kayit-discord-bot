# 🎵 Ses Karşılama Sistemi Kurulum Rehberi

## 📋 Gereksinimler

### 1. FFmpeg Kurulumu

Bot'un ses dosyası çalabilmesi için FFmpeg'in sistemde yüklü olması gerekir.

#### Windows:
1. [FFmpeg İndirme Sayfası](https://ffmpeg.org/download.html)
2. Windows için binary dosyasını indirin
3. Zip dosyasını çıkarın
4. `ffmpeg.exe` dosyasını bot klasörüne koyun VEYA sistem PATH'ine ekleyin

**Kolay Yöntem (Bot klasörüne koyma):**
- `ffmpeg.exe`, `ffprobe.exe` dosyalarını bot'un ana klasörüne (main.py ile aynı yere) kopyalayın

**Alternatif (PATH ekleme):**
```
1. FFmpeg klasörünün "bin" dizinini bulun
2. Windows arama çubuğuna "Ortam değişkenleri" yazın
3. "Sistem ortam değişkenlerini düzenle"yi açın
4. "Ortam Değişkenleri" butonuna tıklayın
5. "Path" değişkenini bulun ve "Düzenle" tıklayın
6. "Yeni"ye tıklayıp FFmpeg bin klasörünün yolunu ekleyin
```

### 2. Python Kütüphanesi Kurulumu

```bash
pip install PyNaCl==1.5.0
```

## 🎵 Ses Dosyası Hazırlama

### Dosya Adı ve Formatı:
- **Dosya Adı:** `welcome.mp3`
- **Format:** MP3 (önerilen)
- **Konum:** Bot'un ana klasörü (main.py ile aynı klasör)

### Ses Dosyası Özellikleri (Önerilen):
- **Süre:** 2-5 saniye (çok uzun olmamalı)
- **Bit Rate:** 128 kbps veya daha düşük
- **Ses Seviyesi:** Normalize edilmiş (çok yüksek veya düşük olmamalı)

### Örnek Ses Dosyası İçeriği:
- Kısa bir karşılama müziği
- "Hoş geldin" ses efekti
- Kısa bir melodi

## 📁 Dosya Yapısı

Kurulum sonrası klasör yapınız şöyle olmalı:

```
hydrabon-kayit-discord-bot/
├── cogs/
│   ├── voice_greet.py  ✅ (Yeni eklendi)
│   ├── registration.py
│   ├── welcome.py
│   └── ...
├── main.py
├── welcome.mp3         ✅ (Eklemeniz gereken dosya)
├── ffmpeg.exe          ✅ (Windows için - opsiyonel)
├── ffprobe.exe         ✅ (Windows için - opsiyonel)
├── requirements.txt
└── .env
```

## ⚙️ Ayarlar

### Ses Kanalı ID'si
Varsayılan olarak `1428811752232976566` ID'li ses kanalında çalışır.

Değiştirmek için `cogs/voice_greet.py` dosyasındaki şu satırı düzenleyin:
```python
self.voice_channel_id = 1428811752232976566  # Yeni kanal ID'nizi buraya yazın
```

### Ses Dosyası Adı
Farklı bir ses dosyası kullanmak istiyorsanız:
```python
self.greeting_sound = "welcome.mp3"  # Dosya adını değiştirin
```

## 🚀 Kullanım

1. `welcome.mp3` dosyasını bot klasörüne ekleyin
2. FFmpeg'in kurulu olduğundan emin olun
3. Botu başlatın
4. Bot otomatik olarak ses kanalına bağlanacak
5. Kullanıcılar kanala girdiğinde karşılama sesi çalacak

## 🔧 Sorun Giderme

### "FFmpeg not found" Hatası
- FFmpeg'in PATH'de olduğundan emin olun
- Veya `ffmpeg.exe`'yi bot klasörüne kopyalayın

### "Ses dosyası bulunamadı" Hatası
- `welcome.mp3` dosyasının bot klasöründe olduğundan emin olun
- Dosya adının tam olarak `welcome.mp3` olduğunu kontrol edin

### Ses Çalmıyor
- Bot'un ses kanalında olduğundan emin olun
- Console'da hata mesajları olup olmadığını kontrol edin
- FFmpeg'in doğru kurulduğunu test edin: `ffmpeg -version`

### Ses Kesik Kesik Geliyor
- İnternet bağlantınızı kontrol edin
- Ses dosyasının boyutunu küçültmeyi deneyin
- Bit rate'i düşürün (128 kbps veya daha az)

## 📝 Notlar

- Aynı anda sadece bir ses çalınır (lock mekanizması ile korunur)
- Bot kanaldan atılırsa otomatik olarak tekrar bağlanır (main.py'deki özellik)
- Ses dosyası her kullanıcı için çalınır
- Bot kendisi kanala girdiğinde ses çalmaz

## 🎯 Test Etme

1. Botu başlatın
2. Bot'un olduğu ses kanalına girin
3. Karşılama sesi çalmalı
4. Console'da "🎵 Karşılama sesi çalındı" mesajını görmeli siniz

## 💡 İpuçları

- Kısa ve hoş bir ses kullanın (2-3 saniye ideal)
- Ses seviyesini normalize edin
- MP3 formatı önerilir (daha küçük dosya boyutu)
- Farklı ses dosyaları için dosya adını değiştirebilirsiniz

