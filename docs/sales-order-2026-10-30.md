# Product order and scrolling rows (30 Oct 2026)

**Request (Ammar, 30 Oct):** «بدي ترتب لي المنتجات بالمنتجات المتوقع أن تنباع أكثر على هوا السجلات… بدون ما تحط
أكثر مبيعا… ويتخربطوا» — every listing (All, each category, the home tabs) should open on what usually sells,
kinds mixed, with no "best seller" label. And «ما في لا سهم ولا قرار أروح للطرف الثاني» — the category rows that
scroll sideways need a way to reach the other end.

## How the order is made (`lib/ranking.py`)
1. Every product gets a **kind**: business cards, brochures, stickers, envelopes, letterhead, folders, paper bags,
   agendas, notebooks, desk flags, ceremonial flags, feather flags, roll-ups, gift boxes, gift sets, … and otherwise
   its own category (metal pens, plastic pens, keychains, mugs, calculators …).
2. A kind's **weight** = a fixed prior (what we expect to sell) + the demand from the portal's quotes and orders
   (`data/sales_rank.json`: orders ×3, accepted ×2.5, sent ×1, lost/expired ×0.6, cancelled ×0.3, 498 distinct
   lines on 30 Oct). Most asked for: business cards, metal pens, notebooks, brochures, gift boxes and sets,
   desk flags, roll-ups, paper bags, stickers, ceremonial flags. Calculators: nothing.
3. Listings take products from all kinds in proportion to the weights, so each page starts with what sells and
   keeps mixing kinds. Calculators now first appear around place 120 of 807 (they were first on «الهدايا الدعائية»).
4. Inside a kind: products quoted by code in the portal first (e.g. pens 0417, 0497, 0441, umbrellas 0823–0825,
   sun visor 0963), then one of each line and look-alike before the next, and products whose picture is still a text
   card (44 on 30 Oct) after all products with a photo.
5. `lead` in `data/sales_rank.json` puts a product first in its kind: the 2027 agenda, the business card, the desk
   flag set, the ceremonial flag set, the feather flag.

The same order drives the first page (built), «load more» and sorting (the browser), and the English and Turkish
sites. Refresh the numbers when there are more quotes: `python3 tools/sales_rank.py js` (run the printed script in
the portal while logged in), then `python3 tools/sales_rank.py update --demand <saved JSON>`; `show --cat <id>`
prints the top of any listing.

## Scrolling rows
Category tabs, sub-category chips and the home tabs show a round arrow at each end that has more, and the row
fades at that edge (`data-hs` in `templates/shop.html`, `partials/ptabs.html`; `assets/js/site.js`, `m.css`).
Arrows follow the reading direction (Arabic and English/Turkish). The current category is scrolled into view
when it is off screen.

## 31 Oct: new kinds
- Car fragrances (MD-TR-1-0966) are their own kind with the portal demand for «فواحات» (orders from Syria and Libya).
- Clothing now counts in full (the site has polos, T-shirts, hoodies, jackets, vests and caps).
- Offers (category «العروض والباقات», MD-OF-0001…0006) have a high prior, so they show early in «الكل»; they also
  open the home page tabs.
