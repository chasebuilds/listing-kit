# Lighthouse results

Measured on the live demo at https://chasebuilds.github.io/listing-kit/ on 2026-11-23 (version 1.1.0) with Lighthouse 12.8.2 (command line, headless Chromium, default settings: simulated mobile throttling for "mobile", the desktop preset for "desktop"). Each cell was run 3 times from a Windows PC; the table shows the median, with the lowest and highest score in brackets when they differed. Two runs failed outright with Lighthouse's NO_FCP error (the page did not paint in the headless window); they were dropped, so those two rows show 2 runs.

| Page | Form factor | Runs | Performance | Accessibility | Best practices | SEO | FCP | LCP | TBT | CLS |
|---|---|---|---|---|---|---|---|---|---|---|
| index | mobile | 3 | 100 (95 to 100) | 100 | 100 | 100 | 0.9 s | 0.9 s | 15 ms | 0 |
| index | desktop | 3 | 100 (94 to 100) | 100 | 100 | 100 | 0.3 s | 0.3 s | 0 ms | 0 |
| maple-court | mobile | 2 | 100 | 100 | 100 | 100 | 1.0 s | 1.0 s | 0 ms | 0 |
| maple-court | desktop | 3 | 100 (92 to 100) | 100 | 100 | 100 (92 to 100) | 0.3 s | 0.4 s | 0 ms | 0 |
| alder-street | mobile | 3 | 100 (99 to 100) | 100 | 100 | 100 (92 to 100) | 0.9 s | 1.0 s | 0 ms | 0 |
| alder-street | desktop | 3 | 100 | 100 | 100 | 100 (92 to 100) | 0.3 s | 0.4 s | 0 ms | 0 |
| harbor-lane | mobile | 3 | 100 (93 to 100) | 100 | 100 | 100 | 0.9 s | 1.3 s | 50 ms | 0 |
| harbor-lane | desktop | 2 | 100 | 100 | 100 | 100 | 0.3 s | 0.4 s | 0 ms | 0 |
| checker | mobile | 3 | 100 | 100 | 100 | 100 | 0.8 s | 0.8 s | 0 ms | 0 |
| checker | desktop | 3 | 100 | 100 | 100 | 100 | 0.3 s | 0.3 s | 0 ms | 0 |

Notes on the spread:

- Single runs vary. An earlier single pass hit performance 62 to 71 on mobile (LCP 3.8 to 5.7 s) on the index and one listing; the repeat runs did not reproduce it. The server and the network from this PC are the likely cause, not the page, but I could not prove that, so the range is shown instead of hiding it.
- SEO dipped to 91 or 92 in a few runs. The only failing audit was "robots.txt is not valid": Lighthouse checks `chasebuilds.github.io/robots.txt` at the host root, which is not part of this repo, and it answered with a 503 error page at those moments (later checks returned 404, which Lighthouse accepts).
- These are lab numbers. A different machine or network will move them.

What earlier runs found, and what was changed (version 1.0.0):

- Best practices scored 78 to 79 because the contact form used a `mailto:` form action, which Chrome reports as insecure on an https page. The form now has no `mailto:` action; the script opens the email app, and a `<noscript>` note gives a plain email link.
- The checker page had a layout shift of 0.063 on desktop. Its results area now reserves its height.
- A missing favicon logged a console error. Each page now has an inline icon.

Lighthouse checks only part of accessibility. The pages were also checked by keyboard (gallery, viewer, forms, index filter) and at 360 pixels wide with no sideways scrolling, but not with a screen reader.

To repeat a run:

```
listing-kit build examples/maple-court.yml examples/alder-street.yml examples/harbor-lane.yml -o site --checker --index-config examples/index.yml
python -m http.server 8123 --directory site
npx lighthouse http://localhost:8123/maple-court/ --only-categories=performance,accessibility,best-practices,seo
```
