import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from typing import List, Optional
import os
import sys
import time
import scipy.optimize as opt
from scipy.spatial.transform import Rotation as R

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Assuming access to propulsion equations; import if available
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

# Constants (example values)
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

# New constants for fail-safes
MAX_TEMP = 100.0  # °C
MAX_B_FIELD = 60.0  # T
TEMP_THRESHOLD = 90.0  # °C for warning

# Sensor noise parameters (for simulation)
IMU_ACCEL_NOISE = 0.01
IMU_GYRO_NOISE = 0.005
GPS_POS_NOISE = 1.0
GPS_VEL_NOISE = 0.1
ALTIMETER_NOISE = 0.5
MAGNETOMETER_NOISE = 0.01

class KalmanFilter:
    """
    Simple Extended Kalman Filter for sensor fusion (position, velocity, attitude).
    Fuses IMU (accel, gyro), GPS (pos, vel), altimeter (z), magnetometer (heading).
    """
    def __init__(self, dt=DT):
        self.dt = dt
        # State: [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, roll, pitch, yaw]
        self.x = np.zeros(9)
        self.P = np.eye(9) * 0.1  # Covariance
        self.Q = np.eye(9) * 0.001  # Process noise
        self.R = np.diag([GPS_POS_NOISE**2]*3 + [GPS_VEL_NOISE**2]*3 + [MAGNETOMETER_NOISE**2]*3)  # Measurement noise
        
    def predict(self, accel, gyro):
        # Predict state using IMU
        accel = np.asarray(accel)
        gyro = np.asarray(gyro)
        
        # Update velocity and position
        self.x[3:6] += accel * self.dt
        self.x[0:3] += self.x[3:6] * self.dt
        
        # Update attitude (simple Euler integration)
        roll_rate, pitch_rate, yaw_rate = gyro
        self.x[6] += roll_rate * self.dt
        self.x[7] += pitch_rate * self.dt
        self.x[8] += yaw_rate * self.dt
        
        # Normalize angles
        self.x[6:9] = np.mod(self.x[6:9] + np.pi, 2*np.pi) - np.pi
        
        # Predict covariance (simplified, no full Jacobian)
        self.P += self.Q
    
    def update(self, measurements):
        # Measurements: [gps_pos_x, y, z, gps_vel_x, y, z, mag_roll, pitch, yaw]
        # But altimeter overrides z pos
        z = np.asarray(measurements[:9])  # Assume full for simplicity
        H = np.eye(9)  # Observation matrix (direct for demo)
        y = z - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x += K @ y
        self.P = (np.eye(9) - K @ H) @ self.P
        
        # Altimeter specific update for z
        if len(measurements) > 9:
            alt_z = measurements[9]
            alt_R = ALTIMETER_NOISE**2
            y_alt = alt_z - self.x[2]
            S_alt = self.P[2,2] + alt_R
            K_alt = self.P[2,:] / S_alt
            self.x += K_alt * y_alt
            self.P -= np.outer(K_alt, K_alt) * S_alt

class PIDController:
    """
    PID Controller for 6DOF thrust vector management.
    One per axis (position or attitude).
    """
    def __init__(self, kp=1.0, ki=0.1, kd=0.5, dt=DT):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, setpoint, current):
        error = setpoint - current
        self.integral += error * self.dt
        derivative = (error - self.prev_error) / self.dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

# MPC Function (simple horizon=1 for demo, using scipy.optimize)
def mpc_control(current_state, target_state, horizon=1):
    """
    Simple Model Predictive Control for 6DOF.
    Optimizes control input over short horizon.
    """
    def cost(u):
        # Predict next state (simple: state + u * dt)
        next_state = current_state + np.asarray(u) * DT
        return np.sum((next_state - target_state)**2)
    
    res = opt.minimize(cost, np.zeros(6), method='BFGS')
    return res.x

class MaintenanceNN(nn.Module):
    """
    ML model for predictive maintenance and adaptive pulsing.
    Inputs: cycles, temp, B_field, threat_level
    Outputs: degradation_prob, adapted_frequency
    """
    def __init__(self, input_size=4, hidden_size=32, output_size=2):
        super(MaintenanceNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        return self.fc2(x)

def simulate_sensors(true_pos, true_vel, true_attitude):
    """Simulate sensor readings with noise."""
    imu_accel = np.random.normal(0, IMU_ACCEL_NOISE, 3)  # Simulated accel (assuming no gravity for demo)
    imu_gyro = np.random.normal(0, IMU_GYRO_NOISE, 3)
    gps_pos = true_pos + np.random.normal(0, GPS_POS_NOISE, 3)
    gps_vel = true_vel + np.random.normal(0, GPS_VEL_NOISE, 3)
    alt_z = true_pos[2] + np.random.normal(0, ALTIMETER_NOISE)
    mag_attitude = true_attitude + np.random.normal(0, MAGNETOMETER_NOISE, 3)
    return imu_accel, imu_gyro, gps_pos, gps_vel, alt_z, mag_attitude

class MIMONetwork(nn.Module):
    """
    MIMO Neural Network for 6DOF control.
    Inputs: Current position, velocity, target (9 dims: 3 pos + 3 vel + 3 target)
    Outputs: Control signals for thrust vectors (6 dims for 6DOF)
    """
    def __init__(self, input_size=9, hidden_size=64, output_size=6):
        super(MIMONetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.tanh(self.fc3(x))  # Output between -1 and 1 for control
        return x

def simulate_navigation(primary_model, secondary_model, start_pos, start_vel, target_pos, obstacles=None):
    """
    Simulate drone navigation using the MIMO network with sensor fusion, PID/MPC, fail-safes, redundancy, and maintenance.
    
    Parameters:
    primary_model (MIMONetwork): Primary trained model
    secondary_model (MIMONetwork): Secondary model for failover
    start_pos (np.array): Starting position [x, y, z]
    start_vel (np.array): Starting velocity [vx, vy, vz]
    target_pos (np.array): Target position [x, y, z]
    obstacles (List[np.array], optional): List of obstacle positions
    
    Returns:
    tuple: (trajectory positions, velocities, controls)
    """
    # Ensure inputs are numpy arrays
    pos = np.asarray(start_pos, dtype=np.float64).copy()
    vel = np.asarray(start_vel, dtype=np.float64).copy()
    target = np.asarray(target_pos, dtype=np.float64)
    attitude = np.zeros(3)  # [roll, pitch, yaw]
    
    trajectory = [pos.copy()]
    velocities = [vel.copy()]
    controls_history = []
    
    # Initialize Kalman filter
    kf = KalmanFilter()
    
    # Initialize PID controllers (one per DOF, for low-level)
    pids = [PIDController(kp=2.0, ki=0.5, kd=1.0) for _ in range(6)]  # 3 pos, 3 att
    
    # Initialize maintenance model
    maintenance_model = MaintenanceNN()
    maintenance_model.eval()  # Assume pre-trained
    
    # Simulate hardware states
    current_temp = 25.0
    current_B = B
    cycles = 0
    threat_level = 0.0  # 0-1 scale
    
    use_primary = True
    model = primary_model
    model.eval()
    
    for step in range(NUM_STEPS):
        # Simulate sensors
        imu_accel, imu_gyro, gps_pos, gps_vel, alt_z, mag_attitude = simulate_sensors(pos, vel, attitude)
        
        # Kalman predict and update
        kf.predict(imu_accel, imu_gyro)
        measurements = np.concatenate([gps_pos, gps_vel, mag_attitude, [alt_z]])
        kf.update(measurements)
        
        # Fused state
        fused_pos = kf.x[0:3]
        fused_vel = kf.x[3:6]
        fused_att = kf.x[6:9]
        
        # Input: fused_pos + fused_vel + target
        input_state = np.concatenate([fused_pos, fused_vel, target])
        input_tensor = torch.tensor(input_state, dtype=torch.float32).unsqueeze(0)
        
        # Get control outputs from NN
        try:
            with torch.no_grad():
                control = model(input_tensor).squeeze(0).numpy()
        except Exception as e:
            print(f"Model error: {e}. Failing over to secondary model.")
            use_primary = False
            model = secondary_model
            with torch.no_grad():
                control = model(input_tensor).squeeze(0).numpy()
        
        controls_history.append(control.copy())
        
        # Apply PID for fine-tuning (on position and attitude errors)
        pos_error = target - fused_pos
        att_error = np.zeros(3)  # Assume target att=0 for simplicity
        pid_outputs = np.array([pids[i].compute(pos_error[i], 0) for i in range(3)] +
                               [pids[i+3].compute(att_error[i], 0) for i in range(3)])
        control += pid_outputs * 0.1  # Blend with NN
        
        # Optionally use MPC for optimization
        if step % 10 == 0:  # Every 10 steps for efficiency
            current_state = np.concatenate([fused_pos, fused_att])
            target_state = np.concatenate([target, np.zeros(3)])
            mpc_u = mpc_control(current_state, target_state)
            control = mpc_u  # Override with MPC
        
        # Split control into gradient and direction components
        grad_h2 = control[:3] * 10.0  # Scale for demo (simulated gradient)
        thrust_direction = control[3:]  # Direction modifiers
        
        # Normalize thrust direction if non-zero
        thrust_dir_norm = np.linalg.norm(thrust_direction)
        if thrust_dir_norm > 1e-6:
            thrust_direction = thrust_direction / thrust_dir_norm
        else:
            thrust_direction = np.array([1.0, 0.0, 0.0])  # Default direction
        
        # Compute force and thrust
        try:
            F_vec = force_vector(CHI, current_B, grad_h2, A, RHO)
            F_mag = np.linalg.norm(F_vec)
            T = total_thrust(N_UNITS, F_mag, ETA, THETA)
            a_mag = acceleration(T, MASS)
            
            # Apply direction to acceleration
            a = a_mag * thrust_direction
        except Exception as e:
            print(f"Warning: Error in thrust calculation at step {step}: {e}")
            a = np.zeros(3)
        
        # Simple obstacle avoidance (repulsion if close)
        if obstacles:
            for obs in obstacles:
                obs = np.asarray(obs)
                dist_vec = fused_pos - obs
                dist = np.linalg.norm(dist_vec)
                if dist < 10.0 and dist > 0.1:  # Avoidance threshold
                    repulsion = (dist_vec / dist) * (10.0 / (dist + 0.1))**2
                    a += repulsion
        
        # Update velocity and position
        vel += a * DT
        pos += vel * DT
        
        # Update attitude (from gyro integration, but fused)
        attitude = fused_att
        
        trajectory.append(pos.copy())
        velocities.append(vel.copy())
        
        # Simulate hardware: temp increase, cycles
        current_temp += 0.5  # Simulated heating
        cycles += 1
        threat_level = np.random.uniform(0, 1)  # Simulated
        
        # Predictive maintenance
        maint_input = torch.tensor([cycles, current_temp, current_B, threat_level], dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            maint_output = maintenance_model(maint_input).squeeze(0).numpy()
        degradation_prob, adapted_freq = maint_output
        if degradation_prob > 0.5:
            print(f"Warning: High degradation probability ({degradation_prob:.2f}). Adapting pulsing to {adapted_freq:.2f} Hz.")
            # Adapt pulsing (mock: adjust ETA)
            ETA = max(0.5, ETA - 0.05)
        
        # Fail-safes
        if current_temp > MAX_TEMP or current_B > MAX_B_FIELD:
            print(f"Fail-safe triggered: Temp={current_temp:.1f}°C, B={current_B:.1f}T. Shutting down.")
            break
        if current_temp > TEMP_THRESHOLD:
            print(f"Warning: High temperature ({current_temp:.1f}°C). Reducing power.")
            current_B *= 0.9
        
        # Check if reached target
        dist_to_target = np.linalg.norm(pos - target)
        if dist_to_target < 1.0:
            print(f"✓ Reached target at step {step} (distance: {dist_to_target:.3f}m)")
            break
        
        # Progress indicator
        if step % 20 == 0:
            print(f"Step {step}: Distance to target = {dist_to_target:.2f}m, "
                  f"Speed = {np.linalg.norm(vel):.2f}m/s, Temp={current_temp:.1f}°C")
        
        # Simulate real-time
        time.sleep(DT / 10)  # Scaled down for faster sim
    
    else:
        final_dist = np.linalg.norm(pos - target)
        print(f"✗ Did not reach target. Final distance: {final_dist:.2f}m")
    
    return trajectory, velocities, controls_history

def train_demo_model(num_epochs=100, batch_size=32, lr=0.001):
    """
    Demo training: Train a simple model on random data (placeholder).
    In real use, train on simulation data or RL.
    
    Parameters:
    num_epochs (int): Number of training epochs
    batch_size (int): Batch size
    lr (float): Learning rate
    
    Returns:
    MIMONetwork: Trained model
    """
    print("Training demo model...")
    model = MIMONetwork()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    
    model.train()
    
    # Placeholder training loop (random data)
    for epoch in range(num_epochs):
        inputs = torch.randn(batch_size, 9)  # Batch of random states
        targets = torch.randn(batch_size, 6)  # Random controls
        
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss.item():.4f}")
    
    print("Training complete.")
    return model

def plot_trajectory(trajectory, velocities=None, obstacles=None, target_pos=None):
    """
    Plot the 3D trajectory with optional velocity vectors and obstacles.
    
    Parameters:
    trajectory (list): List of position arrays
    velocities (list, optional): List of velocity arrays
    obstacles (list, optional): List of obstacle positions
    target_pos (np.array, optional): Target position
    """
    traj = np.array(trajectory)
    
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot trajectory
    ax.plot(traj[:, 0], traj[:, 1], traj[:, 2], 'b-', linewidth=2, label='Trajectory')
    ax.scatter(traj[0, 0], traj[0, 1], traj[0, 2], c='g', s=100, marker='o', 
               label='Start', edgecolors='k')
    ax.scatter(traj[-1, 0], traj[-1, 1], traj[-1, 2], c='r', s=100, marker='o', 
               label='End', edgecolors='k')
    
    # Plot target
    if target_pos is not None:
        target = np.asarray(target_pos)
        ax.scatter(target[0], target[1], target[2], c='gold', s=200, marker='*', 
                   label='Target', edgecolors='k')
    
    # Plot obstacles
    if obstacles:
        for i, obs in enumerate(obstacles):
            obs = np.asarray(obs)
            ax.scatter(obs[0], obs[1], obs[2], c='orange', s=150, marker='X', 
                       label='Obstacle' if i == 0 else '', edgecolors='k', alpha=0.7)
    
    # Plot velocity vectors (subsample for clarity)
    if velocities is not None:
        vels = np.array(velocities)
        step = max(1, len(traj) // 10)  # Show ~10 velocity vectors
        for i in range(0, len(traj), step):
            if i < len(vels):
                ax.quiver(traj[i, 0], traj[i, 1], traj[i, 2],
                         vels[i, 0], vels[i, 1], vels[i, 2],
                         length=2.0, alpha=0.3, color='purple')
    
    ax.set_xlabel('X (m)', fontsize=12)
    ax.set_ylabel('Y (m)', fontsize=12)
    ax.set_zlabel('Z (m)', fontsize=12)
    ax.legend()
    ax.set_title('QED Drone Navigation Trajectory (6DOF)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def save_model(model, filepath='navigation_model.pth'):
    """Save model to disk."""
    torch.save(model.state_dict(), filepath)
    print(f"Model saved to {filepath}")

def load_model(filepath='navigation_model.pth'):
    """Load model from disk."""
    model = MIMONetwork()
    model.load_state_dict(torch.load(filepath))
    model.eval()
    print(f"Model loaded from {filepath}")
    return model

if __name__ == "__main__":
    print("=" * 60)
    print("QED VACUUM PROPULSION - AI NAVIGATION DEMO")
    print("=" * 60)
    print(f"Using {'real' if EQUATIONS_AVAILABLE else 'mock'} equations module\n")
    
    # Demo models (primary and secondary)
    primary_model = train_demo_model(num_epochs=100, batch_size=32, lr=0.001)
    secondary_model = train_demo_model(num_epochs=100, batch_size=32, lr=0.001)  # Slightly different training?
    
    # Starting conditions
    start_pos = np.array([0.0, 0.0, 0.0])
    start_vel = np.array([0.0, 0.0, 0.0])
    target_pos = np.array([100.0, 50.0, 20.0])
    obstacles = [np.array([50.0, 25.0, 10.0])]  # Example obstacle
    
    print(f"\nSimulation Parameters:")
    print(f"  Start Position: {start_pos}")
    print(f"  Start Velocity: {start_vel}")
    print(f"  Target Position: {target_pos}")
    print(f"  Obstacles: {len(obstacles)}")
    print(f"  Time Step: {DT}s")
    print(f"  Max Steps: {NUM_STEPS}")
    print(f"  Drone Mass: {MASS}kg")
    print(f"  MADA Units: {N_UNITS}\n")
    
    # Simulate
    print("Running navigation simulation...\n")
    trajectory, velocities, controls = simulate_navigation(
        primary_model, secondary_model, start_pos, start_vel, target_pos, obstacles
    )
    
    # Statistics
    print(f"\n{'=' * 60}")
    print("SIMULATION RESULTS")
    print(f"{'=' * 60}")
    print(f"Trajectory length: {len(trajectory)} steps")
    print(f"Total distance traveled: {sum(np.linalg.norm(trajectory[i+1] - trajectory[i]) for i in range(len(trajectory)-1)):.2f}m")
    print(f"Final position: {trajectory[-1]}")
    print(f"Final velocity: {velocities[-1]}")
    print(f"Final speed: {np.linalg.norm(velocities[-1]):.2f}m/s")
    
    # Plot
    print("\nGenerating trajectory plot...")
    plot_trajectory(trajectory, velocities, obstacles, target_pos)
    
    print("\nDemo complete.")
    
    # Optionally save model
    # save_model(primary_model, 'navigation_model.pth')
