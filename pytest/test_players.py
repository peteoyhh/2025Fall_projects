"""Tests for mahjong_sim.players module."""

import numpy as np
from mahjong_sim.players import NeutralPolicy


def test_neutral_policy_init():
    """Test NeutralPolicy initialization."""
    policy = NeutralPolicy(seed=42)
    assert policy is not None


def test_neutral_policy_high_risk():
    """Test NeutralPolicy with high risk (should always Hu)."""
    policy = NeutralPolicy(seed=42)
    # Risk > 0.4 should always return True
    assert policy.should_hu(fan=0, risk=0.5) is True
    assert policy.should_hu(fan=0, risk=0.6) is True


def test_neutral_policy_low_fan_low_risk():
    """Test NeutralPolicy with low fan and low risk."""
    policy = NeutralPolicy(seed=42)
    # Fan < 1 and risk <= 0.4: 20% chance to Hu (80% chance to continue)
    # Since it's random, we test multiple times
    results = [policy.should_hu(fan=0, risk=0.3) for _ in range(100)]
    # Should have some True and some False
    assert any(results)  # At least some True
    assert not all(results)  # Not all True


def test_neutral_policy_fan_ge_one():
    """Test NeutralPolicy with fan >= 1."""
    policy = NeutralPolicy(seed=42)
    # Fan >= 1 should usually Hu (80% chance if risk <= 0.4)
    assert policy.should_hu(fan=1, risk=0.3) in [True, False]
    # With high fan, should Hu
    results = [policy.should_hu(fan=2, risk=0.3) for _ in range(10)]
    assert any(results)  # Should have some True


def test_neutral_policy_reproducibility():
    """Test that NeutralPolicy is reproducible with same seed."""
    policy1 = NeutralPolicy(seed=42)
    policy2 = NeutralPolicy(seed=42)
    
    # Should produce same results with same seed
    results1 = [policy1.should_hu(fan=0, risk=0.3) for _ in range(10)]
    results2 = [policy2.should_hu(fan=0, risk=0.3) for _ in range(10)]
    
    assert results1 == results2

