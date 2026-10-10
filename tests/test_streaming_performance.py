from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from src.positive_retrieval import ContactSource, DAY, historical_scores, historical_scores_multi, rank_scores, METHODS
from test_positive_retrieval import source, T


def test_cross_chunk_dedup_preserves_same_time_other_pairs_and_adjacent_events(tmp_path):
    rows = [(0, 1, 2), (0, 1, 3), (20, 1, 2), (0, 1, 2)] * 18000
    frame = pd.DataFrame(rows, columns=['timestamp', 'user_min', 'user_max']).assign(dataset_id='one')
    path = tmp_path/'contacts.parquet';frame.to_parquet(path, row_group_size=13)
    src = ContactSource(path, 'one', 0, 20, 'seconds')
    chunks = list(src.iter_unique())
    assert sum(len(c) for c in chunks) == 3
    expected = frame.drop_duplicates(['timestamp', 'dataset_id', 'user_min', 'user_max']).reset_index(drop=True)
    pd.testing.assert_frame_equal(src.read(), expected[['dataset_id', 'timestamp', 'user_min', 'user_max']])
    assert Counter(zip(src.read().user_min, src.read().user_max)) == {(1, 2): 2, (1, 3): 1}


def test_multiwindow_scores_ranks_boundaries_and_hit_parity(source):
    expected = {w: historical_scores(source, T, w) for w in (1, 3, 7)}
    first = historical_scores_multi(source, T)
    second = historical_scores_multi(source, T)
    for w in (1, 3, 7):
        pd.testing.assert_frame_equal(first[w], expected[w])
        pd.testing.assert_frame_equal(second[w], expected[w])
        for method in METHODS:
            pd.testing.assert_frame_equal(rank_scores(first[w], method), rank_scores(expected[w], method))


def test_large_synthetic_resource_check_in_independent_process(tmp_path):
    # Genuine large synthetic stress fixture, explicitly not a real experiment measurement.
    frame = pd.DataFrame({'dataset_id': ['stress']*200000, 'timestamp': [i%2000 for i in range(200000)],
                          'user_min': [1]*200000, 'user_max': [2]*200000})
    path = tmp_path/'stress.parquet';frame.to_parquet(path, row_group_size=16000)
    script = """import json,resource,sys
from pathlib import Path
from src.positive_retrieval import ContactSource
s=ContactSource(Path(sys.argv[1]),'stress',0,1999,'unverified tick')
print(json.dumps({'unique':sum(len(f) for f in s.iter_unique()),'rss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
"""
    result = subprocess.check_output([sys.executable, '-c', script, str(path)], text=True)
    record = json.loads(result)
    assert record['unique'] == 2000 and record['rss'] > 0
    rss_mb = record['rss']/(1024**2) if sys.platform=='darwin' else record['rss']/1024
    assert rss_mb < 1024  # Broad resource budget; no noisy runtime/speedup assertion.
