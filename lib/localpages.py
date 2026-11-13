"""Service pages per city: «طباعة كروت شخصية في دمشق», «طباعة هدايا دعائية في طرابلس» …

Ammar 13 Nov 2026: «مطبعة عم تطلع، طباعة ما عم تطلع. بدي يطلع بالبحث وقت البحث عن اي شيء من عملنا مشهور، متل طباعة كروت،
طباعة هدايا دعائية». The «مطبعة <مدينة>» pages already rank, so each of them gets its services as pages of their own.

Rules for what is written here:
- prices are read from the catalog at build time, never typed;
- what is said about a city (office, port, shipping route, times) is only what its «مطبعة <مدينة>» page, the shipping
  page and build.py (TRANSIT_DAYS, HANDLING_DAYS, FREE_SHIPPING) already say;
- no client names and nothing about government work (Ammar 7 Nov: «اشياء الحكومة لا تحطها على الموقع»);
- Arabic only for now, like the articles.
"""
import html as H
import json
import re
import urllib.parse as up

SITE = 'https://www.madarekmatbaa.com'
SHARE_IMG = SITE + '/wp-content/uploads/2026/10/madarek-share-2026.jpg'
TIPS = '/print-tips/'

# ---------------------------------------------------------------- markets and cities
MARKETS = {
    'sy': dict(name='سوريا', hub='/markets/مطبعة-في-سوريا/', contact='سوريا',
               time='من اعتماد التصميم إلى التسليم في {city}: من 8 إلى 13 يوماً. التنفيذ يأخذ من 7 إلى 10 أيام، والتوصيل من يوم إلى 3 أيام.',
               time_short='التسليم خلال 8 إلى 13 يوماً من اعتماد التصميم، والتوصيل مجاني',
               ship_line='<b>التوصيل داخل سوريا:</b> من يوم إلى 3 أيام، وهو مجاني.',
               price_note='التوصيل داخل سوريا مجاني.',
               last_step='نسلّمك الطلبية في {city}، وتدفع الباقي عند التجهيز.'),
    'ly': dict(name='ليبيا', hub='/markets/مطبعة-في-ليبيا/', contact='ليبيا',
               time='التنفيذ يأخذ من 7 إلى 10 أيام بعد اعتماد التصميم. بعده يأخذ الشحن البحري من أسبوعين إلى ثلاثة من الباب إلى الباب.',
               time_short='التنفيذ من 7 إلى 10 أيام، ثم الشحن بحراً إلى مصراتة',
               ship_line='<b>الشحن إلى ليبيا:</b> من أسبوعين إلى ثلاثة بحراً، من الباب إلى الباب.',
               price_note='الأسعار لا تشمل الشحن إلى {city}. نحسبه ونوضحه في عرض السعر.',
               last_step='تدفع الباقي عند تجهيز البضاعة، ثم نشحنها إلى مصراتة.'),
    'iq': dict(name='العراق', hub='/markets/مطبعة-في-العراق/', contact='العراق',
               time='التنفيذ يأخذ من 7 إلى 10 أيام بعد اعتماد التصميم، ثم نحو 10 أيام للشحن إلى {city}.',
               time_short='التنفيذ من 7 إلى 10 أيام، ثم نحو 10 أيام للشحن',
               ship_line='<b>الشحن إلى {city}:</b> نحو 10 أيام.',
               price_note='الأسعار لا تشمل الشحن إلى {city}. نحسبه ونوضحه في عرض السعر.',
               last_step='تدفع الباقي عند تجهيز البضاعة، ثم نشحنها إلى {city}.'),
    'gulf': dict(name='الخليج', hub='/markets/مطبعة-في-الخليج/', contact='الخليج',
                 time='التنفيذ يأخذ من 7 إلى 10 أيام بعد اعتماد التصميم، ثم نحو 25 يوماً للشحن إلى {city}. الطلبيات العاجلة نرسلها جواً.',
                 time_short='التنفيذ من 7 إلى 10 أيام، ثم الشحن جواً أو بحراً',
                 ship_line='<b>الشحن إلى {city}:</b> نحو 25 يوماً، والعاجل جواً.',
                 price_note='الأسعار لا تشمل الشحن إلى {city} ولا الضريبة. نحسبهما ونوضحهما في عرض السعر.',
                 last_step='تدفع الباقي عند تجهيز البضاعة، ثم نشحنها جواً أو بحراً.'),
}

CITIES = [
    dict(key='damascus', name='دمشق', tname='دمشق', market='sy', page='/markets/مطبعة-في-سوريا/مطبعة-دمشق/', en='Damascus', country_en='Syria',
         reach='نسلّم الطلبيات داخل دمشق، ومكتبنا في البحصة.',
         deliver='مكتبنا في دمشق في البحصة، شارع يوسف العظمة، برج الفندق الذهبي، الطابق السادس. ومركز الإنتاج في ريف دمشق، لذلك نسلّم '
                 'الطلبيات داخل دمشق مباشرة بعد التنفيذ. المنتجات التي تأتي من إسطنبول تصل براً، ونؤكد موعدها في عرض السعر.',
         order='تواصل مع عمار رجب، مسؤول المبيعات في سوريا، عبر واتساب، أو زر المكتب في البحصة.'),
    dict(key='aleppo', name='حلب', tname='حلب', market='sy', page='/markets/مطبعة-في-سوريا/مطبعة-حلب/', en='Aleppo', country_en='Syria',
         reach='نوصل الطلبيات إلى حلب براً.',
         deliver='نوصل الطلبيات إلى حلب براً، من مركز الإنتاج في ريف دمشق أو من إسطنبول حسب المنتج. الكميات الصغيرة تصل بالشحن الجزئي، '
                 'وللكميات الكبيرة نقترح شاحنة كاملة. نؤكد المسار والموعد في عرض السعر.',
         order='تواصل مع عمار رجب، مسؤول المبيعات في سوريا، عبر واتساب.'),
    dict(key='misrata', name='مصراتة', tname='مصراتة', market='ly', page='/markets/مطبعة-في-ليبيا/مطبعة-مصراتة/', en='Misrata', country_en='Libya',
         reach='مكتب مبيعاتنا في مصراتة، وإلى مينائها تصل شحناتنا من إسطنبول.',
         deliver='في مصراتة مكتب مبيعات مدارك منذ 2024، وإلى مينائها تصل شحناتنا البحرية من إسطنبول بعد 5 إلى 7 أيام إبحار. بعد وصول '
                 'الشحنة نسلّمها إلى مكتبك أو مستودعك. العينات والطلبيات العاجلة نرسلها جواً.',
         order='أرسل المنتج أو كوده والكمية عبر واتساب، ويتابع فريقنا في مصراتة طلبك حتى التسليم.'),
    dict(key='tripoli', name='طرابلس', tname='طرابلس ليبيا', market='ly', page='/markets/مطبعة-في-ليبيا/مطبعة-طرابلس/', en='Tripoli', country_en='Libya',
         reach='نشحن بحراً إلى مصراتة، ثم نرتّب التسليم إلى طرابلس.',
         deliver='تصل الشحنة البحرية من إسطنبول إلى ميناء مصراتة خلال 5 إلى 7 أيام إبحار، ثم نرتّب نقلها إلى طرابلس. الطلبيات العاجلة '
                 'والعينات نرسلها جواً. نؤكد الموعد الكامل في عرض السعر.',
         order='أرسل المنتج أو كوده والكمية وعنوان التسليم في طرابلس عبر واتساب، ونرد عليك بعرض السعر.'),
    dict(key='benghazi', name='بنغازي', tname='بنغازي', market='ly', page='/markets/مطبعة-في-ليبيا/مطبعة-بنغازي/', en='Benghazi', country_en='Libya',
         reach='نشحن بحراً إلى مصراتة، ثم نرتّب التسليم إلى بنغازي.',
         deliver='نشحن الطلبية بحراً من إسطنبول إلى مصراتة، ثم نرتّب نقلها إلى بنغازي. المسافة من ميناء الوصول أطول، لذلك نحدد معك موعد '
                 'التسليم قبل بدء التنفيذ. العينات والطلبيات العاجلة نرسلها جواً عند الحاجة.',
         order='أرسل المنتج أو كوده والكمية وموعد التسليم المطلوب في بنغازي عبر واتساب، ونرد عليك بعرض السعر وموعد الوصول المتوقع.'),
    dict(key='baghdad', name='بغداد', tname='بغداد', market='iq', page='/markets/مطبعة-في-العراق/مطبعة-بغداد/', en='Baghdad', country_en='Iraq',
         reach='نشحن من تركيا إلى بغداد براً، والعاجل جواً.',
         deliver='نشحن من تركيا إلى بغداد براً للكميات المتوسطة والكبيرة، ونرسل الطلبيات العاجلة والعينات جواً. إذا كانت الطلبية لمعرض أو '
                 'مناسبة فأخبرنا بالموعد عند الطلب، لنختار الطريقة التي توصلها قبله.',
         order='أرسل المنتج أو كوده والكمية عبر واتساب إلى الآنسة هبة.'),
    dict(key='erbil', name='أربيل', tname='أربيل', market='iq', page='/markets/مطبعة-في-العراق/مطبعة-أربيل/', en='Erbil', country_en='Iraq',
         reach='نشحن من تركيا إلى أربيل براً، والعاجل جواً.',
         deliver='أربيل قريبة من الحدود التركية، لذلك نشحن إليها براً من تركيا: شحناً جزئياً للكميات الصغيرة، أو بشاحنة كاملة للطلبيات '
                 'الكبيرة. العاجل نرسله جواً. ونطبع تصميمك كما ترسله، بالعربية أو الكردية أو الإنجليزية.',
         order='أرسل المنتج أو كوده والكمية عبر واتساب إلى الآنسة هبة.'),
    dict(key='riyadh', name='الرياض', tname='الرياض', market='gulf', page='/markets/مطبعة-في-الخليج/مطبعة-الرياض/', en='Riyadh', country_en='Saudi Arabia',
         reach='نشحن إلى الرياض جواً للعاجل، وبحراً للكميات الكبيرة.',
         deliver='نشحن إلى الرياض جواً للطلبيات العاجلة والعينات، وبحراً للكميات الكبيرة. نؤكد الموعد وكلفة الشحن في عرض السعر قبل بدء التنفيذ.',
         order='أرسل المنتج أو كوده والكمية عبر واتساب إلى الآنسة هبة.'),
    dict(key='jeddah', name='جدة', tname='جدة', market='gulf', page='/markets/مطبعة-في-الخليج/مطبعة-جدة/', en='Jeddah', country_en='Saudi Arabia',
         reach='نشحن إلى جدة جواً للعاجل، وبحراً إلى مينائها للكميات الكبيرة.',
         deliver='جدة مدينة ميناء، لذلك تصل الشحنات البحرية للكميات الكبيرة إلى مينائها مباشرة. الطلبيات العاجلة والعينات نرسلها جواً. '
                 'نختار طريقة الشحن حسب الكمية والموعد، ونوضح كلفتها في عرض السعر.',
         order='أرسل المنتج أو كوده والكمية عبر واتساب إلى الآنسة هبة.'),
    dict(key='dubai', name='دبي', tname='دبي', market='gulf', page='/markets/مطبعة-في-الخليج/مطبعة-دبي/', en='Dubai', country_en='United Arab Emirates',
         reach='نشحن إلى دبي جواً للعاجل، وبحراً للكميات الكبيرة.',
         deliver='نشحن إلى دبي جواً للطلبيات العاجلة وهدايا المعارض القريبة، وبحراً للكميات الكبيرة. إذا كانت الطلبية لمعرض فأخبرنا بموعده '
                 'عند الطلب، لنختار الطريقة التي توصلها قبله.',
         order='أرسل المنتج أو كوده والكمية وموعد المعرض عبر واتساب إلى الآنسة هبة.'),
]

# where each kind of work is made, per market (from the market pages)
MADE = {
    'sy': {
        'paper': 'ننفّذ المطبوعات الورقية في سوريا بالأوفست والديجيتال.',
        'logo': 'نطبع الشعار في مركز الإنتاج بريف دمشق، بطباعة UV أو بالحفر بالليزر.',
        'notebooks': 'نختار مركز التنفيذ الأنسب لكل طلب: ريف دمشق للطباعة السريعة، وإسطنبول للتشكيلة الأوسع.',
        'flags': 'نطبع الأعلام والأقمشة في مركز الإنتاج بريف دمشق. الساريات والقواعد الفاخرة قد تأتي من إسطنبول.',
        'apparel': 'نطبع الشعار على الملابس بطباعة DTF في مركز الإنتاج بريف دمشق، أو نطرّزه.',
        'boxes': 'نختار مركز التنفيذ الأنسب لكل طلب: ريف دمشق للطباعة السريعة، وإسطنبول للتشكيلة الأوسع.',
    },
    'ly': {'paper': 'ننفّذ المطبوعات في إسطنبول.',
           'china': 'ننفّذ الطلبية في إسطنبول، أو في الصين للكميات الكبيرة حين يكون السعر هو الأهم.',
           'plain': 'ننفّذ الطلبية في إسطنبول.'},
    'iq': {'paper': 'ننفّذ المطبوعات في إسطنبول.',
           'china': 'ننفّذ الطلبية في إسطنبول. وللكميات الكبيرة بسعر أقل نقترح التنفيذ في الصين، ونخطط للشحن مبكراً.',
           'plain': 'ننفّذ الطلبية في إسطنبول.'},
    'gulf': {'paper': 'ننفّذ المطبوعات في إسطنبول.',
             'china': 'ننفّذ الطلبية في إسطنبول للكميات المتوسطة، وفي الصين للكميات الكبيرة حين يكون السعر هو الأهم.',
             'plain': 'ننفّذ الطلبية في إسطنبول.'},
}
CHINA_KINDS = ('logo', 'notebooks')
# a word on shipping by the weight of the goods, outside Syria (the market pages: «جواً للعاجل، وبحراً/براً للكميات الكبيرة»)
SHIP_NOTE = {
    'light': {'ly': '{the} خفيفة الوزن، لذلك يمكن إرسالها جواً إذا كان موعدك قريباً.',
              'iq': '{the} خفيفة الوزن، لذلك يمكن إرسالها جواً إذا كان موعدك قريباً.',
              'gulf': '{the} خفيفة الوزن، لذلك يمكن إرسالها جواً إذا كان موعدك قريباً.'},
    'bulky': {'ly': '{the} تأخذ وزناً وحجماً في الشحن، لذلك يكون الشحن البحري أوفر للكميات الكبيرة.',
              'iq': '{the} تأخذ وزناً وحجماً في الشحن، لذلك يكون الشحن البري أوفر للكميات الكبيرة.',
              'gulf': '{the} تأخذ وزناً وحجماً في الشحن، لذلك يكون الشحن البحري أوفر للكميات الكبيرة.'},
}

FILE_TIPS = ['ملف التصميم بصيغة PDF أو AI، بألوان CMYK ودقة 300 نقطة في البوصة.',
             '3 مم نزف من كل جهة، والنص بعيد 3 مم على الأقل عن حافة القص.']
DESIGN_TIP = 'إذا لم يكن عندك تصميم، يجهّزه فريقنا ويرسل لك نموذجاً للموافقة قبل الطباعة.'
PROMO = '/product-category/promotional-ar/'

# ---------------------------------------------------------------- the services
# prices: name -> source. Sources: 'var:SKU' a variation, 'sku:SKU' a product (its price or lowest price), 'max:SKU' its highest,
# 'cat:/path/' the lowest price in a category. In the texts {name} becomes the price.
SERVICES = [
    dict(key='cards', slug='طباعة-كروت-شخصية', name='طباعة كروت شخصية', the='الكروت الشخصية', kind='paper', weight='light',
         base='sku:KART-N', base_label='اختر المواصفات من صفحة الكرت الشخصي', img='KART-N', img_alt='كروت شخصية مطبوعة',
         prices=dict(lo='var:KART-N-250', hi='max:KART-N', two='var:KART-N-350-D'),
         lead='نطبع الكروت الشخصية بتصميمك على ورق من 250 إلى 700 غرام، بسلوفان مطفي أو لامع. سعر الألف كرت يبدأ من {lo}.',
         from_label='{lo} لألف كرت', desc_price='سعر الألف كرت يبدأ من {lo}',
         h2='كروت شخصية بهوية شركتك',
         intro='الكرت الشخصي أكثر مطبوعات الشركة تداولاً، لذلك يُطلب بالألف. تختار سماكة الورق والتشطيب، ونطبعه بوجه واحد أو بوجهين.',
         opts=['<b>الورق:</b> 250 غرام للتوزيع الواسع، 350 غرام للشركات، 700 غرام للكرت الفاخر.',
               '<b>التشطيب:</b> سلوفان مطفي أو لامع، ومعه سبوت UV على الشعار عند الطلب.',
               '<b>القص:</b> زوايا حادة أو دائرية، أو قص بشكل خاص.'],
         price_h2='أسعار طباعة الكروت الشخصية', table=('price', ['المواصفات', 'سعر 1000 كرت'], [
             ('var:KART-N-250', '250 غرام · وجه واحد · سلوفان لامع'),
             ('var:KART-N-250-02', '250 غرام · وجهان · سلوفان لامع'),
             ('var:01-KART-N-350', '350 غرام · وجه واحد · سلوفان مطفي'),
             ('var:KART-N-350-D', '350 غرام · وجهان · سلوفان مطفي'),
             ('var:KART-N-350-D-L', '350 غرام · وجهان · سلوفان مطفي مع سبوت UV'),
             ('var:KART-N-700', '700 غرام · وجهان · سبوت UV · زوايا دائرية')]),
         note='السعر يشمل الطباعة حسب المواصفات، ولا يشمل التصميم.',
         send='المواصفات والكمية', tips=FILE_TIPS + ['الخطوط محوّلة إلى منحنيات (Outlines) قبل الإرسال.', DESIGN_TIP],
         article=('business-cards-printing', 'دليل طباعة الكروت الشخصية'),
         q_price='كم سعر طباعة 1000 كرت شخصي في {city}؟',
         a_price='سعر الألف كرت من {lo} إلى {hi} حسب سماكة الورق والتشطيب.',
         faq=('هل تطبعون الكرت بوجهين، عربي وإنجليزي؟',
              'نعم. الوجهان يناسبان الكرت بلغتين، أو وجهاً للشعار ووجهاً للبيانات. سعر الألف بوجهين على ورق 350 غرام {two}.')),
    dict(key='brochures', slug='طباعة-بروشورات', name='طباعة بروشورات', the='البروشورات', kind='paper', weight='',
         base='sku:BRO', base_label='اختر المواصفات من صفحة البروشور', img='BRO', img_alt='بروشورات مطبوعة',
         prices=dict(lo='var:BRO-130-A5', a4='var:BRO-130-A4', hi='max:BRO'),
         lead='نطبع البروشورات والمطويات بتصميمك بمقاسات A5 وA4 وA3، على ورق من 150 إلى 300 غرام. سعر الألف يبدأ من {lo}.',
         from_label='{lo} لألف بروشور', desc_price='سعر الألف بروشور يبدأ من {lo}',
         h2='بروشورات ومطويات لمعرضك ومبيعاتك',
         intro='البروشور يشرح خدماتك لمن يريد التفاصيل، في المعرض أو مع عرض السعر. تختار المقاس وسماكة الورق، وتضيف الطي أو السلوفان عند الحاجة.',
         opts=['<b>المقاس:</b> A5 للتوزيع السريع، وA4 للعرض الكامل، وA3 يُطوى إلى A4 بأربع صفحات.',
               '<b>الورق:</b> 150 غرام للفلاير، و200 أو 300 غرام للبروشور المتماسك.',
               '<b>الإضافات:</b> طي، وسلوفان، وسبوت UV بارز.'],
         price_h2='أسعار طباعة البروشورات', table=('price', ['المقاس والورق', 'سعر 1000 بروشور'], [
             ('var:BRO-130-A5', 'A5 · ورق 150 غرام'), ('var:BRO-130-A4', 'A4 · ورق 150 غرام'), ('var:BRO-130-A3', 'A3 · ورق 150 غرام'),
             ('var:BRO-200-A4', 'A4 · ورق 200 غرام'), ('var:BRO-200-A4-S', 'A4 · ورق 200 غرام · مع سلوفان'), ('var:BRO-300-A4', 'A4 · ورق 300 غرام')]),
         note='السعر يشمل الطباعة حسب المواصفات، ولا يشمل التصميم.',
         send='المقاس ونوع الورق والكمية',
         tips=FILE_TIPS + ['حدّد نوع الطي قبل التصميم، نصفين أو ثلاث طيات، لأن ترتيب الصفحات يتغيّر معه.', DESIGN_TIP],
         article=None,
         q_price='كم سعر طباعة 1000 بروشور في {city}؟',
         a_price='يبدأ سعر الألف من {lo} بمقاس A5، ومن {a4} بمقاس A4، ويصل إلى {hi} بمقاس A3 على ورق 300 غرام مع السلوفان وسبوت UV.',
         faq=('ما الفرق بين الفلاير والبروشور؟',
              'الفلاير ورقة واحدة بلا طي، وتكفيها سماكة 150 غرام. البروشور يُطوى ويحمل تفاصيل أكثر، ويناسبه ورق 200 غرام وما فوق.')),
    dict(key='gifts', slug='طباعة-هدايا-دعائية', name='طباعة هدايا دعائية', the='الهدايا الدعائية', kind='logo', weight='',
         base='path:' + PROMO, base_label='تصفّح الهدايا الدعائية وأسعارها', img='MD-OF-0001', img_alt='هدايا دعائية: دفتر وقلم وميدالية',
         prices=dict(lo='cat:' + PROMO + 'pens/klp/', key='cat:' + PROMO + 'anh/', thermos='cat:' + PROMO + 'drinkware/thermoses/'),
         lead='نطبع شعارك على أكثر من {count} منتج دعائي: أقلام وميداليات وترامس وإلكترونيات وأطقم هدايا. الأسعار تبدأ من {lo} للقطعة.',
         count=PROMO, from_label='{lo} للقطعة', desc_price='أكثر من {count} منتج بأسعار تبدأ من {lo} للقطعة',
         h2='هدايا دعائية تحمل شعارك',
         intro='لكل منتج في الموقع سعر وكود. تختار المنتجات، وترسل لنا الأكواد والكميات، ونقترح طريقة الطباعة المناسبة لكل خامة.',
         opts=['<b>للتوزيع الواسع:</b> أقلام وميداليات.', '<b>للعملاء والموظفين:</b> ترامس ودفاتر وباوربانك.',
               '<b>لكبار العملاء:</b> أطقم هدايا في علبة.'],
         price_h2='أسعار الهدايا الدعائية حسب القسم', table=('cats', ['القسم', 'عدد المنتجات', 'يبدأ من'], [
             ('cat:' + PROMO + 'pens/', 'الأقلام'), ('cat:' + PROMO + 'anh/', 'الميداليات'), ('cat:' + PROMO + 'drinkware/', 'الأكواب والترامس'),
             ('cat:' + PROMO + 'electronics/', 'الإلكترونيات الدعائية'), ('cat:' + PROMO + 'desk-accessories/', 'المستلزمات المكتبية'),
             ('cat:' + PROMO + 'clocks/', 'الساعات'), ('cat:' + PROMO + 'bags/', 'الحقائب'), ('cat:' + PROMO + 'gift-sets/', 'أطقم الهدايا')]),
         note='الأسعار للقطعة دون طباعة الشعار. كلفة الشعار تُحسب في عرض السعر حسب الطريقة والكمية.',
         send='أكواد المنتجات والكميات',
         tips=['أكواد المنتجات والكمية لكل منتج.', 'الشعار بصيغة مفتوحة (AI أو PDF).', 'موعد المناسبة أو المعرض، لنرتّب التنفيذ والشحن قبله.',
               'الميزانية التقريبية للقطعة، إذا أردت أن نقترح عليك.'],
         article=('logo-printing-methods', 'طرق طباعة الشعار على الهدايا'),
         q_price='كم سعر الهدايا الدعائية في {city}؟',
         a_price='يبدأ القلم البلاستيكي من {lo}، والميدالية من {key}، والترمس من {thermos}. السعر للقطعة دون طباعة الشعار.',
         faq=('ما أقل كمية للهدايا الدعائية؟', 'يختلف الحد الأدنى حسب المنتج. أرسل لنا الكمية التي تحتاجها، ونقترح عليك الخيار المناسب.')),
    dict(key='pens', slug='طباعة-أقلام-دعائية', name='طباعة أقلام دعائية', the='الأقلام الدعائية', kind='logo', weight='',
         base='path:' + PROMO + 'pens/', base_label='تصفّح الأقلام وأسعارها', img='MD-TR-1-0438', img_alt='أقلام دعائية معدنية بألوان متعددة',
         prices=dict(lo='cat:' + PROMO + 'pens/klp/', metal='cat:' + PROMO + 'pens/metal-kalem/'),
         lead='نطبع شعارك على الأقلام البلاستيكية والمعدنية، بطباعة UV أو بالحفر بالليزر. في الموقع أكثر من {count} قلم، وسعر القلم يبدأ من {lo}.',
         count=PROMO + 'pens/', from_label='{lo} للقلم', desc_price='أكثر من {count} قلم، والسعر يبدأ من {lo} للقلم',
         h2='أقلام بشعار شركتك',
         intro='القلم أكثر هدية دعائية تُستعمل بعد توزيعها. البلاستيكي يناسب المعارض والكميات الكبيرة، والمعدني يناسب العملاء والموظفين.',
         opts=['<b>بلاستيكية:</b> يُطبع عليها الشعار بألوانه.', '<b>معدنية:</b> يُحفر الشعار بالليزر، فيظهر بلون المعدن ولا يزول.',
               '<b>أطقم أقلام:</b> في علبة، هدية لكبار العملاء.'],
         price_h2='أسعار الأقلام الدعائية حسب النوع', table=('cats', ['النوع', 'عدد المنتجات', 'يبدأ من'], [
             ('cat:' + PROMO + 'pens/klp/', 'أقلام بلاستيكية'), ('cat:' + PROMO + 'pens/metal-kalem/', 'أقلام معدنية'),
             ('cat:' + PROMO + 'pens/eco-pens/', 'أقلام صديقة للبيئة'), ('cat:' + PROMO + 'pens/pencils-highlighters/', 'أقلام رصاص وتمييز'),
             ('cat:' + PROMO + 'pens/pen-sets/', 'أطقم أقلام')]),
         note='الأسعار للقلم دون طباعة الشعار. كلفة الشعار تُحسب في عرض السعر حسب الطريقة والكمية.',
         send='كود القلم ولونه والكمية',
         tips=['كود القلم ولونه والكمية.', 'الشعار بصيغة مفتوحة (AI أو PDF)، ونسخة بلون واحد للحفر بالليزر.',
               'نرسل لك نموذجاً يُظهر مكان الشعار على القلم قبل التنفيذ.'],
         article=('logo-printing-methods', 'طرق طباعة الشعار على الهدايا'),
         q_price='كم سعر القلم الدعائي في {city}؟',
         a_price='يبدأ القلم البلاستيكي من {lo}، والمعدني من {metal}. السعر للقلم دون طباعة الشعار، وينزل مع الكمية.',
         faq=('طباعة أم حفر على القلم؟',
              'القلم المعدني يُحفر بالليزر، فيظهر الشعار بلون المعدن ولا يزول. القلم البلاستيكي يُطبع بالألوان، وهذا يناسب الشعار الملوّن.')),
    dict(key='notebooks', slug='طباعة-دفاتر-وأجندات', name='طباعة دفاتر وأجندات', the='الدفاتر والأجندات', kind='notebooks', weight='bulky',
         base='path:/product-category/notebooks/', base_label='تصفّح الدفاتر والأجندات وأسعارها', img='MD-AG-0001', img_alt='أجندة 2027 بشعار الشركة',
         prices=dict(lo='cat:/product-category/notebooks/', thermo='sku:MD-TR-1-0689', agenda='var:MD-AG-0001-01-200'),
         lead='نطبع شعارك على الدفاتر والأجندات: دفاتر بغلاف جلد حراري أو كرافت، وأجندة 2027 مؤرخة بهوية شركتك. سعر الدفتر يبدأ من {lo}.',
         from_label='{lo} للدفتر', desc_price='سعر الدفتر يبدأ من {lo}، وأجندة 2027 مؤرخة بهوية شركتك',
         h2='دفاتر وأجندة 2027 بشعارك',
         intro='الدفتر والأجندة يبقيان على المكتب طوال السنة. تختار دفتراً جاهزاً ونضع عليه شعارك، أو أجندة مؤرخة تُطبع كاملة بهوية شركتك.',
         opts=['<b>دفاتر جاهزة:</b> بغلاف جلد حراري أو كرافت أو ورق معاد التدوير، بمقاس 9×14 أو 13×21 سم.',
               '<b>أجندة 2027:</b> مؤرخة، بمقاس 17×25 سم، يُطبع غلافها وصفحاتها الإعلانية بتصميمك.',
               '<b>دفاتر ملاحظات مطبوعة:</b> 50 ورقة بصفحات مطبوعة بشعارك.'],
         price_h2='أسعار الدفاتر والأجندات', table=('price', ['المنتج', 'السعر'], [
             ('sku:MD-TR-1-0568', 'دفتر ملاحظات من ورق معاد تدويره', 'للقطعة'), ('sku:MD-TR-1-0687', 'دفتر خياطة 9×14 سم', 'للقطعة'),
             ('sku:MD-TR-1-0688', 'دفتر خياطة 13×21 سم', 'للقطعة'), ('sku:MD-TR-1-0689', 'دفتر جلد حراري 13×21 سم', 'للقطعة'),
             ('sku:MD-TR-1-0663', 'أجندة جلد حراري 17×24 سم', 'للقطعة'),
             ('var:MD-AG-0001-01-200', 'أجندة 2027 مؤرخة 17×25 سم', 'لـ 200 نسخة')]),
         note='أسعار الدفاتر الجاهزة للقطعة دون طباعة الشعار. سعر الأجندة المؤرخة يشمل الطباعة.',
         send='كود الدفتر ولون الغلاف والكمية',
         tips=['كود الدفتر ولون الغلاف والكمية.', 'الشعار بصيغة مفتوحة (AI أو PDF).', 'نرسل لك نموذج الغلاف للموافقة قبل التنفيذ.'],
         article=('agenda-2027', 'دليل أجندة 2027 بشعار الشركة'),
         q_price='كم سعر الدفتر بشعار الشركة في {city}؟',
         a_price='يبدأ سعر الدفتر من {lo}، ودفتر الجلد الحراري 13×21 سم بسعر {thermo} للقطعة دون الشعار. أجندة 2027 المؤرخة تبدأ من {agenda} لـ 200 نسخة.',
         faq=('كيف يوضع الشعار على الدفتر؟', 'على الجلد الحراري يُحفر الشعار بالحرارة، فيظهر غائراً بلا لون. وعلى الكرافت والكرتون يُطبع بالألوان.')),
    dict(key='bags', slug='طباعة-أكياس-ورقية', name='طباعة أكياس ورقية', the='الأكياس الورقية', kind='boxes', weight='bulky',
         base='sku:MD-PR-0015', base_label='اختر المقاس والكمية من صفحة الأكياس', img='MD-PR-0015', img_alt='كيس ورقي مطبوع بالشعار',
         prices=dict(lo='var:MD-PR-0015-01-100', k='var:MD-PR-0015-01-1000'),
         lead='نطبع الأكياس الورقية بشعار متجرك بالألوان الكاملة، بستة مقاسات وبكميات من 100 إلى 2,000 كيس. سعر 100 كيس يبدأ من {lo}.',
         from_label='{lo} لـ 100 كيس', desc_price='سعر 100 كيس يبدأ من {lo}',
         h2='أكياس ورقية بشعار متجرك',
         intro='الكيس المطبوع يحمل اسمك مع كل عملية بيع. نطبعه على بريستول 230 غرام بسلوفان مطفي أو لامع، مع علّاقات.',
         opts=['<b>المقاسات:</b> ستة، من 17×24×7 سم إلى 50×34×15 سم.',
               '<b>الكميات:</b> 100 و250 و500 و1,000 و2,000 كيس، وسعر الكيس ينزل كلما زادت الكمية.',
               '<b>الإضافات:</b> ورنيش موضعي على الشعار.'],
         price_h2='أسعار طباعة الأكياس الورقية', table=('pivot', 'MD-PR-0015', 'المقاس', 'الكمية', ['100', '500', '1,000'], {'الورنيش الموضعي': 'بدون'}, 'كيس'),
         note='السعر للكمية كاملة مع الطباعة، بلا ورنيش موضعي.',
         send='المقاس والكمية',
         tips=['مقاس الكيس، أو مقاس المنتج الذي سيحمله لنقترح المقاس.', 'الكمية، ونوع السلوفان: مطفي أو لامع.', 'الشعار بصيغة مفتوحة (AI أو PDF).',
               'نرسل لك نموذج التصميم على الكيس للموافقة قبل الطباعة.'],
         article=None,
         q_price='كم سعر طباعة الأكياس الورقية في {city}؟',
         a_price='يبدأ سعر 100 كيس بمقاس 17×24×7 سم من {lo}، وسعر 1,000 كيس بالمقاس نفسه {k}. السعر للكمية كاملة مع الطباعة.',
         faq=('ما أقل كمية للأكياس الورقية؟', '100 كيس من التصميم نفسه. وسعر الكيس ينزل كلما زادت الكمية، لذلك قارن بين سعر 500 و1,000 قبل أن تطلب.')),
    dict(key='stickers', slug='طباعة-ستيكرات', name='طباعة ستيكرات', the='الستيكرات', kind='paper', weight='light',
         base='sku:ETK', base_label='اختر المقاس من صفحة الاستيكر', img='ETK', img_alt='ستيكرات لاصقة مطبوعة',
         prices=dict(lo='var:ETK-8X5-D', cut='var:ETK-8X5-O'),
         lead='نطبع الستيكرات اللاصقة بتصميمك على ورق لاصق 90 غرام، بقص مستقيم أو بقص خاص على شكل شعارك. سعر الألف ستيكر يبدأ من {lo}.',
         from_label='{lo} لألف ستيكر', desc_price='سعر الألف ستيكر يبدأ من {lo}',
         h2='ستيكرات لاصقة لمنتجاتك وعلبك',
         intro='الستيكر أرخص طريقة لوضع شعارك على العلبة والكيس والمنتج. يُطلب بالألف، بمقاس 8×5 سم أو 16×5 سم.',
         opts=['<b>القص المستقيم:</b> ستيكر مستطيل، وهو الأرخص.', '<b>القص الخاص:</b> على شكل الشعار أو دائرة أو أي شكل تختاره.'],
         price_h2='أسعار طباعة الستيكرات', table=('price', ['المقاس والقص', 'سعر 1000 ستيكر'], [
             ('var:ETK-8X5-D', '8×5 سم · قص مستقيم'), ('var:ETK-8X5-O', '8×5 سم · قص خاص'),
             ('var:ETK-16X5-D', '16×5 سم · قص مستقيم'), ('var:ETK-16X5-O', '16×5 سم · قص خاص')]),
         note='السعر يشمل الطباعة على ورق لاصق 90 غرام، ولا يشمل التصميم.',
         send='المقاس ونوع القص والكمية',
         tips=FILE_TIPS + ['في القص الخاص أرسل خط القص في طبقة منفصلة داخل الملف.', DESIGN_TIP],
         article=None,
         q_price='كم سعر طباعة 1000 ستيكر في {city}؟',
         a_price='يبدأ سعر الألف من {lo} بمقاس 8×5 سم وقص مستقيم.',
         faq=('ما الفرق بين القص المستقيم والقص الخاص؟',
              'المستقيم يقص الستيكر مستطيلاً. الخاص يقصه على شكل التصميم، لذلك سعره أعلى: {cut} للألف بمقاس 8×5 سم، مقابل {lo} للمستقيم.')),
    dict(key='flags', slug='طباعة-أعلام-ورول-أب', name='طباعة أعلام ورول أب', the='الأعلام والرول أب', kind='flags', weight='',
         base='path:/product-category/flag-ar/', base_label='تصفّح الأعلام والرول أب وأسعارها', img='MD-FL-27', img_alt='رول أب مطبوع للمعارض',
         prices=dict(lo='var:MD-FL-27-03', set='var:MD-FL-27-01', desk='var:MD-FL-01-01'),
         lead='نطبع الأعلام والرول أب بتصميمك بالألوان الكاملة: رول أب للمعارض، وأعلام مكتبية، وأعلام ساريات، وأعلام شراعية. طباعة الرول أب تبدأ من {lo}، والطقم الكامل بسعر {set}.',
         from_label='{lo} لطباعة الرول أب', desc_price='طباعة الرول أب من {lo}، والطقم الكامل {set}',
         h2='أعلام ورول أب لمكتبك ومعرضك',
         intro='الرول أب يحمل شعارك ورسالتك في المعرض، ثم يُطوى في حقيبته. والعلم المكتبي يوضع على مكتب الإدارة وفي قاعة الاجتماعات.',
         opts=['<b>رول أب:</b> آلية ألمنيوم مع حقيبة حمل، وطباعة على ساتان.',
               '<b>أعلام مكتبية:</b> ساتان مطبوع على الوجهين مع حامل كروم. أقل كمية 5 قطع من التصميم نفسه.',
               '<b>أعلام خارجية:</b> أعلام ساريات وأعلام شراعية وقطرة، على قماش بوليستر.'],
         price_h2='أسعار طباعة الأعلام والرول أب', table=('price', ['المنتج', 'السعر'], [
             ('var:MD-FL-27-01', 'رول أب: طقم كامل، آلية وطباعة', 'للطقم'), ('var:MD-FL-27-03', 'رول أب: الطباعة فقط', 'للقطعة'),
             ('var:MD-FL-01-01', 'علم مكتبي مفرد مع حامل كروم', 'للطقم'), ('var:MD-FL-16-03', 'علم سارية خارجي 100×150 سم', 'للقطعة'),
             ('var:MD-FL-12-01', 'علم شراعي 75×200 سم: طقم كامل', 'للطقم'), ('var:MD-FL-13-01', 'علم قطرة 100×200 سم: طقم كامل', 'للطقم')]),
         note='الأسعار تشمل الطباعة بالألوان الكاملة.',
         send='نوع العلم والمقاس والكمية',
         tips=['نوع العلم والمقاس والكمية.', 'التصميم بصيغة PDF أو AI.', 'نطبع العلم بشعارك أو بعلم الدولة، ويراجع فريق التصميم الملف قبل التنفيذ.'],
         article=('flag-printing-guide', 'دليل طباعة الأعلام'),
         q_price='كم سعر الرول أب في {city}؟',
         a_price='الطقم الكامل، آلية ألمنيوم مع الطباعة والحقيبة، بسعر {set}. وإذا كانت عندك الآلية فالطباعة وحدها بسعر {lo}.',
         faq=('ما أقل كمية للأعلام المكتبية؟', '5 قطع من التصميم نفسه. سعر الطقم المفرد مع الحامل الكروم {desk}.')),
    dict(key='apparel', slug='طباعة-تيشيرتات-وملابس', name='طباعة تيشيرتات وملابس', the='التيشيرتات والملابس', kind='apparel', weight='bulky',
         base='path:/product-category/tekstil-ar/', base_label='تصفّح الألبسة وأسعارها', img='MD-TR-1-1003', img_alt='بولو بشعار الشركة بألوان متعددة',
         prices=dict(lo='sku:MD-TR-1-1001', polo='sku:MD-TR-1-1003', hoodie='sku:MD-TR-1-1005'),
         lead='نجهّز ملابس فريقك بشعار الشركة، مطبوعاً بطباعة DTF أو مطرّزاً: تيشيرت وبولو وهودي وفيست وقبعة. البولو يبدأ من {polo}، والقبعة من {lo}.',
         from_label='{lo} للقبعة، و{polo} للبولو', desc_price='البولو يبدأ من {polo}، والقبعة من {lo}، دون الشعار',
         h2='ملابس موحّدة بشعار شركتك',
         intro='اللباس الموحّد يعرّف الزبون بموظفيك في المعرض والمحل والموقع الميداني. تختار القطعة واللون، ونضع الشعار على الصدر أو الظهر أو الكم.',
         opts=['<b>طباعة DTF:</b> تنقل الشعار بألوانه وتدرّجاته، وتناسب التيشيرت والهودي.',
               '<b>التطريز:</b> شعار بارز بالخيط، يناسب البولو والقبعة والجاكيت.'],
         price_h2='أسعار الملابس بشعار الشركة', table=('price', ['القطعة', 'يبدأ من'], [
             ('sku:MD-TR-1-1002', 'تيشيرت قطن'), ('sku:MD-TR-1-1003', 'بولو نصف كم'), ('sku:MD-TR-1-1007', 'بولو كم طويل'),
             ('sku:MD-TR-1-1004', 'فيست (صدرية)'), ('sku:MD-TR-1-1005', 'هودي بغطاء رأس'), ('sku:MD-TR-1-1008', 'جاكيت فليس'),
             ('sku:MD-TR-1-1001', 'قبعة قطن')]),
         note='السعر للقطعة دون الشعار، ويتغيّر حسب الكمية والمقاسات وطريقة الشعار.',
         send='القطعة واللون والمقاسات',
         tips=['جدول المقاسات: عدد القطع لكل مقاس.', 'لون القماش لكل فريق.', 'الشعار بصيغة مفتوحة (AI أو PDF)، ومكانه ومقاسه على القطعة.'],
         article=('corporate-apparel-printing', 'دليل ملابس الشركات بالشعار'),
         q_price='كم سعر طباعة التيشيرتات والبولو في {city}؟',
         a_price='البولو نصف كم يبدأ من {polo}، والهودي من {hoodie}، والقبعة من {lo}. السعر للقطعة دون الشعار، وسعر التيشيرت يُحدَّد في عرض السعر حسب الكمية.',
         faq=('طباعة أم تطريز؟', 'شعار صغير على الصدر يُطرَّز، وتصميم كبير أو ملوّن على الظهر يُطبع.')),
    dict(key='boxes', slug='طباعة-علب-هدايا', name='طباعة علب هدايا', the='علب الهدايا', kind='boxes', weight='bulky',
         base='path:/product-category/packaging/gift-boxes/', base_label='تصفّح علب الهدايا وأسعارها', img='MD-TR-1-0272', img_alt='علبة هدايا بكسوة جلد حراري',
         prices=dict(lo='sku:MD-TR-1-0282', pen='sku:MD-TR-1-0342', thermo='sku:MD-TR-1-0272'),
         lead='نضع شعارك على علب الهدايا: كرافت وكرتون مغلّف وجلد حراري، من علبة القلم إلى صندوق كبار الضيوف. جراب القلم من {pen}، والعلبة من {lo}.',
         from_label='{lo} للعلبة', desc_price='العلبة من {lo}، وجراب القلم من {pen}',
         h2='علب هدايا بشعارك',
         intro='العلبة أول ما يراه من يستلم الهدية، وهي التي تجمع القطع في هدية واحدة. حدّد أولاً ما ستضعه فيها، ثم اختر المقاس.',
         opts=['<b>كرافت وكرتون مغلّف:</b> اقتصادية، ويُطبع عليها الشعار بالألوان.', '<b>جلد حراري:</b> يُحفر عليه الشعار بالحرارة.',
               '<b>صناديق حسب الطلب:</b> بالمقاس واللون اللذين تختارهما، لكبار الضيوف.'],
         price_h2='أسعار علب الهدايا', table=('price', ['العلبة', 'السعر'], [
             ('sku:MD-TR-1-0282', 'كرتون مغلّف 17×9.5 سم'), ('sku:MD-TR-1-0284', 'كرافت 25×25×10 سم'), ('sku:MD-TR-1-0274', 'كرتون مغلّف 26×21×4 سم'),
             ('sku:MD-TR-1-0281', 'جلد حراري 18×12.5 سم'), ('sku:MD-TR-1-0272', 'جلد حراري 26×21×4 سم'), ('sku:MD-TR-1-0270', 'جلد حراري 32×28×10 سم')]),
         note='السعر للعلبة فارغة ودون طباعة الشعار.',
         send='محتوى الهدية والكمية',
         tips=['قائمة القطع التي ستدخل العلبة، لنقترح المقاس والحشوة.', 'الخامة والكمية.', 'الشعار بصيغة مفتوحة (AI أو PDF).'],
         article=('gift-boxes-printing', 'دليل علب الهدايا المطبوعة'),
         q_price='كم سعر علبة الهدايا بالشعار في {city}؟',
         a_price='العلبة الكرتون المغلّف تبدأ من {lo}، وعلبة الجلد الحراري 26×21×4 سم بسعر {thermo}. السعر للعلبة فارغة ودون طباعة الشعار.',
         faq=('هل تنفّذون علبة بمقاس خاص؟', 'نعم. صناديق كبار الضيوف ننفّذها بالمقاس واللون اللذين تختارهما، ونرسل لك نموذجاً قبل التنفيذ.')),
]
# guide articles that end with «… في مدينتك»
ARTICLE_SERVICE = {'business-cards-printing': 'cards', 'flag-printing-guide': 'flags', 'corporate-apparel-printing': 'apparel',
                   'gift-boxes-printing': 'boxes', 'agenda-2027': 'notebooks', 'exhibition-giveaways': 'gifts',
                   'corporate-gifts-new-year-2027': 'gifts', 'logo-printing-methods': 'pens'}

_S = {}   # filled by setup()


def qpath(ar):
    """/markets/مطبعة-دمشق/ -> the percent-encoded lower-case form the rest of the site uses."""
    return '/'.join(up.quote(x, safe='').lower() for x in ar.split('/'))


def usd(x):
    return '$' + (f'{x:,.0f}' if abs(x - round(x)) < 0.005 else f'{x:,.2f}')


def usd2(x):
    """In a price column every figure keeps its two decimals."""
    return f'${x:,.2f}'


def bdi(html):
    """Prices stay left-to-right inside the Arabic line."""
    return re.sub(r'\$[\d,]+(?:\.\d+)?', lambda m: f'<bdi>{m.group(0)}</bdi>', html)


def setup(catalog, pages_raw, contacts):
    by_sku = {p['sku']: p for p in catalog['products'] if p.get('sku')}
    var = {v['sku']: v for p in catalog['products'] for v in (p.get('variations') or []) if v.get('sku')}
    cats = {c['path']: c for c in catalog['categories']}
    kids = {}
    for c in catalog['categories']:
        kids.setdefault(c['parent'], []).append(c['id'])

    def cat_products(path):
        if path not in cats:
            raise SystemExit(f'localpages: no category {path}')
        ids, todo = set(), [cats[path]['id']]
        while todo:
            i = todo.pop()
            ids.add(i)
            todo += kids.get(i, [])
        return [p for p in catalog['products'] if ids & set(p['cats'])]

    def low(p):
        pr = p['price']
        return pr['min'] if p['type'] == 'variable' and pr.get('min') is not None else pr.get('price')

    def price(src):
        kind, code = src.split(':', 1)
        if kind == 'var':
            if code not in var:
                raise SystemExit(f'localpages: no variation {code}')
            return var[code]['price']
        if kind in ('sku', 'max'):
            if code not in by_sku:
                raise SystemExit(f'localpages: no product {code}')
            return by_sku[code]['price'].get('max') if kind == 'max' else low(by_sku[code])
        if kind == 'cat':
            v = [x for x in map(low, cat_products(code)) if x]
            if not v:
                raise SystemExit(f'localpages: no priced product in {code}')
            return min(v)
        raise SystemExit(f'localpages: bad price source {src}')

    paths = {up.unquote(p['path']): p for p in pages_raw}
    for c in CITIES:
        if c['page'] not in paths:
            raise SystemExit(f'localpages: the city page {c["page"]} is not in pages-raw.json')
        c['path'] = paths[c['page']]['path']
        c['page_title'] = paths[c['page']]['title']
    for m in MARKETS.values():
        if m['hub'] not in paths:
            raise SystemExit(f'localpages: the market page {m["hub"]} is not in pages-raw.json')
        m['hub_path'] = paths[m['hub']]['path']
        m['hub_title'] = paths[m['hub']]['title']
        who = next((x for x in contacts if x['market'] == m['contact']), contacts[0])   # Syria has its own line; the rest go to export sales
        m.update(person=who['person'], phone=who['phone'], wa=who['wa'])
    style = re.search(r'<style>.*?</style>', paths[CITIES[0]['page']]['parts'][0][1], flags=re.S)
    if not style:
        raise SystemExit('localpages: the guide style block is missing from the Damascus page')
    for s in SERVICES:
        vals = {k: usd(price(v)) for k, v in s['prices'].items()}
        if s.get('count'):
            n = len(cat_products(s['count']))
            vals['count'] = str(n // 100 * 100)
        s['vals'] = vals
        b_kind, b_code = s['base'].split(':', 1)
        if b_kind == 'sku' and b_code not in by_sku:
            raise SystemExit(f'localpages: no product {b_code}')
        s['base_path'] = by_sku[b_code]['path'] if b_kind == 'sku' else b_code
        if b_kind == 'path' and b_code not in cats:
            raise SystemExit(f'localpages: no category {b_code}')
        if s['img'] not in by_sku or not by_sku[s['img']]['images']:
            raise SystemExit(f'localpages: no picture for {s["img"]}')
        s['img_src'] = '/' + by_sku[s['img']]['images'][0]['src'].split('madarekmatbaa.com/', 1)[-1].lstrip('/')
    waves = re.search(r'<svg aria-hidden="true" class="mdk-waves".*?</svg>', paths[CITIES[0]['page']]['parts'][0][1], flags=re.S)
    _S.update(by_sku=by_sku, var=var, cats=cats, cat_products=cat_products, low=low, price=price, style=style.group(0),
              waves=waves.group(0) if waves else '')


def page_path(city, svc):
    return city['path'] + qpath(svc['slug']) + '/'


def table_html(svc):
    t = svc['table']
    if t[0] == 'pivot':
        _, sku, row_attr, col_attr, cols, fixed, unit = t
        p = _S['by_sku'][sku]
        grid, order = {}, []
        for v in p['variations']:
            a = v.get('attrs') or v.get('attributes') or {}
            if any(a.get(k) != val for k, val in fixed.items()) or a.get(col_attr) not in cols:
                continue
            if a[row_attr] not in grid:
                order.append(a[row_attr])
            grid.setdefault(a[row_attr], {})[a[col_attr]] = v['price']
        if not order or any(len(grid[r]) != len(cols) for r in order):
            raise SystemExit(f'localpages: the options of {sku} changed, so its price table cannot be built')
        head = f'<th>{row_attr}</th>' + ''.join(f'<th>{c} {unit}</th>' for c in cols)
        rows = ''.join('<tr><td>' + H.escape(r) + '</td>' + ''.join(f'<td class="n">{usd2(grid[r][c])}</td>' for c in cols) + '</tr>' for r in order)
        return f'<table class="md-table loc-t"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'
    kind, heads, rows = t
    out = ''
    for r in rows:
        src, label = r[0], r[1]
        k, code = src.split(':', 1)
        if kind == 'cats':
            ps = _S['cat_products'](code)
            out += f'<tr><td><a href="{code}">{label}</a></td><td class="n">{len(ps)}</td><td class="n">{usd2(_S["price"](src))}</td></tr>'
            continue
        v = _S['price'](src)
        unit = f' <small>{r[2]}</small>' if len(r) > 2 else ''
        name = f'<a href="{_S["by_sku"][code]["path"]}">{label}</a>' if k == 'sku' else label
        out += f'<tr><td>{name}</td><td class="n">{usd2(v) + unit if v else "حسب الكمية، في عرض السعر"}</td></tr>'
    return (f'<table class="md-table loc-t"><thead><tr>{"".join(f"<th>{h}</th>" for h in heads)}</tr></thead>'
            f'<tbody>{out}</tbody></table>')


def wa_link(market, text):
    return f'https://wa.me/{market["wa"]}?text={up.quote(text)}'


def render(city, svc):
    m = MARKETS[city['market']]
    v = svc['vals']
    cn, tn = city['name'], city['tname']
    h1 = f'{svc["name"]} في {tn}'
    path = page_path(city, svc)
    url = SITE + path
    wa = wa_link(m, f'مرحباً مدارك، أريد عرض سعر: {svc["name"]} — {cn}')
    made = MADE[city['market']]
    made_p = made.get(svc['kind']) or made['china' if svc['kind'] in CHINA_KINDS else 'plain']
    ship = SHIP_NOTE.get(svc['weight'], {}).get(city['market'], '').format(the=svc['the'])
    lis = lambda items: ''.join(f'<li>{x}</li>' for x in items)   # noqa: E731
    others = [s for s in SERVICES if s is not svc]
    cities = [c for c in CITIES if c is not city]
    art = svc['article']
    cards = (f'<a class="g-card" href="{city["path"]}"><span class="g-card-t">مطبعة مدارك في {cn}</span><p>كل ما نطبعه ونوصله إلى {cn}.</p><span class="g-go">تصفّح ←</span></a>'
             f'<a class="g-card" href="{svc["base_path"]}"><span class="g-card-t">{svc["price_h2"]}</span><p>كل الخيارات والأسعار في الموقع.</p><span class="g-go">تصفّح ←</span></a>'
             + (f'<a class="g-card" href="{TIPS}{art[0]}/"><span class="g-card-t">{art[1]}</span><p>ما تحتاج أن تعرفه قبل الطلب.</p><span class="g-go">اقرأ ←</span></a>' if art else
                f'<a class="g-card" href="{TIPS}"><span class="g-card-t">نصائح الطباعة</span><p>جهّز ملفاتك قبل الطباعة.</p><span class="g-go">اقرأ ←</span></a>')
             + '<a class="g-card" href="/shipping/"><span class="g-card-t">الشحن</span><p>الشحن الجزئي والكلي، وكيف تصلك الطلبية.</p><span class="g-go">تصفّح ←</span></a>')
    faq = [(svc['q_price'].format(city=cn), svc['a_price'].format(**v) + ' ' + m['price_note'].format(city=cn)),
           (f'كم تستغرق الطلبية حتى تصل إلى {cn}؟', m['time'].format(city=cn) + ' الطلبيات الكبيرة تحتاج من 20 إلى 25 يوماً للتنفيذ.'),
           (svc['faq'][0], svc['faq'][1].format(**v)),
           (f'كيف أطلب من {cn}؟', city['order'])]
    body = (
        '<div class="mdk-g loc-page"><section class="mdk mdk-page-hero">' + _S['waves'] + '<div class="mdk-wrap">'
        f'<h1>{h1}</h1><p>{svc["lead"].format(**v)} {city["reach"]}</p>'
        f'<div class="mdk-cta"><a class="mdk-btn mdk-btn-primary" href="{wa}" rel="noopener" target="_blank">اطلب عرض سعر عبر واتساب</a>'
        f'<a class="mdk-btn mdk-btn-outline" href="{svc["base_path"]}">{svc["base_label"]}</a></div>'
        f'<div class="g-crumbs"><a href="{city["path"]}">{city["page_title"]}</a><a href="{m["hub_path"]}">{m["hub_title"]}</a><a href="/shipping/">الشحن</a></div>'
        '</div></section>'
        # what it is
        '<section class="mdk g-sec"><div class="mdk-wrap"><div class="g-split"><div>'
        f'<h2 class="mdk-h2">{svc["h2"]}</h2><p class="g-lead">{svc["intro"]}</p><ul class="g-list">{lis(svc["opts"])}</ul></div>'
        f'<figure class="g-figure"><img alt="{svc["img_alt"]}" decoding="async" height="520" loading="lazy" src="{svc["img_src"]}" width="520"/></figure>'
        '</div></div></section>'
        # prices
        '<section class="mdk g-sec g-alt"><div class="mdk-wrap">'
        f'<div class="g-head"><h2 class="mdk-h2">{svc["price_h2"]}</h2><p class="mdk-lead">الأسعار بالدولار، وهي نفسها المعروضة في المتجر.</p></div>'
        f'<div class="g-tablewrap loc-tw">{table_html(svc)}</div>'
        f'<p class="g-note">{svc["note"]} {m["price_note"].format(city=cn)}</p>'
        f'<div class="mdk-cta loc-cta"><a class="mdk-btn mdk-btn-outline" href="{svc["base_path"]}">{svc["base_label"]}</a></div>'
        '</div></section>'
        # how it reaches the city
        '<section class="mdk g-sec"><div class="mdk-wrap"><div class="g-split" style="align-items:start"><div>'
        f'<h2 class="mdk-h2">كيف تصل {svc["the"]} إلى {cn}؟</h2><p class="g-lead">{made_p} {city["deliver"]}</p>'
        + (f'<p class="g-lead">{ship}</p>' if ship else '') +
        '<ul class="g-list"><li><b>التنفيذ:</b> من 7 إلى 10 أيام بعد اعتماد التصميم، ومن 20 إلى 25 يوماً للطلبيات الكبيرة.</li>'
        f'<li>{m["ship_line"].format(city=cn)}</li><li><b>الدفع:</b> 50% للبدء، والباقي عند تجهيز البضاعة.</li></ul></div>'
        f'<div><ol class="g-steps"><li>ترسل {svc["send"]} وموعدك عبر واتساب.</li><li>نرسل عرض السعر ونموذج التصميم للموافقة.</li>'
        f'<li>بعد دفع 50% نبدأ التنفيذ.</li><li>{m["last_step"].format(city=cn)}</li></ol></div>'
        '</div></div></section>'
        # what we need
        '<section class="mdk g-sec g-alt"><div class="mdk-wrap"><div class="g-head"><h2 class="mdk-h2">ما الذي نحتاجه منك؟</h2></div>'
        f'<ul class="g-list loc-need">{lis(svc["tips"])}</ul></div></section>'
        # questions
        f'<section class="mdk g-sec"><div class="mdk-wrap g-faq"><h2 class="mdk-h2">أسئلة عن {svc["name"]} في {cn}</h2>'
        + ''.join(f'<h3>{q}</h3><p>{a}</p>' for q, a in faq) + '</div></section>'
        # links
        f'<section class="mdk g-sec g-alt"><div class="mdk-wrap"><div class="g-head"><h2 class="mdk-h2">خدمات طباعة أخرى في {cn}</h2></div>'
        '<div class="g-crumbs loc-links">' + ''.join(f'<a href="{page_path(city, s)}">{s["name"]}</a>' for s in others) + '</div>'
        f'<h2 class="mdk-h2 loc-h">{svc["name"]} في مدن أخرى</h2>'
        '<div class="g-crumbs loc-links">' + ''.join(f'<a href="{page_path(c, svc)}">{c["name"]}</a>' for c in cities) + '</div>'
        f'<div class="g-grid g4 loc-cards">{cards}</div></div></section>'
        # contact
        '<section class="mdk loc-end"><div class="mdk-wrap"><div class="mdk-cta-band"><div>'
        f'<h2>اطلب عرض سعر في {cn}</h2><p>أرسل {svc["send"]} وموعدك، ونرد عليك بعرض سعر ونموذج تصميم.</p></div>'
        f'<div class="mdk-contacts"><a class="mdk-contact" href="{wa}" rel="noopener" target="_blank"><div><small>{m["name"]} — {m["person"]}</small>'
        f'<b>{m["phone"]}</b></div><i>واتساب</i></a><a class="mdk-contact" href="mailto:sales@madarekmatbaa.com"><div><small>البريد الإلكتروني</small>'
        '<b>sales@madarekmatbaa.com</b></div><i>راسلنا</i></a></div></div></div></section></div>')
    desc = f'{svc["name"]} في {tn} من مطبعة مدارك: {svc["desc_price"].format(**v)}. {m["time_short"]}.'
    if len(desc) <= 136:
        desc += ' اطلب عرض سعر عبر واتساب.'
    title = f'{h1}: الأسعار ومدة التسليم | مدارك'
    if len(title) > 62:
        title = f'{h1}: الأسعار والتسليم | مدارك'
    org = {'@id': SITE + '/#organization'}
    crumbs = [('الرئيسية', SITE + '/'), ('الأسواق', SITE + '/markets/'), (m['hub_title'], SITE + m['hub_path']),
              (city['page_title'], SITE + city['path']), (svc['name'], None)]
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Service', '@id': url + '#service', 'name': h1, 'serviceType': svc['name'], 'description': desc, 'url': url, 'provider': org,
         'areaServed': [{'@type': 'City', 'name': city['en']}, {'@type': 'Country', 'name': city['country_en']}],
         'availableChannel': {'@type': 'ServiceChannel', 'serviceUrl': wa}},
        {'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': [
            dict({'@type': 'ListItem', 'position': i + 1, 'name': n}, **({'item': u} if u else {})) for i, (n, u) in enumerate(crumbs)]},
        {'@type': 'Organization', '@id': SITE + '/#organization', 'name': 'مطبعة مدارك - Madarek Matbaa', 'url': SITE + '/'}]}
    d, t = H.escape(desc, quote=True), H.escape(title, quote=True)
    tags = ['<meta content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" name="robots"/>',
            f'<meta content="{d}" name="description"/>', '<meta content="ar_AR" property="og:locale"/>', '<meta content="website" property="og:type"/>',
            f'<meta content="{t}" property="og:title"/>', f'<meta content="{d}" property="og:description"/>', f'<meta content="{url}" property="og:url"/>',
            '<meta content="مطبعة مدارك - Madarek Matbaa" property="og:site_name"/>', f'<meta content="{SHARE_IMG}" property="og:image"/>',
            '<meta content="1200" property="og:image:width"/>', '<meta content="630" property="og:image:height"/>',
            '<meta content="summary_large_image" name="twitter:card"/>', '<meta content="@MadarekMatbaa" name="twitter:site"/>',
            f'<link href="{url}" rel="canonical"/>']
    return {'id': 0, 'slug': svc['slug'], 'path': path, 'parent': 0, 'title': h1, 'template': '', 'ar_only': True, 'local': True,
            'seo': {'title': title, 'tags': tags, 'ld': [json.dumps(ld, ensure_ascii=False)]}, 'parts': [['html', _S['style'] + bdi(body)]]}


def pages():
    return [render(c, s) for c in CITIES for s in SERVICES]


def city_section(path, html):
    """The city's own page lists its services, with a price each, above its questions."""
    city = next((c for c in CITIES if c['path'] == path), None)
    if not city:
        return html
    at = html.find('<h2 class="mdk-h2">أسئلة شائعة')
    at = html.rfind('<section', 0, at) if at > 0 else -1
    if at < 0:
        raise SystemExit(f'localpages: the questions section moved on {city["page"]}')
    rows = ''.join(f'<tr><td><a href="{page_path(city, s)}">{s["name"]} في {city["name"]}</a></td><td class="n">{s["from_label"].format(**s["vals"])}</td></tr>'
                   for s in SERVICES)
    sec = ('<section class="mdk g-sec loc-svc"><div class="mdk-wrap">'
           f'<div class="g-head"><h2 class="mdk-h2">خدمات الطباعة في {city["name"]}</h2>'
           '<p class="mdk-lead">لكل خدمة صفحة فيها الأسعار ومدة التسليم.</p></div>'
           '<div class="g-tablewrap loc-tw"><table class="md-table loc-t"><thead><tr><th>الخدمة</th><th>يبدأ من</th></tr></thead>'
           f'<tbody>{bdi(rows)}</tbody></table></div></div></section>')
    return html[:at] + sec + html[at:]


def article_cities(slug):
    """Guide articles end with the same service in each city."""
    key = ARTICLE_SERVICE.get(slug)
    if not key:
        return ''
    svc = next(s for s in SERVICES if s['key'] == key)
    links = ''.join(f'<a href="{page_path(c, svc)}">{c["name"]}</a>' for c in CITIES)
    return f'<p class="art-cities"><b>{svc["name"]} في مدينتك:</b>{links}</p>'
