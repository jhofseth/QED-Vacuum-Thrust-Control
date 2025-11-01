import pytest
import numpy as np
from unittest.mock import patch
from io import StringIO
from simulations.thrust_model import main
from simulations.equations import (
    opposing_field,
    pulsed_enhancement,
    rg_beta_chi,
    force_vector,
    total_thrust,
    acceleration,
    power_consumption,
    efficiency,
    range_calc
)

# Default values from thrust_model.py
DEFAULT_M1 = 100.0
DEFAULT_M2 = 100.0
DEFAULT_D = 0.05
DEFAULT_K = 1.0
DEFAULT_N_TURNS = 100
DEFAULT_I = 15.0
DEFAULT_CHI = 1e-10
DEFAULT_G = 1.0
DEFAULT_LAMBDA = 0.1
DEFAULT_GRAD_H2 = np.array([1.0, 0.0, 0.0])
DEFAULT_A = 1.0
DEFAULT_RHO = 1000.0
DEFAULT_N_UNITS = 24
DEFAULT_ETA = 0.95
DEFAULT_THETA = 0.0
DEFAULT_MASS = 20000.0
DEFAULT_R = 5.0
DEFAULT_P_EDDY = 100.0
DEFAULT_V = 1000.0
DEFAULT_E = 500000.0 * 3600  # 500 kWh in J

def test_opposing_field_calc():
    expected = opposing_field(DEFAULT_M1, DEFAULT_M2, DEFAULT_D, DEFAULT_K)
    assert expected > 0  # Basic sanity

def test_pulsed_enhancement_scaling():
    freq = 100.0
    scaled_I = DEFAULT_I * (freq / 50.0)
    expected = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
    assert expected > pulsed_enhancement(DEFAULT_N_TURNS, DEFAULT_I)

def test_rg_beta_chi_in_model():
    expected = rg_beta_chi(DEFAULT_CHI, DEFAULT_G, DEFAULT_LAMBDA)
    assert np.isclose(expected, -4 * DEFAULT_CHI + (DEFAULT_G / (2 * np.pi)) * (DEFAULT_CHI / (1 - 2 * DEFAULT_LAMBDA)))

def test_force_vector_in_model():
    B = 50.0
    expected_vec = force_vector(DEFAULT_CHI, B, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
    expected_mag = np.linalg.norm(expected_vec)
    assert np.isclose(expected_mag, DEFAULT_CHI * B**2 * np.linalg.norm(DEFAULT_GRAD_H2) * DEFAULT_A * DEFAULT_RHO)

def test_total_thrust_in_model():
    F_mag = 1000.0  # Example
    expected = total_thrust(DEFAULT_N_UNITS, F_mag, DEFAULT_ETA, DEFAULT_THETA)
    assert np.isclose(expected, DEFAULT_N_UNITS * F_mag * DEFAULT_ETA * np.cos(np.deg2rad(DEFAULT_THETA)))

def test_acceleration_in_model():
    T = 1000.0
    expected = acceleration(T, DEFAULT_MASS)
    assert np.isclose(expected, T / DEFAULT_MASS)

def test_power_consumption_in_model():
    freq = 100.0
    scaled_I = DEFAULT_I * (freq / 50.0)
    expected = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
    assert np.isclose(expected, scaled_I**2 * DEFAULT_R + DEFAULT_P_EDDY)

def test_efficiency_in_model():
    T, P = 1000.0, 5000.0
    expected = efficiency(T, DEFAULT_V, P)
    assert np.isclose(expected, (T * DEFAULT_V / P) * 100)

def test_range_calc_in_model():
    P = 5000.0
    expected = range_calc(DEFAULT_V, DEFAULT_E, P)
    assert np.isclose(expected, DEFAULT_V * (DEFAULT_E / P))

@patch('sys.stdout', new_callable=StringIO)
@patch('argparse.ArgumentParser.parse_args')
def test_main_output(mock_args, mock_stdout):
    # Mock args
    mock_args.return_value = argparse.Namespace(b_opposing=50.0, frequency=100.0)
    
    main()
    
    output = mock_stdout.getvalue()
    assert "Thrust Model Simulation" in output
    assert "B_opposing = 50.0 T" in output
    assert "Frequency = 100.0 Hz" in output
    assert "Total Thrust" in output
    assert "Acceleration" in output
    assert "Estimated Range" in output

@patch('argparse.ArgumentParser.parse_args')
def test_main_with_default_b_opposing(mock_args):
    mock_args.return_value = argparse.Namespace(b_opposing=None, frequency=50.0)
    
    # Should compute B_opposing internally
    # No assert, just ensure no crash (integration test)
    main()

