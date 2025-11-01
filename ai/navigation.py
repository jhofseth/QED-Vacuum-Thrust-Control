import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from typing import List, Optional
import os
import sys

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

# Constants (example values from docs)
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
MAX_VELOCITY = 100.0  # m/s (safety limit)

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

def simulate_navigation(model, start_pos, start_vel, target_pos, obstacles=None):
    """
    Simulate drone navigation using the MIMO network.
    
    Parameters:
    model (MIMONetwork): Trained or demo model
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
    
    trajectory = [pos.copy()]
    velocities = [vel.copy()]
    controls_history = []
    
    model.eval()  # Set to evaluation mode
    
    for step in range(NUM_STEPS):
        # Input: pos + vel + target
        input_state = np.concatenate([pos, vel, target])
        input_tensor = torch.tensor(input_state, dtype=torch.float32).unsqueeze(0)
        
        # Get control outputs (scaled gradients for simplicity)
        with torch.no_grad():
            control = model(input_tensor).squeeze(0).numpy()
        
        controls_history.append(control.copy())
        
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
            F_vec = force_vector(CHI, B, grad_h2, A, RHO)
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
                dist_vec = pos - obs
                dist = np.linalg.norm(dist_vec)
                if dist < 10.0 and dist > 0.1:  # Avoidance threshold
                    repulsion = (dist_vec / dist) * (10.0 / (dist + 0.1))**2
                    a += repulsion
        
        # Update velocity and position
        vel += a * DT
        pos += vel * DT
        
        trajectory.append(pos.copy())
        velocities.append(vel.copy())
        
        # Check if reached target
        dist_to_target = np.linalg.norm(pos - target)
        if dist_to_target < 1.0:
            print(f"✓ Reached target at step {step} (distance: {dist_to_target:.3f}m)")
            break
        
        # Progress indicator
        if step % 20 == 0:
            print(f"Step {step}: Distance to target = {dist_to_target:.2f}m, "
                  f"Speed = {vel_mag:.2f}m/s")
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
    
    # Demo model (untrained or placeholder-trained)
    model = train_demo_model(num_epochs=100, batch_size=32, lr=0.001)
    
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
        model, start_pos, start_vel, target_pos, obstacles
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
    # save_model(model, 'navigation_model.pth')
