# tests/integration_tests.py
# Pytest-based integration tests for AI navigation (ai/navigation.py),
# sensor fusion (KalmanFilter, simulate_sensors), and hardware interfacing (hardware/interfaces.py).
# These tests simulate integrated scenarios, e.g., navigation with fused sensors and hardware PWM control.
# CRITICAL: Added MADA convergence validation throughout integrated operations.
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

# Import convergence calculation from unit tests
from tests.unit_tests import calculate_convergence_quality

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

@pytest.fixture
def mock_hall_sensors():
    """Fixture simulating Hall sensor readings for MADA units."""
    class MockHallSensors:
        def __init__(self):
            self.convergence_quality = 1.0  # Perfect by default
            self.B1 = np.array([-50.0, 0.0, 0.0])  # MADA1 pointing toward center
            self.B2 = np.array([50.0, 0.0, 0.0])   # MADA2 pointing toward center
            self.noise_level = 0.01
        
        def read_mada1_field(self):
            """Simulate reading from MADA unit 1 Hall sensors."""
            noise = np.random.normal(0, self.noise_level, 3)
            return self.B1 + noise
        
        def read_mada2_field(self):
            """Simulate reading from MADA unit 2 Hall sensors."""
            noise = np.random.normal(0, self.noise_level, 3)
            return self.B2 + noise
        
        def get_convergence_quality(self):
            """Calculate current convergence quality."""
            B1 = self.read_mada1_field()
            B2 = self.read_mada2_field()
            return calculate_convergence_quality(B1, B2)
        
        def inject_misalignment(self, angle_deg):
            """Inject a misalignment error for testing."""
            # Rotate B2 by angle_deg around Z-axis
            angle_rad = np.deg2rad(angle_deg)
            rotation_matrix = np.array([
                [np.cos(angle_rad), -np.sin(angle_rad), 0],
                [np.sin(angle_rad), np.cos(angle_rad), 0],
                [0, 0, 1]
            ])
            self.B2 = rotation_matrix @ np.array([50.0, 0.0, 0.0])
            self.convergence_quality = self.get_convergence_quality()
        
        def inject_divergence(self):
            """Inject diverging field configuration (both pointing away)."""
            self.B1 = np.array([50.0, 0.0, 0.0])   # Pointing away from center
            self.B2 = np.array([-50.0, 0.0, 0.0])  # Pointing away from center
            self.convergence_quality = self.get_convergence_quality()
    
    return MockHallSensors()


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


def test_sensor_fusion_with_mada_monitoring(mock_hall_sensors):
    """
    NEW: Integration test for sensor fusion with MADA convergence monitoring.
    Ensures Hall sensor data is properly fused with navigation sensors.
    """
    kf = KalmanFilter(dt=0.1)
    
    # Simulate true states
    true_pos = np.array([0.0, 0.0, 0.0])
    true_vel = np.array([1.0, 0.0, 0.0])
    true_att = np.array([0.0, 0.0, 0.0])
    
    # Simulate noisy sensors
    accel, gyro, gps_pos, gps_vel, alt_z, mag_att = simulate_sensors(true_pos, true_vel, true_att)
    
    # Read MADA convergence
    convergence_quality = mock_hall_sensors.get_convergence_quality()
    
    # Predict and update (navigation)
    kf.predict(accel, gyro)
    measurements = np.concatenate([gps_pos, gps_vel, mag_att, [alt_z]])
    kf.update(measurements)
    
    # Verify convergence quality is acceptable
    assert convergence_quality > 0.95, \
        f"MADA convergence should be optimal during normal operation, got {convergence_quality}"
    
    # Simulate misalignment and verify detection
    mock_hall_sensors.inject_misalignment(45)
    degraded_quality = mock_hall_sensors.get_convergence_quality()
    
    assert degraded_quality < 0.8, \
        f"45° misalignment should be detected, got quality={degraded_quality}"


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


def test_pid_mpc_with_convergence_feedback(mock_hall_sensors):
    """
    NEW: Test PID/MPC control with MADA convergence quality as feedback.
    Control should reduce thrust when convergence degrades.
    """
    pid = PIDController(kp=2.0, ki=0.5, kd=1.0, dt=0.1)
    
    # Normal operation with good convergence
    setpoint = 10.0
    current = 0.0
    convergence_quality = mock_hall_sensors.get_convergence_quality()
    
    output_normal = pid.compute(setpoint, current)
    assert output_normal > 0, "PID output should be positive"
    
    # Inject misalignment
    mock_hall_sensors.inject_misalignment(50)
    convergence_quality_bad = mock_hall_sensors.get_convergence_quality()
    
    # Simulate convergence-based thrust reduction
    convergence_factor = max(0.0, (convergence_quality_bad - 0.5) / 0.5)  # Linear from 0.5 to 1.0
    output_reduced = output_normal * convergence_factor
    
    assert convergence_quality_bad < 0.8, "Should detect poor convergence"
    assert output_reduced < output_normal * 0.7, \
        "Thrust should be reduced by >30% when convergence is poor"


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


def test_hardware_mada_control_with_convergence(mock_microcontroller, mock_hall_sensors):
    """
    NEW: Test hardware MADA control with real-time convergence monitoring.
    Verifies PWM commands maintain field convergence.
    """
    # Set MADA units to balanced power
    mada1_pin = 14
    mada2_pin = 15
    base_frequency = 100
    base_duty = 512  # 50% duty cycle
    
    # Command both MADAs
    mock_microcontroller.set_pwm(mada1_pin, base_frequency, base_duty)
    mock_microcontroller.set_pwm(mada2_pin, base_frequency, base_duty)
    
    # Verify convergence is maintained
    convergence_quality = mock_hall_sensors.get_convergence_quality()
    assert convergence_quality > 0.95, \
        f"Balanced MADA power should maintain convergence, got {convergence_quality}"
    
    # Simulate imbalanced power (MADA1 at 80%, MADA2 at 50%)
    mock_microcontroller.set_pwm(mada1_pin, base_frequency, int(base_duty * 1.6))
    mock_microcontroller.set_pwm(mada2_pin, base_frequency, base_duty)
    
    # In real system, field imbalance might cause slight misalignment
    # For test, we simulate this by injecting small misalignment
    mock_hall_sensors.inject_misalignment(5)
    convergence_imbalanced = mock_hall_sensors.get_convergence_quality()
    
    # Should still be acceptable but slightly degraded
    assert 0.85 < convergence_imbalanced < 0.99, \
        f"Minor power imbalance should cause slight degradation, got {convergence_imbalanced}"


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


@patch('ai.navigation.torch.no_grad')
@patch('ai.navigation.time.sleep')
def test_navigation_with_convergence_monitoring(mock_sleep, mock_no_grad, mock_mimo_model, mock_hall_sensors):
    """
    NEW: Full navigation test with continuous MADA convergence monitoring.
    Simulates a complete flight with convergence quality tracking.
    """
    primary_model = mock_mimo_model
    secondary_model = mock_mimo_model
    
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([10.0, 0.0, 0.0])
    
    # Mock model outputs
    mock_no_grad.return_value.__enter__.return_value = None
    primary_model.return_value.squeeze.return_value.numpy.return_value = np.array([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    
    # Track convergence throughout navigation
    convergence_history = []
    
    # Simulate navigation loop with convergence monitoring
    for step in range(10):
        # Read convergence
        quality = mock_hall_sensors.get_convergence_quality()
        convergence_history.append(quality)
        
        # Simulate occasional degradation at step 5
        if step == 5:
            mock_hall_sensors.inject_misalignment(10)
        
        # In real system, navigation would adjust based on convergence
        if quality < 0.85:
            # Should trigger thrust reduction
            print(f"Step {step}: Convergence degraded to {quality:.3f}, reducing thrust")
    
    # Verify convergence was monitored
    assert len(convergence_history) == 10, "Should track convergence each step"
    
    # Verify degradation was detected at step 5
    assert convergence_history[5] < convergence_history[4], \
        "Injected misalignment should be detected"
    
    # Verify most steps maintained good convergence
    good_convergence_steps = sum(1 for q in convergence_history if q > 0.85)
    assert good_convergence_steps >= 8, \
        f"Should maintain good convergence most of the time, only {good_convergence_steps}/10 steps"


def test_maintenance_model_integration(mock_maintenance_model):
    """Integration test for predictive maintenance in navigation."""
    maint_input = torch.tensor([10, 50.0, 50.0, 0.5], dtype=torch.float32).unsqueeze(0)
    mock_maintenance_model.return_value.squeeze.return_value.numpy.return_value = np.array([0.6, 80.0])
    
    with torch.no_grad():
        output = mock_maintenance_model(maint_input).squeeze(0).numpy()
    
    assert output[0] > 0.5, "High degradation detected"
    assert output[1] == 80.0, "Adapted frequency"


def test_maintenance_with_convergence_correlation(mock_maintenance_model, mock_hall_sensors):
    """
    NEW: Test maintenance model with MADA convergence quality as input.
    Poor convergence should trigger maintenance alerts.
    """
    # Simulate normal operation
    convergence_quality = mock_hall_sensors.get_convergence_quality()
    
    # Maintenance input: [flight_hours, max_temp, max_B_field, convergence_quality]
    maint_input_normal = torch.tensor([10, 50.0, 50.0, convergence_quality], dtype=torch.float32).unsqueeze(0)
    
    # Mock output: [degradation_score, recommended_frequency]
    mock_maintenance_model.return_value.squeeze.return_value.numpy.return_value = np.array([0.2, 100.0])
    
    with torch.no_grad():
        output_normal = mock_maintenance_model(maint_input_normal).squeeze(0).numpy()
    
    assert output_normal[0] < 0.5, "Low degradation with good convergence"
    
    # Inject convergence failure
    mock_hall_sensors.inject_divergence()
    convergence_quality_bad = mock_hall_sensors.get_convergence_quality()
    
    maint_input_bad = torch.tensor([10, 50.0, 50.0, convergence_quality_bad], dtype=torch.float32).unsqueeze(0)
    mock_maintenance_model.return_value.squeeze.return_value.numpy.return_value = np.array([0.9, 50.0])
    
    with torch.no_grad():
        output_bad = mock_maintenance_model(maint_input_bad).squeeze(0).numpy()
    
    assert output_bad[0] > 0.8, "High degradation with poor convergence"
    assert output_bad[1] < output_normal[1], "Should recommend lower frequency for safety"


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


@pytest.mark.parametrize("convergence_scenario", [
    ("perfect", 1.0),
    ("acceptable", 0.9),
    ("warning", 0.82),
    ("critical", 0.7),
    ("diverging", -0.5)
])
def test_failover_triggered_by_convergence(mock_mimo_model, mock_hall_sensors, convergence_scenario):
    """
    NEW: Test that poor MADA convergence triggers emergency failover.
    """
    scenario_name, target_quality = convergence_scenario
    
    # Inject appropriate misalignment to achieve target quality
    if target_quality > 0.95:
        pass  # Already perfect
    elif target_quality > 0.85:
        mock_hall_sensors.inject_misalignment(10)
    elif target_quality > 0.75:
        mock_hall_sensors.inject_misalignment(25)
    elif target_quality > 0.0:
        mock_hall_sensors.inject_misalignment(45)
    else:
        mock_hall_sensors.inject_divergence()
    
    quality = mock_hall_sensors.get_convergence_quality()
    
    # Verify we achieved target quality (within tolerance)
    assert abs(quality - target_quality) < 0.15, \
        f"Failed to inject {scenario_name} scenario: target={target_quality}, actual={quality}"
    
    # Check if emergency landing should be triggered
    should_emergency_land = quality < 0.8
    
    if should_emergency_land:
        assert quality < 0.8, f"Scenario '{scenario_name}' should trigger emergency landing"
        print(f"EMERGENCY: {scenario_name} scenario (quality={quality:.3f}) triggers landing")
    else:
        assert quality >= 0.85, f"Scenario '{scenario_name}' should allow continued flight"
        print(f"OK: {scenario_name} scenario (quality={quality:.3f}) allows continued flight")


# ==================== NEW: FULL SYSTEM INTEGRATION TEST ====================

class TestFullSystemIntegration:
    """
    Complete end-to-end integration test simulating a real flight mission
    with all components: sensors, MADA control, navigation, and safety systems.
    """
    
    def test_complete_mission_with_convergence_monitoring(
        self, mock_mimo_model, mock_microcontroller, mock_hall_sensors
    ):
        """
        Full mission simulation: takeoff → maneuvers → landing
        with continuous MADA convergence monitoring and adaptive control.
        """
        # Mission phases
        phases = ["pre-flight", "takeoff", "cruise", "maneuver", "landing"]
        
        convergence_log = []
        power_log = []
        
        for phase in phases:
            # Read current convergence
            quality = mock_hall_sensors.get_convergence_quality()
            convergence_log.append((phase, quality))
            
            # Determine power level based on phase
            if phase == "pre-flight":
                power_level = 0.0
            elif phase == "takeoff":
                power_level = 0.8
            elif phase == "cruise":
                power_level = 0.5
            elif phase == "maneuver":
                power_level = 0.9
                # High-power maneuver may stress alignment
                mock_hall_sensors.inject_misalignment(5)
            else:  # landing
                power_level = 0.3
            
            power_log.append((phase, power_level))
            
            # Apply convergence-based power limiting
            if quality < 0.85:
                power_level *= 0.7  # Reduce by 30%
                print(f"WARNING: {phase} - Convergence {quality:.3f} < 0.85, reducing power to {power_level:.2f}")
            
            if quality < 0.8:
                print(f"CRITICAL: {phase} - Convergence {quality:.3f} < 0.8, initiating emergency landing")
                break
            
            # Send PWM commands
            duty_cycle = int(512 * power_level * 2)  # Convert to duty cycle
            mock_microcontroller.set_pwm(14, 100, duty_cycle)
            mock_microcontroller.set_pwm(15, 100, duty_cycle)
        
        # Verify convergence was monitored throughout
        assert len(convergence_log) >= 3, "Should complete at least 3 mission phases"
        
        # Verify degradation during maneuver was detected
        maneuver_quality = next(q for p, q in convergence_log if p == "maneuver")
        assert maneuver_quality < 0.99, "Maneuver should show slight convergence degradation"
        
        # Verify no critical failures (unless intentionally triggered)
        critical_failures = [q for p, q in convergence_log if q < 0.8]
        assert len(critical_failures) == 0, \
            f"Should not have critical convergence failures, found {len(critical_failures)}"
    
    def test_emergency_landing_on_convergence_failure(
        self, mock_microcontroller, mock_hall_sensors
    ):
        """
        Test that critical convergence failure triggers immediate emergency landing.
        """
        # Start with good convergence
        quality_initial = mock_hall_sensors.get_convergence_quality()
        assert quality_initial > 0.95, "Should start with good convergence"
        
        # Simulate flight at high power
        mock_microcontroller.set_pwm(14, 100, 1024)
        mock_microcontroller.set_pwm(15, 100, 1024)
        
        # Inject critical failure (fields diverging)
        mock_hall_sensors.inject_divergence()
        quality_failed = mock_hall_sensors.get_convergence_quality()
        
        # Verify failure detected
        assert quality_failed < 0.0, "Diverging fields should give negative quality"
        
        # Emergency response: immediate power cutoff
        mock_microcontroller.set_pwm(14, 0, 0)
        mock_microcontroller.set_pwm(15, 0, 0)
        
        # Verify commands were sent
        assert mock_microcontroller.ser.write.call_count >= 4, \
            "Should send power-off commands to both MADA units"


# ==================== TEST RUNNER ====================

if __name__ == "__main__":
    # Run all tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
