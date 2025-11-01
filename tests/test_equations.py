import pytest
import numpy as np
import scipy.constants as const
import sympy as sp
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
    # Sample 4x4 matrices for testing
    h_mu_nu = np.eye(4)  # Identity for simplicity
    h_mu_nu_inv = np.eye(4)
    return h_mu_nu, h_mu_nu_inv

def test_surface_field():
    B_r, L, R, d = 1.4, 0.3, 0.15, 0.05
    expected = (B_r / 2) * (L / np.sqrt(R**2 + L**2) + (L + d) / np.sqrt(R**2 + (L + d)**2))
    assert np.isclose(surface_field(B_r, L, R, d), expected)

def test_opposing_field():
    m1, m2, d, k = 100.0, 100.0, 0.05, 1.0
    expected = (MU_0 * m1 * m2 / (2 * np.pi * d**2)) * k
    assert np.isclose(opposing_field(m1, m2, d, k), expected)

def test_pulsed_enhancement():
    n, I = 100, 15.0
    expected = MU_0 * n * I
    assert np.isclose(pulsed_enhancement(n, I), expected)

def test_lagrangian_disrupt(sample_metric):
    chi, B = 1e-10, 50.0
    h_mu_nu, h_mu_nu_inv = sample_metric
    contraction = np.einsum('ij,ij->', h_mu_nu, h_mu_nu_inv)  # 4 for identity
    expected = -0.5 * chi * B**2 * contraction
    assert np.isclose(lagrangian_disrupt(chi, B, h_mu_nu, h_mu_nu_inv), expected)

def test_rg_beta_chi():
    chi, g, lambda_val = 1e-10, 1.0, 0.1
    expected = -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lambda_val))
    assert np.isclose(rg_beta_chi(chi, g, lambda_val), expected)

def test_source_term(sample_metric):
    chi, B = 1e-10, 50.0
    h_mu_nu, _ = sample_metric
    expected = chi * B**2 * h_mu_nu
    np.testing.assert_allclose(source_term(chi, B, h_mu_nu), expected)

def test_force_vector():
    chi, B = 1e-10, 50.0
    grad_h2 = np.array([1.0, 0.0, 0.0])
    A, rho = 1.0, 1000.0
    expected = chi * B**2 * grad_h2 * A * rho
    np.testing.assert_allclose(force_vector(chi, B, grad_h2, A, rho), expected)

def test_total_thrust():
    N, F, eta, theta = 24, 1000.0, 0.95, 0.0
    expected = N * F * eta * np.cos(np.deg2rad(theta))
    assert np.isclose(total_thrust(N, F, eta, theta), expected)

def test_acceleration():
    T, m = 1000.0, 20000.0
    expected = T / m
    assert np.isclose(acceleration(T, m), expected)

def test_power_consumption():
    I, R, P_eddy = 15.0, 5.0, 100.0
    expected = I**2 * R + P_eddy
    assert np.isclose(power_consumption(I, R, P_eddy), expected)

def test_efficiency():
    T, v, P = 1000.0, 1000.0, 5000.0
    expected = (T * v / P) * 100
    assert np.isclose(efficiency(T, v, P), expected)

def test_range_calc():
    v, E, P = 1000.0, 1.8e9, 5000.0  # Example: 500 kWh = 1.8e9 J
    expected = v * (E / P)
    assert np.isclose(range_calc(v, E, P), expected)

def test_symbolic_surface_field():
    expr = symbolic_surface_field()
    B_r, L, R, d = sp.symbols('B_r L R d')
    expected = (B_r / 2) * (L / sp.sqrt(R**2 + L**2) + (L + d) / sp.sqrt(R**2 + (L + d)**2))
    assert expr == expected

