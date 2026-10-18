# SupplyGraph — Türkçe kullanım rehberi

SupplyGraph şu soruya cevap verir: **Bir tedarikçi veya tesis kapasite kaybederse,
hangi ürünler ve mağazalar etkilenir; yedek yollar kaybın ne kadarını giderir?**

Uygulama: http://localhost:8080. GitHub kaynak kodu saklar; GitHub Packages ise
uygulamanın dağıtılabilir Docker imajını saklar. Packages sayfası simülatör ekranı değildir.

## İlk deneme

1. **Overview** bölümünde **Atlas Textiles** seç.
2. Kapasite kaybını **%100** bırak ve senaryoyu çalıştır.
3. Etkilenen ürünleri ve karşılanamayan günlük talebi incele.
4. Yedekleri açarak toparlanma sonucunu karşılaştır.
5. Bir ürün seçip **Products** bölümünde geçtiği yolları incele.
6. **Assistant** bölümünde “Atlas Textiles (SUP-01) kapanırsa ne olur?” diye sor.
   Cevabın yanında kullanılan Cypher sorgusunu ve kanıtları görebilirsin.

Tam Atlas kesintisi için doğrulanan örnekte 40 ürün etkilenir. Bir ürünün etkilenmesi,
o ürünün bütün arzının mutlaka sıfırlandığı anlamına gelmez; kalan ve yedek yollar
ayrıca hesaplanır. Sonuçlar seçili kesinti ve yedek ayarlarına bağlıdır.

## Ekranlar ve terimler

| Terim / bölüm | Anlamı |
|---|---|
| Supplier | Ürün akışının başladığı tedarikçi |
| Manufacturer | Ürünün geçtiği üretici tesisi; modelde reçete/BOM dönüşümü yoktur |
| Distributor | Ürünleri mağazalara aktaran dağıtıcı |
| Retailer | Talebi karşılanmaya çalışılan mağaza |
| SKU | Bir ürünü ayırt eden kod |
| Lane | Belirli bir ürün için iki şirket arasındaki yol; kapasitesi ve süresi vardır |
| Baseline | Kesinti öncesi, ana yollarla karşılanabilen talep |
| Shortfall / unmet demand | Mevcut talebin karşılanamayan kısmı |
| Recovery | Yedekler devreye girdiğinde geri kazanılan ürün akışı |
| Service level | Talebin karşılanabilen yüzdesi |
| Overview | Kesinti ayarları, ağ ve sonuç karşılaştırması |
| Products | Ürünün kökeni, yolları ve süre bilgileri |
| Analytics | Ağ bağlantıları ve köprü görevi gören tesisler |
| Assistant | Doğal dille, izin verilen ağ sorularını sorma |

Miktarlar günlük ortalama ürün adedidir. “112 birim/gün kayıp”, 112 şirket veya
112 ürün türü demek değildir. Ayrıca toplam eksik talep ile kesintinin **eklediği**
kayıp farklı olabilir: başlangıçta da karşılanamayan talep bulunabilir.

## İçeride nasıl çalışıyor?

**Neo4j**, şirketleri, ürünleri, yolları ve siparişleri bir graf olarak saklar.
**FastAPI**, arayüzün isteklerini karşılar ve hesaplamaları çalıştırır.
Her ürün için **maksimum akış** algoritması, kapasitelere ve mağaza talebine göre
ulaştırılabilen miktarı bulur. Aynı stok birden fazla yola iki kez yazılmaz.
Kesinti denemeleri kayıtlı ağı değiştirmez; yeniden senaryo çalıştırabilirsin.

**GDS betweenness**, çok sayıda kısa yolun arasında kalan şirketleri gösterir.
Yüksek değer, o şirketin kapanınca kesinlikle en çok zararı vereceği anlamına gelmez;
kapasite kaybını görmek için simülasyon kullanılır. **WCC**, yönü göz ardı ederek
hangi şirketlerin aynı bağlantılı grupta olduğunu bulur.

**Ollama**, yerel Qwen2.5:1.5b modelini çalıştırır. Model soruyu yorumlayıp izin verilen
Cypher sorgularından birini üretir; uygulama sorguyu ve parametrelerini kontrol eder,
Neo4j'de çalıştırır ve sonuçları döndürür. Kesinti miktarlarını hesaplayan bileşen
LLM değildir. Model hazır değilse asistan kullanılamaz; diğer ekranlar çalışabilir.
İlk model indirmesi `make model` ile yapılır; ücretli API anahtarı gerekmez.

**Docker Compose**, Neo4j, API, Nginx ve Ollama servislerini birlikte başlatır.
Durdurmak için `make docker-stop`, tekrar başlatmak için `make docker-run` kullanılır.
Durdurma komutu veritabanı ve model disklerini korur.

## Hangi bilgiler gerçek?

118 ürün ve anonim geçmiş siparişler gerçek DataCo veri setinden gelir. 13 şirket,
962 yol, kapasite, taşıma süresi ve yedek ilişkileri açıkça varsayımsal senaryodur.
Uygulama, kurduğumuz senaryonun sonucunu hesaplar; gerçek şirketler için kesin
üretim/teslimat tahmini yapmaz. Geçmiş siparişin gerçekleşmiş teslim süresi ile
senaryodaki en kısa yolun tahmini taşıma süresi ayrı tutulur.

ML raporu geçmiş siparişlerde gecikme sınıflandırmasıdır; kesintinin gelecekte
kesin olarak yaşanacağını veya etkisini tahmin eden bir model değildir.

Savunmaya hazırlanmak için [DEFENSE.md](DEFENSE.md), model kararları için
[MODELING.md](MODELING.md), hesapların ayrıntısı için [SIMULATION.md](SIMULATION.md) okunabilir.

## Yeni görsel düzen

Üstte dört özet kartı, altında senaryo oluşturucu, ağ ve ürün etkisi bulunur.
Telefonda menü etiketleri görünür kalır. Ağ dar ekranda **Facilities** listesiyle
açılır; **Map** düğmesiyle haritaya geçebilirsin. Harita ve tablolar kendi
alanlarında yana kaydırılabilir. **Review product impact** bağlantısı doğrudan
etkilenen ürünlere götürür. Asistanın Cypher ayrıntıları istenince açılır.
