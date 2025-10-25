# 🐧 Ubuntu Sunucu Kurulum Rehberi

## 📋 Sistem Gereksinimleri

- Ubuntu 20.04 LTS veya üzeri
- Python 3.8 veya üzeri
- En az 512 MB RAM
- İnternet bağlantısı

## 🚀 Kurulum Adımları

### 1️⃣ Sistem Güncellemesi

```bash
sudo apt update
sudo apt upgrade -y
```

### 2️⃣ Python ve Pip Kurulumu

```bash
# Python 3 ve pip kurulumu
sudo apt install python3 python3-pip -y

# Python versiyonunu kontrol et
python3 --version
```

### 3️⃣ FFmpeg Kurulumu (Ses için gerekli)

```bash
# FFmpeg ve gerekli kütüphaneleri kur
sudo apt install ffmpeg libopus0 libffi-dev libnacl-dev -y

# Kurulumu kontrol et
ffmpeg -version
```

### 4️⃣ Git Kurulumu (Proje indirmek için)

```bash
sudo apt install git -y
```

### 5️⃣ Projeyi İndirme

```bash
# Ana dizine git
cd ~

# Projeyi klonla (veya mevcut projenizi yükleyin)
git clone https://github.com/kullaniciadi/hydrabon-kayit-discord-bot.git

# Proje klasörüne gir
cd hydrabon-kayit-discord-bot
```

### 6️⃣ Python Sanal Ortamı (Virtual Environment) - Önerilen

```bash
# venv kurulumu
sudo apt install python3-venv -y

# Sanal ortam oluştur
python3 -m venv venv

# Sanal ortamı aktif et
source venv/bin/activate

# Deaktif etmek için (gerektiğinde):
# deactivate
```

### 7️⃣ Python Paketlerini Kurma

```bash
# requirements.txt'den yükle
pip install -r requirements.txt

# Veya manuel olarak:
pip install discord.py==2.3.2 python-dotenv==1.0.0 aiosqlite==0.19.0 psutil==5.9.8 pytz==2023.3 PyNaCl==1.5.0
```

### 8️⃣ .env Dosyası Oluşturma

```bash
# .env dosyasını oluştur
nano .env
```

İçeriği:
```env
TOKEN=your_discord_bot_token_here
```

Kaydet ve çık: `CTRL + X`, `Y`, `ENTER`

### 9️⃣ Ses Dosyası Ekleme

```bash
# welcome.mp3 dosyasını yükle (WinSCP, FileZilla veya scp ile)
# Veya wget ile indir (eğer link varsa):
# wget -O welcome.mp3 https://example.com/welcome.mp3

# Dosya izinlerini ayarla
chmod 644 welcome.mp3
```

### 🔟 Veritabanı Dosyası

```bash
# names.db dosyasını yükle
# Dosya izinlerini ayarla
chmod 644 names.db
```

## 🎯 Botu Çalıştırma Yöntemleri

### Yöntem 1: Screen Kullanarak (Önerilen - Basit)

```bash
# Screen kurulumu
sudo apt install screen -y

# Yeni screen oturumu başlat
screen -S hydrabon-bot

# Sanal ortamı aktif et (eğer kullanıyorsanız)
source venv/bin/activate

# Botu başlat
python3 main.py

# Screen'den çık (bot çalışmaya devam eder)
# CTRL + A, sonra D tuşlarına basın

# Screen'e geri dön
screen -r hydrabon-bot

# Screen'i sonlandır (bot durur)
# Screen içindeyken: CTRL + C, sonra exit
```

### Yöntem 2: Tmux Kullanarak

```bash
# Tmux kurulumu
sudo apt install tmux -y

# Yeni tmux oturumu başlat
tmux new -s hydrabon-bot

# Sanal ortamı aktif et
source venv/bin/activate

# Botu başlat
python3 main.py

# Tmux'tan çık (bot çalışmaya devam eder)
# CTRL + B, sonra D tuşlarına basın

# Tmux'a geri dön
tmux attach -t hydrabon-bot
```

### Yöntem 3: Systemd Service (Önerilen - Profesyonel)

#### Systemd Service Dosyası Oluşturma

```bash
sudo nano /etc/systemd/system/hydrabon-bot.service
```

İçerik:
```ini
[Unit]
Description=HydRaboN Discord Kayit Bot
After=network.target

[Service]
Type=simple
User=kullaniciadi
WorkingDirectory=/home/kullaniciadi/hydrabon-kayit-discord-bot
ExecStart=/home/kullaniciadi/hydrabon-kayit-discord-bot/venv/bin/python3 /home/kullaniciadi/hydrabon-kayit-discord-bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Önemli:** `kullaniciadi` kısımlarını kendi kullanıcı adınızla değiştirin!

#### Service'i Etkinleştirme

```bash
# Service'i yeniden yükle
sudo systemctl daemon-reload

# Service'i etkinleştir (otomatik başlatma)
sudo systemctl enable hydrabon-bot

# Service'i başlat
sudo systemctl start hydrabon-bot

# Service durumunu kontrol et
sudo systemctl status hydrabon-bot

# Logları görüntüle
sudo journalctl -u hydrabon-bot -f

# Service'i durdur
sudo systemctl stop hydrabon-bot

# Service'i yeniden başlat
sudo systemctl restart hydrabon-bot
```

### Yöntem 4: Nohup Kullanarak

```bash
# Arka planda çalıştır
nohup python3 main.py > bot.log 2>&1 &

# Process ID'yi kaydet
echo $! > bot.pid

# Logları takip et
tail -f bot.log

# Botu durdur
kill $(cat bot.pid)
```

## 🔧 Yararlı Komutlar

### Botu Güncelleme

```bash
# Git ile güncelle
cd ~/hydrabon-kayit-discord-bot
git pull

# Paketleri güncelle
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Service'i yeniden başlat
sudo systemctl restart hydrabon-bot
```

### Log İzleme

```bash
# Systemd service log
sudo journalctl -u hydrabon-bot -f --lines=100

# Screen içinde log
screen -r hydrabon-bot

# Nohup log
tail -f bot.log
```

### Port ve Güvenlik

```bash
# Firewall kurulumu (ufw)
sudo apt install ufw -y

# SSH portunu aç
sudo ufw allow 22/tcp

# Firewall'ı etkinleştir
sudo ufw enable

# Durum kontrol
sudo ufw status
```

## 📊 Performans İyileştirmeleri

### RAM Kullanımını İzleme

```bash
# Sistem durumu
htop

# Kurulum
sudo apt install htop -y
```

### Otomatik Yeniden Başlatma (Cron)

Günlük yeniden başlatma için:

```bash
# Crontab düzenle
crontab -e

# Her gün saat 04:00'te yeniden başlat
0 4 * * * /usr/bin/systemctl restart hydrabon-bot
```

## 🔒 Güvenlik Önerileri

### 1. Root Kullanıcısı ile Çalıştırmayın

```bash
# Yeni kullanıcı oluştur
sudo adduser botuser

# Kullanıcıyı değiştir
su - botuser
```

### 2. Dosya İzinlerini Ayarlayın

```bash
# .env dosyası sadece sahibi okuyabilsin
chmod 600 .env

# Diğer dosyalar
chmod 755 main.py
chmod -R 755 cogs/
```

### 3. SSH Anahtarı Kullanın

```bash
# SSH key oluştur (local)
ssh-keygen -t rsa -b 4096

# Public key'i sunucuya kopyala
ssh-copy-id kullanici@sunucu_ip
```

## 🐛 Sorun Giderme

### Bot Başlamıyor

```bash
# Python versiyonu kontrol
python3 --version

# Paketleri kontrol et
pip list

# Manuel başlatıp hata mesajını oku
python3 main.py
```

### FFmpeg Hatası

```bash
# FFmpeg yeniden kur
sudo apt remove ffmpeg -y
sudo apt install ffmpeg -y

# Versiyonu kontrol et
ffmpeg -version
```

### Ses Çalmıyor

```bash
# PyNaCl yeniden kur
pip uninstall PyNaCl -y
pip install PyNaCl==1.5.0

# Ses dosyası var mı kontrol et
ls -lh welcome.mp3

# Ses dosyası izinleri
chmod 644 welcome.mp3
```

### Veritabanı Hatası

```bash
# SQLite versiyonu
sqlite3 --version

# Veritabanı izinleri
chmod 644 names.db
chmod 644 registration_stats.db
```

## 📱 Uzaktan Erişim

### FileZilla ile Dosya Aktarımı

1. FileZilla'yı aç
2. Host: `sftp://sunucu_ip`
3. Username: Kullanıcı adınız
4. Password: Şifreniz
5. Port: 22

### WinSCP ile Dosya Aktarımı

1. WinSCP'yi aç
2. File Protocol: SFTP
3. Host: Sunucu IP
4. Port: 22
5. Username & Password

## 🔄 Yedekleme

### Otomatik Yedekleme Script'i

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/kullaniciadi/backups"
BOT_DIR="/home/kullaniciadi/hydrabon-kayit-discord-bot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/bot_backup_$DATE.tar.gz -C $BOT_DIR .

# Eski yedekleri sil (30 günden eski)
find $BACKUP_DIR -name "bot_backup_*.tar.gz" -mtime +30 -delete
```

Çalıştırılabilir yap:
```bash
chmod +x backup.sh

# Cron ile otomatik yedekleme (her gün 02:00)
0 2 * * * /home/kullaniciadi/backup.sh
```

## ✅ Kurulum Kontrolü

```bash
# Python
python3 --version

# FFmpeg
ffmpeg -version

# Pip paketleri
pip list | grep discord

# Dosyalar
ls -lh welcome.mp3 names.db .env

# Service durumu
sudo systemctl status hydrabon-bot
```

## 📞 Hızlı Başlangıç Özeti

```bash
# 1. Güncellemeler
sudo apt update && sudo apt upgrade -y

# 2. Gerekli paketler
sudo apt install python3 python3-pip python3-venv ffmpeg git screen -y

# 3. Projeye git
cd ~/hydrabon-kayit-discord-bot

# 4. Sanal ortam
python3 -m venv venv
source venv/bin/activate

# 5. Paketler
pip install -r requirements.txt

# 6. .env oluştur
nano .env

# 7. Screen ile başlat
screen -S hydrabon-bot
python3 main.py
# CTRL+A, D ile çık
```

## 🎉 Kurulum Tamamlandı!

Botunuz artık Ubuntu sunucuda çalışıyor. Herhangi bir sorun yaşarsanız yukarıdaki "Sorun Giderme" bölümüne bakabilirsiniz.

**Önemli Komutlar:**
- Bot loglarını görmek: `screen -r hydrabon-bot` veya `sudo journalctl -u hydrabon-bot -f`
- Botu yeniden başlatmak: `sudo systemctl restart hydrabon-bot`
- Bot durumunu kontrol: `sudo systemctl status hydrabon-bot`

