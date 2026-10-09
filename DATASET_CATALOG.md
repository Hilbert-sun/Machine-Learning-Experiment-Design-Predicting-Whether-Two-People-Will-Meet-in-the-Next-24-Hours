# Encounter Lab — Dataset Catalog

Verified:2026-10-10 (Asia/Kuala_Lumpur). Every population has a separate namespace; no identical anonymous numbers were matched across sources. No raw sources/models/individual records are committed or uploaded.

| Dataset | Access | License | Contact IDs | Event rows | Observed span(days) | Primary status |
| --- | --- | --- | --- | --- | --- | --- |
|[Copenhagen Networks Study](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433)|public|MIT (data; article license separately)|692|2426279|27.996528|eligible_primary_24h|
|[SocioPatterns High School2013](https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/)|public|CC BY-NC-SA|327|188508|4.207870|insufficient_history|
|[MIT Reality Mining (Mendeley processed)](https://data.mendeley.com/datasets/d6bzzfd23g/1)|public|CC BY4.0 (Mendeley processed version)|96|1086403|unknown|exploratory_only|
|[SocioPatterns Workplace2015](https://sociopatterns.org/datasets/test/)|public|Creative Commons Public Domain Dedication (CC0)|217|78249|11.499306|exploratory_only|
|[SocioPatterns Workplace2013](https://sociopatterns.org/datasets/contacts-in-a-workplace/)|public|Creative Commons Public Domain Dedication (CC0)|92|9827|11.430787|exploratory_only|
|[MIT Social Evolution](https://realitycommons.media.mit.edu/socialevolution.html)|unavailable_at_verification|not verified; no automatic acquisition|unknown|unknown|unknown|not_yet_verified|

## Copenhagen Networks Study

Source:[publisher/source](https://figshare.com/articles/dataset/The_Copenhagen_Networks_Study_interaction_data/7267433). Citation:Sapiezynski et al. (2019), Scientific Data, DOI10.1038/s41597-019-0325-x; dataset10.6084/m9.figshare.7267433.

Recorded reporter bins including empty scans; symmetrized rows remain an availability proxy, not continuous presence.

Status:eligible_primary_24h. Coverage policy supported; still require cohort/class/time checks before training.

| History | Calendar-complete snapshots | Reliable primary snapshots | Purged date capacity train/validation/test |
| --- | --- | --- | --- |
|1d|26|26|{'train': 14, 'validation': 4, 'test': 6}|
|3d|24|24|{'train': 13, 'validation': 4, 'test': 5}|
|7d|20|20|{'train': 11, 'validation': 3, 'test': 4}|

File:bt_symmetric.csv;SHA256:`1c620f0f0f25d59730dc3427b051d5ab9e7c0b70173d9f92c04cf7c2d8b97e44`.

## SocioPatterns High School2013

Source:[publisher/source](https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/). Citation:Mastrandrea, Fournet, Barrat (2015), DOI10.1371/journal.pone.0136497.

Positive contact list only; no independent scanner-online logs.

Status:insufficient_history. missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption; insufficient_days after7d history and strict chronological purge

| History | Calendar-complete snapshots | Reliable primary snapshots | Purged date capacity train/validation/test |
| --- | --- | --- | --- |
|1d|2|0|{'train': 0, 'validation': 0, 'test': 0}|
|3d|0|0|{'train': 0, 'validation': 0, 'test': 0}|
|7d|0|0|{'train': 0, 'validation': 0, 'test': 0}|

File:HighSchool2013_proximity_net.csv.gz;SHA256:`ecf4a90312c8d72057f72e936c366b470e63876da7db846300044795f045e2ea`.

## MIT Reality Mining (Mendeley processed)

Source:[publisher/source](https://data.mendeley.com/datasets/d6bzzfd23g/1). Citation:Khushnood Abbas (2018), Real Human Contact processed data, DOI10.17632/d6bzzfd23g.1; Eagle & Pentland (2006), DOI10.1007/s00779-005-0046-3.

Only positive dyadic edges; no empty scan/online logs. Third column observed as small integer ticks; scale not confirmed.

Status:exploratory_only. missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption; timestamp tick scale not verified; no conversion to seconds/days or24h labels

| History | Calendar-complete snapshots | Reliable primary snapshots | Purged date capacity train/validation/test |
| --- | --- | --- | --- |
|1d|None|0|unverified|
|3d|None|0|unverified|
|7d|None|0|unverified|

File:realHumanContactMIT.txt;SHA256:`ededff41b0befdd6ba370602d496dc8b93cc38c3a39d2e47ecd82443d093bf49`.

## SocioPatterns Workplace2015

Source:[publisher/source](https://sociopatterns.org/datasets/test/). Citation:Genois & Barrat (2018), EPJ Data Science7,11.

Active contact intervals[t-20s,t] only; absent independent badge-online logs. Contact-free intervals are not reliable negatives.

Status:exploratory_only. missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption; insufficient_days after7d history and strict chronological purge

| History | Calendar-complete snapshots | Reliable primary snapshots | Purged date capacity train/validation/test |
| --- | --- | --- | --- |
|1d|9|0|{'train': 4, 'validation': 1, 'test': 2}|
|3d|7|0|{'train': 3, 'validation': 0, 'test': 2}|
|7d|3|0|{'train': 0, 'validation': 0, 'test': 1}|

File:workplace_InVS15_tij.dat.gz;SHA256:`339eb090d506d750f38a2c1ac6aca76c00c55b462f9dea325933d8b7bc260871`.

## SocioPatterns Workplace2013

Source:[publisher/source](https://sociopatterns.org/datasets/contacts-in-a-workplace/). Citation:Genois et al. (2015), Network Science3,326.

Active contact intervals[t-20s,t] only; absent independent badge-online logs. Contact-free intervals are not reliable negatives.

Status:exploratory_only. missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption; insufficient_days after7d history and strict chronological purge

| History | Calendar-complete snapshots | Reliable primary snapshots | Purged date capacity train/validation/test |
| --- | --- | --- | --- |
|1d|9|0|{'train': 4, 'validation': 1, 'test': 2}|
|3d|7|0|{'train': 3, 'validation': 0, 'test': 2}|
|7d|3|0|{'train': 0, 'validation': 0, 'test': 1}|

File:workplace_InVS_tij.dat.zip;SHA256:`bf818f7e819864e134c90ed82f2cda6ca9d9548d43fe4d05002ac068c91258c0`.

## MIT Social Evolution

Source:[publisher/source](https://realitycommons.media.mit.edu/socialevolution.html). Citation:MIT Human Dynamics Lab, Social Evolution dataset; source data dictionary https://realitycommons.media.mit.edu/socialevolution1.html.

Published dictionary describes Bluetooth/Wi-Fi proximity and six-minute sampling, plus interpolated missing Bluetooth records. No verified raw-only flag/online logs.

Status:not_yet_verified. Live official overview/dictionary/download navigation unavailable (connection refused/502). No verified lawful download or license; do not infer restriction from outage.


## Eligibility interpretation

Calendar span/snapshot capacity is a time-only upper bound, not scan coverage or an actual labeled cohort. Unavailable counts remain null rather than invented as zero measured contacts. eligible_primary_24h means source observation policy and purged eligible labels were checked; each study still needs its own common candidate/full-history/class/day audit. Only Copenhagen supports the reported actual predictive experiment. High School lacks reliable scan evidence and7d span. Both Workplace sources have only3 calendar-complete7d snapshots and no online logs. Reality Mining processed ticks have unknown units and many repeats. Social Evolution actual files/license/path remain unverified; published interpolation creates an additional strict-time risk.

The original MIT official endpoints failed live connection; this is not proof of restricted access. No access bypass was attempted. Mendeley CC BY4.0 applies to its processed redistribution; the mirror's site-code license was not repurposed as a data license. See reports/T25_REALITY_MINING.md and reports/T26_SOURCE_VERIFICATION.md for source dictionaries and measured limitations. Workplaces' publisher descriptions and actual timestamp extent are kept distinct; no calendar mismatch is silently repaired.

Raw files:data/raw/catalog/<dataset_id>/; local per-source dataset_manifest.json and contact Parquet:data/processed/catalog/<dataset_id>/. Existing Copenhagen/High School paths/loaders/downloads remain supported. The Dataset Catalog UI can scan, inspect, legally download verified sources, or validate manual imports. A bounded schema probe precedes a first full new-source acquisition. Imports validate before publishing and refuse to replace existing raw files. Restricted/unverified acquisition paths do not run automatically.
