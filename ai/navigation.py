"""
ai/navigation.py

Advanced navigation system with sensor fusion, PID/MPC control, fail-safes,
redundancy, and predictive maintenance for QED vacuum propulsion drones.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from typing import List, Optional, Tuple
import os
import sys
import time
import logging

# Optional imports
try:
    import scipy.optimize as opt
    from scipy.spatial.transform import Rotation as R
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. MPC functionality limited.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import propulsion equations
try:
    from simulations.equations import force_vector, total_thrust, acceleration
    EQUATIONS_AVAILABLE = True
except ImportError:
    print("Warning: Could not import equations module. Using mock functions.")
    EQUATIONS_AVAILABLE = False
    
    # Mock functions if not available
    def force_vector(chi, B, grad_h2, A, rho):
        grad_h2 = np.asarray(grad_h2)
        return chi * B**2 * grad_h2 * A * rho
    
    def total_thrust(N, F_mag, eta, theta):
        return N * F_mag * eta * np.cos(np.deg2rad(theta))
    
    def acceleration(T, m):
        if m <= 0:
            raise ValueError("Mass must be positive")
        return T / m

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Physical constants
CHI = 1e-10
B = 50.0  # T
A = 1.0  # m²
RHO = 1000.0  # kg/m³
N_UNITS = 24
ETA = 0.95
THETA = 0.0  # degrees
MASS = 20000.0  # kg
DT = 0.1  # time step (s)
NUM_STEPS = 100  # simulation steps

# Safety limits
MAX_TEMP = 100.0  # °C
MAX_B_FIELD = 60.0  # T
TEMP_THRESHOLD = 90.0  # °C for warning

# Sensor noise parameters
IMU_ACCEL_NOISE = 0.01  # m/s²
IMU_GYRO_NOISE = 0.005  # rad/s
GPS_POS_NOISE = 1.0  # m
GPS_VEL_NOISE = 0.1  # m/s
ALTIMETER_NOISE = 0.5  # m
MAGNETOMETER_NOISE = 0.01  # rad


class KalmanFilter:
    """
    Extended Kalman Filter for sensor fusion.
    
    Fuses IMU (accelerometer, gyroscope), GPS (position, velocity),
    altimeter (altitude), and magnetometer (heading).
    
    State vector: [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, roll, pitch, yaw]
    """
    
    def __init__(self, dt: float = DT):
        """
        Initialize Kalman filter.
        
        Parameters:
        dt (float): Time step in seconds
        """
        self.dt = dt
        
        # State: [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, roll, pitch, yaw]
        self.x = np.zeros(9)
        
        # Covariance matrix
        self.P = np.eye(9) * 0.1
        
        # Process noise covariance
        self.Q = np.eye(9) * 0.001
        
        # Measurement noise covariance
        self.R = np.diag([
            GPS_POS_NOISE**2, GPS_POS_NOISE**2, GPS_POS_NOISE**2,
            GPS_VEL_NOISE**2, GPS_VEL_NOISE**2, GPS_VEL_NOISE**2,
            MAGNETOMETER_NOISE**2, MAGNETOMETER_NOISE**2, MAGNETOMETER_NOISE**2
        ])
    
    def predict(self, accel: np.ndarray, gyro: np.ndarray):
        """
        Prediction step using IMU data.
        
        Parameters:
        accel (np.ndarray): Acceleration from IMU [ax, ay, az] (m/s²)
        gyro (np.ndarray): Angular velocity from gyro [wx, wy, wz] (rad/s)
        """
        accel = np.asarray(accel)
        gyro = np.asarray(gyro)
        
        # Update velocity from acceleration
        self.x[3:6] += accel * self.dt
        
        # Update position from velocity
        self.x[0:3] += self.x[3:6] * self.dt
        
        # Update attitude from gyroscope (simple Euler integration)
        self.x[6:9] += gyro * self.dt
        
        # Normalize angles to [-π, π]
        self.x[6:9] = np.mod(self.x[6:9] + np.pi, 2 * np.pi) - np.pi
        
        # Predict covariance (simplified - no full Jacobian)
        self.P += self.Q
    
    def update(self, measurements: np.ndarray):
        """
        Update step with sensor measurements.
        
        Parameters:
        measurements (np.ndarray): Measurement vector
            [gps_x, gps_y, gps_z, vel_x, vel_y, vel_z, roll, pitch, yaw]
            Additional altimeter reading can be appended as 10th element
        """
        z = np.asarray(measurements[:9])
        
        # Observation matrix (direct observation)
        H = np.eye(9)
        
        # Innovation
        y = z - H @ self.x
        
        # Innovation covariance
        S = H @ self.P @ H.T + self.R
        
        # Kalman gain
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            logger.warning("Singular matrix in Kalman update. Using pseudo-inverse.")
            K = self.P @ H.T @ np.linalg.pinv(S)
        
        # Update state
        self.x += K @ y
        
        # Update covariance
        self.P = (np.eye(9) - K @ H) @ self.P
        
        # Altimeter-specific update for z-position
        if len(measurements) > 9:
            alt_z = measurements[9]
            alt_R = ALTIMETER_NOISE**2
            y_alt = alt_z - self.x[2]
            S_alt = self.P[2, 2] + alt_R
            
            if S_alt > 1e-10:  # Avoid division by zero
                K_alt = self.P[:, 2] / S_alt
                self.x += K_alt * y_alt
                self.P -= np.outer(K_alt, K_alt) * S_alt


class PIDController:
    """
    PID Controller for single-axis control.
    
    Used for position or attitude control per axis.
    """
    
    def __init__(self, kp: float = 1.0, ki: float = 0.1, kd: float = 0.5, 
                 dt: float = DT, output_limit: Optional[float] = None):
        """
        Initialize PID controller.
        
        Parameters:
        kp (float): Proportional gain
        ki (float): Integral gain
        kd (float): Derivative gain
        dt (float): Time step
        output_limit (float, optional): Maximum absolute output value
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.output_limit = output_limit
        
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, setpoint: float, current: float) -> float:
        """
        Compute control output.
        
        Parameters:
        setpoint (float): Desired value
        current (float): Current value
        
        Returns:
        float: Control output
        """
        error = setpoint - current
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (with anti-windup)
        self.integral += error * self.dt
        if self.output_limit:
            self.integral = np.clip(self.integral, -self.output_limit/self.ki, 
                                   self.output_limit/self.ki)
        i_term = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.prev_error) / self.dt
        d_term = self.kd * derivative
        
        # Total output
        output = p_term + i_term + d_term
        
        # Apply output limit
        if self.output_limit:
            output = np.clip(output, -self.output_limit, self.output_limit)
        
        self.prev_error = error
        return output
    
    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0


def mpc_control(current_state: np.ndarray, target_state: np.ndarray, 
                horizon: int = 1) -> np.ndarray:
    """
    Model Predictive Control for 6DOF.
    
    Optimizes control input over short prediction horizon.
    
    Parameters:
    current_state (np.ndarray): Current state [pos, attitude] (6D)
    target_state (np.ndarray): Target state [pos, attitude] (6D)
    horizon (int): Prediction horizon
    
    Returns:
    np.ndarray: Optimal control input (6D)
    """
    if not SCIPY_AVAILABLE:
        logger.warning("SciPy not available. Using zero control.")
        return np.zeros(6)
    
    def cost(u):
        """Cost function for MPC optimization."""
        # Predict next state (simplified dynamics)
        next_state = current_state + np.asarray(u) * DT
        
        # Quadratic cost on state error
        state_error = next_state - target_state
        return np.sum(state_error**2) + 0.1 * np.sum(u**2)  # Add control effort penalty
    
    # Optimize control input
    try:
        result = opt.minimize(cost, np.zeros(6), method='BFGS', 
                            options={'maxiter': 50})
        return result.x
    except Exception as e:
        logger.error(f"MPC optimization failed: {e}")
        return np.zeros(6)


class MaintenanceNN(nn.Module):
    """
    Neural network for predictive maintenance and adaptive pulsing.
    
    Inputs: operational cycles, temperature, B-field, threat level
    Outputs: degradation probability, adapted pulsing frequency
    """
    
    def __init__(self, input_size: int = 4, hidden_size: int = 32, output_size: int = 2):
        """
        Initialize maintenance neural network.
        
        Parameters:
        input_size (int): Input dimension
        hidden_size (int): Hidden layer size
        output_size (int): Output dimension
        """
        super(MaintenanceNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        """Forward pass."""
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        return self.fc3(x)


def simulate_sensors(true_pos: np.ndarray, true_vel: np.ndarray, 
                    true_attitude: np.ndarray) -> Tuple:
    """
    Simulate sensor readings with realistic noise.
    
    Parameters:
    true_pos (np.ndarray): True position [x, y, z]
    true_vel (np.ndarray): True velocity [vx, vy, vz]
    true_attitude (np.ndarray): True attitude [roll, pitch, yaw]
    
    Returns:
    tuple: (imu_accel, imu_gyro, gps_pos, gps_vel, alt_z, mag_attitude)
    """
    # IMU acceleration (simplified - no gravity compensation)
    imu_accel = np.random.normal(0, IMU_ACCEL_NOISE, 3)
    
    # IMU gyroscope
    imu_gyro = np.random.normal(0, IMU_GYRO_NOISE, 3)
    
    # GPS position
    gps_pos = true_pos + np.random.normal(0, GPS_POS_NOISE, 3)
    
    # GPS velocity
    gps_vel = true_vel + np.random.normal(0, GPS_VEL_NOISE, 3)
    
    # Altimeter (z-position only)
    alt_z = true_pos[2] + np.random.normal(0, ALTIMETER_NOISE)
    
    # Magnetometer (attitude)
    mag_attitude = true_attitude + np.random.normal(0, MAGNETOMETER_NOISE, 3)
    
    return imu_accel, imu_gyro, gps_pos, gps_vel, alt_z, mag_attitude


class MIMONetwork(nn.Module):
    """
    MIMO Neural Network for 6DOF control.
    
    Inputs: position, velocity, target (9 dimensions)
    Outputs: control signals for thrust vectors (6 dimensions)
    """
    
    def __init__(self, input_size: int = 9, hidden_size: int = 64, output_size: int = 6):
        """Initialize MIMO network."""
        super(MIMONetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        """Forward pass."""
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.tanh(self.fc3(x))
        return x


def simulate_navigation(primary_model: MIMONetwork, secondary_model: MIMONetwork,
                       start_pos: np.ndarray, start_vel: np.ndarray, 
                       target_pos: np.ndarray, obstacles: Optional[List[np.ndarray]] = None) -> Tuple:
    """
    Advanced navigation simulation with sensor fusion, control, and fail-safes.
    
    Parameters:
    primary_model (MIMONetwork): Primary navigation model
    secondary_model (MIMONetwork): Backup model for redundancy
    start_pos (np.ndarray): Starting position
    start_vel (np.ndarray): Starting velocity
    target_pos (np.ndarray): Target position
    obstacles (List[np.ndarray], optional): Obstacle positions
    
    Returns:
    tuple: (trajectory, velocities, controls, telemetry)
    """
    # Initialize state
    pos = np.asarray(start_pos, dtype=np.float64).copy()
    vel = np.asarray(start_vel, dtype=np.float64).copy()
    target = np.asarray(target_pos, dtype=np.float64)
    attitude = np.zeros(3)
    
    trajectory = [pos.copy()]
    velocities = [vel.copy()]
    controls_history = []
    telemetry = {'temp': [], 'b_field': [], 'degradation': []}
    
    # Initialize sensor fusion
    kf = KalmanFilter(dt=DT)
    
    # Initialize PID controllers (3 position + 3 attitude)
    pids = [PIDController(kp=2.0, ki=0.5, kd=1.0, dt=DT, output_limit=10.0) 
            for _ in range(6)]
    
    # Initialize maintenance model
    maintenance_model = MaintenanceNN()
    maintenance_model.eval()
    
    # Hardware state simulation
    current_temp = 25.0
    current_B = B
    current_eta = ETA
    cycles = 0
    threat_level = 0.0
    
    # Model selection
    use_primary = True
    model = primary_model
    model.eval()
    
    logger.info("Starting advanced navigation simulation")
    
    for step in range(NUM_STEPS):
        # Simulate sensor readings
        imu_accel, imu_gyro, gps_pos, gps_vel, alt_z, mag_attitude = \
            simulate_sensors(pos, vel, attitude)
        
        # Kalman filter: predict and update
        kf.predict(imu_accel, imu_gyro)
        measurements = np.concatenate([gps_pos, gps_vel, mag_attitude, [alt_z]])
        kf.update(measurements)
        
        # Get fused state estimate
        fused_pos = kf.x[0:3]
        fused_vel = kf.x[3:6]
        fused_att = kf.x[6:9]
        
        # Prepare neural network input
        input_state = np.concatenate([fused_pos, fused_vel, target])
        input_tensor = torch.tensor(input_state, dtype=torch.float32).unsqueeze(0)
        
        # Get control from neural network (with failover)
        try:
            with torch.no_grad():
                control = model(input_tensor).squeeze(0).numpy()
        except Exception as e:
            logger.error(f"Primary model failed: {e}. Switching to secondary.")
            use_primary = False
            model = secondary_model
            model.eval()
            with torch.no_grad():
                control = model(input_tensor).squeeze(0).numpy()
        
        controls_history.append(control.copy())
        
        # Apply PID fine-tuning
        pos_error = target - fused_pos
        att_error = np.zeros(3)  # Target attitude = 0 for simplicity
        
        pid_corrections = np.array([
            pids[i].compute(target[i], fused_pos[i]) for i in range(3)
        ] + [
            pids[i+3].compute(0.0, fused_att[i]) for i in range(3)
        ])
        
        control += pid_corrections * 0.1  # Blend with NN output
        
        # Optional MPC optimization (every 10 steps for efficiency)
        if step % 10 == 0 and SCIPY_AVAILABLE:
            current_state = np.concatenate([fused_pos, fused_att])
            target_state = np.concatenate([target, np.zeros(3)])
            mpc_output = mpc_control(current_state, target_state)
            control = 0.7 * control + 0.3 * mpc_output  # Blend with MPC
        
        # Extract thrust components
        grad_h2 = control[:3] * 10.0
        thrust_direction = control[3:]
        
        # Normalize thrust direction
        thrust_norm = np.linalg.norm(thrust_direction)
        if thrust_norm > 1e-6:
            thrust_direction /= thrust_norm
        else:
            thrust_direction = np.array([1.0, 0.0, 0.0])
        
        # Compute propulsion
        try:
            F_vec = force_vector(CHI, current_B, grad_h2, A, RHO)
            F_mag = np.linalg.norm(F_vec)
            T = total_thrust(N_UNITS, F_mag, current_eta, THETA)
            a_mag = acceleration(T, MASS)
            a = a_mag * thrust_direction
            
            # Limit acceleration
            a_mag_total = np.linalg.norm(a)
            if a_mag_total > MAX_ACCEL:
                a = a * (MAX_ACCEL / a_mag_total)
                logger.warning(f"Step {step}: Acceleration limited to {MAX_ACCEL/9.81:.1f}g")
        except Exception as e:
            logger.error(f"Thrust calculation error at step {step}: {e}")
            a = np.zeros(3)
        
        # Obstacle avoidance
        if obstacles:
            for obs in obstacles:
                obs = np.asarray(obs)
                dist_vec = fused_pos - obs
                dist = np.linalg.norm(dist_vec)
                if 0.1 < dist < 10.0:
                    repulsion = (dist_vec / dist) * (10.0 / (dist + 0.1))**2
                    a += repulsion
        
        # Update dynamics
        vel += a * DT
        pos += vel * DT
        attitude = fused_att
        
        trajectory.append(pos.copy())
        velocities.append(vel.copy())
        
        # Simulate hardware state
        current_temp += 0.5  # Heating
        cycles += 1
        threat_level = np.random.uniform(0, 1)
        
        telemetry['temp'].append(current_temp)
        telemetry['b_field'].append(current_B)
        
        # Predictive maintenance
        maint_input = torch.tensor([cycles, current_temp, current_B, threat_level],
                                   dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            maint_output = maintenance_model(maint_input).squeeze(0).numpy()
        
        degradation_prob = maint_output[0]
        adapted_freq = abs(maint_output[1])  # Ensure positive
        
        telemetry['degradation'].append(degradation_prob)
        
        # Adaptive pulsing based on degradation
        if degradation_prob > 0.5:
            logger.warning(f"High degradation probability: {degradation_prob:.2f}. "
                         f"Adapting frequency to {adapted_freq:.1f} Hz")
            current_eta = max(0.5, current_eta - 0.05)
        
        # Fail-safe checks
        if current_temp > MAX_TEMP:
            logger.critical(f"Temperature limit exceeded: {current_temp:.1f}°C. Emergency shutdown.")
            break
        
        if current_B > MAX_B_FIELD:
            logger.critical(f"B-field limit exceeded: {current_B:.1f}T. Emergency shutdown.")
            break
        
        if current_temp > TEMP_THRESHOLD:
            logger.warning(f"High temperature: {current_temp:.1f}°C. Reducing power.")
            current_B *= 0.95
        
        # Check target reached
        dist_to_target = np.linalg.norm(pos - target)
        if dist_to_target < 1.0:
            logger.info(f"✓ Target reached at step {step} (distance: {dist_to_target:.3f}m)")
            break
        
        # Progress updates
        if step % 20 == 0:
            logger.info(f"Step {step}: dist={dist_to_target:.1f}m, "
                       f"speed={np.linalg.norm(vel):.1f}m/s, temp={current_temp:.1f}°C")
    
    else:
        final_dist = np.linalg.norm(pos - target)
        logger.info(f"✗ Simulation ended. Final distance: {final_dist:.1f}m")
    
    return trajectory, velocities, controls_history, telemetry


def train_demo_model(num_epochs: int = 100, batch_size: int = 32, 
                    lr: float = 0.001) -> MIMONetwork:
    """Train demo model on random data."""
    logger.info("Training demo model...")
    model = MIMONetwork()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    
    model.train()
    
    for epoch in range(num_epochs):
        inputs = torch.randn(batch_size, 9)
        targets = torch.randn(batch_size, 6)
        
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 20 == 0:
            logger.info(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss.item():.4f}")
    
    logger.info("Training complete")
    return model


def plot_trajectory(trajectory: List[np.ndarray], velocities: Optional[List[np.ndarray]] = None,
                   obstacles: Optional[List[np.ndarray]] = None, 
                   target_pos: Optional[np.ndarray] = None):
    """Plot 3D trajectory with optional elements."""
    traj = np.array(trajectory)
    
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    ax.plot(traj[:, 0], traj[:, 1], traj[:, 2], 'b-', linewidth=2, label='Trajectory')
    ax.scatter(traj[0, 0], traj[0, 1], traj[0, 2], c='g', s=100, marker='o',
              label='Start', edgecolors='k')
    ax.scatter(traj[-1, 0], traj[-1, 1], traj[-1, 2], c='r', s=100, marker='o',
              label='End', edgecolors='k')
    
    if target_pos is not None:
        target = np.asarray(target_pos)
        ax.scatter(target[0], target[1], target[2], c='gold', s=200, marker='*',
                  label='Target', edgecolors='k')
    
    if obstacles:
        for i, obs in enumerate(obstacles):
            obs = np.asarray(obs)
            ax.scatter(obs[0], obs[1], obs[2], c='orange', s=150, marker='X',
                      label='Obstacle' if i == 0 else '', edgecolors='k', alpha=0.7)
    
    if velocities:
        vels = np.array(velocities)
        step = max(1, len(traj) // 10)
        for i in range(0, len(traj), step):
            if i < len(vels):
                ax.quiver(traj[i, 0], traj[i, 1], traj[i, 2],
                         vels[i, 0], vels[i, 1], vels[i, 2],
                         length=2.0, alpha=0.3, color='purple')
    
    ax.set_xlabel('X (m)', fontsize=12)
    ax.set_ylabel('Y (m)', fontsize=12)
    ax.set_zlabel('Z (m)', fontsize=12)
    ax.legend()
    ax.set_title('QED Advanced Navigation (6DOF + Sensor Fusion)', 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("QED VACUUM PROPULSION - ADVANCED NAVIGATION DEMO")
    logger.info("=" * 70)
    logger.info(f"Equations module: {'available' if EQUATIONS_AVAILABLE else 'mock'}")
    logger.info(f"SciPy/MPC: {'available' if SCIPY_AVAILABLE else 'unavailable'}\n")
    
    # Train models
    primary_model = train_demo_model(num_epochs=50, batch_size=32, lr=0.001)
    secondary_model = train_demo_model(num_epochs=50, batch_size=32, lr=0.001)
    
    # Setup scenario
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([100.0, 50.0, 20.0])
    obstacles = [np.array([50.0, 25.0, 10.0])]
    
    logger.info("\nSimulation Parameters:")
    logger.info(f"  Start: {start_pos}")
    logger.info(f"  Target: {target_pos}")
    logger.info(f"  Obstacles: {len(obstacles)}")
    logger.info(f"  Time step: {DT}s")
    logger.info(f"  Max steps: {NUM_STEPS}\n")
    
    # Run simulation
    trajectory, velocities, controls, telemetry = simulate_navigation(
        primary_model, secondary_model, start_pos, start_vel, target_pos, obstacles
    )
    
    # Results
    logger.info("\n" + "=" * 70)
    logger.info("SIMULATION RESULTS")
    logger.info("=" * 70)
    logger.info(f"Steps: {len(trajectory)}")
    logger.info(f"Distance traveled: {sum(np.linalg.norm(trajectory[i+1] - trajectory[i]) for i in range(len(trajectory)-1)):.2f}m")
    logger.info(f"Final position: {trajectory[-1]}")
    logger.info(f"Final velocity: {velocities[-1]}")
    logger.info(f"Final speed: {np.linalg.norm(velocities[-1]):.2f}m/s")
    logger.info(f"Max temperature: {max(telemetry['temp']):.1f}°C")
    logger.info(f"Max degradation: {max(telemetry['degradation']):.2f}")
    
    # Plot
    logger.info("\nGenerating visualization...")
    plot_trajectory(trajectory, velocities, obstacles, target_pos)
    
    logger.info("\nDemo complete.")
