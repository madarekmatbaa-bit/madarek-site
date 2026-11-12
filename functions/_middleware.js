// عناوين ووردبريس وووكومرس القديمة يلي Google لسا عم يزورها (عمار 12 ت2 2026: «اللي ما بدنا اياها شيلها، نظفها وظبطها»).
// _redirects ما بيشوف يلي بعد علامة الاستفهام، فهالملف بيعمل شغلتين قبل ما تنخدم الصفحة:
//   1) بيشيل وسوم ووكومرس (ترتيب، عملة، سلة…) وبيحوّل 301 للعنوان النظيف.
//   2) بيرجّع 410 «انشالت نهائياً» لصفحات ووردبريس يلي ما إلها مقابل.
// وسوم الإعلانات (utm_ وfbclid وgclid…) ما بتنلمس. وأي خطأ هون بيخلّي الصفحة تنخدم عادي.
const JUNK = new Set(['orderby', 'per_page', 'per_row', 'shop_view', 'wmc-currency', 'add-to-cart', 'min_price', 'max_price', 'product_cat', 'product-page',
  'redirect_to', 'reauth', 'jetpack-sso-show-default-form', 'action', 'removed_item', 'add_to_wishlist', 'quantity', 'variation_id', 'rating_filter', 'paged']);
const JUNK_PREFIX = ['attribute_', 'filter_', 'query_type_'];
const GONE = [/^\/wp-login\.php$/, /^\/wp-admin(\/|$)/, /^\/xmlrpc\.php$/, /^\/wp-json(\/|$)/, /^\/cgi-sys\//, /^\/wp-cron\.php$/, /^\/exploring-atlantas-modern-homes\/?$/];
const SEARCH = { '/': '/search/', '/en/': '/en/search/', '/tr/': '/tr/arama/' };

export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    if (GONE.some((re) => re.test(url.pathname))) {
      return new Response('Gone', { status: 410, headers: { 'content-type': 'text/plain; charset=utf-8', 'x-robots-tag': 'noindex', 'cache-control': 'public, max-age=86400' } });
    }
    if (url.search) {
      // بحث ووردبريس القديم /?s=… بيروح لصفحة البحث
      if (SEARCH[url.pathname] && url.searchParams.has('s')) {
        const to = new URL(SEARCH[url.pathname], url.origin);
        to.searchParams.set('s', url.searchParams.get('s'));
        return Response.redirect(to.toString(), 301);
      }
      // صفحة البحث بتقرا s وproduct_cat، فما منلمس وسومها
      if (/^\/(search|en\/search|tr\/arama)\//.test(url.pathname)) return context.next();
      let dropped = false;
      for (const key of [...url.searchParams.keys()]) {
        if (JUNK.has(key) || JUNK_PREFIX.some((p) => key.startsWith(p))) {
          url.searchParams.delete(key);
          dropped = true;
        }
      }
      if (dropped) return Response.redirect(url.toString(), 301);
    }
  } catch (e) {
    // ما منوقّف الموقع كرمال تنضيف عناوين
  }
  return context.next();
}
