# madarekmatbaa.com — static site

The public website of Madarek Matbaa (مطبعة مدارك), rebuilt without WordPress.
Same URLs, same SEO heads, same look; a fraction of the weight.

## Build

```
pip install -r requirements.txt
python3 build.py          # writes dist/
```

`python3 build.py --no-media` skips copying the original uploads (faster while editing).

## What is where

| Path | What |
|---|---|
| `content/catalog.json` | categories + products (prices, options, SEO heads, descriptions) |
| `content/pages-raw.json` | the content pages (home, about, contact, markets …) |
| `content/nav.json` | header menu and category tree |
| `data/order_menu.json` | default product order (same as the old shop) |
| `data/ref/` | reference markup, live sitemaps (for lastmod), robots.txt |
| `media/wp-content/uploads/` | original images and PDFs, kept at their old URLs |
| `templates/` | Jinja templates |
| `assets/css`, `assets/js` | styles and scripts (bundled + hashed at build) |
| `lib/images.py` | WebP thumbnails and WordPress-sized image names |
| `tools/snapshot.py` | one-time import from the WordPress export |

## Output extras

- `sitemap_index.xml`, `page-sitemap.xml`, `product-sitemap.xml`, `product_cat-sitemap.xml` (same names as Yoast)
- `_redirects` (old WordPress redirects + removed cart/account pages), `_headers` (cache + noindex on *.pages.dev)
- `feeds/google.xml` (Merchant Center, ids `gla_<id>`) and `feeds/meta.xml` (Commerce Manager, ids `<sku>_<id>`)
- `data/catalog.json` — one shared file for load-more, sorting and search

## Next

Products and prices will come from the employee portal (one source of truth) instead of `content/catalog.json`.
