# Flight Control Tutorial: Real-Time Systems, PID/MPC, and Safety

## Introduction

This comprehensive tutorial guides you through implementing real-time flight control systems for RVG (Refractive Vacuum Gravity) Unified Field Propulsion drones. Topics covered:

- **Real-time control loops**: Low-latency (1-10 ms) response systems
- **PID controllers**: Basic stabilization for 6DOF
- **Model Predictive Control (MPC)**: Advanced trajectory optimization
- **Safety features**: Fail-safes, thermal management, redundancy
- **Sensor fusion**: Kalman filtering for state estimation
- **MADA convergence monitoring**: Essential for Master Equation thrust via Θ_dilaton

**Integration**: This tutorial connects `ai/navigation.py` (control algorithms), `hardware/interfaces.py` (hardware I/O), and `simulations/thrust_model.py` (RVG physics validation).

**Prerequisites**:
- Assembled prototype with integrated sensors (see Hardware Setup Guide)
- Python 3.12+ environment
- ROS2 Humble or later (optional but recommended)
- Basic control theory knowledge
- Understanding of the Master Equation of Levitation: F = ∫(Θ_dilaton(B)·∇B²)dV

---

## Table of Contents

1. [Real-Time Control Systems](#1-real-time-control-systems)
2. [PID Controllers](#2-pid-controllers)
3. [Model Predictive Control (MPC)](#3-model-predictive-control-mpc)
4. [Sensor Fusion with Kalman Filtering](#4-sensor-fusion-with-kalman-filtering)
5. [Safety Features](#5-safety-features)
6. [Testing and Validation](#6-testing-and-validation)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Real-Time Control Systems

Real-time systems ensure deterministic, low-latency responses critical for stable flight. Target loop rates: 100-1000 Hz (1-10 ms periods).

### 1.1 System Architecture

```
┌─────────────┐    I2C     ┌──────────┐
│  IMU Sensor │◄──────────►│          │
└─────────────┘            │          │
                           │  ESP32   │    PWM    ┌─────────────┐
┌─────────────┐   Analog   │    or    │◄─────────►│ MOSFET      │
│ Hall Sensor │◄──────────►│  Flight  │           │ Drivers     │
└─────────────┘            │Controller│           └─────────────┘
                           │          │                  │
┌─────────────┐   MAVLink  │          │                  ▼
│     GPS     │◄──────────►│          │           ┌─────────────┐
└─────────────┘            └──────────┘           │ MADA Coils  │
                                  │                └─────────────┘
                                  │ ROS2/Serial
                                  ▼
                           ┌──────────────┐
                           │ Control Node │
                           │(Python/ROS2) │
                           └──────────────┘
```

### 1.2 Setup ROS2 Real-Time Node

**Install ROS2 (Ubuntu/Debian)**:

```bash
# Add ROS2 repository
sudo apt update && sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl gnupg lsb-release

# Add ROS2 GPG key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop python3-colcon-common-extensions

# Source setup
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 1.3 Create Control Node

**File: `control/drone_control_node.py`**

```python
#!/usr/bin/env python3
"""
Real-time drone control node for QED vacuum propulsion.
Integrates PID, MPC, and sensor fusion.
"""

import rclpy
from rclpy.node import Node
import numpy as np
from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
from ai.navigation import PIDController, KalmanFilter, mpc_control

class DroneControlNode(Node):
    """Real-time control node with 5ms loop (200 Hz)."""
    
    def __init__(self):
        super().__init__('qed_drone_control')
        
        # Control parameters
        self.loop_rate = 200  # Hz
        self.dt = 1.0 / self.loop_rate
        
        # Initialize hardware interfaces
        try:
            self.mcu = MicrocontrollerPWMInterface(port='/dev/ttyUSB0')
            self.fc = FlightControllerInterface()
            self.get_logger().info("✓ Hardware interfaces initialized")
        except Exception as e:
            self.get_logger().error(f"Hardware init failed: {e}")
            raise
        
        # Initialize Kalman filter for sensor fusion
        self.kf = KalmanFilter(dt=self.dt)
        
        # Initialize PID controllers (3 position + 3 attitude)
        self.pids = [
            PIDController(kp=2.0, ki=0.5, kd=1.0, dt=self.dt) 
            for _ in range(6)
        ]
        
        # State variables
        self.target_pos = np.array([0.0, 0.0, 5.0])  # Hover at 5m
        self.target_att = np.zeros(3)
        self.mpc_counter = 0
        
        # Safety limits
        self.max_temp = 100.0  # °C
        self.temp_warning = 90.0  # °C
        self.current_temp = 25.0
        
        # Create timer for control loop
        self.timer = self.create_timer(self.dt, self.control_loop_callback)
        
        self.get_logger().info(f"✓ Control node started: {self.loop_rate}Hz")
    
    def control_loop_callback(self):
        """Main control loop - executes every 5ms (200 Hz)."""
        
        try:
            # 1. Read sensors
            imu_data = self.read_imu()
            gps_data = self.read_gps()
            hall_data = self.read_hall_sensors()
            temp_data = self.read_temperature()
            
            # 2. Sensor fusion (Kalman filter)
            self.kf.predict(imu_data['accel'], imu_data['gyro'])
            measurements = np.concatenate([
                gps_data['pos'],
                gps_data['vel'],
                imu_data['att'],
                [temp_data['altitude']]
            ])
            self.kf.update(measurements)
            
            # Extract fused state
            fused_pos = self.kf.x[0:3]
            fused_vel = self.kf.x[3:6]
            fused_att = self.kf.x[6:9]
            
            # 3. Compute control using PID
            pos_error = self.target_pos - fused_pos
            att_error = self.target_att - fused_att
            
            # PID outputs for each axis
            pid_outputs = np.array([
                self.pids[i].compute(self.target_pos[i], fused_pos[i]) 
                for i in range(3)
            ] + [
                self.pids[i+3].compute(self.target_att[i], fused_att[i]) 
                for i in range(3)
            ])
            
            # 4. Optional: MPC optimization (every 10 cycles for efficiency)
            if self.mpc_counter % 10 == 0:
                current_state = np.concatenate([fused_pos, fused_att])
                target_state = np.concatenate([self.target_pos, self.target_att])
                mpc_output = mpc_control(current_state, target_state, horizon=5)
                # Blend MPC with PID (70% MPC, 30% PID)
                control = 0.7 * mpc_output + 0.3 * pid_outputs
            else:
                control = pid_outputs
            
            self.mpc_counter += 1
            
            # 5. Safety checks
            self.current_temp = temp_data['coil_temp']
            if not self.check_safety():
                self.emergency_shutdown()
                return
            
            # 6. Apply control to hardware
            self.apply_control(control, hall_data['b_field'])
            
            # 7. Logging (sparse to avoid overhead)
            if self.mpc_counter % 200 == 0:  # Every second
                self.log_status(fused_pos, fused_vel, control)
        
        except Exception as e:
            self.get_logger().error(f"Control loop error: {e}")
            self.emergency_shutdown()
    
    def read_imu(self):
        """Read IMU data (accelerometer + gyroscope)."""
        # Interface with MPU-6050 or similar via I2C
        # Placeholder - implement actual I2C read
        return {
            'accel': np.random.normal(0, 0.01, 3),
            'gyro': np.random.normal(0, 0.005, 3),
            'att': np.random.normal(0, 0.01, 3)
        }
    
    def read_gps(self):
        """Read GPS position and velocity."""
        # Interface with GPS module
        return {
            'pos': np.random.normal([0, 0, 5], 1.0, 3),
            'vel': np.random.normal(0, 0.1, 3)
        }
    
    def read_hall_sensors(self):
        """Read Hall effect sensors for B-field monitoring."""
        # Read from analog pins via ADC
        return {
            'b_field': 50.0 + np.random.normal(0, 2.0)
        }
    
    def read_temperature(self):
        """Read temperature sensors."""
        return {
            'coil_temp': 25.0 + np.random.normal(0, 5.0),
            'altitude': 5.0 + np.random.normal(0, 0.5)
        }
    
    def check_safety(self):
        """Perform safety checks."""
        # Thermal check
        if self.current_temp > self.max_temp:
            self.get_logger().error(f"CRITICAL: Temperature {self.current_temp}°C > {self.max_temp}°C")
            return False
        
        if self.current_temp > self.temp_warning:
            self.get_logger().warn(f"WARNING: High temperature {self.current_temp}°C")
            # Reduce power by 10%
            # Implementation: reduce PWM duty cycle
        
        return True
    
    def apply_control(self, control, b_field):
        """Apply control outputs to MADA coils."""
        # Convert control vector to PWM signals
        # control[:3] = position thrust components
        # control[3:] = attitude adjustments
        
        # Calculate required field strength
        target_b = 50.0 + np.linalg.norm(control[:3]) * 0.1
        
        # Apply to coils via PWM
        for pin in range(24):  # 24 MADA units
            frequency = 100.0  # Hz baseline
            duty_cycle = int((target_b / 60.0) * 1023)  # Scale to 0-1023
            
            try:
                self.mcu.set_pwm(pin + 12, frequency, duty_cycle)  # GPIO 12-35
            except Exception as e:
                self.get_logger().error(f"PWM error on pin {pin}: {e}")
    
    def emergency_shutdown(self):
        """Emergency shutdown procedure."""
        self.get_logger().error("EMERGENCY SHUTDOWN INITIATED")
        
        # Disable all PWM outputs
        try:
            self.mcu.emergency_stop()
        except:
            pass
        
        # Disarm flight controller
        try:
            self.fc.disarm_vehicle(force=True)
        except:
            pass
        
        # Stop node
        self.destroy_node()
        rclpy.shutdown()
    
    def log_status(self, pos, vel, control):
        """Log system status (sparse)."""
        self.get_logger().info(
            f"Pos: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]m  "
            f"Vel: {np.linalg.norm(vel):.2f}m/s  "
            f"Temp: {self.current_temp:.1f}°C"
        )

def main(args=None):
    rclpy.init(args=args)
    node = DroneControlNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### 1.4 Test Latency

**Verify loop timing**:

```bash
# Run control node
ros2 run qed_control drone_control_node

# Monitor in another terminal
ros2 topic hz /drone_status
```

**Expected output**: ~200 Hz (5ms periods)

---

## 2. PID Controllers

PID provides basic stabilization by correcting errors in position and attitude.

### 2.1 PID Theory

$$u(t) = K_p e(t) + K_i \int e(t)dt + K_d \frac{de(t)}{dt}$$

Where:
- **Kp** (Proportional): Immediate response to current error
- **Ki** (Integral): Eliminates steady-state offset
- **Kd** (Derivative): Dampens oscillations

### 2.2 Tuning Guidelines

**Start with conservative values**:

| Axis | Kp | Ki | Kd | Notes |
|------|----|----|----|-|
| Position X/Y | 2.0 | 0.5 | 1.0 | Horizontal stabilization |
| Position Z | 3.0 | 0.8 | 1.5 | Altitude hold (gravity) |
| Roll/Pitch | 4.0 | 0.3 | 2.0 | Attitude stabilization |
| Yaw | 2.5 | 0.2 | 1.0 | Heading hold |

**Tuning procedure**:

1. **Set Ki=0, Kd=0**: Start with P-only control
2. **Increase Kp**: Until system responds quickly but oscillates
3. **Add Kd**: To dampen oscillations
4. **Add Ki**: To eliminate steady-state error (use sparingly)
5. **Fine-tune**: Adjust all gains for smooth, stable response

### 2.3 Implementation Example

```python
from ai.navigation import PIDController
import numpy as np

# Create PID controllers for 6DOF
dt = 0.005  # 5ms control loop

pid_x = PIDController(kp=2.0, ki=0.5, kd=1.0, dt=dt, output_limit=10.0)
pid_y = PIDController(kp=2.0, ki=0.5, kd=1.0, dt=dt, output_limit=10.0)
pid_z = PIDController(kp=3.0, ki=0.8, kd=1.5, dt=dt, output_limit=15.0)
pid_roll = PIDController(kp=4.0, ki=0.3, kd=2.0, dt=dt, output_limit=5.0)
pid_pitch = PIDController(kp=4.0, ki=0.3, kd=2.0, dt=dt, output_limit=5.0)
pid_yaw = PIDController(kp=2.5, ki=0.2, kd=1.0, dt=dt, output_limit=3.0)

pids = [pid_x, pid_y, pid_z, pid_roll, pid_pitch, pid_yaw]

# In control loop
target_pos = np.array([0, 0, 5])  # Hover at 5m
target_att = np.array([0, 0, 0])  # Level flight

# Compute PID outputs
pid_outputs = np.array([
    pids[0].compute(target_pos[0], current_pos[0]),
    pids[1].compute(target_pos[1], current_pos[1]),
    pids[2].compute(target_pos[2], current_pos[2]),
    pids[3].compute(target_att[0], current_att[0]),
    pids[4].compute(target_att[1], current_att[1]),
    pids[5].compute(target_att[2], current_att[2])
])
```

### 2.4 Testing PID

**Simulation test**:

```bash
# Run navigation simulation with PID
python ai/navigation.py
```

**Hardware test** (tethered):

1. Secure drone with tether (safety line)
2. Start control node: `ros2 run qed_control drone_control_node`
3. Set target: Hover at 1m altitude
4. Observe response and oscillations
5. Adjust gains iteratively

**Plot PID performance**:

```python
import matplotlib.pyplot as plt

# Log error and output over time
plt.figure(figsize=(12, 6))
plt.subplot(2, 1, 1)
plt.plot(time, error, label='Error')
plt.ylabel('Position Error (m)')
plt.legend()
plt.subplot(2, 1, 2)
plt.plot(time, pid_output, label='PID Output')
plt.xlabel('Time (s)')
plt.ylabel('Control Output')
plt.legend()
plt.show()
```

---

## 3. Model Predictive Control (MPC)

MPC optimizes control over a prediction horizon, enabling complex trajectories and constraint handling.

### 3.1 MPC Theory

MPC solves an optimization problem at each time step:

$$\min_{u} \sum_{k=0}^{N} ||x_k - x_{ref}||^2_Q + ||u_k||^2_R$$

Subject to:
- Dynamics: $x_{k+1} = f(x_k, u_k)$
- Constraints: $u_{min} \leq u_k \leq u_{max}$

### 3.2 Implementation

The `ai/navigation.py` module includes a basic MPC function:

```python
from ai.navigation import mpc_control
import numpy as np

# Current and target states [pos_x, pos_y, pos_z, roll, pitch, yaw]
current_state = np.array([0, 0, 4.5, 0.1, -0.05, 0])
target_state = np.array([0, 0, 5.0, 0, 0, 0])

# Compute optimal control (6DOF)
optimal_control = mpc_control(current_state, target_state, horizon=5)

# optimal_control contains [thrust_x, thrust_y, thrust_z, torque_roll, torque_pitch, torque_yaw]
```

### 3.3 Advanced MPC with Constraints

For production use, implement full MPC with constraints:

```python
import scipy.optimize as opt

def mpc_with_constraints(current_state, target_state, horizon=10):
    """
    MPC with thrust and rate constraints.
    """
    n_states = 6
    n_controls = 6
    
    def cost_function(u_sequence):
        # Reshape control sequence
        u_seq = u_sequence.reshape((horizon, n_controls))
        
        # Simulate forward
        x = current_state.copy()
        total_cost = 0
        
        for k in range(horizon):
            # State update (simplified dynamics)
            x = x + u_seq[k] * 0.01  # dt = 0.01
            
            # State cost
            state_error = x - target_state
            total_cost += np.sum(state_error**2) * 10  # Q matrix
            
            # Control effort cost
            total_cost += np.sum(u_seq[k]**2) * 0.1  # R matrix
        
        return total_cost
    
    # Initial guess (zero control)
    u0 = np.zeros(horizon * n_controls)
    
    # Constraints: thrust limits
    bounds = [(-10, 10)] * (horizon * n_controls)
    
    # Optimize
    result = opt.minimize(
        cost_function,
        u0,
        method='SLSQP',
        bounds=bounds,
        options={'maxiter': 50}
    )
    
    # Return first control action
    optimal_u = result.x[:n_controls]
    return optimal_u
```

### 3.4 Hybrid PID-MPC Control

Combine PID (fast, stable) with MPC (optimal, predictive):

```python
# Fast inner loop: PID at 200 Hz
pid_output = compute_pid(error)

# Slow outer loop: MPC at 20 Hz (every 10 cycles)
if cycle_count % 10 == 0:
    mpc_output = mpc_with_constraints(state, target)
    mpc_reference = mpc_output
else:
    # Hold previous MPC output
    pass

# Blend: MPC provides reference, PID tracks it
final_control = pid_output + 0.3 * (mpc_reference - pid_output)
```

---

## 4. Sensor Fusion with Kalman Filtering

Kalman filtering combines noisy sensor data (IMU, GPS, altimeter) into optimal state estimates.

### 4.1 Kalman Filter Usage

Already implemented in `ai/navigation.py`:

```python
from ai.navigation import KalmanFilter
import numpy as np

# Initialize filter
kf = KalmanFilter(dt=0.005)  # 5ms timestep

# In control loop:
while True:
    # 1. Prediction step (using IMU)
    imu_accel = read_accelerometer()  # [ax, ay, az]
    imu_gyro = read_gyroscope()       # [wx, wy, wz]
    kf.predict(imu_accel, imu_gyro)
    
    # 2. Update step (using GPS, altimeter, magnetometer)
    gps_pos = read_gps()              # [x, y, z]
    gps_vel = read_gps_velocity()     # [vx, vy, vz]
    mag_att = read_magnetometer()     # [roll, pitch, yaw]
    altimeter_z = read_altimeter()    # z position
    
    measurements = np.concatenate([gps_pos, gps_vel, mag_att, [altimeter_z]])
    kf.update(measurements)
    
    # 3. Extract fused state
    fused_position = kf.x[0:3]
    fused_velocity = kf.x[3:6]
    fused_attitude = kf.x[6:9]
```

### 4.2 Tuning Kalman Filter

Adjust noise covariances in `ai/navigation.py`:

```python
# Process noise (how much we trust the model)
kf.Q = np.eye(9) * 0.001  # Lower = trust model more

# Measurement noise (how much we trust sensors)
kf.R = np.diag([
    1.0, 1.0, 1.0,      # GPS position noise
    0.1, 0.1, 0.1,      # GPS velocity noise
    0.01, 0.01, 0.01    # Magnetometer noise
])
```

---

## 5. Safety Features

Critical safety systems for reliable operation.

### 5.1 Thermal Management

```python
# Temperature monitoring
MAX_TEMP = 100.0  # °C - Emergency shutdown
TEMP_WARNING = 90.0  # °C - Reduce power
TEMP_NORMAL = 80.0  # °C - Normal operation

def check_thermal_safety(current_temp, current_power):
    """Monitor and respond to temperature."""
    
    if current_temp > MAX_TEMP:
        print("CRITICAL: Emergency thermal shutdown!")
        emergency_shutdown()
        return False
    
    elif current_temp > TEMP_WARNING:
        print(f"WARNING: High temperature {current_temp}°C")
        # Reduce power by 20%
        reduced_power = current_power * 0.8
        apply_power_limit(reduced_power)
        return True
    
    elif current_temp > TEMP_NORMAL:
        # Gradual power reduction
        scale_factor = 1.0 - ((current_temp - TEMP_NORMAL) / (TEMP_WARNING - TEMP_NORMAL)) * 0.2
        apply_power_limit(current_power * scale_factor)
        return True
    
    return True
```

### 5.2 Model Redundancy

Dual neural network models for failover:

```python
try:
    # Try primary model
    control = primary_model(input_tensor).numpy()
except Exception as e:
    logger.error(f"Primary model failed: {e}")
    # Failover to secondary
    control = secondary_model(input_tensor).numpy()
    use_primary = False
```

### 5.3 Battery Monitoring

```python
def check_battery_safety(voltage, current):
    """Monitor battery state."""
    
    # Calculate remaining capacity
    capacity_percent = (voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE) * 100
    
    if capacity_percent < 5:
        print("CRITICAL: Battery depleted! Emergency landing.")
        initiate_emergency_landing()
        return False
    
    elif capacity_percent < 15:
        print("WARNING: Low battery. Return to home.")
        initiate_return_to_home()
        return True
    
    elif capacity_percent < 25:
        print("CAUTION: Battery at 25%. Consider landing.")
        return True
    
    return True
```

### 5.4 Geofencing

```python
def check_geofence(position):
    """Ensure drone stays within safe operational area."""
    
    # Define safe zone (example: 100m radius, <50m altitude)
    MAX_RADIUS = 100.0  # meters
    MAX_ALTITUDE = 50.0  # meters
    
    distance_from_home = np.linalg.norm(position[:2])
    altitude = position[2]
    
    if distance_from_home > MAX_RADIUS:
        print("WARNING: Geofence breach (horizontal). Returning to home.")
        initiate_return_to_home()
        return False
    
    if altitude > MAX_ALTITUDE:
        print("WARNING: Geofence breach (altitude). Descending.")
        set_target_altitude(MAX_ALTITUDE - 5.0)
        return False
    
    return True
```

### 5.5 Watchdog Timer

```python
import threading
import time

class WatchdogTimer:
    """Watchdog timer for detecting control loop failures."""
    
    def __init__(self, timeout=1.0, callback=None):
        self.timeout = timeout
        self.callback = callback or self.default_callback
        self.last_kick = time.time()
        self.running = False
        self.thread = None
    
    def start(self):
        """Start watchdog timer."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.daemon = True
        self.thread.start()
    
    def kick(self):
        """Reset watchdog timer (call from control loop)."""
        self.last_kick = time.time()
    
    def _monitor(self):
        """Monitor thread."""
        while self.running:
            time.sleep(0.1)
            if time.time() - self.last_kick > self.timeout:
                print("WATCHDOG: Control loop timeout!")
                self.callback()
                break
    
    def stop(self):
        """Stop watchdog."""
        self.running = False
    
    def default_callback(self):
        """Default action on timeout."""
        emergency_shutdown()

# Usage in control node
watchdog = WatchdogTimer(timeout=0.5)  # 500ms timeout
watchdog.start()

# In control loop
def control_loop():
    while True:
        # ... control logic ...
        watchdog.kick()  # Reset timer
        time.sleep(0.005)
```

---

## 6. Testing and Validation

### 6.1 Incremental Testing Protocol

Follow this sequence for safe development:

1. **Bench test** (no flight):
   - Verify sensor readings
   - Test PWM outputs with multimeter
   - Check thermal sensors

2. **Tethered test** (constrained):
   - Secure drone with safety tether
   - Test at 10% power
   - Verify PID response
   - Gradually increase power

3. **Ground effect test** (near surface):
   - Hover at <0.5m altitude
   - Test stability
   - Emergency landing procedure

4. **Low altitude test** (1-5m):
   - Increase altitude gradually
   - Test all 6DOF controls
   - Practice emergency procedures

5. **Full flight test** (operational):
   - Test complete mission profiles
   - Validate MPC trajectories
   - Stress test safety systems

### 6.2 Data Logging

```python
import csv
from datetime import datetime

class FlightDataLogger:
    """Log flight data for post-analysis."""
    
    def __init__(self, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flight_log_{timestamp}.csv"
        
        self.file = open(filename, 'w', newline='')
        self.writer = csv.writer(self.file)
        
        # Write header
        self.writer.writerow([
            'timestamp', 'pos_x', 'pos_y', 'pos_z',
            'vel_x', 'vel_y', 'vel_z',
            'att_roll', 'att_pitch', 'att_yaw',
            'thrust_x', 'thrust_y', 'thrust_z',
            'b_field', 'temperature', 'power'
        ])
    
    def log(self, timestamp, state, control, telemetry):
        """Log a single data point."""
        self.writer.writerow([
            timestamp,
            *state['pos'], *state['vel'], *state['att'],
            *control[:3],
            telemetry['b_field'], telemetry['temp'], telemetry['power']
        ])
    
    def close(self):
        """Close log file."""
        self.file.close()

# Usage
logger = FlightDataLogger()

# In control loop
logger.log(
    time.time(),
    {'pos': fused_pos, 'vel': fused_vel, 'att': fused_att},
    control_output,
    {'b_field': b_field, 'temp': temperature, 'power': power}
)

# When done
logger.close()
```

### 6.3 Visualization and Analysis

```python
import pandas as pd
import matplotlib.pyplot as plt

def analyze_flight_log(filename):
    """Analyze and plot flight log data."""
    
    # Read log
    df = pd.read_csv(filename)
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    
    # Position over time
    axes[0, 0].plot(df['timestamp'], df['pos_x'], label='X')
    axes[0, 0].plot(df['timestamp'], df['pos_y'], label='Y')
    axes[0, 0].plot(df['timestamp'], df['pos_z'], label='Z')
    axes[0, 0].set_ylabel('Position (m)')
    axes[0, 0].legend()
    axes[0, 0].set_title('Position vs Time')
    axes[0, 0].grid(True)
    
    # Velocity over time
    axes[0, 1].plot(df['timestamp'], df['vel_x'], label='Vx')
    axes[0, 1].plot(df['timestamp'], df['vel_y'], label='Vy')
    axes[0, 1].plot(df['timestamp'], df['vel_z'], label='Vz')
    axes[0, 1].set_ylabel('Velocity (m/s)')
    axes[0, 1].legend()
    axes[0, 1].set_title('Velocity vs Time')
    axes[0, 1].grid(True)
    
    # Attitude over time
    axes[1, 0].plot(df['timestamp'], df['att_roll'], label='Roll')
    axes[1, 0].plot(df['timestamp'], df['att_pitch'], label='Pitch')
    axes[1, 0].plot(df['timestamp'], df['att_yaw'], label='Yaw')
    axes[1, 0].set_ylabel('Attitude (rad)')
    axes[1, 0].legend()
    axes[1, 0].set_title('Attitude vs Time')
    axes[1, 0].grid(True)
    
    # Control outputs
    axes[1, 1].plot(df['timestamp'], df['thrust_x'], label='Tx')
    axes[1, 1].plot(df['timestamp'], df['thrust_y'], label='Ty')
    axes[1, 1].plot(df['timestamp'], df['thrust_z'], label='Tz')
    axes[1, 1].set_ylabel('Thrust Control')
    axes[1, 1].legend()
    axes[1, 1].set_title('Control Outputs vs Time')
    axes[1, 1].grid(True)
    
    # B-field and temperature
    ax2 = axes[2, 0]
    ax2.plot(df['timestamp'], df['b_field'], 'b-', label='B-field')
    ax2.set_ylabel('B-field (T)', color='b')
    ax2.tick_params(axis='y', labelcolor='b')
    ax2.legend(loc='upper left')
    ax2.grid(True)
    
    ax2_twin = ax2.twinx()
    ax2_twin.plot(df['timestamp'], df['temperature'], 'r-', label='Temperature')
    ax2_twin.set_ylabel('Temperature (°C)', color='r')
    ax2_twin.tick_params(axis='y', labelcolor='r')
    ax2_twin.legend(loc='upper right')
    ax2.set_title('B-field and Temperature vs Time')
    
    # Power consumption
    axes[2, 1].plot(df['timestamp'], df['power'] / 1000, 'g-')
    axes[2, 1].set_ylabel('Power (kW)')
    axes[2, 1].set_xlabel('Time (s)')
    axes[2, 1].set_title('Power Consumption vs Time')
    axes[2, 1].grid(True)
    
    plt.tight_layout()
    plt.savefig(filename.replace('.csv', '_analysis.png'), dpi=150)
    plt.show()
    
    # Print statistics
    print("\nFlight Statistics:")
    print(f"  Duration: {df['timestamp'].max() - df['timestamp'].min():.2f}s")
    print(f"  Max altitude: {df['pos_z'].max():.2f}m")
    print(f"  Max speed: {np.sqrt(df['vel_x']**2 + df['vel_y']**2 + df['vel_z']**2).max():.2f}m/s")
    print(f"  Max temperature: {df['temperature'].max():.1f}°C")
    print(f"  Avg power: {df['power'].mean()/1000:.1f}kW")
    print(f"  Total energy: {df['power'].sum() * (df['timestamp'].diff().mean()) / 3600000:.2f}kWh")

# Run analysis
analyze_flight_log('flight_log_20251101_143022.csv')
```

---

## 7. Troubleshooting

### 7.1 Common Issues and Solutions

#### Issue: Unstable Flight / Oscillations

**Symptoms**: Drone oscillates or vibrates excessively

**Solutions**:
1. **Reduce PID gains**:
   - Start by halving Kp and Kd
   - Check for mechanical vibrations (loose components)

2. **Check sensor calibration**:
   ```bash
   # Calibrate IMU
   python hardware/calibrate_sensors.py --imu
   
   # Verify magnetometer
   python hardware/calibrate_sensors.py --magnetometer
   ```

3. **Increase damping**:
   - Add linear/angular damping in PyBullet dynamics
   - Check for resonance frequencies

4. **Filter sensor noise**:
   - Increase Kalman filter measurement noise (R matrix)
   - Add low-pass filter to IMU readings

#### Issue: High Latency / Missed Deadlines

**Symptoms**: Control loop slower than target rate

**Solutions**:
1. **Profile code**:
   ```python
   import cProfile
   cProfile.run('control_loop()', sort='cumtime')
   ```

2. **Optimize bottlenecks**:
   - Cache expensive calculations
   - Use vectorized NumPy operations
   - Reduce MPC horizon or call frequency

3. **Use faster hardware**:
   - Upgrade to ESP32-S3 (faster processor)
   - Use dedicated flight controller (Pixhawk)

4. **Enable RT preemption**:
   ```bash
   # Check kernel
   uname -a | grep PREEMPT
   
   # Install RT kernel if needed
   sudo apt install linux-lowlatency
   ```

#### Issue: Thermal Overload

**Symptoms**: Temperature exceeds safe limits

**Solutions**:
1. **Improve cooling**:
   - Verify PCM channels are functioning
   - Check TEG module connections
   - Add additional heat sinks

2. **Reduce duty cycle**:
   - Lower PWM duty cycle by 10-20%
   - Decrease pulsing frequency temporarily

3. **Limit power**:
   ```python
   MAX_POWER = 30000  # Watts (reduce from 40kW)
   if current_power > MAX_POWER:
       scale_factor = MAX_POWER / current_power
       apply_power_limit(scale_factor)
   ```

4. **Check for shorts**:
   - Inspect coil connections
   - Measure resistance of each MADA unit

#### Issue: GPS/Sensor Dropouts

**Symptoms**: Intermittent loss of sensor data

**Solutions**:
1. **Check connections**:
   - Verify I2C pullup resistors (4.7kΩ)
   - Inspect wire integrity
   - Check power supply stability

2. **Add redundancy**:
   ```python
   # Use last known good value
   if gps_data is None:
       gps_data = last_good_gps
   else:
       last_good_gps = gps_data
   ```

3. **Implement timeout handling**:
   ```python
   GPS_TIMEOUT = 2.0  # seconds
   if time.time() - last_gps_update > GPS_TIMEOUT:
       print("GPS timeout! Using dead reckoning.")
       use_dead_reckoning = True
   ```

#### Issue: Model Prediction Errors

**Symptoms**: NN outputs unrealistic values

**Solutions**:
1. **Retrain model**:
   ```bash
   python ai/navigation.py --train --epochs 200
   ```

2. **Add output clamping**:
   ```python
   control = np.clip(model_output, -10, 10)
   ```

3. **Use failover**:
   - Detect anomalies: `if np.any(np.isnan(control)):`
   - Switch to backup model or PID-only mode

### 7.2 Diagnostic Commands

```bash
# Check ROS2 node status
ros2 node list
ros2 node info /qed_drone_control

# Monitor topics
ros2 topic echo /drone_status
ros2 topic hz /control_output

# View logs
ros2 run rqt_console rqt_console

# Check hardware interfaces
python hardware/test_interfaces.py --all

# Validate thrust model
python simulations/thrust_model.py --verbose --b_opposing 50 --frequency 100
```

### 7.3 Emergency Procedures

**If drone becomes unresponsive**:

1. **Activate kill switch**: Physical button to cut all power
2. **Send emergency stop**: `ros2 topic pub /emergency_stop std_msgs/Bool "data: true"`
3. **Use RC override**: Manual control via transmitter
4. **GPS return-to-home**: If autonomous functions work

**After incident**:

1. Inspect hardware for damage
2. Download and analyze flight logs
3. Check all sensors and connections
4. Perform bench tests before next flight

---

## Next Steps

### Recommended Progression

1. **Complete this tutorial**: Master PID, MPC, and safety systems
2. **Hardware integration**: Follow `docs/tutorials/hardware_setup.md`
3. **Bench testing**: Use `docs/bench_test_designs.md` protocols
4. **Simulation validation**: Run swarm simulations in `examples/swarm_simulation.ipynb`
5. **Flight testing**: Progress through tethered → low altitude → full flight
6. **Advanced features**: Integrate ML optimization, multi-drone coordination

### Additional Resources

- **Code Examples**: `examples/` directory
- **API Documentation**: `docs/api/`
- **Community Forums**: GitHub Discussions
- **Research Papers**: See [Acknowledgments](../../README.md#acknowledgments)

### Contributing

Found an issue or have improvements? See [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## Appendix A: Control Loop Checklist

Before each flight, verify:

- [ ] All sensors calibrated and functioning
- [ ] PID gains tuned and stable
- [ ] Safety limits configured (temp, battery, geofence)
- [ ] Emergency procedures tested
- [ ] Logs enabled and storage available
- [ ] Backup systems operational
- [ ] Weather conditions acceptable
- [ ] Flight area clear and approved
- [ ] Communication link stable
- [ ] Battery fully charged

---

## Appendix B: Performance Targets

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Control loop rate | 200 Hz | 100 Hz | <50 Hz |
| Position accuracy | ±0.1 m | ±0.5 m | ±1.0 m |
| Attitude stability | ±2° | ±5° | ±10° |
| Temperature | <80°C | <90°C | >100°C |
| Response time | <100 ms | <200 ms | >500 ms |
| Battery level | >40% | >20% | <10% |

---

**Document Version**: 1.1  
**Last Updated**: November 1, 2025  
**Maintainer**: Jesse D. Hofseth (auagpt@usa.com)  
**Repository**: https://github.com/jhofseth/QED-Vacuum-Thrust-Control

[Back to top](#flight-control-tutorial-real-time-systems-pidmpc-and-safety)
