from django.apps import AppConfig
import random
from django.db import connection


class IlkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ilk'
    def ready(self):
        # Çift çalıştırmayı önlemek için
        if not connection.in_atomic_block:
            try:
                from .models import Musteri
                # Admin hariç tüm müşterileri sil
                Musteri.objects.exclude(is_admin=1).delete()

                # Örnek isim listesi
                isimler = [
                    "Ahmet", "Mehmet", "Tuğçe", "Fatma", "Ali", "Pınar", "Emre", "Elif", 
                    "Can", "Sümeyye", "Mert", "Seda", "Burak", "Derya", "Oğuz", "Cem", 
                    "Selin", "Berk", "Aleyna", "Ege"
                ]
                
                # Yeni müşteriler oluştur
                for i in range(10):
                    isim = random.choice(isimler)
                    Musteri.objects.create(
                        ad=isim,
                        kullanici_adi=f"{isim}{i+1}",
                        sifre="1234",
                        is_admin=False,
                        butce=random.randint(500, 3000),
                        musteri_turu=random.choice(["Premium", "Standart"]),
                        toplam_harcama=0,
                    )
                print("Random müşteriler başarıyla oluşturuldu!")
            except Exception as e:
                print(f"Hata oluştu: {e}")
