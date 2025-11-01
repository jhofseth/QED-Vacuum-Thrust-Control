import pytest
import numpy as np
import scipy.constants as const
import sympy as sp
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulations.equations import (
    surface_field,
    opposing_field,
    pulsed_enhancement,
    lagrangian_disrupt,
    rg_beta_chi,
    source_term,
    force_vector,
    total_thrust,
    acceleration,
    power_consumption,
    efficiency,
    range_calc,
    symbolic_surface_field
)

MU_0 = const.mu_0


@pytest.fixture
def sample_metric():
    """Sample 4x4 matrices for testing."""
    h_mu_nu = np.eye(4)  # Identity for simplicity
    h_mu_nu_inv = np.eye(4)
    return h_mu_nu, h_mu_nu_inv


class TestMagneticFields:
    """Test magnetic field calculations."""
    
    def test_surface_field(self):
        """Test surface magnetic field calculation."""
        B_r, L, R, d = 1.4, 0.3, 0.15, 0.05
        expected = (B_r / 2) * (
            L / np.sqrt(R**2 + L**2) + 
            (L + d) / np.sqrt(R**2 + (L + d)**2)
        )
        result = surface_field(B_r, L, R, d)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_surface_field_zero_distance(self):
        """Test surface field with zero distance."""
        B_r, L, R, d = 1.4, 0.3, 0.15, 0.0
        result = surface_field(B_r, L, R, d)
        assert result > 0, "Surface field should be positive"
    
    def test_opposing_field(self):
        """Test opposing magnetic field calculation."""
        m1, m2, d, k = 100.0, 100.0, 0.05, 1.0
        expected = (MU_0 * m1 * m2 / (2 * np.pi * d**2)) * k
        result = opposing_field(m1, m2, d, k)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_opposing_field_with_scaling(self):
        """Test opposing field with different scaling factors."""
        m1, m2, d = 100.0, 100.0, 0.05
        result_k1 = opposing_field(m1, m2, d, k=1.0)
        result_k2 = opposing_field(m1, m2, d, k=2.0)
        assert np.isclose(result_k2, 2 * result_k1), "Scaling should be linear"
    
    def test_pulsed_enhancement(self):
        """Test pulsed magnetic field enhancement."""
        n, I = 100, 15.0
        expected = MU_0 * n * I
        result = pulsed_enhancement(n, I)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_pulsed_enhancement_zero_current(self):
        """Test pulsed enhancement with zero current."""
        n, I = 100, 0.0
        result = pulsed_enhancement(n, I)
        assert result == 0.0, "Enhancement should be zero with no current"


class TestQuantumParameters:
    """Test quantum and RG calculations."""
    
    def test_lagrangian_disrupt(self, sample_metric):
        """Test disruption Lagrangian calculation."""
        chi, B = 1e-10, 50.0
        h_mu_nu, h_mu_nu_inv = sample_metric
        contraction = np.einsum('ij,ij->', h_mu_nu, h_mu_nu_inv)  # 4 for identity
        expected = -0.5 * chi * B**2 * contraction
        result = lagrangian_disrupt(chi, B, h_mu_nu, h_mu_nu_inv)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_lagrangian_disrupt_scaled_metric(self):
        """Test Lagrangian with scaled metric."""
        chi, B = 1e-10, 50.0
        h_mu_nu = np.eye(4) * 2.0
        h_mu_nu_inv = np.eye(4) * 0.5
        result = lagrangian_disrupt(chi, B, h_mu_nu, h_mu_nu_inv)
        assert result < 0, "Lagrangian should be negative"
    
    def test_rg_beta_chi(self):
        """Test RG beta function for chi."""
        chi, g, lambda_val = 1e-10, 1.0, 0.1
        expected = -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lambda_val))
        result = rg_beta_chi(chi, g, lambda_val)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_rg_beta_chi_singularity(self):
        """Test that RG function raises error near singularity."""
        chi, g, lambda_val = 1e-10, 1.0, 0.5  # 2*lambda = 1.0, at singularity
        with pytest.raises(ValueError, match="Lambda parameter must satisfy"):
            rg_beta_chi(chi, g, lambda_val)
    
    def test_rg_beta_chi_negative_lambda(self):
        """Test RG function with negative lambda."""
        chi, g, lambda_val = 1e-10, 1.0, -0.1
        result = rg_beta_chi(chi, g, lambda_val)
        assert np.isfinite(result), "Result should be finite for valid lambda"
    
    def test_source_term(self, sample_metric):
        """Test source term calculation."""
        chi, B = 1e-10, 50.0
        h_mu_nu, _ = sample_metric
        expected = chi * B**2 * h_mu_nu
        result = source_term(chi, B, h_mu_nu)
        np.testing.assert_allclose(result, expected)
    
    def test_source_term_shape(self, sample_metric):
        """Test that source term maintains correct shape."""
        chi, B = 1e-10, 50.0
        h_mu_nu, _ = sample_metric
        result = source_term(chi, B, h_mu_nu)
        assert result.shape == (4, 4), "Source term should be 4x4"


class TestForceAndThrust:
    """Test force and thrust calculations."""
    
    def test_force_vector(self):
        """Test force vector calculation."""
        chi, B = 1e-10, 50.0
        grad_h2 = np.array([1.0, 0.0, 0.0])
        A, rho = 1.0, 1000.0
        expected = chi * B**2 * grad_h2 * A * rho
        result = force_vector(chi, B, grad_h2, A, rho)
        np.testing.assert_allclose(result, expected)
    
    def test_force_vector_3d(self):
        """Test force vector in 3D."""
        chi, B = 1e-10, 50.0
        grad_h2 = np.array([1.0, 2.0, 3.0])
        A, rho = 1.0, 1000.0
        result = force_vector(chi, B, grad_h2, A, rho)
        assert result.shape == (3,), "Force should be 3D vector"
        assert np.all(result != 0), "Force components should be non-zero"
    
    def test_force_vector_list_input(self):
        """Test force vector with list input for gradient."""
        chi, B = 1e-10, 50.0
        grad_h2 = [1.0, 0.0, 0.0]  # List instead of array
        A, rho = 1.0, 1000.0
        result = force_vector(chi, B, grad_h2, A, rho)
        assert isinstance(result, np.ndarray), "Result should be numpy array"
    
    def test_total_thrust(self):
        """Test total thrust calculation."""
        N, F, eta, theta = 24, 1000.0, 0.95, 0.0
        expected = N * F * eta * np.cos(np.deg2rad(theta))
        result = total_thrust(N, F, eta, theta)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_total_thrust_angle(self):
        """Test total thrust with different angles."""
        N, F, eta = 24, 1000.0, 0.95
        result_0 = total_thrust(N, F, eta, 0.0)
        result_90 = total_thrust(N, F, eta, 90.0)
        assert result_0 > result_90, "Thrust at 0° should be greater than at 90°"
        assert np.isclose(result_90, 0.0, atol=1e-10), "Thrust at 90° should be ~0"
    
    def test_total_thrust_vector_force(self):
        """Test total thrust with vector force input."""
        N, eta, theta = 24, 0.95, 0.0
        F_vec = np.array([1000.0, 0.0, 0.0])
        result = total_thrust(N, F_vec, eta, theta)
        expected = N * np.linalg.norm(F_vec) * eta * np.cos(np.deg2rad(theta))
        assert np.isclose(result, expected), "Should handle vector force"
    
    def test_acceleration(self):
        """Test acceleration calculation."""
        T, m = 1000.0, 20000.0
        expected = T / m
        result = acceleration(T, m)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_acceleration_zero_mass(self):
        """Test acceleration with zero mass raises error."""
        T, m = 1000.0, 0.0
        with pytest.raises(ValueError, match="Mass must be positive"):
            acceleration(T, m)
    
    def test_acceleration_negative_mass(self):
        """Test acceleration with negative mass raises error."""
        T, m = 1000.0, -100.0
        with pytest.raises(ValueError, match="Mass must be positive"):
            acceleration(T, m)


class TestPowerAndEfficiency:
    """Test power and efficiency calculations."""
    
    def test_power_consumption(self):
        """Test power consumption calculation."""
        I, R, P_eddy = 15.0, 5.0, 100.0
        expected = I**2 * R + P_eddy
        result = power_consumption(I, R, P_eddy)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_power_consumption_no_eddy(self):
        """Test power consumption without eddy losses."""
        I, R, P_eddy = 15.0, 5.0, 0.0
        expected = I**2 * R
        result = power_consumption(I, R, P_eddy)
        assert np.isclose(result, expected), "Power should be I²R only"
    
    def test_efficiency(self):
        """Test efficiency calculation."""
        T, v, P = 1000.0, 1000.0, 5000.0
        expected = (T * v / P) * 100
        result = efficiency(T, v, P)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_efficiency_zero_power(self):
        """Test efficiency with zero power raises error."""
        T, v, P = 1000.0, 1000.0, 0.0
        with pytest.raises(ValueError, match="Power must be positive"):
            efficiency(T, v, P)
    
    def test_efficiency_high_performance(self):
        """Test efficiency can exceed 100% in ideal cases."""
        T, v, P = 1000.0, 1000.0, 500.0  # Very efficient
        result = efficiency(T, v, P)
        assert result > 100, "Efficiency can theoretically exceed 100%"
    
    def test_range_calc(self):
        """Test range calculation."""
        v, E, P = 1000.0, 1.8e9, 5000.0  # Example: 500 kWh = 1.8e9 J
        expected = v * (E / P)
        result = range_calc(v, E, P)
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    
    def test_range_calc_zero_power(self):
        """Test range with zero power raises error."""
        v, E, P = 1000.0, 1.8e9, 0.0
        with pytest.raises(ValueError, match="Power must be positive"):
            range_calc(v, E, P)
    
    def test_range_calc_units(self):
        """Test range calculation with realistic units."""
        v = 1000.0  # m/s
        E = 500000.0 * 3600  # 500 kWh in Joules
        P = 5000.0  # 5 kW
        result = range_calc(v, E, P)
        result_km = result / 1000.0
        assert result_km > 1000, "Range should be over 1000 km with these parameters"


class TestSymbolic:
    """Test symbolic calculations."""
    
    def test_symbolic_surface_field(self):
        """Test symbolic surface field expression."""
        expr = symbolic_surface_field()
        B_r, L, R, d = sp.symbols('B_r L R d', positive=True, real=True)
        expected = (B_r / 2) * (
            L / sp.sqrt(R**2 + L**2) + 
            (L + d) / sp.sqrt(R**2 + (L + d)**2)
        )
        # Use simplify to handle symbolic equivalence
        assert sp.simplify(expr - expected) == 0, "Symbolic expressions should match"
    
    def test_symbolic_surface_field_substitution(self):
        """Test symbolic surface field with numerical substitution."""
        expr = symbolic_surface_field()
        B_r, L, R, d = sp.symbols('B_r L R d', positive=True, real=True)
        
        # Substitute values and compare with numerical function
        values = {B_r: 1.4, L: 0.3, R: 0.15, d: 0.05}
        symbolic_result = float(expr.subs(values))
        numerical_result = surface_field(1.4, 0.3, 0.15, 0.05)
        
        assert np.isclose(symbolic_result, numerical_result), \
            "Symbolic and numerical results should match"


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_thrust_pipeline(self):
        """Test complete thrust calculation pipeline."""
        # Parameters
        chi, B = 1e-10, 50.0
        grad_h2 = np.array([1.0, 0.0, 0.0])
        A, rho = 1.0, 1000.0
        N, eta, theta = 24, 0.95, 0.0
        mass = 20000.0
        
        # Calculate
        F_vec = force_vector(chi, B, grad_h2, A, rho)
        F_mag = np.linalg.norm(F_vec)
        T = total_thrust(N, F_mag, eta, theta)
        a = acceleration(T, mass)
        
        # Verify
        assert F_mag > 0, "Force should be positive"
        assert T > 0, "Thrust should be positive"
        assert a > 0, "Acceleration should be positive"
    
    def test_power_efficiency_consistency(self):
        """Test that power and efficiency calculations are consistent."""
        T, v = 1000.0, 1000.0
        I, R, P_eddy = 15.0, 5.0, 100.0
        
        P = power_consumption(I, R, P_eddy)
        eta = efficiency(T, v, P)
        
        # Check consistency: eta = (T*v/P) * 100
        expected_eta = (T * v / P) * 100
        assert np.isclose(eta, expected_eta), "Efficiency calculation inconsistent"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
