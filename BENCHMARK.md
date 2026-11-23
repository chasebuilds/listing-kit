# Benchmark

Written by `benchmark/evaluate.py` from a real run. Do not edit by hand; re-run the script.

What is measured: for each invented sentence, does the checker flag it (at least one `avoid` or `review` finding) when a person would say it should be flagged? Style notes such as the one for "master bedroom" are not flags.

- **TP** flagged and should be. **FP** flagged but fine. **FN** missed. **TN** correctly left alone.
- **Precision** = TP / (TP + FP). **Recall** = TP / (TP + FN).

## Results

| Set | Sentences | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| dev | 127 | 61 | 4 | 5 | 57 | 93.8% | 92.4% |
| heldout | 137 | 47 | 3 | 18 | 69 | 94.0% | 72.3% |
| **all** | 264 | 108 | 7 | 23 | 126 | 93.9% | 82.4% |

`dev` is the set the rules were tuned on, so its numbers are optimistic. `heldout` was written after the rules were frozen and was not used to tune them. After its first run the only rule edits were relabeling the `basis` field and dropping "sober" from one pattern after reading the HUD memo (it treats "sober" as a lawful conduct rule); no number moved. The heldout row is the one to trust.

## By difficulty (all sentences)

| Set | Sentences | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| std | 234 | 105 | 1 | 6 | 122 | 99.1% | 94.6% |
| hard | 30 | 3 | 6 | 17 | 4 | 33.3% | 15.0% |

`hard` marks sentences written to be tricky: paraphrases the rules cannot see and look-alikes that contain a risky word in a harmless sense.

## By group (all sentences)

| Group | Sentences | Flagged | Not flagged |
|---|---|---|---|
| familial_status | 30 | 25 | 5 |
| disability | 15 | 11 | 4 |
| religion | 16 | 14 | 2 |
| race_color | 13 | 11 | 2 |
| national_origin | 13 | 11 | 2 |
| sex | 17 | 13 | 4 |
| steering | 21 | 19 | 2 |
| local_law | 6 | 4 | 2 |
| plain | 55 | 0 | 55 |
| tricky | 78 | 7 | 71 |

Groups starting with a protected-class name hold sentences that should be flagged; `plain` and `tricky` hold sentences that should not.

## Missed (should be flagged, was not)

- [dev, hard] A cozy retreat for two, with no need for extra bedrooms.
- [dev, hard] Ideal for active people who enjoy hills and stairs.
- [dev, hard] Ideal for those who value Sunday worship nearby.
- [dev, hard] A quiet street with neighbors from the old country, just like you.
- [dev, hard] Gentlemen of means will appreciate the study.
- [heldout, std] Not a good fit for toddlers, the stairs are steep and open.
- [heldout, std] Singles and couples will feel at home in the lofts.
- [heldout, hard] Landlord prefers tenants without little ones.
- [heldout, hard] Two bedrooms, a good match for a pair of professionals who like it calm.
- [heldout, std] We cannot accommodate the handicapped, there are no elevators.
- [heldout, hard] Tenants must be mentally sound and sober.
- [heldout, hard] For people who can handle a long gravel driveway on their own two feet.
- [heldout, hard] A holy and righteous street where everyone knows their neighbors.
- [heldout, std] An all white street with great curb appeal.
- [heldout, hard] Neighborhood is turning, so the price is low.
- [heldout, hard] Tenants should have been born in this country.
- [heldout, std] Homosexuals need not apply.
- [heldout, hard] Every woman dreams of a walk-in closet like this one.
- [heldout, hard] A masculine retreat with a leather and cigar vibe.
- [heldout, hard] Prime location, the kind of area where you will fit in.
- [heldout, hard] Not far from the bad side of town.
- [heldout, std] We do not take Section 8 in this unit.
- [heldout, hard] Must earn income from a job, no benefits or subsidies.

## False alarms (flagged, should not be)

- [dev, hard] Listed by a husband-and-wife team with 20 years of local experience. (rules: spouse-targeting)
- [dev, hard] The sellers are a retired couple who maintained the house carefully. (rules: people-adjective)
- [dev, hard] A short walk to the temple of the old mill, now a museum. (rules: worship-proximity)
- [dev, hard] Kitchen was remodeled by the owner's mother, a licensed contractor. (rules: spouse-targeting)
- [heldout, std] Nearby churches, schools and shops are shown on the neighborhood map in the packet. (rules: worship-proximity)
- [heldout, hard] A mature couple of cedar trees frames the entrance. (rules: people-adjective)
- [heldout, hard] The home inspector noted that the husband-built deck is in good shape. (rules: spouse-targeting)

## Policy cases

78 clean sentences are deliberately tricky ("family room", "single-family", "master bedroom", "Church Street", "wheelchair accessible", "mom-and-pop" and similar). 71 of them are correctly left unflagged, and 7 carry a style note only.

## Limits of this benchmark

- The sentences are invented and were written by the same person who wrote the rules. Real listings are messier, so expect lower recall on real text.
- The labels follow this project's documented policy (see `rules.yml`), which is a conservative reading, not a legal determination. A fair housing attorney may label some sentences differently.
- Sentence counts are small, so a single sentence moves a percentage by about half a point. No confidence interval is given.
