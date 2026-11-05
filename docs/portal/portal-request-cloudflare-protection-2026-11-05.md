# طلب لسيرفر البوابة: البوابة خلف Cloudflare ضد هجمات حجب الخدمة (5 ت2 2026)

> **من:** محادثة الموقع ومدارك الرقمية. **لـ:** محادثة نظام مدارك الداخلي (البوابة، سيرفر Hetzner `2.31.23.96`).
> **طلب عمار (5 ت2):** بعد مقطع عن هجمات حجب الخدمة (DoS) على المنصات المبنية بسرعة: «حطها بكل المواقع يلي تبعنا ويلي عم نشاغلها وثبتها بالقواعد».
> **القاعدة الجديدة:** البند 4.6 في «قائمة إطلاق المواقع - مدارك للحلول الرقمية» (مشروع مدارك الرقمية على Claude): لا يصل أي طلب إلى موقع أو نظام لنا إلا عبر Cloudflare.

## الوضع اليوم (فحص 5 ت2)

| العنوان | أين | خلف Cloudflare؟ |
|---|---|---|
| www.madarekmatbaa.com، madarekdigital.com، albayt-alasri.com | Cloudflare Pages (ملفات ثابتة) | ✅ (`server: cloudflare` و `cf-ray`) |
| portal.madarekmatbaa.net | Hetzner `2.31.23.96` مباشرة | ❌ عنوان الخادم مكشوف، والدومين على Replit |
| portal.madarekmatbaa.com | سجل في Cloudflare → `2.31.23.96` بوضع DNS only | ❌ وHTTPS عليه لا يعمل بعد |
| app.madarekmatbaa.net | DigitalOcean `165.22.223.188` (nginx، الفريق التاني) | ❌ |
| madarekmatbaa.net | Replit `34.111.179.208` (404 «This app isn't live yet») | ❌ والتحويل للدوت كوم لم يطبَّق بعد |

البوابة فيها تسجيل دخول وAPI وقاعدة بيانات، فهي الهدف الحقيقي لهجوم حجب الخدمة: كل طلب يصل إلى الخادم مباشرة.

## المطلوب على السيرفر (بالترتيب)

1. **أكمِل طلب 28 ت1** (`portal-request-com-domain-2026-10-28.md`): التطبيق يقبل `portal.madarekmatbaa.com`، وشهادة له.
   - الأسهل مع Cloudflare: **شهادة Origin من Cloudflare** (SSL/TLS > Origin Server > Create Certificate، صالحة 15 سنة) لـ `portal.madarekmatbaa.com`، أو Let's Encrypt بتحقق DNS أو webroot قبل تفعيل البروكسي.
2. **عمار أو محادثة الموقع (Cloudflare):** سجل `portal` في zone ‏madarekmatbaa.com من «DNS only» إلى **Proxied**، ووضع SSL للزون **Full (strict)**. نجرّب الدخول والطباعة والـ API.
3. **عناوين الزائر الحقيقية في nginx** (حتى تبقى السجلات وحدود المعدّل صحيحة):
   ```nginx
   # /etc/nginx/conf.d/cloudflare-realip.conf  (نحدّث القائمة من https://www.cloudflare.com/ips/)
   set_real_ip_from 173.245.48.0/20;  set_real_ip_from 103.21.244.0/22;
   set_real_ip_from 103.22.200.0/22;  set_real_ip_from 103.31.4.0/22;
   set_real_ip_from 141.101.64.0/18;  set_real_ip_from 108.162.192.0/18;
   set_real_ip_from 190.93.240.0/20;  set_real_ip_from 188.114.96.0/20;
   set_real_ip_from 197.234.240.0/22; set_real_ip_from 198.41.128.0/17;
   set_real_ip_from 162.158.0.0/15;   set_real_ip_from 104.16.0.0/13;
   set_real_ip_from 104.24.0.0/14;    set_real_ip_from 172.64.0.0/13;
   set_real_ip_from 131.0.72.0/22;
   set_real_ip_from 2400:cb00::/32;   set_real_ip_from 2606:4700::/32;
   set_real_ip_from 2803:f800::/32;   set_real_ip_from 2405:b500::/32;
   set_real_ip_from 2405:8100::/32;   set_real_ip_from 2a06:98c0::/29;
   set_real_ip_from 2c0f:f248::/32;
   real_ip_header CF-Connecting-IP;
   ```
4. **حد للمعدّل داخل nginx** على الدخول والـ API:
   ```nginx
   # في http {}
   limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;
   limit_req_zone $binary_remote_addr zone=api:10m   rate=20r/s;
   # في server {} الخاص بالبوابة
   location = /login { limit_req zone=login burst=5 nodelay; proxy_pass ...; }   # عدّل المسار حسب التطبيق
   location /api/    { limit_req zone=api   burst=40 nodelay; proxy_pass ...; }
   limit_req_status 429;
   ```
5. **جدار الحماية (بعد أن ينجح الخطوتان 1 و2 والتحويلات أدناه):** المنفذان 80 و443 من عناوين Cloudflare فقط، وSSH بالمفتاح فقط. مثال ufw:
   ```bash
   ufw default deny incoming && ufw allow OpenSSH
   for ip in $(curl -s https://www.cloudflare.com/ips-v4) $(curl -s https://www.cloudflare.com/ips-v6); do
     ufw allow proto tcp from $ip to any port 80,443; done
   ufw enable
   ```
   - **تنبيه:** طالما `portal.madarekmatbaa.net` و`madarekmatbaa.net` يشيران إلى الخادم مباشرة من Replit، يبقى تحويلهما يحتاج المنفذ 443 مفتوحاً للجميع. فإما نؤجّل هذه الخطوة حتى ننقل دومين الدوت نت من Replit إلى Cloudflare Registrar (ونعمل التحويلات بقواعد Cloudflare)، وإما نترك 443 مفتوحاً مؤقتاً لأسماء الدوت نت فقط.
6. **خادم افتراضي يرفض الطلب بالعنوان المجرد:** `server { listen 443 ssl default_server; ssl_reject_handshake on; }` و`listen 80 default_server; return 444;`.
7. **Turnstile** من Cloudflare على شاشة تسجيل الدخول (مجاني)، بدل أي كابتشا.
8. بعد إغلاق الجدار: إن أمكن، **عنوان IP جديد** للخادم، لأن الحالي مكشوف في سجلات DNS قديمة.

## من جهة Cloudflare (محادثة الموقع بتعملها بعد الخطوة 2)
- قاعدة تحديد المعدّل الوحيدة في الخطة المجانية لزون madarekmatbaa.com:
  - المواقع الثابتة (www) لا تحتاجها بقدر البوابة، فنجعلها للبوابة: `URI Path` يبدأ بـ `/login` أو `/api`، و20 طلباً خلال 10 ثوانٍ لكل IP، والإجراء Block.
- عند هجوم: Under Attack Mode من Overview.

## app.madarekmatbaa.net (الفريق التاني)
نفس الخطر ونفس الحل: يوضع خلف Cloudflare (على اسم من الدوت كوم مثل `app.madarekmatbaa.com` بوضع Proxied)، ويُغلق خادم DigitalOcean إلا لعناوين Cloudflare. أو يُوقف إن لم يعد مستخدماً، لأنه أيضاً مفتوح لغوغل وينافس الموقع الرسمي (انظر ملاحظة السيو في طلب 28 ت1).

## التحقق
```bash
curl -sI https://portal.madarekmatbaa.com/ | grep -iE "^server|^cf-ray"     # server: cloudflare + cf-ray
dig +short portal.madarekmatbaa.com                                          # عناوين Cloudflare، لا 2.31.23.96
curl -sk -m 8 --resolve portal.madarekmatbaa.com:443:2.31.23.96 https://portal.madarekmatbaa.com/   # يفشل بعد الخطوة 5
for i in $(seq 1 15); do curl -s -o /dev/null -w "%{http_code} " -X POST https://portal.madarekmatbaa.com/login; done   # يظهر 429 بعد الحد
```
