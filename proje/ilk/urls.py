from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_paneli, name='admin_paneli'),  # Ana sayfa
    path('login/', views.login_view, name='login'),  # Giriş yolu
    path('logout/', views.logout_view, name='logout'),  # Çıkış yolu
    path('musteriler/', views.musteri_listesi, name='musteri_listesi'),  # Müşteri listesi
    path('urunler/', views.urun_listesi, name='urun_listesi'),  # Ürün listesi
    path('loglar/', views.log_listesi, name='log_listesi'),  # Log listesi
    path('musteri_paneli/', views.musteri_paneli, name='musteri_paneli'),  # Müşteri paneli
    path('siparis_ver/', views.siparis_ver, name='siparis_ver'),  # Sipariş oluşturma
    path('urun_sil/<int:urun_id>/', views.urun_sil, name='urun_sil'),
    path('admin_siparis_listesi/', views.admin_siparis_listesi, name='admin_siparis_listesi'),
    path('siparis_isle/<int:siparis_id>/<str:islem>/', views.siparis_isle, name='siparis_isle'),
    path('admin_siparis_listesi_partial/', views.admin_siparis_listesi_partial, name='admin_siparis_listesi_partial'),
    path('toplu-siparis-onayla/', views.toplu_siparis_onayla, name='toplu_siparis_onayla'),
]
