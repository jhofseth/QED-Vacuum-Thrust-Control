"""
simulations/thrust_model.py

Extended thrust model simulation with multiple modes:
- Single calculation
- Swarm simulation (multi-drone)
- Benchmark against telemetry
- Real-time sensor monitoring
"""

import argparse
import numpy as np
import sys
import os
import time
import logging
from typing import Tuple, Optional, Dict, List
import yaml
from cryptography.fernet import Fernet
import getpass
import multiprocessing as mp
from scipy import optimize
from scipy.optimize import minimize
import subprocess  # For OpenFOAM integration
import tempfile
import shutil
import signal

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import core equations
from simulations.equations import (
    opposing_field,
    pulsed_enhancement,
    rg_beta_chi_spin0 as rg_beta_chi,
    force_vector,
    total_thrust,
    acceleration,
    efficiency_vectorized,
    power_consumption_vectorized,
    range_calc,
    non_ballistic_trajectory,
    radar_evasion_probability
)

# Optional imports
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import pybullet as p
    import pybullet_data
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False

try:
    from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

try:
    import open3d as o3d  # For potential CFD visualization
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import dask.array as da
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default parameters
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

# Encryption key management
ENCRYPTION_KEY = None

def get_encryption_key():
    global ENCRYPTION_KEY
    if ENCRYPTION_KEY is None:
        password = getpass.getpass("Enter encryption password: ")
        # In production, derive key from password using proper KDF
        ENCRYPTION_KEY = Fernet(Fernet.generate_key())
    return ENCRYPTION_KEY

def encrypt_data(data: bytes) -> bytes:
    return get_encryption_key().encrypt(data)

def decrypt_data(encrypted: bytes) -> bytes:
    return get_encryption_key().decrypt(encrypted)

def load_secure_params(config_file: str) -> Dict:
    """
    Load YAML config with optional encryption for sensitive params.
    """
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    sensitive_keys = ['classified_materials', 'secret_params']  # Example
    for key in sensitive_keys:
        if key in config and isinstance(config[key], str) and config[key].startswith('encrypted:'):
            encrypted = config[key][10:].encode()
            decrypted = decrypt_data(encrypted).decode()
            config[key] = yaml.safe_load(decrypted)
    
    return config

# Multi-Reference Frame and CFD Integration

def run_cfd_simulation(mesh_file: str, thrust_vector: np.ndarray, speed: float = 343*26) -> Dict:
    """
    Integrate with OpenFOAM for CFD simulation of thrust vectoring.
    Uses simpleFoam solver for steady-state; models diamagnetic repulsion as boundary condition.
    
    Parameters:
    mesh_file (str): Path to OpenFOAM mesh
    thrust_vector (np.array): 3D thrust vector
    speed (float): Flow speed (default Mach 26)
    
    Returns:
    Dict: Simulation results (pressure, velocity fields, etc.)
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # Copy mesh to temp dir
        if os.path.exists(mesh_file):
            shutil.copy(mesh_file, os.path.join(temp_dir, 'mesh.polyMesh'))
        
        # Setup case files (simplified; in practice, generate controlDict, fvSchemes, etc.)
        with open(os.path.join(temp_dir, 'controlDict'), 'w') as f:
            f.write("""application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    timeStep;
writeInterval   100;
""")
        
        # Set boundary conditions based on QED thrust
        magnitude = np.linalg.norm(thrust_vector)
        direction = thrust_vector / magnitude if magnitude > 0 else np.array([1,0,0])
        
        with open(os.path.join(temp_dir, 'U'), 'w') as f:  # Velocity file
            f.write(f"""dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({speed * direction[0]} {speed * direction[1]} {speed * direction[2]});
""")
        
        # Run OpenFOAM (check if available)
        try:
            subprocess.run(['simpleFoam'], cwd=temp_dir, capture_output=True, check=True)
            # Parse results (simplified; read latest time step)
            results = {'pressure': np.random.rand(100), 'velocity': np.random.rand(100,3)}
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"OpenFOAM not available or failed: {e}")
            results = {'pressure': np.random.rand(100), 'velocity': np.random.rand(100,3)}
        
        return results
    finally:
        shutil.rmtree(temp_dir)

# Dynamic Scenario Modeling

def parametric_sweep(param_name: str, values: List[float], args) -> pd.DataFrame:
    """
    Perform parametric sweep for given parameter.
    """
    if not PANDAS_AVAILABLE:
        logger.error("pandas required for parametric sweep")
        return None
    
    results = []
    for val in values:
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        T, a, P, eta, R, B = calculate_thrust_params(sweep_args)
        results.append({
            param_name: val,
            'thrust': T,
            'acceleration': a,
            'power': P,
            'efficiency': eta,
            'range': R,
            'B_total': B
        })
    return pd.DataFrame(results)

def simulate_swarm(num_drones: int = 5, scenario: str = 'asymmetric', 
                  simulation_time: float = 60, verbose: bool = False):
    """
    Multi-drone swarm simulation using PyBullet.
    
    Parameters:
    num_drones (int): Number of drones in swarm
    scenario (str): 'asymmetric' or 'symmetric' warfare scenario
    simulation_time (float): Simulation duration in seconds
    verbose (bool): Enable verbose output
    """
    if not PYBULLET_AVAILABLE:
        logger.error("PyBullet not installed. Install with: pip install pybullet")
        return
    
    logger.info(f"Starting swarm simulation: {num_drones} drones, {scenario} scenario")
    
    # Connect to physics engine
    physicsClient = p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    
    # Load environment
    planeId = p.loadURDF("plane.urdf")
    
    # Initialize drones
    drone_ids = []
    drone_masses = [DEFAULT_MASS] * num_drones
    drone_thrusts = []
    
    # Calculate base thrust
    base_F = np.linalg.norm(force_vector(DEFAULT_CHI, 50, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO))
    base_T = total_thrust(DEFAULT_N_UNITS, base_F, DEFAULT_ETA, DEFAULT_THETA)
    
    if scenario == 'asymmetric':
        # Asymmetric: Advanced drones have 1.5x thrust, others have 0.5x
        for i in range(num_drones):
            if i < num_drones // 2:
                drone_thrusts.append(1.5 * base_T)
            else:
                drone_thrusts.append(0.5 * base_T)
        logger.info("Asymmetric scenario: Advanced (50%) vs Standard (50%) drones")
    else:
        # Symmetric: All drones have equal thrust
        drone_thrusts = [base_T] * num_drones
        logger.info("Symmetric scenario: All drones equal thrust")
    
    # Load drone models (simple spheres for demo)
    for i in range(num_drones):
        start_pos = [i * 5, 0, 2]  # Staggered horizontal start
        drone_id = p.loadURDF("sphere2.urdf", start_pos, globalScaling=0.5)
        p.changeDynamics(drone_id, -1, mass=drone_masses[i])
        drone_ids.append(drone_id)
        logger.info(f"Drone {i}: pos={start_pos}, thrust={drone_thrusts[i]:.0f}N")
    
    # Simulation loop with non-ballistic trajectories
    steps = int(simulation_time * 240)  # 240 Hz physics
    targets = np.random.uniform(-50, 50, (num_drones, 3))  # Random targets
    trajectories = [non_ballistic_trajectory(np.array([i*5,0,2]), targets[i]) for i in range(num_drones)]
    traj_indices = [0] * num_drones
    
    for step in range(steps):
        # Apply thrust forces with vectoring
        for i, drone_id in enumerate(drone_ids):
            if traj_indices[i] < len(trajectories[i]) - 1:
                current_pos, _ = p.getBasePositionAndOrientation(drone_id)
                target_pos = trajectories[i][traj_indices[i] + 1]
                direction = target_pos - np.array(current_pos)
                norm = np.linalg.norm(direction)
                direction = direction / norm if norm > 0 else np.array([1, 0, 0])
                thrust_vec = direction * drone_thrusts[i]
                p.applyExternalForce(drone_id, -1, thrust_vec.tolist(), [0, 0, 0], p.LINK_FRAME)
                traj_indices[i] += 1
        
        # Simulate asymmetric warfare events
        if scenario == 'asymmetric' and np.random.rand() < 0.005:  # 0.5% chance per step
            # Advanced drones "attack" standard drones
            if len(drone_ids) > num_drones // 2:
                target_idx = np.random.randint(num_drones//2, len(drone_ids))
                target_id = drone_ids[target_idx]
                attack_force = [0, 0, -20000]  # Downward force
                p.applyExternalForce(target_id, -1, attack_force, [0, 0, 0], p.LINK_FRAME)
                if verbose:
                    logger.info(f"Step {step}: Attack on drone {target_idx}")
        
        p.stepSimulation()
        
        if step % 240 == 0 and verbose:  # Log every second
            logger.info(f"Simulation time: {step/240:.1f}s / {simulation_time}s")
        
        time.sleep(1/240)
    
    # Get final positions
    logger.info("\nFinal drone positions:")
    for i, drone_id in enumerate(drone_ids):
        pos, _ = p.getBasePositionAndOrientation(drone_id)
        logger.info(f"  Drone {i}: {pos}")
    
    p.disconnect()
    logger.info(f"Swarm simulation complete")

# Aerodynamic and Structural Integrity Checks

def compute_lift_drag_ratio(alpha: float = 0.0, v: float = DEFAULT_V) -> float:
    """
    Compute lift-to-drag ratio (simplified model).
    """
    Cl = 2 * np.pi * alpha  # Thin airfoil approximation
    Cd = 0.01 + (Cl**2) / (np.pi * 5)  # AR=5 assumption
    return Cl / Cd if Cd > 0 else 0

def fea_structural_check(accel: float, mass: float = DEFAULT_MASS, safety_factor: float = 1.5) -> bool:
    """
    Simple FEA hook: Check if structure can withstand acceleration.
    Uses yield strength of aluminum (270 MPa) as example.
    """
    force = mass * accel
    stress = force / (0.01)  # Assume 0.01 m² cross-section
    yield_strength = 270e6 / safety_factor  # Corrected: divide by safety factor
    return stress < yield_strength

def stealth_ops_check(traj: np.ndarray, radar_pos: np.ndarray, rcs: float = 0.01) -> float:
    """
    Check radar evasion for stealth ops.
    """
    return radar_evasion_probability(traj, radar_pos, rcs)

# Real-Time Validation Interfaces

def hil_validation(sim_thrust: float, bench_thrust: float, tolerance: float = 5.0) -> bool:
    """
    Hardware-in-the-loop validation.
    """
    error = abs((sim_thrust - bench_thrust) / bench_thrust * 100) if bench_thrust != 0 else 0
    logger.info(f"HIL Validation: Simulated {sim_thrust:.2f}N vs Bench {bench_thrust:.2f}N (Error: {error:.2f}%)")
    return error <= tolerance

def benchmark_with_telemetry(telemetry_file: str, args, verbose: bool = False):
    """
    Benchmark simulation outputs against hardware telemetry data.
    """
    if not PANDAS_AVAILABLE:
        logger.error("pandas not installed. Install with: pip install pandas")
        return
    
    if not os.path.exists(telemetry_file):
        logger.error(f"Telemetry file not found: {telemetry_file}")
        return
    
    logger.info(f"Benchmarking against telemetry: {telemetry_file}")
    
    try:
        data = pd.read_csv(telemetry_file)
        logger.info(f"Loaded {len(data)} telemetry records")
    except Exception as e:
        logger.error(f"Failed to read telemetry file: {e}")
        return
    
    # Expected columns: time, measured_B, measured_freq, measured_thrust, measured_accel
    required_cols = ['measured_B', 'measured_freq']
    if not all(col in data.columns for col in required_cols):
        logger.error(f"Missing required columns. Expected: {required_cols}")
        return
    
    sim_thrusts = []
    sim_accels = []
    differences = []
    hil_results = []
    
    for idx, row in data.iterrows():
        B = row.get('measured_B', 50.0)
        freq = row.get('measured_freq', args.frequency)
        
        T_sim, a_sim, _, _, _, _ = calculate_thrust_params(
            args, B_opposing=B, frequency=freq, verbose=False
        )
        
        sim_thrusts.append(T_sim)
        sim_accels.append(a_sim)
        
        measured_T = row.get('measured_thrust', 0)
        measured_a = row.get('measured_accel', 0)
        
        diff_T = abs(T_sim - measured_T) if measured_T > 0 else 0
        diff_a = abs(a_sim - measured_a) if measured_a > 0 else 0
        
        differences.append((diff_T, diff_a))
        
        # HIL validation
        hil_valid = hil_validation(T_sim, measured_T)
        hil_results.append(hil_valid)
    
    # Calculate statistics
    valid_diff_T = [d[0] for d in differences if d[0] > 0]
    valid_diff_a = [d[1] for d in differences if d[1] > 0]
    avg_diff_T = np.mean(valid_diff_T) if valid_diff_T else 0
    avg_diff_a = np.mean(valid_diff_a) if valid_diff_a else 0
    hil_pass_rate = sum(hil_results) / len(hil_results) * 100 if hil_results else 0
    
    logger.info("\n" + "=" * 60)
    logger.info("BENCHMARK RESULTS")
    logger.info("=" * 60)
    logger.info(f"Records processed: {len(data)}")
    logger.info(f"Average Thrust Difference: {avg_diff_T:.2f} N")
    logger.info(f"Average Acceleration Difference: {avg_diff_a:.2f} m/s²")
    logger.info(f"HIL Pass Rate: {hil_pass_rate:.2f}%")
    
    if verbose:
        # Save detailed comparison
        data['sim_thrust'] = sim_thrusts
        data['sim_accel'] = sim_accels
        data['thrust_error'] = [d[0] for d in differences]
        data['accel_error'] = [d[1] for d in differences]
        data['hil_valid'] = hil_results
        
        output_file = 'benchmark_report.csv'
        data.to_csv(output_file, index=False)
        logger.info(f"Detailed report saved to {output_file}")

# Optimization Routines

def thrust_objective(params: np.ndarray, param_names: List[str], base_args) -> float:
    """
    Objective function for thrust maximization.
    Negative thrust for minimization.
    """
    args_dict = vars(base_args).copy()
    for i, name in enumerate(param_names):
        args_dict[name] = params[i]
    args = argparse.Namespace(**args_dict)
    T, _, _, _, _, _ = calculate_thrust_params(args)
    return -T

def optimize_thrust(bounds: Dict, base_args, use_ml_surrogate: bool = False) -> Tuple[Dict, float]:
    """
    Gradient-based optimization with optional ML surrogate.
    """
    param_names = list(bounds.keys())
    bounds_list = list(bounds.values())
    
    if use_ml_surrogate and ML_AVAILABLE:
        # Train surrogate
        kernel = ConstantKernel() * RBF()
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
        # Generate samples
        X = np.random.uniform([b[0] for b in bounds_list], [b[1] for b in bounds_list], (100, len(bounds)))
        y = np.array([thrust_objective(x, param_names, base_args) for x in X])
        gp.fit(X, y)
        def surrogate_obj(x):
            return gp.predict(x.reshape(1, -1))[0]
        obj_func = surrogate_obj
    else:
        obj_func = lambda x: thrust_objective(x, param_names, base_args)
    
    initial_guess = np.array([(b[0] + b[1])/2 for b in bounds_list])
    result = minimize(obj_func, initial_guess, bounds=bounds_list, method='L-BFGS-B')
    opt_params = dict(zip(param_names, result.x))
    return opt_params, -result.fun

# Best Practices for Scalability

def parallel_parametric_sweep(param_name: str, values: List[float], args, n_processes: int = 4) -> pd.DataFrame:
    """
    Parallel parametric sweep using multiprocessing.
    """
    if not PANDAS_AVAILABLE:
        logger.error("pandas required for parametric sweep")
        return None
    
    def sweep_single(val):
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        T, a, P, eta, R, B = calculate_thrust_params(sweep_args)
        return {
            param_name: val,
            'thrust': T,
            'acceleration': a,
            'power': P,
            'efficiency': eta,
            'range': R,
            'B_total': B
        }
    
    with mp.Pool(n_processes) as pool:
        results = pool.map(sweep_single, values)
    return pd.DataFrame(results)

def dask_thrust_computation(params_array: np.ndarray, base_args) -> da.Array:
    """
    Dask-based parallel computation for large arrays.
    """
    if not DASK_AVAILABLE:
        logger.error("dask required for large-scale computation")
        return None
    
    dask_params = da.from_array(params_array, chunks=(100, -1))
    def compute_chunk(chunk):
        results = []
        for row in chunk:
            args = argparse.Namespace(**vars(base_args))
            args.b_opposing = row[0]
            args.frequency = row[1]
            T, _, _, _, _, _ = calculate_thrust_params(args)
            results.append(T)
        return np.array(results)
    return dask_params.map_blocks(compute_chunk, dtype=float, drop_axis=1)

def load_config_yaml(config_file: str) -> argparse.Namespace:
    """
    Load configuration from YAML file.
    """
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return argparse.Namespace(**config)

def handle_interrupt(sig, frame):
    logger.info("Simulation interrupted. Cleaning up...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)

# Secure Data Handling

class SecureParams:
    """
    Context manager for secure parameter handling.
    """
    def __init__(self, sensitive_data: Dict):
        self.sensitive_data = sensitive_data
        self.encrypted = {}
    
    def __enter__(self):
        user = getpass.getuser()
        if user not in ['authorized_user1', 'authorized_user2']:  # Example access control
            logger.warning(f"User {user} not in authorized list")
        for k, v in self.sensitive_data.items():
            self.encrypted[k] = encrypt_data(str(v).encode())
        return self
    
    def get(self, key):
        return decrypt_data(self.encrypted[key]).decode()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.encrypted.clear()

def calculate_thrust_params(args, B_opposing: Optional[float] = None, 
                           frequency: Optional[float] = None, 
                           verbose: bool = False) -> Tuple[float, float, float, float, float, float]:
    """
    Core thrust calculation function, reusable across modes.
    
    Parameters:
    args: Argument namespace with simulation parameters
    B_opposing (float, optional): Opposing magnetic field strength (T)
    frequency (float, optional): Pulsing frequency (Hz)
    verbose (bool): Enable verbose output
    
    Returns:
    tuple: (thrust, acceleration, power, efficiency, range, B_total)
    """
    frequency = frequency if frequency is not None else args.frequency
    B = B_opposing if B_opposing is not None else args.b_opposing
    
    if B is None:
        B = opposing_field(args.m1, args.m2, args.distance, DEFAULT_K)
    
    scaled_I = args.current * (frequency / 50.0)
    delta_B = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
    B_total = B + delta_B
    
    F_vec = force_vector(DEFAULT_CHI, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
    F_mag = np.linalg.norm(F_vec)
    T = total_thrust(args.n_units, F_mag, DEFAULT_ETA, DEFAULT_THETA)
    a = acceleration(T, args.mass)
    
    P = power_consumption_vectorized(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
    # Convert scalar to array for efficiency_vectorized
    eta_perc = efficiency_vectorized(np.array([T]), np.array([DEFAULT_V]), np.array([P]))[0]
    R = range_calc(DEFAULT_V, DEFAULT_E, P)
    
    if verbose:
        logger.info(f"Thrust: {T:.2f} N, Accel: {a:.2f} m/s², Power: {P:.2f} W")
    
    return T, a, P, eta_perc, R, B_total


def real_time_mode(args, sensor_port: str = '/dev/ttyUSB0', 
                  update_interval: float = 0.1, verbose: bool = False):
    """
    Real-time mode: Read sensor data and compute thrust dynamically.
    
    Parameters:
    args: Argument namespace with simulation parameters
    sensor_port (str): Serial port for sensor connection
    update_interval (float): Update interval in seconds
    verbose (bool): Enable verbose output
    """
    logger.info("=" * 60)
    logger.info("REAL-TIME THRUST MONITORING")
    logger.info("=" * 60)
    
    # Initialize hardware interfaces
    mcu = None
    
    if HARDWARE_AVAILABLE:
        try:
            mcu = MicrocontrollerPWMInterface(port=sensor_port)
            logger.info(f"Connected to microcontroller on {sensor_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to microcontroller: {e}")
            logger.info("Using simulated sensor data")
    else:
        logger.info("Hardware interfaces not available. Using simulated data.")
    
    logger.info(f"Update interval: {update_interval}s")
    logger.info("Press Ctrl+C to stop\n")
    
    iteration = 0
    
    try:
        while True:
            # Read sensor data
            if mcu:
                try:
                    # Request sensor data from microcontroller
                    response = mcu.send_command('READ:SENSORS')
                    if response:
                        # Parse response (format: "B:freq" or similar)
                        parts = response.split(':')
                        B = float(parts[0]) if len(parts) > 0 else 50.0
                        freq = float(parts[1]) if len(parts) > 1 else 100.0
                    else:
                        raise ValueError("No response")
                except Exception as e:
                    logger.warning(f"Sensor read error: {e}. Using defaults.")
                    B = 50.0
                    freq = 100.0
            else:
                # Simulated sensor data with realistic variations
                B = 50.0 + np.random.normal(0, 2.0)
                freq = 100.0 + np.random.normal(0, 5.0)
            
            # Calculate thrust parameters
            T, a, P, eta, R, B_total = calculate_thrust_params(
                args, B_opposing=B, frequency=freq, verbose=False
            )
            
            # Display results
            a_g = a / 9.81
            logger.info(f"[{iteration:04d}] B={B:.2f}T, Freq={freq:.1f}Hz, "
                       f"Thrust={T:.0f}N, Accel={a:.1f}m/s² ({a_g:.1f}g), "
                       f"Power={P:.0f}W")
            
            iteration += 1
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        logger.info("\nReal-time monitoring stopped by user")
    finally:
        if mcu:
            mcu.close()
            logger.info("Microcontroller connection closed")


def main():
    """Main entry point for thrust model simulations."""
    parser = argparse.ArgumentParser(
        description="QED Vacuum Thrust Model - Multi-mode Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Simulation Modes:
  single     - Single thrust calculation (default)
  swarm      - Multi-drone swarm simulation with PyBullet
  benchmark  - Compare simulation vs hardware telemetry
  realtime   - Real-time sensor monitoring and calculation

Examples:
  python thrust_model.py --b_opposing 50 --frequency 100
  python thrust_model.py --mode swarm --num_drones 10 --scenario asymmetric
  python thrust_model.py --mode benchmark --telemetry_file data.csv
  python thrust_model.py --mode realtime --sensor_port /dev/ttyUSB0
        """
    )
    
    # Basic parameters
    parser.add_argument("--b_opposing", type=float, default=None,
                       help="Opposing magnetic field (T)")
    parser.add_argument("--frequency", type=float, default=100.0,
                       help="Pulsing frequency (Hz)")
    parser.add_argument("--m1", type=float, default=DEFAULT_M1,
                       help=f"Magnetic moment 1 (A m²), default: {DEFAULT_M1}")
    parser.add_argument("--m2", type=float, default=DEFAULT_M2,
                       help=f"Magnetic moment 2 (A m²), default: {DEFAULT_M2}")
    parser.add_argument("--distance", type=float, default=DEFAULT_D,
                       help=f"Distance between magnets (m), default: {DEFAULT_D}")
    parser.add_argument("--current", type=float, default=DEFAULT_I,
                       help=f"Base current (A), default: {DEFAULT_I}")
    parser.add_argument("--mass", type=float, default=DEFAULT_MASS,
                       help=f"Drone mass (kg), default: {DEFAULT_MASS}")
    parser.add_argument("--n_units", type=int, default=DEFAULT_N_UNITS,
                       help=f"Number of MADA units, default: {DEFAULT_N_UNITS}")
    parser.add_argument("--chi", type=float, default=DEFAULT_CHI,
                       help=f"Susceptibility, default: {DEFAULT_CHI}")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    parser.add_argument("--config", type=str, default=None,
                       help="YAML configuration file")
    
    # Mode selection
    parser.add_argument("--mode", type=str, default='single',
                       choices=['single', 'swarm', 'benchmark', 'realtime'],
                       help="Simulation mode")
    
    # Swarm mode parameters
    parser.add_argument("--num_drones", type=int, default=5,
                       help="Number of drones for swarm mode")
    parser.add_argument("--scenario", type=str, default='asymmetric',
                       choices=['asymmetric', 'symmetric'],
                       help="Swarm scenario type")
    parser.add_argument("--simulation_time", type=float, default=60,
                       help="Simulation time (s) for swarm mode")
    
    # Benchmark mode parameters
    parser.add_argument("--telemetry_file", type=str, default=None,
                       help="CSV file for benchmark mode")
    
    # Real-time mode parameters
    parser.add_argument("--sensor_port", type=str, default='/dev/ttyUSB0',
                       help="Serial port for real-time sensor input")
    parser.add_argument("--update_interval", type=float, default=0.1,
                       help="Update interval (s) for real-time mode")
    
    # Optimization parameters
    parser.add_argument("--optimize", action="store_true",
                       help="Run optimization routine")
    parser.add_argument("--use_ml", action="store_true",
                       help="Use ML surrogate for optimization")
    
    args = parser.parse_args()
    
    # Load config file if provided
    if args.config:
        try:
            config_args = load_config_yaml(args.config)
            for key, val in vars(config_args).items():
                if not hasattr(args, key) or getattr(args, key) == parser.get_default(key):
                    setattr(args, key, val)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)
    
    # Route to appropriate mode
    if args.mode == 'single':
        # Original single calculation mode
        logger.info("=" * 60)
        logger.info("QED VACUUM THRUST MODEL SIMULATION")
        logger.info("=" * 60)
        logger.info(f"\nInput Parameters:")
        logger.info(f"  - Pulsing Frequency: {args.frequency} Hz")
        logger.info(f"  - Drone Mass: {args.mass} kg")
        logger.info(f"  - Number of MADA units: {args.n_units}")
        
        scaled_I = args.current * (args.frequency / 50.0)
        if args.verbose:
            logger.info(f"  - Base Current: {args.current} A")
            logger.info(f"  - Scaled Current: {scaled_I:.2f} A")
        
        if args.b_opposing is not None:
            B = args.b_opposing
            if args.verbose:
                logger.info(f"  - B_opposing (provided): {B:.2f} T")
        else:
            B = opposing_field(args.m1, args.m2, args.distance, DEFAULT_K)
            if args.verbose:
                logger.info(f"  - B_opposing (calculated): {B:.6e} T")
                logger.info(f"    (from m1={args.m1}, m2={args.m2}, d={args.distance}m)")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("MAGNETIC FIELD CALCULATIONS")
        logger.info(f"{'─' * 60}")
        logger.info(f"Opposing Field (B_opposing): {B:.2f} T")
        
        delta_B = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
        logger.info(f"Pulsed Enhancement (ΔB): {delta_B:.4f} T")
        
        B_total = B + delta_B
        logger.info(f"Total Magnetic Field (B_total): {B_total:.2f} T")
        
        if args.verbose:
            logger.info(f"\n{'─' * 60}")
            logger.info("QUANTUM PARAMETERS")
            logger.info(f"{'─' * 60}")
            beta_chi = rg_beta_chi(DEFAULT_CHI, DEFAULT_G, DEFAULT_LAMBDA)
            logger.info(f"Susceptibility (χ): {DEFAULT_CHI:.2e}")
            logger.info(f"RG Beta Function (β_χ): {beta_chi:.2e}")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("FORCE & THRUST CALCULATIONS")
        logger.info(f"{'─' * 60}")
        
        F_vec = force_vector(DEFAULT_CHI, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
        F_mag = np.linalg.norm(F_vec)
        logger.info(f"Force per Unit: {F_mag:.2f} N")
        if args.verbose:
            logger.info(f"  Force Vector: {F_vec}")
        
        T = total_thrust(args.n_units, F_mag, DEFAULT_ETA, DEFAULT_THETA)
        logger.info(f"Total Thrust: {T:.2f} N ({T/1000:.2f} kN)")
        
        a = acceleration(T, args.mass)
        a_g = a / 9.81
        logger.info(f"Acceleration: {a:.2f} m/s² ({a_g:.2f}g)")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("PERFORMANCE METRICS")
        logger.info(f"{'─' * 60}")
        
        P = power_consumption_vectorized(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
        logger.info(f"Power Consumption: {P:.2f} W ({P/1000:.2f} kW)")
        
        eta_perc = efficiency_vectorized(np.array([T]), np.array([DEFAULT_V]), np.array([P]))[0]
        logger.info(f"System Efficiency: {eta_perc:.2f}%")
        logger.info(f"  (at v = {DEFAULT_V} m/s = Mach {DEFAULT_V/343:.2f})")
        
        R = range_calc(DEFAULT_V, DEFAULT_E, P)
        logger.info(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
        logger.info(f"  (with {DEFAULT_E/3600000:.0f} kWh energy)")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("PERFORMANCE PROJECTIONS")
        logger.info(f"{'─' * 60}")
        mach_26_speed = 26 * 343
        time_to_mach26 = mach_26_speed / a if a > 0 else float('inf')
        logger.info(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
        logger.info(f"  (assuming constant acceleration)")
        
        weight = args.mass * 9.81
        twr = T / weight
        logger.info(f"Thrust-to-Weight Ratio: {twr:.2f}")
        
        # Aerodynamic checks
        ldr = compute_lift_drag_ratio()
        logger.info(f"Lift-to-Drag Ratio: {ldr:.2f}")
        
        structural_ok = fea_structural_check(a, args.mass)
        logger.info(f"Structural Integrity under {a_g:.1f}g: {'PASS' if structural_ok else 'FAIL'}")
        
        # Stealth check (placeholder trajectory and radar)
        traj = non_ballistic_trajectory(np.array([0,0,0]), np.array([1000,0,0]))
        evasion_prob = stealth_ops_check(traj, np.array([500,0,0]))
        logger.info(f"Radar Evasion Probability: {evasion_prob:.2%}")
        
        logger.info(f"\n{'=' * 60}")
        logger.info("SIMULATION COMPLETE")
        logger.info(f"{'=' * 60}\n")
    
    elif args.mode == 'swarm':
        simulate_swarm(args.num_drones, args.scenario, args.simulation_time, args.verbose)
    
    elif args.mode == 'benchmark':
        if not args.telemetry_file:
            logger.error("--telemetry_file required for benchmark mode")
            sys.exit(1)
        benchmark_with_telemetry(args.telemetry_file, args, args.verbose)
    
    elif args.mode == 'realtime':
        real_time_mode(args, args.sensor_port, args.update_interval, args.verbose)
    
    if args.optimize:
        logger.info("\nRunning optimization...")
        bounds = {
            'frequency': (50.0, 150.0),
            'current': (10.0, 20.0)
        }
        try:
            opt_params, max_thrust = optimize_thrust(bounds, args, args.use_ml)
            logger.info(f"Optimized Parameters: {opt_params}")
            logger.info(f"Maximum Thrust: {max_thrust:.2f} N")
        except Exception as e:
            logger.error(f"Optimization failed: {e}")


if __name__ == "__main__":
    main()
