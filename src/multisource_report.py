"""T31 aggregate-only files and figures. No participant/pair records in public output."""

import html
import json
from pathlib import Path

import pandas as pd
import plotly.express as px


def study_figures(source, network, retrieval):
    figures = []
    if network:
        histogram = network['degree_histogram']['bins']
        if histogram:
            figures.append(px.bar(pd.DataFrame(histogram), x='bin', y='count', title='Descriptive Network Analysis · Degree distribution'))
        frequency = network['pair_record_histogram']['bins']
        if frequency:
            figures.append(px.bar(pd.DataFrame(frequency), x='bin', y='count', title='Descriptive Network Analysis · Pair contact-record frequency'))
        if network['activity']:
            figures.append(px.line(pd.DataFrame(network['activity']), x='study_day', y=['records', 'active_pairs'], title='Descriptive Network Analysis · Recorded activity'))
    if retrieval:
        frame = pd.DataFrame(retrieval)
        # Compare windows on EXACT common times when available; otherwise display each scope explicitly.
        scope = 'common_7d' if 'common_7d' in set(frame.scope) else 'per_window'
        frame = frame.loc[frame.scope == scope].copy()
        frame['series'] = frame.method + ' / ' + frame.window_days.astype(str) + 'd'
        figures.append(px.line(frame, x='k', y='observed_positive_capture_at_k', color='series', markers=True,
                               title=f'Observed Positive Retrieval · Capture among candidate positives ({scope})'))
        reach = frame.loc[(frame.method == 'historical_frequency') & (frame.k == 5)]
        figures.append(px.bar(reach, x='window_days', y='candidate_reach_of_observed_positives',
                              title=f'Observed Positive Retrieval · Candidate reach ({scope})'))
    return figures


def write_report(result, root, private):
    root = Path(root)
    public = root / 'reports/multisource'
    public.mkdir(parents=True, exist_ok=True)
    for filename, data in [('T31_SOURCE_SUMMARY.json', {k: result[k] for k in ['run_id', 'source_kind', 'sources', 'networks']}),
                           ('T31_FEASIBILITY.json', result['feasibility']), ('T31_PROTOCOL.json', result['protocol'])]:
        (public / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    pd.DataFrame([{k: v for k, v in n.items() if not isinstance(v, (dict, list))} for n in result['networks']]).to_csv(public / 'T31_NETWORK_METRICS.csv', index=False)
    pd.DataFrame(result['retrieval']).to_csv(public / 'T31_RETRIEVAL_METRICS.csv', index=False)
    text = f'''# T31 — Multi-Dataset Exploratory Research

Run `{result['run_id']}`, source_kind=`real_public_dataset`. Copenhagen remains the primary binary source: frozen T17/T22/T30 evidence is referenced, never refitted or mixed into these rankings.

## Actual source quality and graph statistics

| Source | Contact IDs | Raw valid records | Unique canonical records | Pairs | Span days | Status |
| --- | --- | --- | --- | --- | --- | --- |
'''
    for s in result['sources']:
        text += '|' + '|'.join(str(s.get(k, 'unavailable')) for k in ['dataset_id', 'participants', 'event_rows', 'unique_contact_records', 'valid_pairs', 'span_days', 'status']) + '|\n'
    text += '''
Descriptive Network Analysis graphs describe whole archived source networks, never historical input networks. Counts are contact records, not conversations, meetings or friendship strength. Exact canonical (timestamp,pair) repeats count once in this new study; raw/legacy counts remain unchanged. IDs are strictly source-isolated. SourceSummary contains source hashes, schema adapter version, seconds/tick policy, graph components/density, broad degree/pair-frequency distributions and source-level daily activity. Broad histograms containing nonzero groups below5 are entirely suppressed; small public retrieval count/ratio families are suppressed together. No participant-level values or edge lists are exported.

## Prespecified observed-positive retrieval

Candidates are ONLY [t-1d,t) contacts. Frequency (unique records / historical days), last recency (last timestamp−t), and common-neighbor counts use ONLY [t-window,t). All rank descending; ties use ascending source/minID/maxID. K=5/10/20, daily08:00 source-clock snapshots,1/3/7d history and complete source-span future24h are fixed before results. Ranking inputs are saved locally before the explicit future reveal. No model training or parameter/threshold selection occurs.

Future contacts use (t,t+24h]. Capture@K = observed positive hits / all observed future positive pairs IN the historical candidate pool. Capture-all additionally divides by ALL future recorded positive pairs; candidate reach = in-pool positives / all recorded positives. Outside-pool positives are reported separately; they are new to the1d candidate pool, not necessarily first-ever contacts. Missing future contacts remain Unknown. Zero denominators yield unavailable (null); no binary negatives or Accuracy/Precision/F1/AP/ROC/Brier/LogLoss. Metrics aggregate snapshot-pair counts (repeated pairs on different dates count separately), not independent persons or all physical contacts.

Per-window scopes have different dates and cannot identify a pure window effect. Common_7d explicitly shares dates and1d candidates across1/3/7d. No significance claim: fewer than3 positive-pool dates is insufficient descriptive temporal evidence; even more dates remain short dependent observational evidence. Empty candidate dates and empty positive pools are counted separately, never silently dropped to improve scores. Complete recorded span does not establish continuous badge availability. TopK results across different sensors/populations are not a common performance leaderboard.

| Source | Window | Calendar-complete times | Nonempty candidate times | Positive-pool times | Status |
| --- | --- | --- | --- | --- | --- |
'''
    for f in result['feasibility']:
        for w, info in f.get('windows', {}).items():
            if info is not None:
                text += f"|{f['dataset_id']}|{w}d|{info['complete_prediction_times']}|{info['nonempty_candidate_times']}|{info['positive_pool_times']}|{info['status']}|\n"
    text += '\nFixed frequency Top20 on common_7d dates (snapshot-pair totals, descriptive only):\n\n| Source | Window | Hits | In-pool positives | Outside-pool positives | Capture@20 | Candidate reach |\n| --- | --- | --- | --- | --- | --- | --- |\n'
    for r in result['retrieval']:
        if r['scope'] == 'common_7d' and r['method'] == 'historical_frequency' and r['k'] == 20:
            text += '|' + '|'.join(str(r[k]) for k in ['dataset_id', 'window_days', 'observed_positive_hits_at_k', 'future_positive_pairs_in_candidate_pool', 'future_positive_pairs_outside_candidate_pool', 'observed_positive_capture_at_k', 'candidate_reach_of_observed_positives']) + '|\n'
    text += '\n## Source evidence and limitations\n\n'
    for s in result['sources']:
        text += f"- **{s['dataset_id']}**: [{s['name']}]({s['source_url']}); {s['citation']}. License: {s['licence']}. {s.get('reason', '')} SHA256: `{s.get('file_hash', 'unavailable')}`.\n"
    text += '''
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
'''
    (root / 'MULTISOURCE_STUDY.md').write_text(text)
    graphs = []
    for s in result['sources']:
        network = next((n for n in result['networks'] if n['dataset_id'] == s['dataset_id']), None)
        rows = [r for r in result['retrieval'] if r['dataset_id'] == s['dataset_id']]
        graphs.extend(study_figures(s, network, rows))
    body = '<html><head><meta charset="utf-8"><title>T31 real multi-source exploration</title></head><body><pre>' + html.escape(text) + '</pre>'
    body += ''.join(f.to_html(full_html=False, include_plotlyjs=True if i == 0 else False) for i, f in enumerate(graphs)) + '</body></html>'
    (Path(private) / 'T31_REPORT.html').write_text(body)


def load_public_results(root):
    directory = Path(root) / 'reports/multisource'
    summary = directory / 'T31_SOURCE_SUMMARY.json'
    if not summary.exists():
        return None
    result = json.loads(summary.read_text())
    result['retrieval'] = pd.read_csv(directory / 'T31_RETRIEVAL_METRICS.csv').where(lambda f: f.notna(), None).to_dict('records')
    result['feasibility'] = json.loads((directory / 'T31_FEASIBILITY.json').read_text())
    return result
