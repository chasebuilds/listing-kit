# Benchmark

Written by `benchmark/evaluate.py` from a real run. Do not edit by hand; re-run the script.

What is measured: for each invented sentence, does the checker flag it (at least one `avoid` or `review` finding) when a person would say it should be flagged? Style notes such as the one for "master bedroom" are not flags.

- **TP** flagged and should be. **FP** flagged but fine. **FN** missed. **TN** correctly left alone.
- **Precision** = TP / (TP + FP). **Recall** = TP / (TP + FN).

## Results

| Set | Sentences | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| dev | 258 | 121 | 4 | 4 | 129 | 96.8% | 96.8% |
| heldout | 143 | 40 | 2 | 23 | 78 | 95.2% | 63.5% |
| **all** | 401 | 161 | 6 | 27 | 207 | 96.4% | 85.6% |

`dev` is everything the rules were tuned on, so its numbers are optimistic. It holds the first sentence set plus the version 1.0.0 held-out set, which was folded in once its misses were used to write new rules. `heldout` is a new set written after the rules were frozen. It was run for the first time when this file was generated and no rule was changed in response. The heldout row is the one to trust.

## By difficulty (all sentences)

| Set | Sentences | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| std | 355 | 145 | 3 | 12 | 195 | 98.0% | 92.4% |
| hard | 46 | 16 | 3 | 15 | 12 | 84.2% | 51.6% |

`hard` marks sentences written to be tricky: paraphrases the rules cannot see and look-alikes that contain a risky word in a harmless sense.

## By group (all sentences)

| Group | Sentences | Flagged | Not flagged |
|---|---|---|---|
| familial_status | 45 | 36 | 9 |
| disability | 22 | 18 | 4 |
| religion | 24 | 23 | 1 |
| race_color | 21 | 18 | 3 |
| national_origin | 19 | 15 | 4 |
| sex | 26 | 23 | 3 |
| steering | 31 | 28 | 3 |
| plain | 91 | 0 | 91 |
| tricky | 122 | 6 | 116 |

Groups starting with a protected-class name hold sentences that should be flagged; `plain` and `tricky` hold sentences that should not.

## Missed (should be flagged, was not)

- [dev, hard] A cozy retreat for two, with no need for extra bedrooms.
- [dev, hard] A quiet street with neighbors from the old country, just like you.
- [dev, hard] Two bedrooms, a good match for a pair of professionals who like it calm.
- [dev, hard] For people who can handle a long gravel driveway on their own two feet.
- [heldout, std] Not recommended for families with young children because of the balcony.
- [heldout, std] Great spot for a family with school-age kids and a dog.
- [heldout, std] Bring the kids, there are five playgrounds within a mile.
- [heldout, std] Children are not allowed past 9 pm and families are discouraged.
- [heldout, hard] Tenants must be a couple, one person alone will not be considered.
- [heldout, hard] The seller wants a household without small ones underfoot.
- [heldout, hard] The kind of home where grandparents and grandkids gather every Sunday.
- [heldout, std] We are unable to rent to people in wheelchairs.
- [heldout, std] Not for the elderly, there is no elevator and the stairs are steep.
- [heldout, hard] Residents should be sharp and fully independent.
- [heldout, hard] Quiet, prayerful street where folks keep the faith.
- [heldout, std] We will not rent to Black applicants.
- [heldout, hard] The neighborhood used to be nice before they moved in.
- [heldout, hard] Come see the part of town where your own people live.
- [heldout, std] Applicants should speak fluent English and be born here.
- [heldout, std] Immigrants and refugees will not be considered.
- [heldout, hard] Tenants must have lived in this country for at least ten generations.
- [heldout, std] A girl cave with a vanity wall and a wine fridge.
- [heldout, std] Lesbians and gays are not welcome here.
- [heldout, hard] Built for a man who likes his tools and his truck.
- [heldout, std] Close to top-rated elementary and middle schools.
- [heldout, hard] A fine street for people who share your background.
- [heldout, hard] You will not find any riffraff around here.

## False alarms (flagged, should not be)

- [dev, hard] The sellers are a retired couple who maintained the house carefully. (rules: people-adjective)
- [dev, hard] A short walk to the temple of the old mill, now a museum. (rules: worship-proximity)
- [dev, std] Nearby churches, schools and shops are shown on the neighborhood map in the packet. (rules: worship-proximity)
- [dev, hard] A mature couple of cedar trees frames the entrance. (rules: people-adjective)
- [heldout, std] Moms Club of the neighborhood organizes a yearly yard sale. (rules: spouse-targeting)
- [heldout, std] The Moms Demand Action billboard on the corner is gone. (rules: spouse-targeting)

## Opt-in state and local law pack

Source-of-income wording (for example refusing housing vouchers) is state or local law, not federal. Its rules are off by default and run only with `--pack local` or the checkbox on the checker page. These sentences are scored separately, with the pack on, and are not in the tables above.

| Set | Sentences | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| local pack | 18 | 10 | 0 | 1 | 7 | 100.0% | 90.9% |

- missed: Tenants must hold a job, we do not consider other money.

## Policy cases

122 clean sentences are deliberately tricky ("family room", "single-family", "master bedroom", "Church Street", "wheelchair accessible", "mom-and-pop" and similar). 116 of them are correctly left unflagged, and 10 carry a style note only.

## Limits of this benchmark

- The sentences are invented and were written by the same person who wrote the rules. Real listings are messier, so expect lower recall on real text.
- The labels follow this project's documented policy (see `rules.yml`), which is a conservative reading, not a legal determination. A fair housing attorney may label some sentences differently.
- Sentence counts are small, so a single sentence moves a percentage by about half a point. No confidence interval is given.
