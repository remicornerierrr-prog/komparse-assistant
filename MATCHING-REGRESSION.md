# Matching regression — results on the supplied JSON snapshot

## Policy now implemented

- `NOTIFY_WHEN_AGE_UNSPECIFIED` exists in `scraper/matching.py` and defaults to `true`.
- An offer with no numeric age bounds and no descriptive age constraint can match profiles of any age. If its gender is also unspecified, any profile gender can match.
- An explicit broad age label such as `gemischtes Alter` is treated as an open age range.
- A descriptive but non-numeric age such as `Mitte 40` is **not** treated as unrestricted. It remains in `manual_review` until the parser can represent that condition accurately.
- A one-sided bound remains open: `25+` means age >= 25, with no upper limit; `bis 55` means age <= 55, with no lower limit.
- If an age bound exists but the offer gender is unspecified, matching stays in `manual_review`.
- The pipeline's separate rule is unchanged: if there is no exact shooting date, the offer stays in `manual_review`. The open-age setting does not bypass that review requirement.
- The offer must still pass `location_rules.classify_location`; this setting does not widen geography.

## Non-regression comparison

Input: the `komparse_parsed_offers.json` supplied with the project snapshot (71 records).

Sample profile: female, born 1996-06-15. This is a **dry run only**; no Supabase reads/writes or push deliveries occur. It counts potential matched offers in the same normalization/status/matching path as the pipeline, before checking existing matches, `notified_at`, or device subscriptions.

| Counter | Before (`NOTIFY_WHEN_AGE_UNSPECIFIED=false`) | After (default `true`) |
|---|---:|---:|
| Parsed offers in snapshot | 71 | 71 |
| Eligible V1 offers | 20 | 21 |
| Manual review | 19 | 18 |
| Outside V1 | 32 | 32 |
| Potential match offers for sample profile | 6 | 7 |
| Eligible offers without a match for sample profile | 13 | 13 |

Before potential matches: `91.306`, `91.285`, `91.276`, `91.275`, `91.269`, `91.256`.

After potential matches: `91.306`, `91.305`, `91.285`, `91.276`, `91.275`, `91.269`, `91.256`.

`91.305` is the additional potential match. `91.273` is deliberately **not** promoted to unrestricted matching: its `Mitte 40` description is an age requirement, even though no numeric bounds were parsed, so it remains in review.

The snapshot is historical; these numbers are a regression check, not the live count of notifications for today's active Komparse offers. Actual push delivery also depends on existing matches, `notified_at`, registered devices, and provider responses.

## Repeat the dry run locally

From the project root, with the virtual environment active:

```powershell
python -m scraper.matching_regression
```

To compare with the previous conservative behavior for that process:

```powershell
$env:NOTIFY_WHEN_AGE_UNSPECIFIED = "false"
python -m scraper.matching_regression
Remove-Item Env:NOTIFY_WHEN_AGE_UNSPECIFIED
```

The setting defaults to `true` when the environment variable is absent. To make it overridable by a GitHub Actions repository variable, add this line to the `Run scraper` step's `env` block in `.github/workflows/komparse.yml`:

```yaml
NOTIFY_WHEN_AGE_UNSPECIFIED: ${{ vars.NOTIFY_WHEN_AGE_UNSPECIFIED || 'true' }}
```

A variable value of `false` then restores conservative handling for offers without numeric ages.
