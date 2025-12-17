"""Tests for mahjong_sim.players module."""

import numpy as np
from mahjong_sim.players import NeutralPolicy


def test_neutral_policy_init():
    """Test NeutralPolicy initialization."""
    policy = NeutralPolicy(seed=None)
    assert policy is not None


def test_neutral_policy_high_risk():
    """Test NeutralPolicy with high risk (should always Hu at fan >= 1)."""
    policy = NeutralPolicy(seed=None)
    # Risk >= bailout_risk_threshold (0.70): should accept fan >= 1
    assert policy.should_hu(fan=1, risk=0.75) is True
    assert policy.should_hu(fan=2, risk=0.75) is True
    # Fan == 0 should not win even at high risk (invalid win)
    assert policy.should_hu(fan=0, risk=0.75) is False


def test_neutral_policy_medium_risk():
    """Test NeutralPolicy with medium risk (should accept fan >= 2)."""
    policy = NeutralPolicy(seed=None)
    # 0.45 <= risk < 0.70: should accept fan >= 2
    assert policy.should_hu(fan=1, risk=0.5) is False  # Fan == 1 not accepted at medium risk
    assert policy.should_hu(fan=2, risk=0.5) is True
    assert policy.should_hu(fan=3, risk=0.5) is True
    # Fan == 0 should not win
    assert policy.should_hu(fan=0, risk=0.5) is False


def test_neutral_policy_low_risk():
    """Test NeutralPolicy with low risk (should pursue target_fan >= 3)."""
    policy = NeutralPolicy(seed=None)
    # Low risk (risk < 0.45): should pursue target_fan (3)
    assert policy.should_hu(fan=2, risk=0.3) is False  # Fan == 2 not accepted at low risk
    assert policy.should_hu(fan=3, risk=0.3) is True
    assert policy.should_hu(fan=4, risk=0.3) is True
    # Fan == 1 should not win at low risk (prevents winning on small fans)
    assert policy.should_hu(fan=1, risk=0.3) is False
    assert policy.should_hu(fan=0, risk=0.3) is False


def test_neutral_policy_between_def_and_agg():
    """Test that NeutralPolicy is between DEF and AGG strategies."""
    policy = NeutralPolicy(seed=None)
    # At low risk: requires fan >= 3 (more than DEF's fan >= 1, less than AGG's fan >= 5)
    assert policy.should_hu(fan=1, risk=0.0) is False  # DEF would accept, NEU doesn't
    assert policy.should_hu(fan=2, risk=0.0) is False  # NEU doesn't accept at low risk
    assert policy.should_hu(fan=3, risk=0.0) is True  # NEU accepts, AGG wouldn't (needs 5)
    # At medium risk: accepts fan >= 2 (more flexible than AGG)
    assert policy.should_hu(fan=2, risk=0.5) is True  # NEU accepts, AGG wouldn't (needs 4)
    # At high risk: accepts fan >= 1 (most flexible)
    assert policy.should_hu(fan=1, risk=0.75) is True  # NEU accepts, AGG wouldn't (needs 2)

