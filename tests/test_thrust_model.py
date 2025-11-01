import pytest
import numpy as np
import argparse
import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


class TestEquationsInModel:
    """Test equation functions used in thrust model."""
    
    def test_opposing_field_calc(self):
        """Test opposing field calculation returns positive value."""
        result = opposing_field(DEFAULT_M1, DEFAULT_M2, DEFAULT_D, DEFAULT_K)
        assert result > 0, "Opposing field should be positive"
        assert np.isfinite(result), "Opposing field should be finite"
    
    def test_pulsed_enhancement_scaling(self):
        """Test that pulsed enhancement scales with frequency."""
        freq_low = 50.0
        freq_high = 100.0
        
        scaled_I_low = DEFAULT_I * (freq_low / 50.0)
        scaled_I_high = DEFAULT_I * (freq_high / 50.0)
        
        result_low = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I_low)
        result_high = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I_high)
        
        assert result_high > result_low, \
            "Higher frequency should produce greater enhancement"
        assert np.isclose(result_high, 2 * result_low), \
            "Enhancement should scale linearly with frequency"
    
    def test_rg_beta_chi_in_model(self):
        """Test RG beta chi calculation with model parameters."""
        result = rg_beta_chi(DEFAULT_CHI, DEFAULT_G, DEFAULT_LAMBDA)
        expected = -4 * DEFAULT_CHI + (DEFAULT_G / (2 * np.pi)) * \
                   (DEFAULT_CHI / (1 - 2 * DEFAULT_LAMBDA))
        assert np.isclose(result, expected), \
            f"Expected {expected}, got {result}"
    
    def test_force_vector_in_model(self):
        """Test force vector calculation in model context."""
        B = 50.0
        result_vec = force_vector(DEFAULT_CHI, B, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
        result_mag = np.linalg.norm(result_vec)
        
        expected_mag = DEFAULT_CHI * B**2 * np.linalg.norm(DEFAULT_GRAD_H2) * \
                       DEFAULT_A * DEFAULT_RHO
        
        assert np.isclose(result_mag, expected_mag), \
            f"Force magnitude mismatch: expected {expected_mag}, got {result_mag}"
        assert result_vec.shape == (3,), "Force should be 3D vector"
    
    def test_total_thrust_in_model(self):
        """Test total thrust calculation."""
        F_mag = 1000.0
        result = total_thrust(DEFAULT_N_UNITS, F_mag, DEFAULT_ETA, DEFAULT_THETA)
        expected = DEFAULT_N_UNITS * F_mag * DEFAULT_ETA * \
                   np.cos(np.deg2rad(DEFAULT_THETA))
        assert np.isclose(result, expected), \
            f"Expected {expected}, got {result}"
    
    def test_acceleration_in_model(self):
        """Test acceleration calculation."""
        T = 1000.0
        result = acceleration(T, DEFAULT_MASS)
        expected = T / DEFAULT_MASS
        assert np.isclose(result, expected), \
            f"Expected {expected}, got {result}"
        
        # Check units make sense
        a_in_g = result / 9.81
        assert a_in_g > 0, "Acceleration should be positive"
    
    def test_power_consumption_in_model(self):
        """Test power consumption with scaled current."""
        freq = 100.0
        scaled_I = DEFAULT_I * (freq / 50.0)
        result = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
        expected = scaled_I**2 * DEFAULT_R + DEFAULT_P_EDDY
        assert np.isclose(result, expected), \
            f"Expected {expected}, got {result}"
    
    def test_efficiency_in_model(self):
        """Test efficiency calculation."""
        T, P = 1000.0, 5000.0
        result = efficiency(T, DEFAULT_V, P)
        expected = (T * DEFAULT_V / P) * 100
        assert np.isclose(result, expected), \
            f"Expected {expected}%, got {result}%"
    
    def test_range_calc_in_model(self):
        """Test range calculation."""
        P = 5000.0
        result = range_calc(DEFAULT_V, DEFAULT_E, P)
        expected = DEFAULT_V * (DEFAULT_E / P)
        assert np.isclose(result, expected), \
            f"Expected {expected}m, got {result}m"
        
        # Check range is reasonable
        range_km = result / 1000.0
        assert range_km > 100, "Range should be over 100 km"


class TestMainFunction:
    """Test main function behavior with different arguments."""
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--b_opposing', '50.0', '--frequency', '100.0'])
    def test_main_output_provided_b_opposing(self, mock_stdout):
        """Test main function output with provided B_opposing."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Check for key output sections
        assert "QED VACUUM THRUST MODEL SIMULATION" in output, \
            "Missing main header"
        assert "Input Parameters" in output, "Missing input parameters section"
        assert "MAGNETIC FIELD CALCULATIONS" in output, \
            "Missing magnetic field section"
        assert "FORCE & THRUST CALCULATIONS" in output, \
            "Missing force/thrust section"
        assert "PERFORMANCE METRICS" in output, "Missing performance metrics"
        assert "Opposing Field" in output, "Missing opposing field value"
        assert "Total Thrust" in output, "Missing total thrust"
        assert "Acceleration" in output, "Missing acceleration"
        assert "SIMULATION COMPLETE" in output, "Missing completion message"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--frequency', '50.0'])
    def test_main_with_default_b_opposing(self, mock_stdout):
        """Test main function with calculated B_opposing (not provided)."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Should compute B_opposing internally
        assert "Opposing Field" in output, "Should show computed opposing field"
        assert "SIMULATION COMPLETE" in output, "Should complete successfully"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--b_opposing', '20.0', 
                        '--frequency', '200.0', '--mass', '10000.0'])
    def test_main_with_custom_parameters(self, mock_stdout):
        """Test main function with custom parameters."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Check that custom values appear
        assert "10000.0 kg" in output or "10000 kg" in output, \
            "Custom mass should appear in output"
        assert "200" in output, "Custom frequency should appear"
        assert "SIMULATION COMPLETE" in output, "Should complete successfully"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--verbose'])
    def test_main_verbose_mode(self, mock_stdout):
        """Test main function with verbose output."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Verbose mode should show additional details
        assert "QUANTUM PARAMETERS" in output or "Susceptibility" in output, \
            "Verbose mode should show quantum parameters"
        assert "SIMULATION COMPLETE" in output, "Should complete successfully"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--n_units', '48', '--mass', '15000'])
    def test_main_with_different_units_and_mass(self, mock_stdout):
        """Test main function with different number of units and mass."""
        main()
        
        output = mock_stdout.getvalue()
        
        assert "48" in output, "Custom n_units should appear"
        assert "15000" in output, "Custom mass should appear"
        assert "SIMULATION COMPLETE" in output, "Should complete successfully"
    
    @patch('sys.argv', ['thrust_model.py', '--help'])
    def test_main_help_message(self):
        """Test that help message works."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        # argparse exits with 0 for --help
        assert exc_info.value.code == 0, "Help should exit cleanly"


class TestIntegrationScenarios:
    """Integration tests for complete simulation scenarios."""
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--b_opposing', '50', '--frequency', '100'])
    def test_standard_operation_scenario(self, mock_stdout):
        """Test standard operation scenario."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Verify all major calculations present
        assert "Opposing Field" in output
        assert "Pulsed Enhancement" in output
        assert "Total Magnetic Field" in output
        assert "Force per Unit" in output
        assert "Total Thrust" in output
        assert "Acceleration" in output
        assert "Power Consumption" in output
        assert "System Efficiency" in output
        assert "Estimated Range" in output
        assert "Time to Mach 26" in output
        assert "Thrust-to-Weight Ratio" in output
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--b_opposing', '100', 
                        '--frequency', '500', '--n_units', '32'])
    def test_high_performance_scenario(self, mock_stdout):
        """Test high performance scenario with increased parameters."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Should complete without errors
        assert "SIMULATION COMPLETE" in output
        
        # Check for reasonable values (not NaN or inf)
        assert "nan" not in output.lower()
        assert "inf" not in output.lower()
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--b_opposing', '10', 
                        '--frequency', '50', '--mass', '50000'])
    def test_low_performance_scenario(self, mock_stdout):
        """Test low performance scenario with reduced parameters."""
        main()
        
        output = mock_stdout.getvalue()
        
        # Should still complete successfully
        assert "SIMULATION COMPLETE" in output
        assert "nan" not in output.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--b_opposing', '1', '--frequency', '1'])
    def test_minimal_parameters(self, mock_stdout):
        """Test with minimal parameter values."""
        main()
        
        output = mock_stdout.getvalue()
        assert "SIMULATION COMPLETE" in output
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['thrust_model.py', '--current', '0.1'])
    def test_low_current(self, mock_stdout):
        """Test with very low current."""
        main()
        
        output = mock_stdout.getvalue()
        assert "SIMULATION COMPLETE" in output
        
        # Power consumption should be very low
        assert "Power Consumption" in output


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
