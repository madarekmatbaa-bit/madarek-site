# طلب لسيرفر البوابة: البوابة على الدوت كوم، والدوت نت يحوّل (28 ت1 2026)

> **من:** محادثة الموقع (أدرك). **لـ:** محادثة نظام مدارك الداخلي (البوابة، سيرفر Hetzner `2.31.23.96`).
> **طلب عمار:** «بدي المدارك دوت كوم والدوت نت توصل لنفس المكان، والبوابة يكون الدخول عليها بالدوت كوم مو بالدوت نت… بدي الدومينين يكونوا شغالين، وبدي نتأكد من SEO انه كل اموره تمام.»
> **الحالة:** طلب، لسا ما انطبق.

## الهدف
| العنوان | بعد التعديل |
|---|---|
| `portal.madarekmatbaa.com` | **العنوان الرسمي للبوابة** (نفس التطبيق الحالي) |
| `portal.madarekmatbaa.net` | تحويل `308` ← `https://portal.madarekmatbaa.com` + نفس المسار (308 مشان طلبات POST والـ API ما تخرب) |
| `madarekmatbaa.net` و`www.madarekmatbaa.net` | تحويل `301` ← `https://www.madarekmatbaa.com` + نفس المسار (للسيو: جوجل بيعتبرهن موقع واحد) |
| `app.madarekmatbaa.net` | ما بيتغيّر (نسخة الفريق التاني على DigitalOcean) |

## الدومينات والـ DNS (مين بيعمل شو)
- **madarekmatbaa.com:** صار على Cloudflare، وسجل `portal` → `2.31.23.96` (DNS only) **مضاف**. بس السجل ما بيشتغل إلا لما عمار يغيّر الـ Nameservers تبع الدوت كوم لـ Cloudflare (`austin.ns.cloudflare.com` و`paityn.ns.cloudflare.com`). محادثة الموقع بتخبّر لما يصير.
- **madarekmatbaa.net:** مشتري من Replit، وما بينقدر ننقل الـ Nameservers تبعه. فالتحويل لازم يصير **من سيرفرنا**:
  - بصفحة Domains على Replit: نغيّر سجلّي A تبع `@` و`www` من `34.111.179.208` (Replit) لـ `2.31.23.96`. وبيضل سجل `portal` → `2.31.23.96` متل ما هو.
  - **ما منغيّر هالسجلين قبل ما يكون السيرفر جاهز للخطوة 3 تحت.**
  - النظام القديم تبع Replit يلي بيفتح هلأ على madarekmatbaa.net ما رح يعود يفتح من هالعنوان. عمار عارف.

## المطلوب على السيرفر (بالترتيب)
1. **إعداد التطبيق ليقبل الاسم الجديد** (قبل أي تحويل):
   - أضف `portal.madarekmatbaa.com` لكل مكان فيه اسم الدومين: allowed hosts، CSRF/CORS trusted origins، اسم دومين الكوكيز (إذا كان `.madarekmatbaa.net` بيصير بدون دومين أو `.madarekmatbaa.com`)، ومتغيّر الرابط الأساسي (BASE_URL) يلي بينحط بالإيميلات وملفات PDF والرسائل وأي QR.
   - بعد التبديل، الموظفين بيسجلوا دخول مرة وحدة من جديد (لأن الكوكيز مربوطة بالدومين). عادي.
2. **شهادة HTTPS لـ portal.madarekmatbaa.com:** بعد ما يشتغل سجل الـ DNS (تأكد بـ `dig +short portal.madarekmatbaa.com` إنه بيرجع `2.31.23.96`):
   `certbot --nginx -d portal.madarekmatbaa.com` (أو بنفس طريقة الشهادة الحالية).
   ونجرّب الدخول والطباعة والـ API على الدوت كوم قبل الخطوة الجاية.
3. **سيرفرات nginx للتحويل** (مثال، عدّل مسارات الشهادات):
   ```nginx
   # HTTP: شهادات Let's Encrypt + تحويل لـ HTTPS
   server {
     listen 80; listen [::]:80;
     server_name madarekmatbaa.net www.madarekmatbaa.net;
     location /.well-known/acme-challenge/ { root /var/www/certbot; }
     location / { return 301 https://www.madarekmatbaa.com$request_uri; }
   }
   # الدوت نت ← موقع الدوت كوم (بعد إصدار شهادة madarekmatbaa.net + www)
   server {
     listen 443 ssl; listen [::]:443 ssl; http2 on;
     server_name madarekmatbaa.net www.madarekmatbaa.net;
     ssl_certificate     /etc/letsencrypt/live/madarekmatbaa.net/fullchain.pem;
     ssl_certificate_key /etc/letsencrypt/live/madarekmatbaa.net/privkey.pem;
     return 301 https://www.madarekmatbaa.com$request_uri;
   }
   # البوابة القديمة ← الجديدة (بعد ما الخطوة 2 تنجح)
   server {
     listen 443 ssl; listen [::]:443 ssl; http2 on;
     server_name portal.madarekmatbaa.net;
     ssl_certificate     /etc/letsencrypt/live/portal.madarekmatbaa.net/fullchain.pem;
     ssl_certificate_key /etc/letsencrypt/live/portal.madarekmatbaa.net/privkey.pem;
     return 308 https://portal.madarekmatbaa.com$request_uri;
   }
   ```
   - سيرفر الـ HTTP يلي فوق جاهز **قبل** ما نغيّر سجلات Replit. بعد التغيير: `certbot certonly --webroot -w /var/www/certbot -d madarekmatbaa.net -d www.madarekmatbaa.net`، وبعدين نفعّل سيرفر الـ 443.
   - تجديد الشهادات التلقائي لازم يشمل الشهادات الجديدة.
4. **الروابط القديمة:** أي فاتورة أو عرض سعر أو QR انطبع عليه `portal.madarekmatbaa.net` بيضل شغّال بفضل التحويل. لهيك **الدوت نت لازم يضل مجدّد ما ينتهي** (بينتهي 31 تموز 2027).

## التحقق بعد التطبيق
```bash
curl -sI https://portal.madarekmatbaa.com/ | head -1            # 200
curl -sI https://portal.madarekmatbaa.net/login | grep -i location # https://portal.madarekmatbaa.com/login
curl -sI https://madarekmatbaa.net/shop/ | grep -i location        # https://www.madarekmatbaa.com/shop/
curl -sI http://www.madarekmatbaa.net/ | grep -i location          # https://www.madarekmatbaa.com/
```

## من جهة الموقع (محادثة الموقع بتعملها)
- زر «بوابة الموظفين» بالموقع بيصير `https://portal.madarekmatbaa.com/` بعد ما الخطوة 2 تنجح.
- رابط ملف الأسعار بطلب `portal-request-site-catalog-feed` بيصير `https://portal.madarekmatbaa.com/api/public/site-prices.json`.

## ملاحظة سيو للفريق التاني
`app.madarekmatbaa.net` (DigitalOcean) مفتوح لجوجل (`index, follow`) وعنوانه «مدارك — حلول طباعة وتغليف احترافية»، وملف robots فيه بيأشّر على `madarekmatbaa.net/sitemap.xml`. هاد بينافس الموقع الرسمي. المطلوب منهم: `noindex` على كل الصفحات (`X-Robots-Tag: noindex` من nginx)، أو تحويله.
