import numpy as np

from src import hawkes_baseline, hawkes_short


def test_stable_excitation_matches_t36_form_and_survives_short_half_lives():
    events = np.sort(np.random.default_rng(0).uniform(0, 168, 300))
    for hours in (0.5, 2, 8, 24):
        beta = hawkes_baseline.half_life_beta(hours)
        np.testing.assert_allclose(hawkes_short.forecast(events, 168.0, beta), hawkes_baseline.forecast(events, 168.0, beta), rtol=1e-9, atol=1e-12)
    beta = np.log(2)/(5/60)
    a = hawkes_short.excitation(events, beta)
    brute = np.array([np.sum(np.exp(-beta*(events[i]-events[:i]))) for i in range(len(events))])
    assert np.isfinite(a).all()
    np.testing.assert_allclose(a, brute, rtol=1e-9, atol=1e-300)
    assert 0 <= hawkes_short.forecast(events, 168.0, beta) <= 1


def test_grid_is_prespecified_ascending_and_includes_t36_grid():
    assert hawkes_short.GRID_MINUTES == sorted(hawkes_short.GRID_MINUTES) and hawkes_short.GRID_MINUTES[0] == 5
    assert {int(h*60) for h in hawkes_baseline.HAWKES_PROTOCOL["half_life_hours_grid"]} <= set(hawkes_short.GRID_MINUTES)
    assert hawkes_short.SHORT_PROTOCOL["test_used_for_selection"] is False
