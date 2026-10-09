# T26 — Additional source adapters and feasibility

Date:2026-10-10. Separate source namespaces; no datasets were concatenated, no missing contacts labeled negative, no new prediction scores claimed.

## Workplace2015 / Workplace2013

Verified official source pages and public-domain dedication: [2015](https://sociopatterns.org/datasets/test/) and [2013](https://sociopatterns.org/datasets/contacts-in-a-workplace/). Cite Genois & Barrat, EPJ Data Science7,11 (2018), and Genois et al., Network Science3,326 (2015), respectively. Real links were read from these pages, not constructed. Bounded compressed-prefix schema checks preceded full acquisition;gzip2015 andZIP2013 parsers read exactly t,i,j without extracting archive paths. Times are source seconds and each positive record describes[t-20s,t].

### SocioPatterns Workplace2015

Participants:217; valid contact records:78,249; pairs:4,274; raw timestamp range:28840–1022380 seconds; observed span:11.499306 days; days without any contact record:2. SHA256:`339eb090d506d750f38a2c1ac6aca76c00c55b462f9dea325933d8b7bc260871`.

Calendar-complete snapshot counts (including future24h span):1d=9, 3d=7, 7d=3.

The7d history case leaves only3 prediction dates. Even ignoring missingness,60/20/20 strict24h purge has train/validation/test date capacity {'train': 0, 'validation': 0, 'test': 1}. It is insufficient_days; no random-row substitute is used. missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption; insufficient_days after7d history and strict chronological purge. Dataset status:exploratory_only; primary eligible dates0 for all windows.

### SocioPatterns Workplace2013

Participants:92; valid contact records:9,827; pairs:755; raw timestamp range:28820–1016440 seconds; observed span:11.430787 days; days without any contact record:2. SHA256:`bf818f7e819864e134c90ed82f2cda6ca9d9548d43fe4d05002ac068c91258c0`.

Calendar-complete snapshot counts (including future24h span):1d=9, 3d=7, 7d=3.

The7d history case leaves only3 prediction dates. Even ignoring missingness,60/20/20 strict24h purge has train/validation/test date capacity {'train': 0, 'validation': 0, 'test': 1}. It is insufficient_days; no random-row substitute is used. missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption; insufficient_days after7d history and strict chronological purge. Dataset status:exploratory_only; primary eligible dates0 for all windows.

The2013 page's descriptive calendar dates are not used to overwrite the actual timestamp-derived extent. Calendar alignment to those dates has not been verified; diagnostics retain actual seconds and Study Day indices. Contact-free calendar dates could reflect weekends, zero interactions or missing recording; they are not reliable device-online evidence. No1d/3d or7d AP is computed without such evidence. Per-day source diagnostics are exported in T26_WORKPLACE_DIAGNOSTICS.json.

## MIT Social Evolution

The [official overview](https://realitycommons.media.mit.edu/socialevolution.html) and [data dictionary](https://realitycommons.media.mit.edu/socialevolution1.html) could be found in the search index but live official endpoints refused connection during requests; web fetches returned502. These errors are recorded in T26_SOCIAL_EVOLUTION_STATUS.json and are not relabeled as403/authentication restriction.

The dictionary describes Proximity.csv endpoint fields user.id and remote.user.id.if.known, six-minute sensor sampling and prob2 as a Wi-Fi-based same-floor probability. It also describes symmetry/deduplication and interpolated Bluetooth records using whole-period/hour/day patterns. Without raw-only provenance, interpolation can compromise strict future prediction. prob2 is not an observed24h encounter target. No actual file/header/timezone, independently observed negative evidence, license or lawful full download path was verified.

Catalog status:not_yet_verified; access:unavailable_at_verification. No source file was downloaded, no access restriction bypassed, no model score invented. The adapter supports explicit verified endpoint/timestamp mapping and timezone-aware datetime conversion; unknown mappings and naive datetime zones fail instead of assumingUTC. Synthetic parser tests are marked fixtures and do not imply the unavailable real file was parsed.

Focused catalog/schema/downloader tests:42 passed in1.65s, including archive probes/reads, unknown time ticks, missing-day/time-capacity handling, verified timezone and cache invalidation when parsing policy changes. Remaining external limitation:Social Evolution needs a lawful reachable source and trustworthy raw observation dictionary before research eligibility. Dataset acquisition/diagnostic work is complete within the permitted evidence-based scope; no full Social Evolution experiment is claimed.
