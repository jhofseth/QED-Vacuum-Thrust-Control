# tests/unit_tests.py
# Pytest-based unit tests for core functions in simulations/equations.py,
# including thrust calculations (force_vector, total_thrust, acceleration),
# magnetic fields (opposing_field, pulsed_enhancement), and others.
# CRITICAL: Added tests for MADA field convergence validation.
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


# ==================== NEW: MADA CONVERGENCE TESTS ====================

def calculate_convergence_quality(B1: np.ndarray, B2: np.ndarray) -> float:
    """
    Calculate MADA convergence quality (how well fields oppose).
    Returns 1.0 for perfect opposition, 0.0 for perpendicular, -1.0 for parallel.
    
    :param B1: Magnetic field vector from MADA unit 1
    :param B2: Magnetic field vector from MADA unit 2
    :return: Convergence quality [-1, 1]
    """
    B1_mag = np.linalg.norm(B1)
    B2_mag = np.linalg.norm(B2)
    
    if B1_mag == 0 or B2_mag == 0:
        return 0.0
    
    B1_norm = B1 / B1_mag
    B2_norm = B2 / B2_mag
    
    # Dot product: -1 means opposing (good), +1 means parallel (bad)
    dot_product = np.dot(B1_norm, B2_norm)
    
    # Return negative of dot product: 1.0 = opposing, -1.0 = parallel
    return -dot_product


class TestMADAConvergence:
    """Test suite for MADA magnetic field convergence validation."""
    
    def test_perfect_opposition(self):
        """Test fields pointing directly at each other (ideal case)."""
        # MADA1 at +X pointing toward origin (negative X direction)
        B1 = np.array([-100.0, 0.0, 0.0])
        # MADA2 at -X pointing toward origin (positive X direction)
        B2 = np.array([100.0, 0.0, 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert np.isclose(quality, 1.0, atol=1e-6), \
            f"Perfect opposition should give quality=1.0, got {quality}"
    
    def test_parallel_fields_bad(self):
        """Test fields pointing in same direction (INCORRECT configuration)."""
        # Both pointing in +X direction (WRONG!)
        B1 = np.array([100.0, 0.0, 0.0])
        B2 = np.array([100.0, 0.0, 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert np.isclose(quality, -1.0, atol=1e-6), \
            f"Parallel fields should give quality=-1.0, got {quality}"
        assert quality < 0.8, "Parallel configuration should fail convergence threshold"
    
    def test_diverging_fields_bad(self):
        """Test fields pointing away from each other (INCORRECT configuration)."""
        # MADA1 at +X pointing away from origin (positive X direction)
        B1 = np.array([100.0, 0.0, 0.0])
        # MADA2 at -X pointing away from origin (negative X direction)
        B2 = np.array([-100.0, 0.0, 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert np.isclose(quality, -1.0, atol=1e-6), \
            f"Diverging fields should give quality=-1.0, got {quality}"
        assert quality < 0.8, "Diverging configuration should fail convergence threshold"
    
    def test_perpendicular_fields(self):
        """Test perpendicular fields (suboptimal but not parallel)."""
        B1 = np.array([100.0, 0.0, 0.0])
        B2 = np.array([0.0, 100.0, 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert np.isclose(quality, 0.0, atol=1e-6), \
            f"Perpendicular fields should give quality=0.0, got {quality}"
        assert quality < 0.8, "Perpendicular configuration should fail convergence threshold"
    
    def test_45_degree_misalignment(self):
        """Test fields at 45° angle (poor convergence)."""
        # MADA1 pointing toward origin from +X
        B1 = np.array([-100.0, 0.0, 0.0])
        # MADA2 at 45° angle (pointing +X and +Y)
        B2 = np.array([70.7, 70.7, 0.0])  # Normalized would be (0.707, 0.707, 0)
        
        quality = calculate_convergence_quality(B1, B2)
        expected = -(-1.0 * 0.707)  # cos(135°) = -0.707, so quality = 0.707
        assert np.isclose(quality, expected, atol=0.01), \
            f"45° misalignment should give quality≈0.707, got {quality}"
        assert quality < 0.8, "45° misalignment should fail convergence threshold"
    
    def test_acceptable_convergence(self):
        """Test slightly off-axis but acceptable convergence (>0.85)."""
        # MADA1 pointing toward origin from +X
        B1 = np.array([-100.0, 0.0, 0.0])
        # MADA2 slightly misaligned (10° from perfect opposition)
        angle_rad = np.deg2rad(170)  # 170° means 10° off from 180° (perfect opposition)
        B2 = np.array([100.0 * np.cos(angle_rad), 100.0 * np.sin(angle_rad), 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert quality > 0.85, \
            f"10° misalignment should pass 0.85 threshold, got {quality}"
        assert quality < 0.99, \
            f"10° misalignment should not be perfect, got {quality}"
    
    def test_zero_field_edge_case(self):
        """Test behavior with zero magnetic field."""
        B1 = np.array([100.0, 0.0, 0.0])
        B2 = np.array([0.0, 0.0, 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert quality == 0.0, f"Zero field should give quality=0.0, got {quality}"
    
    def test_unequal_magnitudes_same_direction(self):
        """Test that convergence depends on direction, not magnitude."""
        # Different magnitudes but same direction (opposing)
        B1 = np.array([-50.0, 0.0, 0.0])
        B2 = np.array([150.0, 0.0, 0.0])
        
        quality = calculate_convergence_quality(B1, B2)
        assert np.isclose(quality, 1.0, atol=1e-6), \
            f"Unequal magnitudes with perfect opposition should give quality=1.0, got {quality}"
    
    @pytest.mark.parametrize("B1, B2, expected_quality, description", [
        # Perfect opposition
        (np.array([-1, 0, 0]), np.array([1, 0, 0]), 1.0, "X-axis opposition"),
        (np.array([0, -1, 0]), np.array([0, 1, 0]), 1.0, "Y-axis opposition"),
        (np.array([0, 0, -1]), np.array([0, 0, 1]), 1.0, "Z-axis opposition"),
        
        # Parallel (BAD)
        (np.array([1, 0, 0]), np.array([1, 0, 0]), -1.0, "X-axis parallel"),
        (np.array([0, 1, 0]), np.array([0, 1, 0]), -1.0, "Y-axis parallel"),
        
        # Perpendicular
        (np.array([1, 0, 0]), np.array([0, 1, 0]), 0.0, "XY perpendicular"),
        (np.array([1, 0, 0]), np.array([0, 0, 1]), 0.0, "XZ perpendicular"),
    ])
    def test_convergence_parametrized(self, B1, B2, expected_quality, description):
        """Parametrized tests for various field configurations."""
        quality = calculate_convergence_quality(B1, B2)
        assert np.isclose(quality, expected_quality, atol=1e-6), \
            f"{description}: Expected quality={expected_quality}, got {quality}"


class TestMADAConfigurationErrors:
    """Test suite to detect common MADA configuration errors."""
    
    def test_fcstd_rotation_error(self):
        """
        Simulate the error from spherical_drone.fcstd where magnets were
        facing away from center instead of toward center.
        """
        # CORRECT: Both pointing toward center (at origin)
        B1_correct = np.array([-100, 0, 0])  # At +X, pointing toward origin
        B2_correct = np.array([100, 0, 0])   # At -X, pointing toward origin
        
        # INCORRECT: As originally configured (both pointing away)
        B1_wrong = np.array([100, 0, 0])   # At +X, pointing away from origin
        B2_wrong = np.array([-100, 0, 0])  # At -X, pointing away from origin
        
        quality_correct = calculate_convergence_quality(B1_correct, B2_correct)
        quality_wrong = calculate_convergence_quality(B1_wrong, B2_wrong)
        
        assert quality_correct > 0.99, \
            f"Correct configuration should have quality≈1.0, got {quality_correct}"
        assert quality_wrong < -0.99, \
            f"Wrong configuration should have quality≈-1.0, got {quality_wrong}"
        
        # This test would catch the FreeCAD error!
        assert quality_wrong < 0.8, \
            "Original FreeCAD configuration should FAIL convergence check"
    
    def test_wiring_polarity_error(self):
        """Test detection of reversed coil wiring."""
        # One coil wired correctly, one reversed
        B1_correct = np.array([-100, 0, 0])
        B2_reversed = np.array([-100, 0, 0])  # Should be [100, 0, 0]
        
        quality = calculate_convergence_quality(B1_correct, B2_reversed)
        
        assert quality < 0.0, \
            f"Reversed wiring should give negative quality, got {quality}"
        assert quality < 0.8, \
            "Reversed wiring should fail convergence threshold"
    
    def test_mechanical_misalignment_45deg(self):
        """Test detection of 45° mechanical misalignment."""
        B1 = np.array([-100, 0, 0])
        # MADA2 rotated 45° from correct position
        B2_misaligned = np.array([70.7, 70.7, 0])
        
        quality = calculate_convergence_quality(B1, B2_misaligned)
        
        assert quality < 0.8, \
            f"45° misalignment should fail threshold (quality={quality})"


class TestMADAIntegration:
    """Integration tests simulating real-world MADA scenarios."""
    
    def test_dual_mada_spherical_drone(self):
        """
        Test typical dual MADA configuration for spherical drone.
        Two MADA units on opposite sides pointing toward center.
        """
        # MADA positions (in meters)
        mada1_pos = np.array([0.3, 0, 0])   # +300mm on X-axis
        mada2_pos = np.array([-0.3, 0, 0])  # -300mm on X-axis
        center = np.array([0, 0, 0])
        
        # Calculate field directions (pointing toward center)
        B1_direction = center - mada1_pos
        B2_direction = center - mada2_pos
        
        # Normalize and scale to field strength
        B_magnitude = 50.0  # Tesla
        B1 = B1_direction / np.linalg.norm(B1_direction) * B_magnitude
        B2 = B2_direction / np.linalg.norm(B2_direction) * B_magnitude
        
        quality = calculate_convergence_quality(B1, B2)
        
        assert quality > 0.99, \
            f"Dual MADA spherical configuration should have quality≈1.0, got {quality}"
    
    def test_triple_mada_configuration(self):
        """Test three MADA units arranged around sphere."""
        # 120° apart on XY plane, all pointing toward center
        mada1_dir = np.array([-1, 0, 0])
        mada2_dir = np.array([0.5, -0.866, 0])  # 120° rotated
        mada3_dir = np.array([0.5, 0.866, 0])   # 240° rotated
        
        B_magnitude = 50.0
        B1 = mada1_dir * B_magnitude
        B2 = mada2_dir * B_magnitude
        B3 = mada3_dir * B_magnitude
        
        # Check pairwise convergence
        q12 = calculate_convergence_quality(B1, B2)
        q23 = calculate_convergence_quality(B2, B3)
        q31 = calculate_convergence_quality(B3, B1)
        
        # For 120° separation, expected quality ≈ 0.5 (cos(120°) = -0.5)
        expected = 0.5
        assert np.isclose(q12, expected, atol=0.05), \
            f"120° MADA separation should give quality≈{expected}, got {q12}"
        assert np.isclose(q23, expected, atol=0.05)
        assert np.isclose(q31, expected, atol=0.05)


# ==================== TEST RUNNER ====================

if __name__ == "__main__":
    # Run all tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
