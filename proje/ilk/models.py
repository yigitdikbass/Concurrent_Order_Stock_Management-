import datetime
from django.db import models
from django.utils.timezone import now
from django.utils import timezone

class Musteri(models.Model):
    MUSTERI_TURLERI = (
        ('Premium', 'Premium'),
        ('Standart', 'Standart'),
    )

    musteri_id = models.AutoField(primary_key=True)
    ad = models.CharField(max_length=255)
    kullanici_adi = models.CharField(max_length=255, unique=True)  # Kullanıcı adı
    sifre = models.CharField(max_length=255)  # Şifre
    is_admin = models.BooleanField(default=False)  # Admin kontrolü
    butce = models.FloatField()
    musteri_turu = models.CharField(max_length=50, choices=MUSTERI_TURLERI, default='Standart')
    toplam_harcama = models.FloatField(default=0)

    def __str__(self):
        return f"{self.ad} ({self.musteri_turu})"




# Ürün Modeli
class Urun(models.Model):
    urun_id = models.AutoField(primary_key=True)
    ad = models.CharField(max_length=255)
    stok = models.PositiveIntegerField(default=0)
    fiyat = models.FloatField()

    def __str__(self):
        return self.ad


# Sipariş Modeli
class Siparis(models.Model):
    SIPARIS_DURUMLARI = (
        ('Beklemede', 'Beklemede'),
        ('Tamamlandı', 'Tamamlandı'),
        ('İptal Edildi', 'İptal Edildi'),
    )

    siparis_id = models.AutoField(primary_key=True)
    musteri = models.ForeignKey(Musteri, on_delete=models.CASCADE, related_name='siparisler')
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE, related_name='siparisler')
    adet = models.PositiveIntegerField()
    toplam_fiyat = models.FloatField()
    siparis_tarihi = models.DateTimeField(default=now)
    durum = models.CharField(max_length=50, choices=SIPARIS_DURUMLARI, default='Beklemede')
    bekleme_baslangic = models.DateTimeField(default=now)  # Bekleme süresi başlangıcı
    oncelik_skoru = models.FloatField(default=0)  # Dinamik öncelik skoru
    
    @property
    def bekleme_suresi(self):
        """Bekleme süresini saniye olarak döndürür."""
        if self.durum == "Beklemede":
            return (timezone.now() - self.bekleme_baslangic).total_seconds()
        return 0

# Log Modeli
class Log(models.Model):
    LOG_TURLERI = (
        ('Bilgi', 'Bilgi'),
        ('Uyarı', 'Uyarı'),
        ('Hata', 'Hata'),
    )

    log_id = models.AutoField(primary_key=True)
    musteri = models.ForeignKey(Musteri, on_delete=models.SET_NULL, null=True, blank=True, related_name='loglar')
    siparis = models.ForeignKey(Siparis, on_delete=models.SET_NULL, null=True, blank=True, related_name='loglar')
    log_turu = models.CharField(max_length=50, choices=LOG_TURLERI)
    log_tarihi = models.DateTimeField(default=now)
    detaylar = models.TextField()

    def __str__(self):
        return f"Log {self.log_id} - {self.log_turu}"


class SistemDurumu(models.Model):
    admin_modu = models.BooleanField(default=False)  # Admin modu durumu
    guncellenme_tarihi = models.DateTimeField(auto_now=True)

    def _str_(self):
        return f"Admin Modu: {'Aktif' if self.admin_modu else 'Pasif'}"