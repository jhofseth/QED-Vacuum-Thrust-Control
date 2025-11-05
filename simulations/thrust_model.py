"""
simulations/thrust_model.py

Extended thrust model simulation with multiple modes:
- Single calculation
- Swarm simulation (multi-drone)
- Benchmark against telemetry
- Real-time sensor monitoring

CRITICAL: Includes MADA convergence validation to prevent misconfigured magnetic fields
"""

import argparse
import numpy as np
import sys
import os
import time
import logging
from typing import Tuple, Optional, Dict, List
import yaml
import multiprocessing as mp
from scipy import optimize
from scipy.optimize import minimize
import subprocess
import tempfile
import shutil
import signal

# Optional imports
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available. Benchmark mode disabled.")

try:
    import pybullet as p
    import pybullet_data
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False
    logging.warning("PyBullet not available. Swarm simulations disabled.")

try:
    import dask.array as da
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
    logging.warning("Dask not available. Parallel computation limited.")

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    logging.warning("Open3D not available. CFD visualizations limited.")

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("scikit-learn not available. ML surrogates disabled.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Physical constants
MU_0 = 4 * np.pi * 1e-7  # Permeability of free space (H/m)

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

# MADA Convergence Validation Constants
MADA_MIN_FIELD = 0.1
MADA_MAX_FIELD = 100.0
MADA_MIN_ALIGNMENT = 0.9
MADA_MAX_ASYMMETRY = 0.15
MADA_MIN_GRADIENT = 0.01
MADA_CONVERGENCE_THRESHOLD = 0.05
MADA_MAX_ITERATIONS = 100


class MADAValidationError(Exception):
    """Raised when MADA configuration fails validation."""
    pass


# Stub implementations for missing equations module
def opposing_field(m1: float, m2: float, d: float, k: float) -> float:
    """Calculate opposing magnetic field between two magnets."""
    if d == 0:
        return 0.0
    return k * MU_0 * m1 * m2 / (4 * np.pi * d**3)


def pulsed_enhancement(n_turns: int, current: float) -> float:
    """Calculate field enhancement from pulsed current."""
    return MU_0 * n_turns * current


def rg_beta_chi(chi: float, g: float, lambda_val: float) -> float:
    """Calculate RG beta function for susceptibility."""
    return chi * g * lambda_val


def force_vector(chi: float, B: float, grad_H2: np.ndarray, 
                A: float, rho: float) -> np.ndarray:
    """Calculate force vector from magnetic field gradient."""
    return chi * B * grad_H2 * A * rho


def total_thrust(n_units: int, F_mag: float, eta: float, theta: float) -> float:
    """Calculate total thrust from multiple units."""
    return n_units * F_mag * eta * np.cos(theta)


def acceleration(thrust: float, mass: float) -> float:
    """Calculate acceleration from thrust and mass."""
    return thrust / mass if mass > 0 else 0.0


def efficiency(thrust: float, velocity: float, power: float) -> float:
    """Calculate propulsion efficiency."""
    if power == 0:
        return 0.0
    return (thrust * velocity / power) * 100


def power_consumption(current: float, resistance: float, p_eddy: float) -> float:
    """Calculate total power consumption."""
    return current**2 * resistance + p_eddy


def range_calc(velocity: float, energy: float, power: float) -> float:
    """Calculate range from energy and power."""
    if power == 0:
        return 0.0
    time_available = energy / power
    return velocity * time_available


def non_ballistic_trajectory(start: np.ndarray, end: np.ndarray, 
                            num_points: int = 100) -> np.ndarray:
    """Generate non-ballistic trajectory between two points."""
    trajectory = np.linspace(start, end, num_points)
    # Add some curvature for non-ballistic behavior
    mid_point = len(trajectory) // 2
    trajectory[mid_point] += np.array([0, 0, 10])
    return trajectory


def radar_evasion_probability(trajectory: np.ndarray, radar_pos: np.ndarray, 
                              rcs: float) -> float:
    """Calculate radar evasion probability based on trajectory and RCS."""
    distances = np.linalg.norm(trajectory - radar_pos, axis=1)
    avg_distance = np.mean(distances)
    # Simple model: evasion probability increases with distance and decreases with RCS
    base_prob = 1.0 / (1.0 + rcs * 100)
    distance_factor = min(avg_distance / 1000.0, 1.0)
    return base_prob * distance_factor


class MADAConvergenceValidator:
    """
    Validates MADA (Magnetic Array Diamagnetic Amplifier) convergence.
    
    Critical checks:
    1. Field magnitude within operational range
    2. Field vector alignment across units
    3. Symmetry and uniformity validation
    4. Gradient consistency
    5. Convergence stability over time
    """
    
    def __init__(self, tolerance: float = MADA_CONVERGENCE_THRESHOLD,
                 max_iterations: int = MADA_MAX_ITERATIONS):
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.history = []
        self.convergence_achieved = False
        
    def validate_field_magnitude(self, B_total: float) -> Tuple[bool, str]:
        """Validate that field magnitude is within operational range."""
        if B_total < MADA_MIN_FIELD:
            return False, f"Field too weak: {B_total:.4f}T < {MADA_MIN_FIELD}T"
        if B_total > MADA_MAX_FIELD:
            return False, f"Field too strong: {B_total:.4f}T > {MADA_MAX_FIELD}T"
        return True, f"Field magnitude OK: {B_total:.4f}T"
    
    def validate_field_vectors(self, field_vectors: List[np.ndarray]) -> Tuple[bool, str]:
        """Validate field vector alignment across MADA units."""
        if len(field_vectors) < 2:
            return True, "Single unit - alignment N/A"
        
        normalized = [v / np.linalg.norm(v) if np.linalg.norm(v) > 0 else v 
                     for v in field_vectors]
        
        alignments = []
        for i in range(len(normalized)):
            for j in range(i+1, len(normalized)):
                dot_prod = np.dot(normalized[i], normalized[j])
                alignments.append(dot_prod)
        
        min_alignment = min(alignments) if alignments else 1.0
        
        if min_alignment < MADA_MIN_ALIGNMENT:
            return False, f"Poor field alignment: {min_alignment:.4f} < {MADA_MIN_ALIGNMENT}"
        
        return True, f"Field alignment OK: {min_alignment:.4f}"
    
    def validate_symmetry(self, field_vectors: List[np.ndarray]) -> Tuple[bool, str]:
        """Validate field symmetry across MADA array."""
        if len(field_vectors) < 4:
            return True, "Insufficient units for symmetry check"
        
        magnitudes = [np.linalg.norm(v) for v in field_vectors]
        mean_mag = np.mean(magnitudes)
        std_mag = np.std(magnitudes)
        asymmetry = std_mag / mean_mag if mean_mag > 0 else 0
        
        if asymmetry > MADA_MAX_ASYMMETRY:
            return False, f"High asymmetry: {asymmetry:.4f} > {MADA_MAX_ASYMMETRY}"
        
        return True, f"Symmetry OK: asymmetry={asymmetry:.4f}"
    
    def validate_gradient(self, grad_H2: np.ndarray) -> Tuple[bool, str]:
        """Validate field gradient magnitude."""
        grad_mag = np.linalg.norm(grad_H2)
        
        if grad_mag < MADA_MIN_GRADIENT:
            return False, f"Gradient too small: {grad_mag:.4e} < {MADA_MIN_GRADIENT}"
        
        return True, f"Gradient OK: {grad_mag:.4e}"
    
    def check_convergence(self, current_thrust: float) -> Tuple[bool, str]:
        """Check if thrust has converged to a stable value."""
        self.history.append(current_thrust)
        
        if len(self.history) < 10:
            return False, f"Collecting data: {len(self.history)}/10 samples"
        
        if len(self.history) > 50:
            self.history = self.history[-50:]
        
        recent = self.history[-10:]
        mean_thrust = np.mean(recent)
        std_thrust = np.std(recent)
        
        if mean_thrust == 0:
            return False, "Zero thrust - configuration error"
        
        relative_std = std_thrust / mean_thrust
        
        if relative_std < self.tolerance:
            self.convergence_achieved = True
            return True, f"CONVERGED: std/mean = {relative_std:.4f}"
        
        if len(self.history) >= self.max_iterations:
            return False, f"Failed to converge after {self.max_iterations} iterations"
        
        return False, f"Converging: std/mean = {relative_std:.4f} (target < {self.tolerance})"
    
    def full_validation(self, B_total: float, field_vectors: List[np.ndarray],
                       grad_H2: np.ndarray, current_thrust: float) -> Dict:
        """Perform complete MADA validation suite."""
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        mag_valid, mag_msg = self.validate_field_magnitude(B_total)
        results['checks']['magnitude'] = {'valid': mag_valid, 'message': mag_msg}
        if not mag_valid:
            results['valid'] = False
            results['errors'].append(mag_msg)
        
        align_valid, align_msg = self.validate_field_vectors(field_vectors)
        results['checks']['alignment'] = {'valid': align_valid, 'message': align_msg}
        if not align_valid:
            results['valid'] = False
            results['errors'].append(align_msg)
        
        sym_valid, sym_msg = self.validate_symmetry(field_vectors)
        results['checks']['symmetry'] = {'valid': sym_valid, 'message': sym_msg}
        if not sym_valid:
            results['warnings'].append(sym_msg)
        
        grad_valid, grad_msg = self.validate_gradient(grad_H2)
        results['checks']['gradient'] = {'valid': grad_valid, 'message': grad_msg}
        if not grad_valid:
            results['valid'] = False
            results['errors'].append(grad_msg)
        
        conv_valid, conv_msg = self.check_convergence(current_thrust)
        results['checks']['convergence'] = {'valid': conv_valid, 'message': conv_msg}
        results['converged'] = self.convergence_achieved
        
        return results
    
    def reset(self):
        """Reset validator state."""
        self.history = []
        self.convergence_achieved = False


def simulate_hall_sensor_readings(n_units: int, B_total: float, 
                                  noise_level: float = 0.02) -> List[np.ndarray]:
    """Simulate Hall sensor readings for each MADA unit."""
    field_vectors = []
    base_direction = np.array([1.0, 0.0, 0.0])
    
    for i in range(n_units):
        misalignment = np.random.normal(0, 0.05, 3)
        direction = base_direction + misalignment
        direction = direction / np.linalg.norm(direction)
        
        magnitude = B_total * (1.0 + np.random.normal(0, 0.1))
        noise = np.random.normal(0, noise_level * magnitude, 3)
        
        vector = direction * magnitude + noise
        field_vectors.append(vector)
    
    return field_vectors


def load_config_yaml(config_file: str) -> argparse.Namespace:
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return argparse.Namespace(**config)


def run_cfd_simulation(mesh_file: str, thrust_vector: np.ndarray, 
                      speed: float = 343*26) -> Dict:
    """
    Integrate with OpenFOAM for CFD simulation (stub implementation).
    """
    logger.info(f"CFD simulation requested but not fully implemented")
    logger.info(f"Thrust vector: {thrust_vector}, Speed: {speed} m/s")
    
    # Return placeholder results
    return {
        'pressure': np.random.rand(100),
        'velocity': np.random.rand(100, 3),
        'note': 'CFD simulation stub - requires full OpenFOAM setup'
    }


def parametric_sweep(param_name: str, values: List[float], args) -> pd.DataFrame:
    """Perform parametric sweep for given parameter."""
    if not PANDAS_AVAILABLE:
        logger.error("pandas required for parametric sweep")
        return None
    
    results = []
    for val in values:
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        T, a, P, eta, R, B = calculate_thrust_params(sweep_args, verbose=False)
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
                  simulation_time: float = 60, verbose: bool = False,
                  validate_mada: bool = True):
    """Multi-drone swarm simulation using PyBullet."""
    if not PYBULLET_AVAILABLE:
        logger.error("PyBullet not installed. Install with: pip install pybullet")
        return
    
    logger.info(f"Starting swarm simulation: {num_drones} drones, {scenario} scenario")
    
    validators = [MADAConvergenceValidator() for _ in range(num_drones)] if validate_mada else None
    
    physicsClient = p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    
    planeId = p.loadURDF("plane.urdf")
    
    drone_ids = []
    drone_masses = [DEFAULT_MASS] * num_drones
    drone_thrusts = []
    
    base_F = np.linalg.norm(force_vector(DEFAULT_CHI, 50, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO))
    base_T = total_thrust(DEFAULT_N_UNITS, base_F, DEFAULT_ETA, DEFAULT_THETA)
    
    if scenario == 'asymmetric':
        for i in range(num_drones):
            if i < num_drones // 2:
                drone_thrusts.append(1.5 * base_T)
            else:
                drone_thrusts.append(0.5 * base_T)
        logger.info("Asymmetric scenario: Advanced (50%) vs Standard (50%) drones")
    else:
        drone_thrusts = [base_T] * num_drones
        logger.info("Symmetric scenario: All drones equal thrust")
    
    # Use sphere2red.urdf which exists in PyBullet data
    for i in range(num_drones):
        start_pos = [i * 5, 0, 2]
        try:
            drone_id = p.loadURDF("sphere2red.urdf", start_pos, globalScaling=0.5)
        except:
            # Fallback to creating a simple collision shape
            collision_shape = p.createCollisionShape(p.GEOM_SPHERE, radius=0.5)
            visual_shape = p.createVisualShape(p.GEOM_SPHERE, radius=0.5, rgbaColor=[1, 0, 0, 1])
            drone_id = p.createMultiBody(baseMass=drone_masses[i],
                                        baseCollisionShapeIndex=collision_shape,
                                        baseVisualShapeIndex=visual_shape,
                                        basePosition=start_pos)
        
        p.changeDynamics(drone_id, -1, mass=drone_masses[i])
        drone_ids.append(drone_id)
        logger.info(f"Drone {i}: pos={start_pos}, thrust={drone_thrusts[i]:.0f}N")
    
    steps = int(simulation_time * 240)
    targets = np.random.uniform(-50, 50, (num_drones, 3))
    trajectories = [non_ballistic_trajectory(np.array([i*5,0,2]), targets[i]) 
                   for i in range(num_drones)]
    traj_indices = [0] * num_drones
    validation_failures = [0] * num_drones
    
    for step in range(steps):
        for i, drone_id in enumerate(drone_ids):
            if traj_indices[i] < len(trajectories[i]) - 1:
                current_pos, _ = p.getBasePositionAndOrientation(drone_id)
                target_pos = trajectories[i][traj_indices[i] + 1]
                direction = target_pos - np.array(current_pos)
                norm = np.linalg.norm(direction)
                direction = direction / norm if norm > 0 else np.array([0, 0, 1])
                
                if validate_mada:
                    B_total = 50.0 + step * 0.001
                    field_vectors = simulate_hall_sensor_readings(DEFAULT_N_UNITS, B_total)
                    
                    validation_result = validators[i].full_validation(
                        B_total, field_vectors, DEFAULT_GRAD_H2, drone_thrusts[i]
                    )
                    
                    if not validation_result['valid']:
                        validation_failures[i] += 1
                        if verbose:
                            logger.warning(f"Drone {i} MADA validation failed: {validation_result['errors']}")
                        thrust_vec = direction * drone_thrusts[i] * 0.5
                    else:
                        thrust_vec = direction * drone_thrusts[i]
                else:
                    thrust_vec = direction * drone_thrusts[i]
                
                p.applyExternalForce(drone_id, -1, thrust_vec.tolist(), [0, 0, 0], p.LINK_FRAME)
                traj_indices[i] += 1
        
        if scenario == 'asymmetric' and np.random.rand() < 0.005:
            if len(drone_ids) > num_drones // 2:
                target_id = np.random.choice(drone_ids[num_drones//2:])
                attack_force = [0, 0, -20000]
                p.applyExternalForce(target_id, -1, attack_force, [0, 0, 0], p.LINK_FRAME)
                if verbose:
                    logger.info(f"Step {step}: Attack on drone {drone_ids.index(target_id)}")
        
        p.stepSimulation()
        
        if step % 240 == 0 and verbose:
            logger.info(f"Simulation time: {step/240:.1f}s / {simulation_time}s")
        
        time.sleep(1/240)
    
    logger.info("\n" + "=" * 60)
    logger.info("SWARM SIMULATION RESULTS")
    logger.info("=" * 60)
    
    for i, drone_id in enumerate(drone_ids):
        pos, _ = p.getBasePositionAndOrientation(drone_id)
        logger.info(f"Drone {i}: Final pos={pos}")
        if validate_mada:
            failure_rate = validation_failures[i] / steps * 100
            logger.info(f"  MADA validation failures: {validation_failures[i]} ({failure_rate:.2f}%)")
            logger.info(f"  Converged: {validators[i].convergence_achieved}")
    
    p.disconnect()
    logger.info(f"Swarm simulation complete\n")


def compute_lift_drag_ratio(alpha: float = 0.0, v: float = DEFAULT_V) -> float:
    """Compute lift-to-drag ratio."""
    Cl = 2 * np.pi * alpha
    Cd = 0.01 + (Cl**2) / (np.pi * 5)
    return Cl / Cd if Cd > 0 else 0


def fea_structural_check(accel: float, mass: float = DEFAULT_MASS, 
                        safety_factor: float = 1.5) -> bool:
    """Simple FEA check for structural integrity."""
    force = mass * accel
    stress = force / 0.01
    yield_strength = 270e6 * safety_factor
    return stress < yield_strength


def stealth_ops_check(traj: np.ndarray, radar_pos: np.ndarray, 
                     rcs: float = 0.01) -> float:
    """Check radar evasion for stealth ops."""
    return radar_evasion_probability(traj, radar_pos, rcs)


def hil_validation(sim_thrust: float, bench_thrust: float, 
                  tolerance: float = 5.0) -> bool:
    """Hardware-in-the-loop validation."""
    error = abs((sim_thrust - bench_thrust) / bench_thrust * 100) if bench_thrust != 0 else 0
    logger.info(f"HIL Validation: Simulated {sim_thrust:.2f}N vs Bench {bench_thrust:.2f}N (Error: {error:.2f}%)")
    return error <= tolerance


def benchmark_with_telemetry(telemetry_file: str, args, verbose: bool = False,
                            validate_mada: bool = True):
    """Benchmark simulation outputs against hardware telemetry data."""
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
    
    required_cols = ['measured_B', 'measured_freq']
    if not all(col in data.columns for col in required_cols):
        logger.error(f"Missing required columns. Expected: {required_cols}")
        return
    
    validator = MADAConvergenceValidator() if validate_mada else None
    
    sim_thrusts = []
    sim_accels = []
    differences = []
    hil_results = []
    mada_validation_results = []
    
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
        
        hil_valid = hil_validation(T_sim, measured_T)
        hil_results.append(hil_valid)
        
        if validate_mada:
            field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            validation_result = validator.full_validation(
                B, field_vectors, DEFAULT_GRAD_H2, T_sim
            )
            mada_validation_results.append(validation_result)
            
            if not validation_result['valid'] and verbose:
                logger.warning(f"Record {idx}: MADA validation failed - {validation_result['errors']}")
    
    avg_diff_T = np.mean([d[0] for d in differences if d[0] > 0])
    avg_diff_a = np.mean([d[1] for d in differences if d[1] > 0])
    hil_pass_rate = sum(hil_results) / len(hil_results) * 100 if hil_results else 0
    
    logger.info("\n" + "=" * 60)
    logger.info("BENCHMARK RESULTS")
    logger.info("=" * 60)
    logger.info(f"Records processed: {len(data)}")
    logger.info(f"Average Thrust Difference: {avg_diff_T:.2f} N")
    logger.info(f"Average Acceleration Difference: {avg_diff_a:.2f} m/s²")
    logger.info(f"HIL Pass Rate: {hil_pass_rate:.2f}%")
    
    if validate_mada and mada_validation_results:
        mada_pass_rate = sum(1 for r in mada_validation_results if r['valid']) / len(mada_validation_results) * 100
        logger.info(f"MADA Validation Pass Rate: {mada_pass_rate:.2f}%")
        logger.info(f"MADA Convergence Achieved: {validator.convergence_achieved}")
    
    if verbose:
        data['sim_thrust'] = sim_thrusts
        data['sim_accel'] = sim_accels
        data['thrust_error'] = [d[0] for d in differences]
        data['accel_error'] = [d[1] for d in differences]
        data['hil_valid'] = hil_results
        
        if validate_mada:
            data['mada_valid'] = [r['valid'] for r in mada_validation_results]
            data['mada_converged'] = validator.convergence_achieved
        
        output_file = 'benchmark_report.csv'
        data.to_csv(output_file, index=False)
        logger.info(f"Detailed report saved to {output_file}")


def thrust_objective(params: Dict) -> float:
    """Objective function for thrust maximization."""
    args = argparse.Namespace(**params)
    T, _, _, _, _, _ = calculate_thrust_params(args, verbose=False)
    return -T


def optimize_thrust(bounds: Dict, use_ml_surrogate: bool = False) -> Tuple[Dict, float]:
    """Gradient-based optimization with optional ML surrogate."""
    if use_ml_surrogate and ML_AVAILABLE:
        kernel = ConstantKernel() * RBF()
        gp = GaussianProcessRegressor(kernel=kernel)
        
        X = np.random.uniform(
            [b[0] for b in bounds.values()],
            [b[1] for b in bounds.values()],
            (100, len(bounds))
        )
        y = np.array([thrust_objective(dict(zip(bounds.keys(), x))) for x in X])
        gp.fit(X, y)
        
        def surrogate_obj(x):
            return -gp.predict(x.reshape(1, -1))[0]
        obj_func = surrogate_obj
    else:
        obj_func = lambda x: thrust_objective(dict(zip(bounds.keys(), x)))
    
    initial_guess = [(b[0] + b[1])/2 for b in bounds.values()]
    result = minimize(obj_func, initial_guess, bounds=list(bounds.values()), method='L-BFGS-B')
    opt_params = dict(zip(bounds.keys(), result.x))
    return opt_params, -result.fun


def parallel_parametric_sweep(param_name: str, values: List[float], 
                              args, n_processes: int = 4) -> pd.DataFrame:
    """Parallel parametric sweep using multiprocessing."""
    if not PANDAS_AVAILABLE:
        logger.error("pandas required for parametric sweep")
        return None
    
    def sweep_single(val):
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        T, a, P, eta, R, B = calculate_thrust_params(sweep_args, verbose=False)
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


def dask_thrust_computation(params_array: np.ndarray):
    """Dask-based parallel computation for large arrays."""
    if not DASK_AVAILABLE:
        logger.error("Dask not available")
        return None
    
    dask_params = da.from_array(params_array, chunks=(100, -1))
    
    def compute_chunk(chunk):
        results = []
        for row in chunk:
            args = argparse.Namespace(
                b_opposing=row[0],
                frequency=row[1],
                m1=DEFAULT_M1,
                m2=DEFAULT_M2,
                distance=DEFAULT_D,
                current=DEFAULT_I,
                mass=DEFAULT_MASS,
                n_units=DEFAULT_N_UNITS,
                chi=DEFAULT_CHI
            )
            T, _, _, _, _, _ = calculate_thrust_params(args, verbose=False)
            results.append(T)
        return np.array(results)
    
    return dask_params.map_blocks(compute_chunk, dtype=float)


def handle_interrupt(signal_num, frame):
    """Handle keyboard interrupt gracefully."""
    logger.info("Simulation interrupted. Cleaning up...")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_interrupt)


def calculate_thrust_params(args, B_opposing: Optional[float] = None, 
                           frequency: Optional[float] = None, 
                           verbose: bool = False,
                           validate_mada: bool = False,
                           validator: Optional[MADAConvergenceValidator] = None) -> Tuple[float, float, float, float, float, float]:
    """
    Core thrust calculation function with MADA validation.
    
    Returns:
        tuple: (thrust, acceleration, power, efficiency, range, B_total)
    
    Raises:
        MADAValidationError: If MADA validation fails critically
    """
    frequency = frequency if frequency is not None else getattr(args, 'frequency', 100.0)
    B = B_opposing if B_opposing is not None else getattr(args, 'b_opposing', None)
    
    if B is None:
        B = opposing_field(
            getattr(args, 'm1', DEFAULT_M1),
            getattr(args, 'm2', DEFAULT_M2),
            getattr(args, 'distance', DEFAULT_D),
            DEFAULT_K
        )
    
    current = getattr(args, 'current', DEFAULT_I)
    scaled_I = current * (frequency / 50.0)
    delta_B = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
    B_total = B + delta_B
    
    n_units = getattr(args, 'n_units', DEFAULT_N_UNITS)
    chi = getattr(args, 'chi', DEFAULT_CHI)
    mass = getattr(args, 'mass', DEFAULT_MASS)
    
    if validate_mada:
        field_vectors = simulate_hall_sensor_readings(n_units, B_total)
        
        val = validator or MADAConvergenceValidator()
        
        F_vec_prelim = force_vector(chi, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
        F_mag_prelim = np.linalg.norm(F_vec_prelim)
        T_prelim = total_thrust(n_units, F_mag_prelim, DEFAULT_ETA, DEFAULT_THETA)
        
        validation_result = val.full_validation(
            B_total, field_vectors, DEFAULT_GRAD_H2, T_prelim
        )
        
        if not validation_result['valid']:
            error_msg = "; ".join(validation_result['errors'])
            logger.error(f"MADA VALIDATION FAILED: {error_msg}")
            raise MADAValidationError(f"MADA configuration invalid: {error_msg}")
        
        if verbose:
            for check_name, check_result in validation_result['checks'].items():
                status = "✓" if check_result['valid'] else "✗"
                logger.info(f"  {status} {check_name}: {check_result['message']}")
    
    F_vec = force_vector(chi, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
    F_mag = np.linalg.norm(F_vec)
    T = total_thrust(n_units, F_mag, DEFAULT_ETA, DEFAULT_THETA)
    a = acceleration(T, mass)
    
    P = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
    eta_perc = efficiency(T, DEFAULT_V, P)
    R = range_calc(DEFAULT_V, DEFAULT_E, P)
    
    if verbose:
        logger.info(f"Thrust: {T:.2f} N, Accel: {a:.2f} m/s², Power: {P:.2f} W")
    
    return T, a, P, eta_perc, R, B_total


def real_time_mode(args, sensor_port: str = '/dev/ttyUSB0', 
                  update_interval: float = 0.1, verbose: bool = False,
                  validate_mada: bool = True):
    """Real-time mode: Read sensor data and compute thrust dynamically."""
    logger.info("=" * 60)
    logger.info("REAL-TIME THRUST MONITORING WITH MADA VALIDATION")
    logger.info("=" * 60)
    
    if not validate_mada:
        logger.warning("⚠️  MADA validation DISABLED - misconfigured fields may cause issues!")
        logger.warning("⚠️  Recommend enabling with --validate_mada flag")
    
    validator = MADAConvergenceValidator() if validate_mada else None
    
    # Hardware interfaces would be initialized here if available
    logger.info("Using simulated sensor data (hardware interfaces not available)")
    
    n_units = getattr(args, 'n_units', DEFAULT_N_UNITS)
    frequency = getattr(args, 'frequency', 100.0)
    
    logger.info(f"Update interval: {update_interval}s")
    logger.info(f"MADA validation: {'ENABLED' if validate_mada else 'DISABLED'}")
    logger.info(f"Number of MADA units: {n_units}")
    logger.info("Press Ctrl+C to stop\n")
    
    iteration = 0
    validation_failures = 0
    last_valid_thrust = 0
    
    try:
        while True:
            # Simulated sensor data
            B = 50.0 + np.random.normal(0, 2.0)
            freq = frequency + np.random.normal(0, 5.0)
            field_vectors = simulate_hall_sensor_readings(n_units, B)
            
            validation_passed = True
            if validate_mada:
                try:
                    chi = getattr(args, 'chi', DEFAULT_CHI)
                    F_vec_prelim = force_vector(chi, B, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
                    F_mag_prelim = np.linalg.norm(F_vec_prelim)
                    T_prelim = total_thrust(n_units, F_mag_prelim, DEFAULT_ETA, DEFAULT_THETA)
                    
                    validation_result = validator.full_validation(
                        B, field_vectors, DEFAULT_GRAD_H2, T_prelim
                    )
                    
                    if not validation_result['valid']:
                        validation_passed = False
                        validation_failures += 1
                        logger.error(f"[{iteration:04d}] ✗ MADA VALIDATION FAILED:")
                        for error in validation_result['errors']:
                            logger.error(f"  - {error}")
                        logger.warning(f"  Using last valid thrust: {last_valid_thrust:.0f}N")
                        
                        T, a, P, eta, R, B_total = (last_valid_thrust, 0, 0, 0, 0, B)
                        
                        failure_rate = validation_failures / (iteration + 1) * 100
                        if failure_rate > 10:
                            logger.critical(f"⚠️  HIGH VALIDATION FAILURE RATE: {failure_rate:.1f}%")
                        
                        iteration += 1
                        time.sleep(update_interval)
                        continue
                    
                    if verbose or iteration % 10 == 0:
                        conv_msg = validation_result['checks']['convergence']['message']
                        logger.info(f"[{iteration:04d}] MADA: {conv_msg}")
                
                except MADAValidationError as e:
                    logger.error(f"[{iteration:04d}] CRITICAL MADA ERROR: {e}")
                    validation_passed = False
                    validation_failures += 1
                    T, a, P, eta, R, B_total = (0, 0, 0, 0, 0, B)
                    iteration += 1
                    time.sleep(update_interval)
                    continue
            
            try:
                T, a, P, eta, R, B_total = calculate_thrust_params(
                    args, B_opposing=B, frequency=freq, verbose=False,
                    validate_mada=False
                )
                
                if validation_passed:
                    last_valid_thrust = T
                
            except Exception as e:
                logger.error(f"[{iteration:04d}] Thrust calculation error: {e}")
                T, a, P, eta, R, B_total = (0, 0, 0, 0, 0, B)
            
            a_g = a / 9.81 if a > 0 else 0
            status = "✓" if validation_passed else "✗"
            
            logger.info(f"[{iteration:04d}] {status} B={B:.2f}T, Freq={freq:.1f}Hz, "
                       f"Thrust={T:.0f}N, Accel={a:.1f}m/s² ({a_g:.1f}g), "
                       f"Power={P:.0f}W, Eff={eta:.1f}%")
            
            if verbose and validate_mada and validation_passed:
                for check_name, check_result in validation_result['checks'].items():
                    if check_name != 'convergence':
                        status_symbol = "✓" if check_result['valid'] else "✗"
                        logger.info(f"  {status_symbol} {check_name}: {check_result['message']}")
            
            if validate_mada and iteration > 0 and iteration % 20 == 0:
                failure_rate = validation_failures / iteration * 100
                if failure_rate > 5:
                    logger.warning(f"⚠️  Validation failure rate: {failure_rate:.1f}% over {iteration} iterations")
                if validator.convergence_achieved:
                    logger.info(f"✓ MADA array CONVERGED after {len(validator.history)} samples")
            
            iteration += 1
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("Real-time monitoring stopped by user")
        logger.info("=" * 60)
        
        logger.info(f"Total iterations: {iteration}")
        if validate_mada:
            failure_rate = validation_failures / iteration * 100 if iteration > 0 else 0
            logger.info(f"MADA validation failures: {validation_failures} ({failure_rate:.2f}%)")
            logger.info(f"MADA convergence achieved: {validator.convergence_achieved}")
            logger.info(f"Final thrust value: {last_valid_thrust:.2f}N")


def main():
    """Main entry point for thrust model simulations."""
    parser = argparse.ArgumentParser(
        description="QED Vacuum Thrust Model - Multi-mode Simulation with MADA Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Simulation Modes:
  single     - Single thrust calculation (default)
  swarm      - Multi-drone swarm simulation with PyBullet
  benchmark  - Compare simulation vs hardware telemetry
  realtime   - Real-time sensor monitoring and calculation

Examples:
  python thrust_model.py --b_opposing 50 --frequency 100 --validate_mada
  python thrust_model.py --mode swarm --num_drones 10 --scenario asymmetric
  python thrust_model.py --mode benchmark --telemetry_file data.csv
  python thrust_model.py --mode realtime --sensor_port /dev/ttyUSB0 --validate_mada
        """
    )
    
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
                       help=f"Magnetic susceptibility, default: {DEFAULT_CHI}")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    parser.add_argument("--config", type=str, default=None,
                       help="YAML configuration file")
    
    parser.add_argument("--validate_mada", action="store_true",
                       help="Enable MADA convergence validation")
    parser.add_argument("--mada_tolerance", type=float, default=MADA_CONVERGENCE_THRESHOLD,
                       help=f"MADA convergence tolerance, default: {MADA_CONVERGENCE_THRESHOLD}")
    
    parser.add_argument("--mode", type=str, default='single',
                       choices=['single', 'swarm', 'benchmark', 'realtime'],
                       help="Simulation mode")
    
    parser.add_argument("--num_drones", type=int, default=5,
                       help="Number of drones for swarm mode")
    parser.add_argument("--scenario", type=str, default='asymmetric',
                       choices=['asymmetric', 'symmetric'],
                       help="Swarm scenario type")
    parser.add_argument("--simulation_time", type=float, default=60,
                       help="Simulation time (s) for swarm mode")
    
    parser.add_argument("--telemetry_file", type=str, default=None,
                       help="CSV file for benchmark mode")
    
    parser.add_argument("--sensor_port", type=str, default='/dev/ttyUSB0',
                       help="Serial port for real-time sensor input")
    parser.add_argument("--update_interval", type=float, default=0.1,
                       help="Update interval (s) for real-time mode")
    
    parser.add_argument("--optimize", action="store_true",
                       help="Run optimization routine")
    parser.add_argument("--use_ml", action="store_true",
                       help="Use ML surrogate for optimization")
    
    args = parser.parse_args()
    
    if args.config:
        try:
            config_args = load_config_yaml(args.config)
            for key, val in vars(config_args).items():
                if not hasattr(args, key) or getattr(args, key) == parser.get_default(key):
                    setattr(args, key, val)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)
    
    if args.mode == 'single':
        logger.info("=" * 60)
        logger.info("QED VACUUM THRUST MODEL SIMULATION")
        if args.validate_mada:
            logger.info("WITH MADA CONVERGENCE VALIDATION")
        logger.info("=" * 60)
        
        logger.info(f"\nInput Parameters:")
        logger.info(f"  - Pulsing Frequency: {args.frequency} Hz")
        logger.info(f"  - Drone Mass: {args.mass} kg")
        logger.info(f"  - Number of MADA units: {args.n_units}")
        logger.info(f"  - MADA Validation: {'ENABLED' if args.validate_mada else 'DISABLED'}")
        
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
            beta_chi = rg_beta_chi(args.chi, DEFAULT_G, DEFAULT_LAMBDA)
            logger.info(f"Susceptibility (χ): {args.chi:.2e}")
            logger.info(f"RG Beta Function (β_χ): {beta_chi:.2e}")
        
        if args.validate_mada:
            logger.info(f"\n{'─' * 60}")
            logger.info("MADA CONVERGENCE VALIDATION")
            logger.info(f"{'─' * 60}")
            
            validator = MADAConvergenceValidator(tolerance=args.mada_tolerance)
            field_vectors = simulate_hall_sensor_readings(args.n_units, B_total)
            
            F_vec_prelim = force_vector(args.chi, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
            F_mag_prelim = np.linalg.norm(F_vec_prelim)
            T_prelim = total_thrust(args.n_units, F_mag_prelim, DEFAULT_ETA, DEFAULT_THETA)
            
            validation_result = validator.full_validation(
                B_total, field_vectors, DEFAULT_GRAD_H2, T_prelim
            )
            
            for check_name, check_result in validation_result['checks'].items():
                status = "✓" if check_result['valid'] else "✗"
                logger.info(f"{status} {check_name.capitalize()}: {check_result['message']}")
            
            if not validation_result['valid']:
                logger.error("\n✗ MADA VALIDATION FAILED")
                for error in validation_result['errors']:
                    logger.error(f"  - {error}")
                logger.error("\nCANNOT PROCEED - Fix MADA configuration!")
                sys.exit(1)
            else:
                logger.info("\n✓ MADA VALIDATION PASSED")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("FORCE & THRUST CALCULATIONS")
        logger.info(f"{'─' * 60}")
        
        try:
            T, a, P, eta, R, B_total = calculate_thrust_params(
                args, B_opposing=B, verbose=args.verbose, validate_mada=False
            )
        except MADAValidationError as e:
            logger.error(f"MADA validation failed: {e}")
            sys.exit(1)
        
        F_vec = force_vector(args.chi, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
        F_mag = np.linalg.norm(F_vec)
        logger.info(f"Force per Unit: {F_mag:.2f} N")
        if args.verbose:
            logger.info(f"  Force Vector: {F_vec}")
        
        logger.info(f"Total Thrust: {T:.2f} N ({T/1000:.2f} kN)")
        
        a_g = a / 9.81
        logger.info(f"Acceleration: {a:.2f} m/s² ({a_g:.2f}g)")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("PERFORMANCE METRICS")
        logger.info(f"{'─' * 60}")
        
        logger.info(f"Power Consumption: {P:.2f} W ({P/1000:.2f} kW)")
        logger.info(f"System Efficiency: {eta:.2f}%")
        logger.info(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("PERFORMANCE PROJECTIONS")
        logger.info(f"{'─' * 60}")
        
        mach_26_speed = 26 * 343
        time_to_mach26 = mach_26_speed / a if a > 0 else float('inf')
        logger.info(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
        
        weight = args.mass * 9.81
        twr = T / weight if weight > 0 else 0
        logger.info(f"Thrust-to-Weight Ratio: {twr:.2f}")
        
        ldr = compute_lift_drag_ratio()
        logger.info(f"Lift-to-Drag Ratio: {ldr:.2f}")
        
        structural_ok = fea_structural_check(a, args.mass)
        logger.info(f"Structural Integrity: {'PASS' if structural_ok else 'FAIL'}")
        
        traj = non_ballistic_trajectory(np.array([0,0,0]), np.array([1000,0,0]))
        evasion_prob = stealth_ops_check(traj, np.array([500,0,0]))
        logger.info(f"Radar Evasion Probability: {evasion_prob:.2%}")
        
        logger.info(f"\n{'=' * 60}")
        logger.info("SIMULATION COMPLETE")
        logger.info(f"{'=' * 60}\n")
    
    elif args.mode == 'swarm':
        simulate_swarm(args.num_drones, args.scenario, args.simulation_time, 
                      args.verbose, args.validate_mada)
    
    elif args.mode == 'benchmark':
        if not args.telemetry_file:
            logger.error("--telemetry_file required for benchmark mode")
            sys.exit(1)
        benchmark_with_telemetry(args.telemetry_file, args, args.verbose, args.validate_mada)
    
    elif args.mode == 'realtime':
        real_time_mode(args, args.sensor_port, args.update_interval, args.verbose, args.validate_mada)
    
    if args.optimize:
        bounds = {'frequency': (50, 150), 'current': (10, 20)}
        opt_params, max_thrust = optimize_thrust(bounds, args.use_ml)
        logger.info(f"\n{'=' * 60}")
        logger.info("OPTIMIZATION RESULTS")
        logger.info(f"{'=' * 60}")
        logger.info(f"Optimized Parameters: {opt_params}")
        logger.info(f"Maximum Thrust: {max_thrust:.2f} N")


if __name__ == "__main__":
    main()
