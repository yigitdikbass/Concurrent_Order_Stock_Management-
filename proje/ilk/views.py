import datetime
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Musteri, Urun, Siparis, Log, SistemDurumu
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from .models import Musteri
from django.utils.timezone import now
from django.template.loader import render_to_string
from django.utils import timezone

def login_view(request):
    if request.method == "POST":
        kullanici_adi = request.POST.get("kullanici_adi")
        sifre = request.POST.get("sifre")

        try:
            kullanici = Musteri.objects.get(kullanici_adi=kullanici_adi)

            # Eğer admin modu aktifse ve giriş yapmak isteyen admin değilse giriş engellenir
            admin_modu = SistemDurumu.objects.filter(id=1).first()
            if admin_modu and admin_modu.admin_modu and not kullanici.is_admin:
                messages.error(request, "Sistem şu anda admin tarafından askıya alınmıştır. Lütfen daha sonra tekrar deneyin.")
                return redirect('login')

            if sifre == kullanici.sifre:
                request.session['kullanici_id'] = kullanici.musteri_id
                request.session['is_admin'] = kullanici.is_admin

                if kullanici.is_admin:
                    # Admin modu aktif et
                    SistemDurumu.objects.update_or_create(id=1, defaults={'admin_modu': True})
                    return redirect('admin_paneli')
                else:
                    return redirect('musteri_paneli')
            else:
                messages.error(request, "Geçersiz şifre.")
        except Musteri.DoesNotExist:
            messages.error(request, "Kullanıcı adı bulunamadı.")

    return render(request, "login.html")

def logout_view(request):
    if request.session.get('is_admin', False):
        # Admin çıkışı yapıldığında admin modunu kapat
        SistemDurumu.objects.update_or_create(id=1, defaults={'admin_modu': False})
    request.session.flush()
    return redirect('login')

# Ana Sayfa Görünümü
def admin_paneli(request):

    if not request.session.get('is_admin', False):
        return redirect('login')  # Admin değilse giriş sayfasına yönlendir
    
    musteriler = Musteri.objects.all()
    urunler = Urun.objects.all()
    siparisler = Siparis.objects.filter(durum="Beklemede").order_by('-oncelik_skoru')  # Sadece bekleyen siparişler

    return render(request, 'admin_paneli.html', {
        'musteriler': musteriler,
        'urunler': urunler,
        'siparisler': siparisler
    })

def musteri_paneli(request):
    # Oturumdaki müşteriyi al
    timezone.activate('Europe/Istanbul')
    musteri_id = request.session.get('kullanici_id')
    if not musteri_id:
        return redirect('login')  # Giriş yapılmadıysa login sayfasına yönlendir

    musteri = Musteri.objects.get(pk=musteri_id)
    siparisler = Siparis.objects.filter(musteri=musteri)  # Kullanıcının siparişleri

    musteri.save()

    urunler = Urun.objects.all()  # Tüm ürünler

    return render(request, 'musteri_paneli.html', {
        'musteri': musteri,
        'siparisler': siparisler,
        'urunler': urunler
    })

def siparis_ver(request):
    # Admin modunu kontrol et
    admin_modu = SistemDurumu.objects.first()
    if admin_modu and admin_modu.admin_modu:
        messages.warning(request, "Sistem şu anda admin tarafından askıya alındı. Lütfen daha sonra tekrar deneyin.")
        return redirect('musteri_paneli')
    
    if request.method == "POST":
        # Oturumdaki müşteriyi al
        musteri_id = request.session.get('kullanici_id')
        if not musteri_id:
            messages.error(request, "Giriş yapmalısınız.")
            return redirect('login')

        musteri = Musteri.objects.get(pk=musteri_id)
        urun_id = request.POST.get('urun_id')
        adet = int(request.POST.get('adet'))

        try:
            urun = Urun.objects.get(pk=urun_id)
        except Urun.DoesNotExist:
            messages.error(request, "Seçilen ürün bulunamadı.")
            Log.objects.create(
                musteri_id=musteri_id,
                log_turu="Hata",
                detaylar=f"Müşteri Türü: {musteri.musteri_turu}, Ürün: Geçersiz, Satın Alınan Miktar: {adet}, İşlem Sonucu: Ürün bulunamadı."
            )
            return redirect('musteri_paneli')

        toplam_fiyat = urun.fiyat * adet

        # Stok kontrolü (sadece kontrol, düşürme yok)
        if urun.stok < adet:
            messages.error(request, f"Yetersiz stok! Mevcut stok: {urun.stok}")
            Log.objects.create(
                musteri_id=musteri_id,
                log_turu="Hata",
                detaylar=f"Müşteri Türü: {musteri.musteri_turu}, Ürün: {urun.ad}, Satın Alınan Miktar: {adet}, İşlem Zamanı: {now()}, İşlem Sonucu: Ürün stoğu yetersiz."
            )
            return redirect('musteri_paneli')

        # Bütçe kontrolü
        if musteri.butce < toplam_fiyat:
            messages.error(request, f"Bütçeniz yetersiz! Gerekli: {toplam_fiyat} TL, Mevcut: {musteri.butce} TL")
            Log.objects.create(
                musteri_id=musteri_id,
                log_turu="Hata",
                detaylar=f"Müşteri Türü: {musteri.musteri_turu}, Ürün: {urun.ad}, Satın Alınan Miktar: {adet}, İşlem Zamanı: {now()}, İşlem Sonucu: Yetersiz bütçe."
            )
            return redirect('musteri_paneli')

        # Bütçeyi güncelle
        musteri.butce -= toplam_fiyat
        musteri.save()

        # Yeni siparişi kaydet
        siparis = Siparis.objects.create(
            musteri=musteri,
            urun=urun,
            adet=adet,
            toplam_fiyat=toplam_fiyat,
            siparis_tarihi=timezone.now(),
            bekleme_baslangic=timezone.now(),
            durum="Beklemede"
        )

        # Log kaydet: Başarılı sipariş
        Log.objects.create(
            musteri_id=musteri_id,
            siparis_id=siparis.pk,
            log_turu="Bilgi",
            detaylar=f"Müşteri Türü: {musteri.musteri_turu}, Ürün: {urun.ad}, Satın Alınan Miktar: {adet}, İşlem Zamanı: {now()}, İşlem Sonucu: Başarılı."
        )
        
        messages.success(request, "Siparişiniz başarıyla oluşturuldu ve onay bekliyor!")
        return redirect('musteri_paneli')

    return redirect('musteri_paneli')

def siparis_isle(request, siparis_id, islem):
    siparis = get_object_or_404(Siparis, pk=siparis_id)

    if siparis.durum != "Beklemede":
        messages.error(request, "Bu sipariş zaten işlenmiş.")
        return redirect('admin_paneli')

    if islem == "onayla":
        siparis.durum = "Tamamlandı"
        siparis.urun.stok -= siparis.adet
        siparis.urun.save()
        
        # Toplam harcamayı artır
        siparis.musteri.toplam_harcama += siparis.toplam_fiyat
        siparis.musteri.save()

        # Müşteri statüsünü kontrol et
        eski_statu = siparis.musteri.musteri_turu
        if siparis.musteri.toplam_harcama > 2000 and siparis.musteri.musteri_turu == "Standart":
            siparis.musteri.musteri_turu = "Premium"
            # Premium statü değişikliği için log kaydı
            Log.objects.create(
                musteri_id=siparis.musteri.musteri_id,
                siparis_id=siparis.siparis_id,
                log_turu="Bilgi",
                detaylar=f"Müşteri statüsü {eski_statu}'dan Premium'a yükseltildi. Toplam Harcama: {siparis.musteri.toplam_harcama} TL"
            )
            messages.info(request, f"Müşteri {siparis.musteri.ad} artık Premium üye!")
        siparis.musteri.save()

        Log.objects.create(
            musteri_id=siparis.musteri.musteri_id,
            siparis_id=siparis.siparis_id,
            log_turu="Bilgi",
            detaylar=f"Admin, sipariş {siparis.siparis_id} onayladı. Ürün: {siparis.urun.ad}, Adet: {siparis.adet}, Stok güncellendi."
        )
        messages.success(request, f"Sipariş {siparis.siparis_id} başarıyla onaylandı!")

    elif islem == "iptal":
        siparis.durum = "İptal Edildi"
        siparis.musteri.butce += siparis.toplam_fiyat
        siparis.musteri.save()

        Log.objects.create(
            musteri_id=siparis.musteri.musteri_id,
            siparis_id=siparis.siparis_id,
            log_turu="Uyarı",
            detaylar=f"Admin, sipariş {siparis.siparis_id} iptal etti. Ürün: {siparis.urun.ad}, Adet: {siparis.adet}, Müşterinin bütçesi güncellendi."
        )
        messages.warning(request, f"Sipariş {siparis.siparis_id} iptal edildi ve bütçe iade edildi!")

    else:
        messages.error(request, "Geçersiz işlem.")
        return redirect('admin_paneli')

    siparis.save()
    return redirect('admin_paneli')

# Müşteri Listeleme
def musteri_listesi(request):
    musteriler = Musteri.objects.all()
    return render(request, 'musteri_listesi.html', {'musteriler': musteriler})

def urun_listesi(request):
    if request.method == "POST":
        islem = request.POST.get("islem")

        if islem == "urun_ekle":
            # Yeni ürün ekleme işlemi
            ad = request.POST.get('ad')
            stok = int(request.POST.get('stok'))
            fiyat = float(request.POST.get('fiyat'))

            yeni_urun = Urun.objects.create(ad=ad, stok=stok, fiyat=fiyat)
            messages.success(request, "Ürün başarıyla eklendi!")

            # Log kaydet
            Log.objects.create(
                log_turu="Bilgi",
                detaylar=f"{ad} ürününü ekledi. Stok: {stok}, Fiyat: {fiyat} TL."
            )
        elif islem == "stok_guncelle":
            # Stok güncelleme işlemi
            urun_id = request.POST.get('urun_id')
            if not urun_id:
                messages.error(request, "Ürün ID'si eksik!")
                return redirect('urun_listesi')

            try:
                urun = Urun.objects.get(pk=urun_id)
            except Urun.DoesNotExist:
                messages.error(request, "Ürün bulunamadı!")
                # Log kaydet
                Log.objects.create(
                    log_turu="Hata",
                    detaylar=f"Admin, geçersiz bir ürün ID'si ({urun_id}) ile stok güncelleme yapmaya çalıştı."
                )
                return redirect('urun_listesi')

            miktar = int(request.POST.get('miktar'))
            islem_turu = request.POST.get('islem_turu')

            if islem_turu == "arttir":
                urun.stok += miktar
                log_detay = f" {urun.ad} ürününün stok miktarını {miktar} arttırdı. Yeni Stok: {urun.stok}."
            elif islem_turu == "azalt":
                if urun.stok < miktar:
                    messages.error(request, f"Stok yetersiz! Mevcut stok: {urun.stok}")
                    # Log kaydet
                    Log.objects.create(
                        log_turu="Hata",
                        detaylar=f" {urun.ad} ürününden {miktar} azaltmak istedi. Mevcut stok yetersiz."
                    )
                    return redirect('urun_listesi')
                urun.stok -= miktar
                log_detay = f" {urun.ad} ürününün stok miktarını {miktar} azalttı. Yeni Stok: {urun.stok}."

            urun.save()
            messages.success(request, "Stok başarıyla güncellendi!")

            # Log kaydet
            Log.objects.create(
                log_turu="Bilgi",
                detaylar=log_detay
            )

        return redirect('urun_listesi')

    # Ürünler ve grafik için veri hazırlama
    urunler = Urun.objects.all()
    urun_adlari = [urun.ad for urun in urunler]
    urun_stoklari = [urun.stok for urun in urunler]
    kritik_seviye = 10  # Kritik stok seviyesi

    return render(request, 'urun_listesi.html', {
        'urunler': urunler,
        'urun_adlari': urun_adlari,
        'urun_stoklari': urun_stoklari,
        'kritik_seviye': kritik_seviye
    })

def urun_sil(request, urun_id):
    if request.method == "POST":
        urun = get_object_or_404(Urun, pk=urun_id)

        # Log kaydetmeden önce ürünü kaydet
        urun_adi = urun.ad  # Log için ürün adını sakla
        urun.delete()
        messages.success(request, f"{urun_adi} ürünü başarıyla silindi!")

        # Log kaydet
        Log.objects.create(
            log_turu="Bilgi",
            detaylar=f"{urun_adi} ürününü sildi."
        )
        return redirect('urun_listesi')

    return redirect('urun_listesi')

def log_listesi(request):
    loglar = Log.objects.select_related('siparis').all().order_by('-log_tarihi')  # Sipariş ilişkisi ön yüklendi
    log_verileri = []

    for log in loglar:
        # Müşteri adını ID üzerinden çekme
        if log.musteri_id:
            try:
                musteri = Musteri.objects.get(pk=log.musteri_id)
                musteri_ad = musteri.ad
            except Musteri.DoesNotExist:
                musteri_ad = "Admin"
        else:
            musteri_ad = "Admin"

        # Sipariş bilgisi
        siparis_bilgisi = f" - Sipariş ID: {log.siparis.siparis_id}" if log.siparis else ""

        # Log detayı
        detay = f"{musteri_ad} - {log.detaylar}{siparis_bilgisi}"

        log_verileri.append({
            'log_id': log.log_id,
            'log_tarihi': log.log_tarihi.strftime('%Y-%m-%d %H:%M:%S'),
            'log_turu': log.log_turu,
            'detay': detay,
        })

    return render(request, 'log_listesi.html', {'loglar': log_verileri})

def dinamik_oncelik_hesapla():
    from django.utils import timezone
    siparisler = Siparis.objects.filter(durum="Beklemede")
    for siparis in siparisler:
        bekleme_suresi = (timezone.now() - siparis.bekleme_baslangic).total_seconds()  # Bekleme süresi hesaplama
        temel_oncelik = 15 if siparis.musteri.musteri_turu == "Premium" else 10
        bekleme_agirlik = 0.5  # Bekleme süresi ağırlığı
        siparis.oncelik_skoru = temel_oncelik + (bekleme_suresi * bekleme_agirlik)
        siparis.save()

def admin_siparis_listesi(request):
    # Öncelik skorlarını hesapla ve güncelle
    dinamik_oncelik_hesapla()

    # Bekleyen siparişleri sırala
    siparisler = Siparis.objects.filter(durum="Beklemede").order_by('-oncelik_skoru')

    # Bekleme süresi ve formatlı değerleri siparişlere ekle
    for siparis in siparisler:
        bekleme_suresi_saniye = (timezone.now() - siparis.bekleme_baslangic).total_seconds()
        dakika = int(bekleme_suresi_saniye // 60)
        saniye = int(bekleme_suresi_saniye % 60)
        siparis.bekleme_suresi = f"{dakika} dakika {saniye} saniye" if dakika > 0 else f"{saniye} saniye"

    return render(request, 'admin_paneli.html', {'siparisler': siparisler})

def admin_siparis_listesi_partial(request):
    # Öncelik skorlarını güncelleyin
    dinamik_oncelik_hesapla()

    # Bekleyen siparişleri alın
    siparisler = Siparis.objects.filter(durum="Beklemede").order_by('-oncelik_skoru')

    # Sadece satırları döndürün
    html = render_to_string('siparis_listesi_partial.html', {'siparisler': siparisler}, request=request)
    return JsonResponse({'html': html})


def toplu_siparis_onayla(request):
    if request.method == "POST":
        # Bekleyen siparişleri öncelik skoruna göre sırala
        bekleyen_siparisler = Siparis.objects.filter(durum="Beklemede").order_by('-oncelik_skoru')
        
        onaylanan_count = 0
        iptal_edilen_count = 0

        for siparis in bekleyen_siparisler:
            # Stok kontrolü
            if siparis.urun.stok >= siparis.adet:
                # Siparişi onayla
                siparis.durum = "Tamamlandı"
                siparis.urun.stok -= siparis.adet
                siparis.urun.save()

                # Toplam harcamayı artır
                siparis.musteri.toplam_harcama += siparis.toplam_fiyat
                
                eski_statu = siparis.musteri.musteri_turu
                if siparis.musteri.toplam_harcama > 2000 and siparis.musteri.musteri_turu == "Standart":
                    siparis.musteri.musteri_turu = "Premium"
                    # Premium statü değişikliği için log kaydı
                    Log.objects.create(
                        musteri_id=siparis.musteri.musteri_id,
                        siparis_id=siparis.siparis_id,
                        log_turu="Bilgi",
                        detaylar=f"Müşteri statüsü {eski_statu}'dan Premium'a yükseltildi. Toplam Harcama: {siparis.musteri.toplam_harcama} TL"
                    )
                siparis.musteri.save()
                siparis.save()
                onaylanan_count += 1

                # Log kaydet
                Log.objects.create(
                    musteri_id=siparis.musteri.musteri_id,
                    siparis_id=siparis.siparis_id,
                    log_turu="Bilgi",
                    detaylar=f"Toplu onaylama: Sipariş {siparis.siparis_id} onaylandı. Ürün: {siparis.urun.ad}, Adet: {siparis.adet}"
                )
            else:
                # Stok yetersiz - Siparişi iptal et
                siparis.durum = "İptal Edildi"
                
                # Müşterinin bütçesini iade et
                siparis.musteri.butce += siparis.toplam_fiyat
                siparis.musteri.save()
                siparis.save()
                iptal_edilen_count += 1

                # Log kaydet
                Log.objects.create(
                    musteri_id=siparis.musteri.musteri_id,
                    siparis_id=siparis.siparis_id,
                    log_turu="Uyarı",
                    detaylar=f"Toplu onaylama: Sipariş {siparis.siparis_id} iptal edildi. Yetersiz stok. Ürün: {siparis.urun.ad}, İstenen: {siparis.adet}, Mevcut: {siparis.urun.stok}"
                )

        messages.success(request, f"{onaylanan_count} sipariş onaylandı, {iptal_edilen_count} sipariş iptal edildi.")
    
    return redirect('admin_paneli')

