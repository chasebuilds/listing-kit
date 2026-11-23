# Limitations

## Wording checker

- **Not legal advice.** It is a writing aid. A person who knows your state and city law has to make the call on anything that matters.
- **It matches words, not meaning.** It cannot see paraphrases ("a mostly retired crowd", "born in this country") and it flags look-alikes ("a short walk to the temple of the old mill", "husband-and-wife team"). The measured misses and false alarms are in BENCHMARK.md.
- **Recall is about 64% on the newest held-out set (143 sentences).** About 1 in 3 problem sentences in that test was missed. Do not treat a clean result as approval.
- **The test sentences are invented** by the author of the rules. Real listings are messier.
- **US federal protected classes only by default.** An opt-in pack (`--pack local`) adds two state and local law rules about source of income; it does not cover your state's full list. It does not know your state's or city's extra protected classes, and it does not check photos, symbols or human models in photos.
- **English only.** Matching is ASCII-oriented; accented text is passed through unchanged.
- **Some rules go further than HUD's published examples.** Those are marked `basis: judgment` in the rules file.
- **Housing for older persons.** A 55+ community can be lawful when it meets the exemption. The checker cannot tell whether it does, so it flags for review.
- **Roommate ads.** A shared-living exemption can apply, but the person placing the ad must meet it. The checker cannot tell.

## Listing pages

- **One property per page.** There is no search, no multi-listing portal and no MLS import.
- **The contact form has no spam filtering beyond a honeypot,** and `mailto` mode depends on the visitor having an email app set up. Use `endpoint` mode with a form service if you need delivery you can track.
- **The payment estimate is an estimate.** It uses the rates and tax figures in your file, not live data, and leaves out mortgage insurance and closing costs.
- **Open house times are fixed text in the page.** Update the YAML and rebuild to change them. Ended events are marked in the browser by comparing with the visitor's clock.
- **The map uses the public OpenStreetMap tile server,** which is fine for a listing page but is not meant for heavy traffic. Point `tileLayer` in `listing.js` at a tile service you pay for if you expect a lot of visitors.
- **Photos are not edited or checked.** Alt text is required, but its quality is up to you. Photos are resized and converted to WebP; original files are not published.
- **The flyer has no QR code.** It prints the contact details and the page is linked from the listing, not from the flyer.
- **No built-in analytics, forms inbox or hosting.** You publish the output folder yourself.
