# T31 — Multi-Dataset Exploratory Research

Run `6d5df52b7fd76419`, source_kind=`real_public_dataset`. Copenhagen remains the primary binary source: frozen T17/T22/T30 evidence is referenced, never refitted or mixed into these rankings.

## Actual source quality and graph statistics

| Source | Contact IDs | Raw valid records | Unique canonical records | Pairs | Span days | Status |
| --- | --- | --- | --- | --- | --- | --- |
|workplace2013|92|9827|9827|755|11.430787037037037|positive_retrieval_ready|
|workplace2015|217|78249|78249|4274|11.499305555555555|positive_retrieval_ready|
|highschool2013|327|188508|188508|5818|4.207870370370371|insufficient_history|
|reality_mining_mendeley|96|1086403|27572|2539|None|time_unit_unverified|
|social_evolution|unavailable|unavailable|unavailable|unavailable|unavailable|source_unavailable|

Descriptive Network Analysis graphs describe whole archived source networks, never historical input networks. Counts are contact records, not conversations, meetings or friendship strength. Exact canonical (timestamp,pair) repeats count once in this new study; raw/legacy counts remain unchanged. IDs are strictly source-isolated. SourceSummary contains source hashes, schema adapter version, seconds/tick policy, graph components/density, broad degree/pair-frequency distributions and source-level daily activity. Broad histograms containing nonzero groups below5 are entirely suppressed; small public retrieval count/ratio families are suppressed together. No participant-level values or edge lists are exported.

## Prespecified observed-positive retrieval

Candidates are ONLY [t-1d,t) contacts. Frequency (unique records / historical days), last recency (last timestamp−t), and common-neighbor counts use ONLY [t-window,t). All rank descending; ties use ascending source/minID/maxID. K=5/10/20, daily08:00 source-clock snapshots,1/3/7d history and complete source-span future24h are fixed before results. Ranking inputs are saved locally before the explicit future reveal. No model training or parameter/threshold selection occurs.

Future contacts use (t,t+24h]. Capture@K = observed positive hits / all observed future positive pairs IN the historical candidate pool. Capture-all additionally divides by ALL future recorded positive pairs; candidate reach = in-pool positives / all recorded positives. Outside-pool positives are reported separately; they are new to the1d candidate pool, not necessarily first-ever contacts. Missing future contacts remain Unknown. Zero denominators yield unavailable (null); no binary negatives or Accuracy/Precision/F1/AP/ROC/Brier/LogLoss. Metrics aggregate snapshot-pair counts (repeated pairs on different dates count separately), not independent persons or all physical contacts.

Per-window scopes have different dates and cannot identify a pure window effect. Common_7d explicitly shares dates and1d candidates across1/3/7d. No significance claim: fewer than3 positive-pool dates is insufficient descriptive temporal evidence; even more dates remain short dependent observational evidence. Empty candidate dates and empty positive pools are counted separately, never silently dropped to improve scores. Complete recorded span does not establish continuous badge availability. TopK results across different sensors/populations are not a common performance leaderboard.

| Source | Window | Calendar-complete times | Nonempty candidate times | Positive-pool times | Status |
| --- | --- | --- | --- | --- | --- |
|workplace2013|1d|9|7|6|positive_retrieval_ready|
|workplace2013|3d|7|5|4|positive_retrieval_ready|
|workplace2013|7d|3|3|3|positive_retrieval_ready|
|workplace2015|1d|9|7|6|positive_retrieval_ready|
|workplace2015|3d|7|5|4|positive_retrieval_ready|
|workplace2015|7d|3|3|3|positive_retrieval_ready|
|highschool2013|1d|2|2|2|insufficient_history|
|highschool2013|3d|0|0|0|insufficient_history|
|highschool2013|7d|0|0|0|insufficient_history|

Fixed frequency Top20 on common_7d dates (snapshot-pair totals, descriptive only):

| Source | Window | Hits | In-pool positives | Outside-pool positives | Capture@20 | Candidate reach |
| --- | --- | --- | --- | --- | --- | --- |
|workplace2013|1|31|147|322|0.2108843537414966|0.31343283582089554|
|workplace2013|3|34|147|322|0.23129251700680273|0.31343283582089554|
|workplace2013|7|35|147|322|0.23809523809523808|0.31343283582089554|
|workplace2015|1|31|533|1610|0.058161350844277676|0.2487167522165189|
|workplace2015|3|35|533|1610|0.06566604127579738|0.2487167522165189|
|workplace2015|7|34|533|1610|0.06378986866791744|0.2487167522165189|

## Source evidence and limitations

- **workplace2013**: [SocioPatterns Workplace2013](https://sociopatterns.org/datasets/contacts-in-a-workplace/); Genois et al. (2015), Network Science3,326. License: Creative Commons Public Domain Dedication (CC0). No reliable independent online/scan logs: no binary prediction evaluation. SHA256: `bf818f7e819864e134c90ed82f2cda6ca9d9548d43fe4d05002ac068c91258c0`.
- **workplace2015**: [SocioPatterns Workplace2015](https://sociopatterns.org/datasets/test/); Genois & Barrat (2018), EPJ Data Science7,11. License: Creative Commons Public Domain Dedication (CC0). No reliable independent online/scan logs: no binary prediction evaluation. SHA256: `339eb090d506d750f38a2c1ac6aca76c00c55b462f9dea325933d8b7bc260871`.
- **highschool2013**: [SocioPatterns High School2013](https://sociopatterns.org/datasets/high-school-contact-and-friendship-networks/); Mastrandrea, Fournet, Barrat (2015), DOI10.1371/journal.pone.0136497. License: CC BY-NC-SA. No reliable independent online/scan logs: no binary prediction evaluation. SHA256: `ecf4a90312c8d72057f72e936c366b470e63876da7db846300044795f045e2ea`.
- **reality_mining_mendeley**: [MIT Reality Mining (Mendeley processed)](https://data.mendeley.com/datasets/d6bzzfd23g/1); Khushnood Abbas (2018), Real Human Contact processed data, DOI10.17632/d6bzzfd23g.1; Eagle & Pentland (2006), DOI10.1007/s00779-005-0046-3. License: CC BY4.0 (Mendeley processed version). No publisher dictionary or transformation maps processed ticks to seconds; original study duration is not a mapping. SHA256: `ededff41b0befdd6ba370602d496dc8b93cc38c3a39d2e47ecd82443d093bf49`.
- **social_evolution**: [MIT Social Evolution](https://realitycommons.media.mit.edu/socialevolution.html); MIT Human Dynamics Lab, Social Evolution dataset; source data dictionary https://realitycommons.media.mit.edu/socialevolution1.html. License: not verified; no automatic acquisition. Live official overview/dictionary/download navigation unavailable (connection refused/502). No verified lawful download or license; do not infer restriction from outage. SHA256: `None`.

Publisher pages rechecked2026-10-10: Workplace2013/2015 give20s active intervals[t−20,t], seconds and CC0; HighSchool gives seconds/UNIXctime,20s intervals, CC BY-NC-SA. Actual file spans are used, not narrative recording dates; Workplace2013's published June24–July3 description does not resolve the file's11.43-day extent. Study Day indexing avoids inventing or repairing civil dates. End timestamps define event boundaries; missing intervals are not physical negatives.

Mendeley processed Reality Mining is CC BY4.0 but its page does not specify a conversion of third-column ticks0–233 to seconds or map them to the nine-month original archive. Search of publisher description/documentation produced no transformation evidence. Its1,086,403 valid rows have many exact repeats; only topology/unique raw ticks are used. No1/3/7d or24h results. A different original/mirror time encoding is not evidence for this processed file.

Social Evolution overview and dictionary live fetches returned502; no lawful actual source file, license/header/timezone or raw-only interpolation provenance verified. Indexed descriptions are not actual file verification. Status source_unavailable; no download, bypass, parsed-real-file or successful integration claim. This optional-source limitation does not substitute synthetic metrics for a real experiment.

There are no independent online/scan logs for these contact-only sources. Record availability by event time does not prove the data had arrived then. Static archives are not prospective live inference. All figures read measured aggregate outputs; unavailable sources show reasons rather than placeholder metrics.

## Reproduction and local artifacts

```bash
.venv/bin/python -m src.multisource_exploration
.venv/bin/python -m pytest -q tests/test_positive_retrieval.py tests/test_multisource_exploration.py tests/test_multisource_ui.py
.venv/bin/python -m pytest -q
.venv/bin/streamlit run app.py
```

No network/download is performed by the study. Existing verified catalog caches are read-only; absent caches are created only inside the new ignored T31 directory. Matching lawful raw sources are needed for real reproduction. Public JSON/CSV includes exact source hashes, adapter/algorithm version, fixed rules and snapshot timestamps. Protocol is frozen before ranking/reveal. Local data/processed/multisource/<run_id> holds private ranking inputs, future positive keys, retrieval_rows.parquet, RESULTS.json and interactive T31_REPORT.html; none enters Git. Reruns verify existing frozen rank inputs instead of replacing them. Public aggregates can be recomputed from local retrieval_rows.parquet with aggregate_retrieval; individual records never become binary labels.

Only the five exact reviewed reports/multisource filenames are whitelisted. T17–T30 frozen code, metrics, reports and model files remain unchanged. T32–T34 not started. Next: T32 performance measurements and optimization.
