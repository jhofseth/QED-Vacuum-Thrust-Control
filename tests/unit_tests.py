# tests/unit_tests.py
# Pytest-based unit tests for core functions in simulations/equations.py,
# including thrust calculations (force_vector, total_thrust, acceleration),
# magnetic fields (opposing_field, pulsed_enhancement), and others.
# Assumes equations.py is in the parent directory or sys.path.

import sys
import os
import pytest
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulations.equations import (
    opposing_field,
    pulsed_enhancement,
    rg_beta_chi,
    force_vector,
    total_thrust,
    acceleration,
    efficiency,
    power_consumption,
    range_calc
)

# Constants for tests (matching defaults where possible)
TEST_M1 = 100.0
TEST_M2 = 100.0
TEST_D = 0.05
TEST_K = 1.0
TEST_N_TURNS = 100
TEST_I = 15.0
TEST_CHI = 1e-10
TEST_G = 1.0
TEST_LAMBDA = 0.1
TEST_GRAD_H2 = np.array([1.0, 0.0, 0.0])
TEST_A = 1.0
TEST_RHO = 1000.0
TEST_N_UNITS = 24
TEST_ETA = 0.95
TEST_THETA = 0.0
TEST_MASS = 20000.0
TEST_R = 5.0
TEST_P_EDDY = 100.0
TEST_V = 1000.0

@pytest.fixture
def default_params():
    """Fixture for default test parameters."""
    return {
        'm1': TEST_M1,
        'm2': TEST_M2,
        'd': TEST_D,
        'k': TEST_K,
        'n_turns': TEST_N_TURNS,
        'I': TEST_I,
        'chi': TEST_CHI,
        'g': TEST_G,
        'lam': TEST_LAMBDA,
        'grad_h2': TEST_GRAD_H2,
        'A': TEST_A,
        'rho': TEST_RHO,
        'N': TEST_N_UNITS,
        'eta': TEST_ETA,
        'theta': TEST_THETA,
        'mass': TEST_MASS,
        'R': TEST_R,
        'P_eddy': TEST_P_EDDY,
        'v': TEST_V
    }

def test_opposing_field(default_params):
    """Test opposing_field calculation."""
    B = opposing_field(default_params['m1'], default_params['m2'], default_params['d'], default_params['k'])
    expected = (4 * np.pi * 1e-7 * TEST_M1 * TEST_M2) / (2 * np.pi * TEST_D**2) * TEST_K  # μ0 = 4πe-7
    assert np.isclose(B, expected, rtol=1e-5), f"Expected {expected}, got {B}"

def test_pulsed_enhancement(default_params):
    """Test pulsed_enhancement."""
    delta_B = pulsed_enhancement(default_params['n_turns'], default_params['I'])
    expected = 4 * np.pi * 1e-7 * TEST_N_TURNS * TEST_I  # μ0 n I
    assert np.isclose(delta_B, expected, rtol=1e-5), f"Expected {expected}, got {delta_B}"

def test_rg_beta_chi(default_params):
    """Test rg_beta_chi for spin-0."""
    beta = rg_beta_chi(default_params['chi'], default_params['g'], default_params['lam'])
    expected = -4 * TEST_CHI + (TEST_G / (2 * np.pi)) * (TEST_CHI / (1 - 2 * TEST_LAMBDA))
    assert np.isclose(beta, expected, rtol=1e-5), f"Expected {expected}, got {beta}"

def test_force_vector(default_params):
    """Test force_vector (vector output)."""
    F_vec = force_vector(default_params['chi'], 50.0, default_params['grad_h2'], default_params['A'], default_params['rho'])
    F_mag = np.linalg.norm(F_vec)
    expected_mag = TEST_CHI * 50.0**2 * np.linalg.norm(TEST_GRAD_H2) * TEST_A * TEST_RHO
    assert np.isclose(F_mag, expected_mag, rtol=1e-5), f"Expected mag {expected_mag}, got {F_mag}"
    assert F_vec.shape == (3,), "Force vector should be 3D"

def test_total_thrust(default_params):
    """Test total_thrust."""
    F_mag = 100.0  # Arbitrary
    T = total_thrust(default_params['N'], F_mag, default_params['eta'], default_params['theta'])
    expected = TEST_N_UNITS * 100.0 * TEST_ETA * np.cos(np.deg2rad(TEST_THETA))
    assert np.isclose(T, expected, rtol=1e-5), f"Expected {expected}, got {T}"

def test_acceleration(default_params):
    """Test acceleration."""
    T = 10000.0  # Arbitrary thrust
    a = acceleration(T, default_params['mass'])
    expected = 10000.0 / TEST_MASS
    assert np.isclose(a, expected, rtol=1e-5), f"Expected {expected}, got {a}"

    with pytest.raises(ValueError):
        acceleration(T, 0.0)  # Zero mass error

def test_power_consumption(default_params):
    """Test power_consumption."""
    P = power_consumption(default_params['I'], default_params['R'], default_params['P_eddy'])
    expected = TEST_I**2 * TEST_R + TEST_P_EDDY
    assert np.isclose(P, expected, rtol=1e-5), f"Expected {expected}, got {P}"

def test_efficiency(default_params):
    """Test efficiency."""
    T = 10000.0
    P = 5000.0
    eta = efficiency(T, default_params['v'], P)
    expected = (10000.0 * TEST_V / 5000.0) * 100
    assert np.isclose(eta, expected, rtol=1e-5), f"Expected {expected}, got {eta}"

def test_range_calc(default_params):
    """Test range_calc."""
    E = 1e6  # Arbitrary energy
    P = 5000.0
    R = range_calc(default_params['v'], E, P)
    expected = TEST_V * (1e6 / 5000.0)
    assert np.isclose(R, expected, rtol=1e-5), f"Expected {expected}, got {R}"

@pytest.mark.parametrize("chi, expected_beta", [
    (1e-10, -4e-10 + (1 / (2 * np.pi)) * (1e-10 / (1 - 0.2))),
    (0.0, 0.0),
    (1e-5, -4e-5 + (1 / (2 * np.pi)) * (1e-5 / (1 - 0.2))),
])
def test_rg_beta_chi_parametrized(chi, expected_beta):
    """Parametrized test for rg_beta_chi."""
    beta = rg_beta_chi(chi, TEST_G, TEST_LAMBDA)
    assert np.isclose(beta, expected_beta, rtol=1e-5)

@pytest.mark.parametrize("grad_h2, expected_dir", [
    (np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])),
    (np.array([0.0, 1.0, 0.0]), np.array([0.0, 1.0, 0.0])),
])
def test_force_vector_direction(grad_h2, expected_dir):
    """Test force_vector direction aligns with grad_h2."""
    F_vec = force_vector(TEST_CHI, 50.0, grad_h2, TEST_A, TEST_RHO)
    F_dir = F_vec / np.linalg.norm(F_vec)
    assert np.allclose(F_dir, expected_dir / np.linalg.norm(expected_dir)), "Force direction mismatch"
