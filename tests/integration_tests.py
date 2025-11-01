# tests/integration_tests.py
# Pytest-based integration tests for AI navigation (ai/navigation.py),
# sensor fusion (KalmanFilter, simulate_sensors), and hardware interfacing (hardware/interfaces.py).
# These tests simulate integrated scenarios, e.g., navigation with fused sensors and hardware PWM control.
# Uses mocking for hardware to avoid real dependencies.

import sys
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.navigation import (
    KalmanFilter,
    simulate_sensors,
    PIDController,
    mpc_control,
    simulate_navigation,
    MIMONetwork,
    MaintenanceNN
)
from hardware.interfaces import (
    FlightControllerInterface,
    MicrocontrollerPWMInterface,
    RealTimeControlNode
)
import torch

# Fixtures for models and interfaces
@pytest.fixture
def mock_mimo_model():
    """Fixture for a mock MIMONetwork model."""
    model = MIMONetwork()
    model.eval()
    return model

@pytest.fixture
def mock_maintenance_model():
    """Fixture for a mock MaintenanceNN model."""
    model = MaintenanceNN()
    model.eval()
    return model

@pytest.fixture
def mock_flight_controller():
    """Fixture mocking FlightControllerInterface."""
    with patch('hardware.interfaces.mavutil') as mock_mav:
        mock_conn = MagicMock()
        mock_mav.mavlink_connection.return_value = mock_conn
        mock_conn.wait_heartbeat.return_value = None
        fc = FlightControllerInterface()
        return fc

@pytest.fixture
def mock_microcontroller():
    """Fixture mocking MicrocontrollerPWMInterface."""
    with patch('hardware.interfaces.serial') as mock_ser:
        mock_serial = MagicMock()
        mock_ser.Serial.return_value = mock_serial
        mock_serial.readline.return_value = b'OK'
        mcu = MicrocontrollerPWMInterface()
        return mcu

@pytest.fixture
def mock_ros_node():
    """Fixture mocking RealTimeControlNode (ROS2)."""
    with patch('hardware.interfaces.rclpy') as mock_rclpy:
        mock_rclpy.init.return_value = None
        mock_rclpy.spin.return_value = None
        mock_rclpy.shutdown.return_value = None
        node = RealTimeControlNode(loop_period=0.01)
        return node

def test_sensor_fusion_integration():
    """Integration test for sensor fusion with KalmanFilter."""
    kf = KalmanFilter(dt=0.1)
    
    # Simulate true states
    true_pos = np.array([0.0, 0.0, 0.0])
    true_vel = np.array([1.0, 0.0, 0.0])
    true_att = np.array([0.0, 0.0, 0.0])
    
    # Simulate noisy sensors
    accel, gyro, gps_pos, gps_vel, alt_z, mag_att = simulate_sensors(true_pos, true_vel, true_att)
    
    # Predict and update
    kf.predict(accel, gyro)
    measurements = np.concatenate([gps_pos, gps_vel, mag_att, [alt_z]])
    kf.update(measurements)
    
    # Check fused state close to true
    assert np.allclose(kf.x[:3], true_pos, atol=1.0), "Fused position mismatch"
    assert np.allclose(kf.x[3:6], true_vel, atol=0.5), "Fused velocity mismatch"
    assert np.allclose(kf.x[6:9], true_att, atol=0.1), "Fused attitude mismatch"

def test_pid_mpc_integration():
    """Integration test for PID and MPC in control loop."""
    pid = PIDController(kp=2.0, ki=0.5, kd=1.0, dt=0.1)
    
    # Simulate control
    setpoint = 10.0
    current = 0.0
    output = pid.compute(setpoint, current)
    assert output > 0, "PID output should be positive for positive error"
    
    # MPC
    current_state = np.array([0.0] * 6)
    target_state = np.array([10.0] * 3 + [0.0] * 3)
    u = mpc_control(current_state, target_state)
    assert len(u) == 6, "MPC output should be 6D"
    assert np.all(u > current_state), "MPC should move towards target"

def test_hardware_interfacing_integration(mock_flight_controller, mock_microcontroller, mock_ros_node):
    """Integration test for hardware interfaces working together."""
    # Test flight controller commands
    mock_flight_controller.arm_vehicle()
    mock_flight_controller.master.mav.command_long_send.assert_called()
    
    mock_flight_controller.send_rc_override([1500] * 8)
    mock_flight_controller.master.mav.rc_channels_override_send.assert_called()
    
    # Test microcontroller PWM
    mock_microcontroller.set_pwm(14, 100, 512)
    mock_microcontroller.ser.write.assert_called_with(b'PWM:14:100:512\n')
    
    mock_microcontroller.pulse_mada(14, frequency=100, bursts=5)
    assert mock_microcontroller.ser.write.call_count >= 10  # On/off per burst
    
    # Test ROS node (mocked spin)
    assert mock_ros_node.timer is not None, "ROS timer should be created"

@patch('ai.navigation.torch.no_grad')
@patch('ai.navigation.time.sleep')
def test_navigation_integration(mock_sleep, mock_no_grad, mock_mimo_model):
    """Integration test for full navigation simulation with sensor fusion, models, and fail-safes."""
    primary_model = mock_mimo_model
    secondary_model = mock_mimo_model  # Same for test
    
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([10.0, 0.0, 0.0])
    
    # Mock model outputs
    mock_no_grad.return_value.__enter__.return_value = None
    primary_model.return_value.squeeze.return_value.numpy.return_value = np.array([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    
    trajectory, velocities, controls = simulate_navigation(
        primary_model, secondary_model, start_pos, start_vel, target_pos
    )
    
    assert len(trajectory) > 1, "Trajectory should have multiple points"
    assert np.linalg.norm(trajectory[-1] - target_pos) < 5.0, "Should approach target"  # Loose tol for mock

def test_maintenance_model_integration(mock_maintenance_model):
    """Integration test for predictive maintenance in navigation."""
    maint_input = torch.tensor([10, 50.0, 50.0, 0.5], dtype=torch.float32).unsqueeze(0)
    mock_maintenance_model.return_value.squeeze.return_value.numpy.return_value = np.array([0.6, 80.0])
    
    with torch.no_grad():
        output = mock_maintenance_model(maint_input).squeeze(0).numpy()
    
    assert output[0] > 0.5, "High degradation detected"
    assert output[1] == 80.0, "Adapted frequency"

@pytest.mark.parametrize("fail_primary", [False, True])
def test_failover_integration(mock_mimo_model, fail_primary):
    """Test model failover in navigation."""
    primary_model = mock_mimo_model
    secondary_model = mock_mimo_model
    
    if fail_primary:
        primary_model.side_effect = Exception("Model failure")
    
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([10.0, 0.0, 0.0])
    
    trajectory, _, _ = simulate_navigation(primary_model, secondary_model, start_pos, start_vel, target_pos)
    
    assert len(trajectory) > 1, "Navigation should continue with/without failover"
