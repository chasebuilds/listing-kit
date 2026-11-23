# Lighthouse results

Measured on the live demo at https://chasebuilds.github.io/listing-kit/ on 2026-11-23 with Lighthouse 12.8.2 (command line, headless Chromium, default settings: simulated mobile throttling for "mobile", the desktop preset for "desktop"). One run per row, from a Windows PC. These are lab numbers, so a different machine or network will move them a little.

| Page | Form factor | Performance | Accessibility | Best practices | SEO | FCP | LCP | TBT | CLS |
|---|---|---|---|---|---|---|---|---|---|
| maple-court | mobile | 100 | 100 | 100 | 100 | 1.0 s | 1.0 s | 0 ms | 0 |
| maple-court | desktop | 100 | 100 | 100 | 100 | 0.2 s | 0.3 s | 0 ms | 0 |
| alder-street | mobile | 100 | 100 | 100 | 100 | 0.8 s | 1.1 s | 10 ms | 0 |
| alder-street | desktop | 100 | 100 | 100 | 100 | 0.3 s | 0.3 s | 0 ms | 0 |
| checker | mobile | 100 | 100 | 100 | 100 | 0.8 s | 0.8 s | 0 ms | 0 |
| checker | desktop | 100 | 100 | 100 | 100 | 0.2 s | 0.2 s | 0 ms | 0 |

What the first run found, and what was changed:

- Best practices scored 78 to 79 on the listing pages because the contact form used a `mailto:` form action, which Chrome reports as an insecure form target on an https page. The form now has no `mailto:` action; the script opens the email app, and a `<noscript>` note gives a plain email link when JavaScript is off.
- The checker page had a layout shift of 0.063 on desktop because the results area grew after load. The area now reserves its height.
- A missing favicon logged a console error on a local run. Each page now has an inline icon.

Lighthouse checks only part of accessibility. The pages were also checked by keyboard (gallery, viewer, forms) and at 360 pixels wide with no sideways scrolling, but they have not been tested with a screen reader.

To repeat a run:

```
listing-kit build examples/maple-court.yml examples/alder-street.yml -o site --checker
python -m http.server 8123 --directory site
npx lighthouse http://localhost:8123/maple-court/ --only-categories=performance,accessibility,best-practices,seo
```
