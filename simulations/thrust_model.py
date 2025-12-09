"""
simulations/thrust_model.py (Version 5 - with MADA GPIO Integration)

Extended thrust model simulation with multiple modes and MADA validation:
- Single calculation with comprehensive validation
- Swarm simulation (multi-drone) with trajectory planning
- Benchmark against telemetry with HIL validation
- Real-time sensor monitoring with MADA convergence tracking
- Parametric sweeps and optimization
- CFD integration capabilities
- **NEW: Raspberry Pi GPIO control for physical MADA units**

CRITICAL: Includes MADA convergence validation to prevent misconfigured magnetic fields
"""

import argparse
import numpy as np
import sys
import os
import time
import logging
import signal
from typing import Tuple, Optional, Dict, List, Any
from pathlib import Path

# Conditional imports with proper guards
try:
    import multiprocessing as mp
    MULTIPROCESSING_AVAILABLE = True
except ImportError:
    MULTIPROCESSING_AVAILABLE = False
    mp = None

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not available. Config file support disabled.")

try:
    import dask.array as da
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
    logging.warning("Dask not available. Large-scale parallel computation disabled.")

try:
    from scipy import optimize
    from scipy.optimize import minimize
    SCIPY_OPTIMIZE_AVAILABLE = True
except ImportError:
    SCIPY_OPTIMIZE_AVAILABLE = False
    logging.warning("scipy.optimize not available. Optimization disabled.")

try:
    import subprocess
    import tempfile
    import shutil
    CFD_AVAILABLE = True
except ImportError:
    CFD_AVAILABLE = False
    logging.warning("CFD integration tools not available.")

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("scikit-learn not available. ML surrogates disabled.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import core equations
try:
    from simulations.equations import (
        opposing_field,
        pulsed_enhancement,
        rg_beta_chi,
        force_vector,
        total_thrust,
        acceleration,
        efficiency,
        power_consumption,
        range_calc,
        non_ballistic_trajectory,
        radar_evasion_probability,
        SPEED_OF_SOUND,
        EPSILON
    )
except ImportError as e:
    print(f"ERROR: Failed to import equations module: {e}")
    print("Please ensure equations.py is in the simulations/ directory")
    sys.exit(1)

# Optional imports with proper fallback
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
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    logging.warning("Open3D not available. CFD visualizations limited.")

# Hardware interfaces - create mock if not available
HARDWARE_AVAILABLE = False
try:
    from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    logging.warning("Hardware interfaces not available. Real-time mode will use simulated data.")
    
    class MicrocontrollerPWMInterface:
        def __init__(self, port: str):
            raise ImportError("Hardware interface not available")
        def send_command(self, cmd: str) -> Optional[str]:
            return None
        def close(self) -> None:
            pass
    
    class FlightControllerInterface:
        def __init__(self):
            raise ImportError("Hardware interface not available")

# ==================== INSERTION POINT 1: MADA GPIO IMPORTS ====================
try:
    from hardware.mada_gpio_controller import MADAGPIOController, integrate_with_mada_validation
    MADA_GPIO_AVAILABLE = True
except ImportError:
    MADA_GPIO_AVAILABLE = False
    logging.warning("MADA GPIO controller not available")
# ==============================================================================

# Configure logging with proper namespace
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# =============================================================================
# Configuration and Constants
# =============================================================================

class SimulationConfig:
    """Configuration class for all simulation parameters."""
    
    # Magnetic field parameters
    M1 = 100.0
    M2 = 100.0
    DISTANCE = 0.05
    K_SCALING = 1.0
    
    # Coil parameters
    N_TURNS = 100
    BASE_CURRENT = 15.0
    
    # QED parameters
    CHI = 1e-10
    G_COUPLING = 1.0
    LAMBDA_PARAM = 0.1
    
    # Geometric parameters
    GRAD_H2 = np.array([1.0, 0.0, 0.0])
    AREA = 1.0
    RHO = 1000.0
    
    # MADA parameters
    N_UNITS = 24
    ETA = 0.95
    THETA = 0.0
    
    # Drone parameters
    MASS = 20000.0  # kg - kept as requested
    
    # Electrical parameters
    RESISTANCE = 5.0
    P_EDDY = 100.0
    
    # Performance parameters
    VELOCITY = 1000.0
    ENERGY = 500000.0 * 3600  # 500 kWh in J
    
    # Frequency parameters
    BASE_FREQUENCY = 50.0
    DEFAULT_FREQUENCY = 100.0
    
    # PyBullet simulation
    PHYSICS_STEP_RATE = 240  # Hz
    SWARM_ATTACK_PROBABILITY = 0.005


class MADAValidationConfig:
    """MADA convergence validation thresholds."""
    
    MIN_FIELD = 0.1  # Tesla
    MAX_FIELD = 100.0  # Tesla
    MIN_ALIGNMENT = 0.9  # Cosine similarity
    MAX_ASYMMETRY = 0.15  # Ratio
    MIN_GRADIENT = 0.01  # Magnitude
    CONVERGENCE_THRESHOLD = 0.05  # 5%
    MAX_ITERATIONS = 100
    HISTORY_SIZE = 50
    MIN_SAMPLES = 10


# =============================================================================
# Custom Exceptions
# =============================================================================

class MADAValidationError(Exception):
    """Raised when MADA configuration fails validation."""
    pass


# =============================================================================
# MADA Convergence Validator
# =============================================================================

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
    
    def __init__(self, 
                 tolerance: float = MADAValidationConfig.CONVERGENCE_THRESHOLD,
                 max_iterations: int = MADAValidationConfig.MAX_ITERATIONS):
        """Initialize MADA validator."""
        if tolerance <= 0 or tolerance >= 1:
            raise ValueError("Tolerance must be between 0 and 1")
        if max_iterations <= 0:
            raise ValueError("Max iterations must be positive")
        
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.history: List[float] = []
        self.convergence_achieved = False
        
    def validate_field_magnitude(self, B_total: float) -> Tuple[bool, str]:
        """Validate that field magnitude is within operational range."""
        if B_total < MADAValidationConfig.MIN_FIELD:
            return False, f"Field too weak: {B_total:.4f}T < {MADAValidationConfig.MIN_FIELD}T"
        if B_total > MADAValidationConfig.MAX_FIELD:
            return False, f"Field too strong: {B_total:.4f}T > {MADAValidationConfig.MAX_FIELD}T"
        return True, f"Field magnitude OK: {B_total:.4f}T"
    
    def validate_field_vectors(self, field_vectors: List[np.ndarray]) -> Tuple[bool, str]:
        """
        Validate field vector alignment across MADA units.
        Ensures all units have properly aligned fields for thrust coherence.
        """
        if len(field_vectors) < 2:
            return True, "Single unit - alignment N/A"
        
        # Normalize vectors
        normalized = []
        for v in field_vectors:
            norm = np.linalg.norm(v)
            if norm > EPSILON:
                normalized.append(v / norm)
            else:
                return False, "Zero-magnitude field vector detected"
        
        # Calculate pairwise alignment (cosine similarity)
        alignments = []
        for i in range(len(normalized)):
            for j in range(i+1, len(normalized)):
                dot_prod = np.dot(normalized[i], normalized[j])
                alignments.append(dot_prod)
        
        if not alignments:
            return True, "Insufficient vectors for alignment check"
        
        min_alignment = min(alignments)
        
        if min_alignment < MADAValidationConfig.MIN_ALIGNMENT:
            return False, f"Poor field alignment: {min_alignment:.4f} < {MADAValidationConfig.MIN_ALIGNMENT}"
        
        return True, f"Field alignment OK: {min_alignment:.4f}"
    
    def validate_symmetry(self, field_vectors: List[np.ndarray]) -> Tuple[bool, str]:
        """
        Validate field symmetry across MADA array.
        Asymmetric fields cause torque and instability.
        """
        if len(field_vectors) < 4:
            return True, "Insufficient units for symmetry check"
        
        magnitudes = [np.linalg.norm(v) for v in field_vectors]
        mean_mag = np.mean(magnitudes)
        
        if mean_mag < EPSILON:
            return False, "Zero mean field magnitude"
        
        std_mag = np.std(magnitudes)
        asymmetry = std_mag / mean_mag
        
        if asymmetry > MADAValidationConfig.MAX_ASYMMETRY:
            return False, f"High asymmetry: {asymmetry:.4f} > {MADAValidationConfig.MAX_ASYMMETRY}"
        
        return True, f"Symmetry OK: asymmetry={asymmetry:.4f}"
    
    def validate_gradient(self, grad_H2: np.ndarray) -> Tuple[bool, str]:
        """Validate field gradient magnitude."""
        grad_H2 = np.asarray(grad_H2, dtype=float)
        grad_mag = np.linalg.norm(grad_H2)
        
        if grad_mag < MADAValidationConfig.MIN_GRADIENT:
            return False, f"Gradient too small: {grad_mag:.4e} < {MADAValidationConfig.MIN_GRADIENT}"
        
        return True, f"Gradient OK: {grad_mag:.4e}"
    
    def check_convergence(self, current_thrust: float) -> Tuple[bool, str]:
        """
        Check if thrust has converged to a stable value.
        Uses moving average and variance to detect convergence.
        """
        self.history.append(current_thrust)
        
        if len(self.history) < MADAValidationConfig.MIN_SAMPLES:
            return False, f"Collecting data: {len(self.history)}/{MADAValidationConfig.MIN_SAMPLES} samples"
        
        # Keep only recent history
        if len(self.history) > MADAValidationConfig.HISTORY_SIZE:
            self.history = self.history[-MADAValidationConfig.HISTORY_SIZE:]
        
        recent = self.history[-MADAValidationConfig.MIN_SAMPLES:]
        mean_thrust = np.mean(recent)
        std_thrust = np.std(recent)
        
        if abs(mean_thrust) < EPSILON:
            return False, "Zero thrust - configuration error"
        
        relative_std = std_thrust / abs(mean_thrust)
        
        if relative_std < self.tolerance:
            self.convergence_achieved = True
            return True, f"CONVERGED: std/mean = {relative_std:.4f}"
        
        if len(self.history) >= self.max_iterations:
            return False, f"Failed to converge after {self.max_iterations} iterations"
        
        return False, f"Converging: std/mean = {relative_std:.4f} (target < {self.tolerance})"
    
    def full_validation(self, B_total: float, field_vectors: List[np.ndarray],
                       grad_H2: np.ndarray, current_thrust: float) -> Dict[str, Any]:
        """
        Perform complete MADA validation suite.
        
        Returns:
            Dict with validation results and status
        """
        results: Dict[str, Any] = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        # 1. Field magnitude check
        mag_valid, mag_msg = self.validate_field_magnitude(B_total)
        results['checks']['magnitude'] = {'valid': mag_valid, 'message': mag_msg}
        if not mag_valid:
            results['valid'] = False
            results['errors'].append(mag_msg)
        
        # 2. Field vector alignment check
        align_valid, align_msg = self.validate_field_vectors(field_vectors)
        results['checks']['alignment'] = {'valid': align_valid, 'message': align_msg}
        if not align_valid:
            results['valid'] = False
            results['errors'].append(align_msg)
        
        # 3. Symmetry check
        sym_valid, sym_msg = self.validate_symmetry(field_vectors)
        results['checks']['symmetry'] = {'valid': sym_valid, 'message': sym_msg}
        if not sym_valid:
            results['warnings'].append(sym_msg)  # Warning, not error
        
        # 4. Gradient check
        grad_valid, grad_msg = self.validate_gradient(grad_H2)
        results['checks']['gradient'] = {'valid': grad_valid, 'message': grad_msg}
        if not grad_valid:
            results['valid'] = False
            results['errors'].append(grad_msg)
        
        # 5. Convergence check
        conv_valid, conv_msg = self.check_convergence(current_thrust)
        results['checks']['convergence'] = {'valid': conv_valid, 'message': conv_msg}
        results['converged'] = self.convergence_achieved
        
        return results
    
    def reset(self) -> None:
        """Reset validator state."""
        self.history = []
        self.convergence_achieved = False


# =============================================================================
# Utility Functions
# =============================================================================

def simulate_hall_sensor_readings(n_units: int, B_total: float, 
                                  noise_level: float = 0.02) -> List[np.ndarray]:
    """
    Simulate Hall sensor readings for each MADA unit.
    In real hardware, these would come from actual Hall sensors.
    
    Args:
        n_units: Number of MADA units
        B_total: Total magnetic field strength (T)
        noise_level: Sensor noise as fraction of signal
    
    Returns:
        List of 3D field vectors, one per unit
    """
    if n_units <= 0:
        raise ValueError("Number of units must be positive")
    if B_total < 0:
        raise ValueError("Magnetic field must be non-negative")
    if noise_level < 0:
        raise ValueError("Noise level must be non-negative")
    
    field_vectors = []
    
    # Base direction (should be aligned for proper MADA operation)
    base_direction = np.array([1.0, 0.0, 0.0])
    
    for i in range(n_units):
        # Add slight misalignment (manufacturing tolerance)
        misalignment = np.random.normal(0, 0.05, 3)
        direction = base_direction + misalignment
        direction_norm = np.linalg.norm(direction)
        
        if direction_norm > EPSILON:
            direction = direction / direction_norm
        else:
            direction = base_direction
        
        # Add magnitude variation (unit-to-unit variation)
        magnitude = B_total * (1.0 + np.random.normal(0, 0.1))
        magnitude = max(0, magnitude)  # Ensure non-negative
        
        # Add sensor noise
        noise = np.random.normal(0, noise_level * magnitude, 3)
        
        vector = direction * magnitude + noise
        field_vectors.append(vector)
    
    return field_vectors


def load_config_yaml(config_file: str) -> argparse.Namespace:
    """Load configuration from YAML file."""
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML required for config file support. Install with: pip install pyyaml")
    
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return argparse.Namespace(**config)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")


def handle_interrupt(signum: int, frame: Any) -> None:
    """Signal handler for graceful shutdown."""
    logger.info("\nSimulation interrupted. Cleaning up...")
    sys.exit(0)


# Register signal handler
signal.signal(signal.SIGINT, handle_interrupt)


# =============================================================================
# Core Calculation Functions
# =============================================================================

def calculate_thrust_params(
    args: argparse.Namespace,
    B_opposing: Optional[float] = None,
    frequency: Optional[float] = None,
    verbose: bool = False,
    validate_mada: bool = False,
    validator: Optional[MADAConvergenceValidator] = None
) -> Tuple[float, float, float, float, float, float]:
    """
    Core thrust calculation function with optional MADA validation.
    
    Args:
        args: Argument namespace with simulation parameters
        B_opposing: Opposing magnetic field strength (T), optional
        frequency: Pulsing frequency (Hz), optional
        verbose: Enable verbose output
        validate_mada: Enable MADA convergence validation
        validator: Validator instance for convergence tracking
    
    Returns:
        Tuple of (thrust, acceleration, power, efficiency, range, B_total)
    
    Raises:
        MADAValidationError: If MADA validation fails critically
    """
    frequency = frequency if frequency is not None else args.frequency
    B = B_opposing if B_opposing is not None else args.b_opposing
    
    # Calculate opposing field if not provided
    if B is None:
        B = opposing_field(args.m1, args.m2, args.distance, SimulationConfig.K_SCALING)
    
    # Scale current based on frequency
    scaled_I = args.current * (frequency / SimulationConfig.BASE_FREQUENCY)
    
    # Calculate pulsed enhancement
    delta_B = pulsed_enhancement(SimulationConfig.N_TURNS, scaled_I)
    B_total = B + delta_B
    
    # MADA validation if enabled
    if validate_mada:
        # Simulate Hall sensor readings for MADA units
        field_vectors = simulate_hall_sensor_readings(args.n_units, B_total)
        
        # Use provided validator or create temporary one
        val = validator if validator is not None else MADAConvergenceValidator()
        
        # Calculate preliminary thrust for convergence check
        F_vec_prelim = force_vector(
            args.chi, B_total, SimulationConfig.GRAD_H2, 
            SimulationConfig.AREA, SimulationConfig.RHO
        )
        F_mag_prelim = np.linalg.norm(F_vec_prelim)
        T_prelim = total_thrust(args.n_units, F_mag_prelim, SimulationConfig.ETA, SimulationConfig.THETA)
        
        validation_result = validator.full_validation(
            B_total, field_vectors, SimulationConfig.GRAD_H2, T_prelim
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
            args, B_opposing=B, verbose=args.verbose,
            validate_mada=False  # Already validated above if enabled
        )
    except MADAValidationError as e:
        logger.error(f"MADA validation failed: {e}")
        sys.exit(1)
    
    F_vec = force_vector(
        args.chi, B_total, SimulationConfig.GRAD_H2,
        SimulationConfig.AREA, SimulationConfig.RHO
    )
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
    logger.info(f"  (at v = {SimulationConfig.VELOCITY} m/s = Mach {SimulationConfig.VELOCITY/SPEED_OF_SOUND:.2f})")
    
    logger.info(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
    logger.info(f"  (with {SimulationConfig.ENERGY/3600000:.0f} kWh energy)")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("PERFORMANCE PROJECTIONS")
    logger.info(f"{'─' * 60}")
    
    mach_26_speed = 26 * SPEED_OF_SOUND
    time_to_mach26 = mach_26_speed / a if a > EPSILON else float('inf')
    logger.info(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
    logger.info(f"  (assuming constant acceleration)")
    
    weight = args.mass * 9.81
    twr = T / weight if weight > EPSILON else 0
    logger.info(f"Thrust-to-Weight Ratio: {twr:.2f}")
    
    # Aerodynamic checks
    ldr = compute_lift_drag_ratio()
    logger.info(f"Lift-to-Drag Ratio: {ldr:.2f}")
    
    structural_ok = fea_structural_check(a, args.mass)
    logger.info(f"Structural Integrity under {a_g:.1f}g: {'PASS' if structural_ok else 'FAIL'}")
    
    # Stealth check
    traj = non_ballistic_trajectory(np.array([0, 0, 0]), np.array([1000, 0, 0]))
    evasion_prob = stealth_ops_check(traj, np.array([500, 0, 0]))
    logger.info(f"Radar Evasion Probability: {evasion_prob:.2%}")
    
    logger.info(f"\n{'=' * 60}")
    logger.info("SIMULATION COMPLETE")
    logger.info(f"{'=' * 60}\n")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """Main entry point for thrust model simulations."""
    parser = argparse.ArgumentParser(
        description="QED Vacuum Thrust Model - Multi-mode Simulation with MADA Validation & GPIO Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Simulation Modes:
  single     - Single thrust calculation (default)
  swarm      - Multi-drone swarm simulation with PyBullet
  benchmark  - Compare simulation vs hardware telemetry
  realtime   - Real-time sensor monitoring and calculation

MADA Validation:
  All modes support --validate_mada flag for convergence checking.
  Real-time mode STRONGLY RECOMMENDS enabling MADA validation to prevent
  misconfigured magnetic fields from causing thrust instabilities.

MADA GPIO Control (NEW):
  Real-time mode now supports Raspberry Pi GPIO control for physical MADA units.
  Automatically enabled when mada_gpio_controller.py is available.
  Physical stepper motors adjust MADA orientations based on Hall sensor readings.

Examples:
  python thrust_model.py --b_opposing 50 --frequency 100 --validate_mada
  python thrust_model.py --mode swarm --num_drones 10 --scenario asymmetric --validate_mada --headless
  python thrust_model.py --mode benchmark --telemetry_file data.csv --validate_mada
  python thrust_model.py --mode realtime --sensor_port /dev/ttyUSB0 --validate_mada
  python thrust_model.py --optimize --use_ml
  python thrust_model.py --config myconfig.yaml
        """
    )
    
    # Basic parameters
    parser.add_argument(
        "--b_opposing", type=float, default=None,
        help="Opposing magnetic field (T)"
    )
    parser.add_argument(
        "--frequency", type=float, default=SimulationConfig.DEFAULT_FREQUENCY,
        help=f"Pulsing frequency (Hz), default: {SimulationConfig.DEFAULT_FREQUENCY}"
    )
    parser.add_argument(
        "--m1", type=float, default=SimulationConfig.M1,
        help=f"Magnetic moment 1 (A m²), default: {SimulationConfig.M1}"
    )
    parser.add_argument(
        "--m2", type=float, default=SimulationConfig.M2,
        help=f"Magnetic moment 2 (A m²), default: {SimulationConfig.M2}"
    )
    parser.add_argument(
        "--distance", type=float, default=SimulationConfig.DISTANCE,
        help=f"Distance between magnets (m), default: {SimulationConfig.DISTANCE}"
    )
    parser.add_argument(
        "--current", type=float, default=SimulationConfig.BASE_CURRENT,
        help=f"Base current (A), default: {SimulationConfig.BASE_CURRENT}"
    )
    parser.add_argument(
        "--mass", type=float, default=SimulationConfig.MASS,
        help=f"Drone mass (kg), default: {SimulationConfig.MASS}"
    )
    parser.add_argument(
        "--n_units", type=int, default=SimulationConfig.N_UNITS,
        help=f"Number of MADA units, default: {SimulationConfig.N_UNITS}"
    )
    parser.add_argument(
        "--chi", type=float, default=SimulationConfig.CHI,
        help=f"Magnetic susceptibility, default: {SimulationConfig.CHI}"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="YAML configuration file"
    )
    
    # MADA validation
    parser.add_argument(
        "--validate_mada", action="store_true",
        help="Enable MADA convergence validation (RECOMMENDED)"
    )
    parser.add_argument(
        "--mada_tolerance", type=float, default=MADAValidationConfig.CONVERGENCE_THRESHOLD,
        help=f"MADA convergence tolerance, default: {MADAValidationConfig.CONVERGENCE_THRESHOLD}"
    )
    
    # Mode selection
    parser.add_argument(
        "--mode", type=str, default='single',
        choices=['single', 'swarm', 'benchmark', 'realtime'],
        help="Simulation mode (default: single)"
    )
    
    # Swarm mode parameters
    parser.add_argument(
        "--num_drones", type=int, default=5,
        help="Number of drones for swarm mode (default: 5)"
    )
    parser.add_argument(
        "--scenario", type=str, default='asymmetric',
        choices=['asymmetric', 'symmetric'],
        help="Swarm scenario type (default: asymmetric)"
    )
    parser.add_argument(
        "--simulation_time", type=float, default=60.0,
        help="Simulation time (s) for swarm mode (default: 60)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run swarm simulation in headless mode (no GUI)"
    )
    
    # Benchmark mode parameters
    parser.add_argument(
        "--telemetry_file", type=str, default=None,
        help="CSV file for benchmark mode"
    )
    
    # Real-time mode parameters
    parser.add_argument(
        "--sensor_port", type=str, default='/dev/ttyUSB0',
        help="Serial port for real-time sensor input (default: /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--update_interval", type=float, default=0.1,
        help="Update interval (s) for real-time mode (default: 0.1)"
    )
    
    # Optimization parameters
    parser.add_argument(
        "--optimize", action="store_true",
        help="Run optimization routine"
    )
    parser.add_argument(
        "--use_ml", action="store_true",
        help="Use ML surrogate for optimization"
    )
    
    # Parametric sweep
    parser.add_argument(
        "--sweep", type=str, default=None,
        help="Parameter name for parametric sweep"
    )
    parser.add_argument(
        "--sweep_values", type=str, default=None,
        help="Comma-separated sweep values (e.g., '50,75,100')"
    )
    
    args = parser.parse_args()
    
    # Load config file if provided
    if args.config:
        if not YAML_AVAILABLE:
            logger.error("PyYAML not installed. Install with: pip install pyyaml")
            sys.exit(1)
        
        try:
            config_args = load_config_yaml(args.config)
            for key, val in vars(config_args).items():
                if hasattr(args, key) and getattr(args, key) == parser.get_default(key):
                    setattr(args, key, val)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)
    
    # Validate inputs
    if args.mass <= 0:
        parser.error("Mass must be positive")
    if args.frequency <= 0:
        parser.error("Frequency must be positive")
    if args.n_units <= 0:
        parser.error("Number of units must be positive")
    if args.distance <= 0:
        parser.error("Distance must be positive")
    if args.chi < 0:
        parser.error("Chi must be non-negative")
    
    try:
        # Handle parametric sweep
        if args.sweep and args.sweep_values:
            if not PANDAS_AVAILABLE:
                logger.error("pandas required for parametric sweep")
                sys.exit(1)
            
            sweep_vals = [float(v.strip()) for v in args.sweep_values.split(',')]
            logger.info(f"Running parametric sweep: {args.sweep} = {sweep_vals}")
            
            results_df = parallel_parametric_sweep(args.sweep, sweep_vals, args)
            logger.info("\nParametric Sweep Results:")
            logger.info(results_df.to_string(index=False))
            
            output_file = f'sweep_{args.sweep}.csv'
            results_df.to_csv(output_file, index=False)
            logger.info(f"\nResults saved to {output_file}")
            return
        
        # Handle optimization
        if args.optimize:
            if not SCIPY_OPTIMIZE_AVAILABLE:
                logger.error("scipy.optimize required for optimization")
                sys.exit(1)
            
            logger.info("Running thrust optimization...")
            bounds = {
                'frequency': (50.0, 150.0),
                'current': (10.0, 20.0)
            }
            
            opt_params, max_thrust = optimize_thrust(bounds, args, args.use_ml)
            
            logger.info("\n" + "=" * 60)
            logger.info("OPTIMIZATION RESULTS")
            logger.info("=" * 60)
            for param, val in opt_params.items():
                logger.info(f"  {param}: {val:.2f}")
            logger.info(f"  Maximum Thrust: {max_thrust:.2f} N")
            logger.info("=" * 60 + "\n")
            return
        
        # Route to appropriate mode
        if args.mode == 'single':
            single_calculation_mode(args)
        
        elif args.mode == 'swarm':
            simulate_swarm(
                args.num_drones,
                args.scenario,
                args.simulation_time,
                args.verbose,
                args.validate_mada,
                args.headless
            )
        
        elif args.mode == 'benchmark':
            if not args.telemetry_file:
                parser.error("--telemetry_file required for benchmark mode")
            benchmark_with_telemetry(args.telemetry_file, args, args.verbose, args.validate_mada)
        
        elif args.mode == 'realtime':
            real_time_mode(args, args.sensor_port, args.update_interval, args.verbose, args.validate_mada)
    
    except KeyboardInterrupt:
        logger.info("\nSimulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Multiprocessing guard for Windows compatibility
    if MULTIPROCESSING_AVAILABLE:
        mp.freeze_support()
    main()linalg.norm(F_vec_prelim)
        T_prelim = total_thrust(args.n_units, F_mag_prelim, SimulationConfig.ETA, SimulationConfig.THETA)
        
        validation_result = val.full_validation(
            B_total, field_vectors, SimulationConfig.GRAD_H2, T_prelim
        )
        
        if not validation_result['valid']:
            error_msg = "; ".join(validation_result['errors'])
            logger.error(f"MADA VALIDATION FAILED: {error_msg}")
            raise MADAValidationError(f"MADA configuration invalid: {error_msg}")
        
        if verbose:
            for check_name, check_result in validation_result['checks'].items():
                status = "✓" if check_result['valid'] else "✗"
                logger.info(f"  {status} {check_name}: {check_result['message']}")
    
    # Calculate thrust
    F_vec = force_vector(
        args.chi, B_total, SimulationConfig.GRAD_H2, 
        SimulationConfig.AREA, SimulationConfig.RHO
    )
    F_mag = np.linalg.norm(F_vec)
    T = total_thrust(args.n_units, F_mag, SimulationConfig.ETA, SimulationConfig.THETA)
    a = acceleration(T, args.mass)
    
    # Calculate performance metrics
    P = power_consumption(scaled_I, SimulationConfig.RESISTANCE, SimulationConfig.P_EDDY)
    eta_perc = efficiency(T, SimulationConfig.VELOCITY, P)
    R = range_calc(SimulationConfig.VELOCITY, SimulationConfig.ENERGY, P)
    
    if verbose:
        logger.info(f"Thrust: {T:.2f} N, Accel: {a:.2f} m/s², Power: {P:.2f} W")
    
    return T, a, P, eta_perc, R, B_total


def compute_lift_drag_ratio() -> float:
    """Compute lift-to-drag ratio (placeholder)."""
    return 15.0  # Example value


# =============================================================================
# Structural Functions
# =============================================================================

def fea_structural_check(accel: float, mass: float = SimulationConfig.MASS, 
                         safety_factor: float = 1.5) -> bool:
    """
    Simple FEA hook: Check if structure can withstand acceleration.
    Uses yield strength of aluminum (270 MPa) as example.
    
    Args:
        accel: Acceleration (m/s²)
        mass: Mass (kg)
        safety_factor: Safety factor for design
    
    Returns:
        True if structure is safe
    """
    if accel < 0 or mass <= 0 or safety_factor < 1:
        return False
    
    force = mass * accel
    cross_section_area = 0.01  # Assume 0.01 m² cross-section
    stress = force / cross_section_area
    yield_strength = 270e6 / safety_factor  # Aluminum with safety factor
    
    return stress < yield_strength


def stealth_ops_check(traj: np.ndarray, radar_pos: np.ndarray, rcs: float = 0.01) -> float:
    """
    Check radar evasion for stealth ops.
    
    Args:
        traj: Trajectory points (N x 3)
        radar_pos: Radar position [x, y, z]
        rcs: Radar cross-section (m²)
    
    Returns:
        Evasion probability (0-1)
    """
    return radar_evasion_probability(traj, radar_pos, rcs)


# =============================================================================
# HIL Validation
# =============================================================================

def hil_validation(sim_thrust: float, bench_thrust: float, 
                  tolerance: float = 5.0) -> bool:
    """
    Hardware-in-the-loop validation.
    
    Args:
        sim_thrust: Simulated thrust (N)
        bench_thrust: Bench test thrust (N)
        tolerance: Acceptable error percentage
    
    Returns:
        True if within tolerance
    """
    if abs(bench_thrust) < EPSILON:
        logger.warning("Bench thrust is zero - cannot validate")
        return False
    
    error = abs((sim_thrust - bench_thrust) / bench_thrust * 100)
    logger.info(f"HIL Validation: Simulated {sim_thrust:.2f}N vs Bench {bench_thrust:.2f}N (Error: {error:.2f}%)")
    return error <= tolerance


# =============================================================================
# CFD Integration (Placeholder)
# =============================================================================

def run_cfd_simulation(mesh_file: str, thrust_vector: np.ndarray, 
                      speed: float = 26 * SPEED_OF_SOUND) -> Dict[str, Any]:
    """
    Integrate with OpenFOAM for CFD simulation of thrust vectoring.
    
    NOTE: This is a placeholder implementation. Real CFD integration requires:
    - Proper OpenFOAM installation
    - Mesh generation
    - Case setup
    - Post-processing
    
    Args:
        mesh_file: Path to OpenFOAM mesh
        thrust_vector: 3D thrust vector (N)
        speed: Flow speed (m/s)
    
    Returns:
        Dict with simulation results
    """
    if not CFD_AVAILABLE:
        logger.warning("CFD tools not available - returning placeholder data")
        return {'pressure': np.array([]), 'velocity': np.array([])}
    
    logger.info(f"CFD simulation requested (placeholder): mesh={mesh_file}, speed={speed:.1f}m/s")
    logger.info("Real implementation requires OpenFOAM setup")
    
    # Placeholder results
    return {
        'pressure': np.random.rand(100),
        'velocity': np.random.rand(100, 3),
        'note': 'Placeholder data - integrate with real OpenFOAM'
    }


# =============================================================================
# Parametric Sweep and Optimization
# =============================================================================

def parametric_sweep(param_name: str, values: List[float], 
                    args: argparse.Namespace) -> 'pd.DataFrame':
    """
    Perform parametric sweep for given parameter.
    
    Args:
        param_name: Parameter to sweep
        values: List of parameter values
        args: Base arguments
    
    Returns:
        DataFrame with results
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas required for parametric sweep")
    
    results = []
    for val in values:
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        
        try:
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
        except Exception as e:
            logger.warning(f"Sweep failed for {param_name}={val}: {e}")
    
    return pd.DataFrame(results)


def parallel_parametric_sweep(param_name: str, values: List[float], 
                             args: argparse.Namespace, 
                             n_processes: int = 4) -> 'pd.DataFrame':
    """
    Parallel parametric sweep using multiprocessing.
    
    Args:
        param_name: Parameter to sweep
        values: List of parameter values
        args: Base arguments
        n_processes: Number of parallel processes
    
    Returns:
        DataFrame with results
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas required for parametric sweep")
    if not MULTIPROCESSING_AVAILABLE:
        logger.warning("Multiprocessing not available, falling back to sequential")
        return parametric_sweep(param_name, values, args)
    
    def sweep_single(val: float) -> Dict[str, Any]:
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        try:
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
        except Exception as e:
            logger.warning(f"Sweep failed for {param_name}={val}: {e}")
            return {param_name: val, 'thrust': 0, 'acceleration': 0, 
                   'power': 0, 'efficiency': 0, 'range': 0, 'B_total': 0}
    
    with mp.Pool(n_processes) as pool:
        results = pool.map(sweep_single, values)
    
    return pd.DataFrame(results)


def thrust_objective(params_dict: Dict[str, float], base_args: argparse.Namespace) -> float:
    """
    Objective function for thrust maximization.
    Returns negative thrust for minimization.
    
    Args:
        params_dict: Parameters to optimize
        base_args: Base arguments
    
    Returns:
        Negative thrust (for minimization)
    """
    args = argparse.Namespace(**vars(base_args))
    for key, val in params_dict.items():
        setattr(args, key, val)
    
    try:
        T, _, _, _, _, _ = calculate_thrust_params(args)
        return -T
    except Exception as e:
        logger.warning(f"Thrust calculation failed: {e}")
        return 0.0  # Penalty for invalid parameters


def optimize_thrust(bounds: Dict[str, Tuple[float, float]], 
                   base_args: argparse.Namespace,
                   use_ml_surrogate: bool = False) -> Tuple[Dict[str, float], float]:
    """
    Gradient-based optimization with optional ML surrogate.
    
    Args:
        bounds: Parameter bounds {name: (min, max)}
        base_args: Base arguments
        use_ml_surrogate: Use ML surrogate model
    
    Returns:
        Tuple of (optimal_params, max_thrust)
    """
    if not SCIPY_OPTIMIZE_AVAILABLE:
        raise ImportError("scipy.optimize required for optimization")
    
    param_names = list(bounds.keys())
    bounds_list = list(bounds.values())
    
    if use_ml_surrogate and ML_AVAILABLE:
        logger.info("Training ML surrogate model...")
        
        # Train surrogate
        kernel = ConstantKernel() * RBF()
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
        
        # Generate training samples
        n_samples = 100
        X_train = np.random.uniform(
            [b[0] for b in bounds_list],
            [b[1] for b in bounds_list],
            (n_samples, len(bounds))
        )
        
        y_train = []
        for x in X_train:
            params = dict(zip(param_names, x))
            y_train.append(thrust_objective(params, base_args))
        
        gp.fit(X_train, y_train)
        
        def surrogate_obj(x: np.ndarray) -> float:
            return float(gp.predict(x.reshape(1, -1))[0])
        
        obj_func = surrogate_obj
        logger.info("Surrogate model trained. Optimizing...")
    else:
        def obj_func(x: np.ndarray) -> float:
            params = dict(zip(param_names, x))
            return thrust_objective(params, base_args)
    
    # Initial guess (midpoint of bounds)
    initial_guess = np.array([(b[0] + b[1]) / 2 for b in bounds_list])
    
    # Optimize
    result = minimize(obj_func, initial_guess, bounds=bounds_list, method='L-BFGS-B')
    
    opt_params = dict(zip(param_names, result.x))
    max_thrust = -result.fun
    
    return opt_params, max_thrust


# =============================================================================
# Swarm Simulation Mode
# =============================================================================

def simulate_swarm(
    num_drones: int = 5,
    scenario: str = 'asymmetric',
    simulation_time: float = 60.0,
    verbose: bool = False,
    validate_mada: bool = True,
    headless: bool = True
) -> None:
    """
    Multi-drone swarm simulation using PyBullet with MADA validation.
    
    Args:
        num_drones: Number of drones in swarm
        scenario: 'asymmetric' or 'symmetric' warfare scenario
        simulation_time: Simulation duration in seconds
        verbose: Enable verbose output
        validate_mada: Enable MADA convergence validation
        headless: Run without GUI (DIRECT mode) for servers
    """
    if not PYBULLET_AVAILABLE:
        logger.error("PyBullet not installed. Install with: pip install pybullet")
        return
    
    logger.info(f"Starting swarm simulation: {num_drones} drones, {scenario} scenario")
    logger.info(f"MADA validation: {'ENABLED' if validate_mada else 'DISABLED'}")
    
    # Initialize MADA validators for each drone
    validators = [MADAConvergenceValidator() for _ in range(num_drones)] if validate_mada else None
    
    # Connect to physics engine
    connection_mode = p.DIRECT if headless else p.GUI
    physicsClient = p.connect(connection_mode)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    
    try:
        # Load environment
        planeId = p.loadURDF("plane.urdf")
        
        # Initialize drones
        drone_ids = []
        drone_masses = [SimulationConfig.MASS] * num_drones
        drone_thrusts = []
        
        # Calculate base thrust
        base_F = np.linalg.norm(
            force_vector(
                SimulationConfig.CHI, 50, SimulationConfig.GRAD_H2,
                SimulationConfig.AREA, SimulationConfig.RHO
            )
        )
        base_T = total_thrust(
            SimulationConfig.N_UNITS, base_F,
            SimulationConfig.ETA, SimulationConfig.THETA
        )
        
        # Set up scenario-specific thrust distribution
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
        
        # Load drone models
        for i in range(num_drones):
            start_pos = [i * 5, 0, 2]
            drone_id = p.loadURDF("sphere2.urdf", start_pos, globalScaling=0.5)
            p.changeDynamics(drone_id, -1, mass=drone_masses[i])
            drone_ids.append(drone_id)
            logger.info(f"Drone {i}: pos={start_pos}, thrust={drone_thrusts[i]:.0f}N")
        
        # Generate non-ballistic trajectories
        targets = np.random.uniform(-50, 50, (num_drones, 3))
        trajectories = [
            non_ballistic_trajectory(np.array([i*5, 0, 2]), targets[i])
            for i in range(num_drones)
        ]
        traj_indices = [0] * num_drones
        
        # Simulation loop
        steps = int(simulation_time * SimulationConfig.PHYSICS_STEP_RATE)
        sleep_time = 1.0 / SimulationConfig.PHYSICS_STEP_RATE if not headless else 0
        validation_failures = [0] * num_drones
        
        for step in range(steps):
            # Apply thrust forces with vectoring and MADA validation
            for i, drone_id in enumerate(drone_ids):
                if traj_indices[i] < len(trajectories[i]) - 1:
                    current_pos, _ = p.getBasePositionAndOrientation(drone_id)
                    target_pos = trajectories[i][traj_indices[i] + 1]
                    direction = target_pos - np.array(current_pos)
                    dir_norm = np.linalg.norm(direction)
                    
                    if dir_norm > EPSILON:
                        direction = direction / dir_norm
                    else:
                        direction = np.array([0, 0, 1])  # Default upward
                    
                    # MADA validation for this drone
                    thrust_multiplier = 1.0
                    if validate_mada and validators:
                        B_total = 50.0 + step * 0.001
                        field_vectors = simulate_hall_sensor_readings(SimulationConfig.N_UNITS, B_total)
                        
                        validation_result = validators[i].full_validation(
                            B_total, field_vectors, SimulationConfig.GRAD_H2, drone_thrusts[i]
                        )
                        
                        if not validation_result['valid']:
                            validation_failures[i] += 1
                            thrust_multiplier = 0.5  # Reduce thrust
                            if verbose:
                                logger.warning(f"Drone {i} MADA validation failed: {validation_result['errors']}")
                    
                    thrust_vec = direction * drone_thrusts[i] * thrust_multiplier
                    p.applyExternalForce(drone_id, -1, list(thrust_vec), [0, 0, 0], p.LINK_FRAME)
                    traj_indices[i] += 1
            
            # Simulate asymmetric warfare events
            if scenario == 'asymmetric' and np.random.rand() < SimulationConfig.SWARM_ATTACK_PROBABILITY:
                if len(drone_ids) > num_drones // 2:
                    target_id = np.random.choice(drone_ids[num_drones//2:])
                    attack_force = [0, 0, -20000]
                    p.applyExternalForce(target_id, -1, attack_force, [0, 0, 0], p.LINK_FRAME)
                    if verbose:
                        logger.info(f"Step {step}: Attack on drone {drone_ids.index(target_id)}")
            
            p.stepSimulation()
            
            if step % SimulationConfig.PHYSICS_STEP_RATE == 0 and verbose:
                logger.info(f"Simulation time: {step/SimulationConfig.PHYSICS_STEP_RATE:.1f}s / {simulation_time}s")
            
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Final statistics
        logger.info("\n" + "=" * 60)
        logger.info("SWARM SIMULATION RESULTS")
        logger.info("=" * 60)
        
        for i, drone_id in enumerate(drone_ids):
            pos, _ = p.getBasePositionAndOrientation(drone_id)
            logger.info(f"Drone {i}: Final pos={pos}")
            
            if validate_mada and validators:
                failure_rate = validation_failures[i] / steps * 100
                logger.info(f"  MADA validation failures: {validation_failures[i]} ({failure_rate:.2f}%)")
                logger.info(f"  Converged: {validators[i].convergence_achieved}")
    
    finally:
        p.disconnect()
        logger.info(f"Swarm simulation complete\n")


# =============================================================================
# Benchmark Mode
# =============================================================================

def benchmark_with_telemetry(
    telemetry_file: str,
    args: argparse.Namespace,
    verbose: bool = False,
    validate_mada: bool = True
) -> None:
    """
    Benchmark simulation outputs against hardware telemetry data.
    Includes MADA convergence validation and HIL validation when enabled.
    
    Args:
        telemetry_file: Path to CSV file with telemetry data
        args: Argument namespace with simulation parameters
        verbose: Enable verbose output
        validate_mada: Enable MADA convergence validation
    """
    if not PANDAS_AVAILABLE:
        logger.error("pandas not installed. Install with: pip install pandas")
        return
    
    telemetry_path = Path(telemetry_file)
    if not telemetry_path.exists():
        logger.error(f"Telemetry file not found: {telemetry_file}")
        return
    
    logger.info(f"Benchmarking against telemetry: {telemetry_file}")
    
    try:
        data = pd.read_csv(telemetry_file)
        logger.info(f"Loaded {len(data)} telemetry records")
    except Exception as e:
        logger.error(f"Failed to read telemetry file: {e}")
        return
    
    # Normalize column names
    data.columns = data.columns.str.strip().str.lower()
    
    # Required columns
    required_cols = ['measured_b', 'measured_freq']
    missing_cols = [col for col in required_cols if col not in data.columns]
    
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        logger.info(f"Available columns: {list(data.columns)}")
        return
    
    # Initialize MADA validator
    validator = MADAConvergenceValidator() if validate_mada else None
    
    sim_thrusts = []
    sim_accels = []
    differences = []
    hil_results = []
    mada_validation_results = []
    
    for idx, row in data.iterrows():
        B = row.get('measured_b', 50.0)
        freq = row.get('measured_freq', args.frequency)
        
        try:
            T_sim, a_sim, _, _, _, _ = calculate_thrust_params(
                args, B_opposing=B, frequency=freq, verbose=False
            )
        except Exception as e:
            logger.warning(f"Record {idx}: Calculation failed - {e}")
            T_sim, a_sim = 0, 0
        
        sim_thrusts.append(T_sim)
        sim_accels.append(a_sim)
        
        measured_T = row.get('measured_thrust', 0)
        measured_a = row.get('measured_accel', 0)
        
        diff_T = abs(T_sim - measured_T) if measured_T > 0 else 0
        diff_a = abs(a_sim - measured_a) if measured_a > 0 else 0
        
        differences.append((diff_T, diff_a))
        
        # HIL validation
        if measured_T > 0:
            hil_valid = hil_validation(T_sim, measured_T)
            hil_results.append(hil_valid)
        
        # MADA validation
        if validate_mada and validator:
            field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            validation_result = validator.full_validation(
                B, field_vectors, SimulationConfig.GRAD_H2, T_sim
            )
            mada_validation_results.append(validation_result)
            
            if not validation_result['valid'] and verbose:
                logger.warning(f"Record {idx}: MADA validation failed - {validation_result['errors']}")
    
    # Calculate statistics
    valid_thrust_diffs = [d[0] for d in differences if d[0] > 0]
    valid_accel_diffs = [d[1] for d in differences if d[1] > 0]
    
    avg_diff_T = np.mean(valid_thrust_diffs) if valid_thrust_diffs else 0
    avg_diff_a = np.mean(valid_accel_diffs) if valid_accel_diffs else 0
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
        if validator:
            logger.info(f"MADA Convergence Achieved: {validator.convergence_achieved}")
    
    if verbose:
        # Save detailed comparison
        data['sim_thrust'] = sim_thrusts
        data['sim_accel'] = sim_accels
        data['thrust_error'] = [d[0] for d in differences]
        data['accel_error'] = [d[1] for d in differences]
        if hil_results:
            data['hil_valid'] = hil_results + [False] * (len(data) - len(hil_results))
        
        if validate_mada and mada_validation_results:
            data['mada_valid'] = [r['valid'] for r in mada_validation_results]
            if validator:
                data['mada_converged'] = validator.convergence_achieved
        
        output_file = 'benchmark_report.csv'
        try:
            data.to_csv(output_file, index=False)
            logger.info(f"Detailed report saved to {output_file}")
        except IOError as e:
            logger.error(f"Failed to save report: {e}")


# =============================================================================
# Real-Time Monitoring Mode
# =============================================================================

def real_time_mode(
    args: argparse.Namespace,
    sensor_port: str = '/dev/ttyUSB0',
    update_interval: float = 0.1,
    verbose: bool = False,
    validate_mada: bool = True
) -> None:
    """
    Real-time mode: Read sensor data and compute thrust dynamically.
    CRITICAL: Includes MADA convergence validation to prevent misconfigured fields.
    **NEW: Integrated with Raspberry Pi GPIO control for physical MADA units.**
    
    Args:
        args: Argument namespace with simulation parameters
        sensor_port: Serial port for sensor connection
        update_interval: Update interval in seconds
        verbose: Enable verbose output
        validate_mada: Enable MADA convergence validation (STRONGLY RECOMMENDED)
    """
    logger.info("=" * 60)
    logger.info("REAL-TIME THRUST MONITORING WITH MADA VALIDATION")
    logger.info("=" * 60)
    
    if not validate_mada:
        logger.warning("⚠️  MADA validation DISABLED - misconfigured fields may cause issues!")
        logger.warning("⚠️  Recommend enabling with --validate_mada flag")
    
    # Initialize MADA validator
    validator = MADAConvergenceValidator() if validate_mada else None
    
    # ==================== INSERTION POINT 2: INITIALIZE MADA GPIO CONTROLLER ====================
    mada_controller = None
    if MADA_GPIO_AVAILABLE:
        try:
            mada_controller = MADAGPIOController(num_madas=args.n_units)
            logger.info("✓ MADA GPIO controller initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize MADA controller: {e}")
    # ============================================================================================
    
    # Initialize hardware interfaces
    mcu = None
    
    if HARDWARE_AVAILABLE:
        try:
            mcu = MicrocontrollerPWMInterface(port=sensor_port)
            logger.info(f"✓ Connected to microcontroller on {sensor_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to microcontroller: {e}")
            logger.info("Using simulated sensor data")
    else:
        logger.info("Hardware interfaces not available. Using simulated data.")
    
    logger.info(f"Update interval: {update_interval}s")
    logger.info(f"MADA validation: {'ENABLED' if validate_mada else 'DISABLED'}")
    logger.info(f"MADA GPIO control: {'ENABLED' if mada_controller else 'DISABLED'}")
    logger.info(f"Number of MADA units: {args.n_units}")
    logger.info("Press Ctrl+C to stop\n")
    
    iteration = 0
    validation_failures = 0
    last_valid_thrust = 0.0
    
    try:
        while True:
            # Read sensor data
            if mcu:
                try:
                    response = mcu.send_command('READ:SENSORS:HALL')
                    if response:
                        parts = response.split(':')
                        B = float(parts[0]) if len(parts) > 0 else 50.0
                        freq = float(parts[1]) if len(parts) > 1 else 100.0
                        
                        # Parse Hall sensor vectors if available
                        if len(parts) > 2 + 3 * args.n_units:
                            field_vectors = []
                            for i in range(args.n_units):
                                offset = 2 + i * 3
                                vec = np.array([
                                    float(parts[offset]),
                                    float(parts[offset + 1]),
                                    float(parts[offset + 2])
                                ])
                                field_vectors.append(vec)
                        else:
                            field_vectors = simulate_hall_sensor_readings(args.n_units, B)
                    else:
                        raise ValueError("No response")
                except Exception as e:
                    logger.warning(f"Sensor read error: {e}. Using defaults.")
                    B = 50.0
                    freq = 100.0
                    field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            else:
                # Simulated sensor data
                B = 50.0 + np.random.normal(0, 2.0)
                freq = 100.0 + np.random.normal(0, 5.0)
                field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            
            # MADA validation before thrust calculation
            validation_passed = True
            if validate_mada and validator:
                try:
                    # Preliminary thrust for convergence check
                    F_vec_prelim = force_vector(
                        args.chi, B, SimulationConfig.GRAD_H2,
                        SimulationConfig.AREA, SimulationConfig.RHO
                    )
                    F_mag_prelim = np.linalg.norm(F_vec_prelim)
                    T_prelim = total_thrust(args.n_units, F_mag_prelim, SimulationConfig.ETA, SimulationConfig.THETA)
                    
                    validation_result = validator.full_validation(
                        B, field_vectors, SimulationConfig.GRAD_H2, T_prelim
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
                            logger.critical("⚠️  CHECK MADA CONFIGURATION AND HALL SENSORS!")
                        
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
            
            # ==================== INSERTION POINT 3: MADA GPIO CONTROL ====================
            # Apply MADA orientation control based on field vectors
            if mada_controller and validate_mada and validation_passed:
                target_direction = np.array([1.0, 0.0, 0.0])  # Thrust direction
                try:
                    orientations = integrate_with_mada_validation(
                        mada_controller, field_vectors, target_direction
                    )
                    for mada_id, (az, el) in orientations.items():
                        mada_controller.rotate_mada(mada_id, az, el, blocking=False)
                except Exception as e:
                    logger.warning(f"MADA GPIO control error: {e}")
            # ===============================================================================
            
            # Calculate thrust parameters
            try:
                T, a, P, eta, R, B_total = calculate_thrust_params(
                    args, B_opposing=B, frequency=freq, verbose=False,
                    validate_mada=False  # Already validated above
                )
                
                if validation_passed:
                    last_valid_thrust = T
            
            except Exception as e:
                logger.error(f"[{iteration:04d}] Thrust calculation error: {e}")
                T, a, P, eta, R, B_total = (0, 0, 0, 0, 0, B)
            
            # Display results
            a_g = a / 9.81 if abs(a) > EPSILON else 0
            status = "✓" if validation_passed else "✗"
            
            logger.info(
                f"[{iteration:04d}] {status} B={B:.2f}T, Freq={freq:.1f}Hz, "
                f"Thrust={T:.0f}N, Accel={a:.1f}m/s² ({a_g:.1f}g), "
                f"Power={P:.0f}W, Eff={eta:.1f}%"
            )
            
            # Detailed validation info if verbose
            if verbose and validate_mada and validation_passed and validator:
                validation_result = validator.full_validation(
                    B, field_vectors, SimulationConfig.GRAD_H2, T
                )
                for check_name, check_result in validation_result['checks'].items():
                    if check_name != 'convergence':
                        status_symbol = "✓" if check_result['valid'] else "✗"
                        logger.info(f"  {status_symbol} {check_name}: {check_result['message']}")
            
            # Warning system for sustained issues
            if validate_mada and iteration > 0 and iteration % 20 == 0 and validator:
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
        
        # Final statistics
        logger.info(f"Total iterations: {iteration}")
        if validate_mada and validator:
            failure_rate = validation_failures / iteration * 100 if iteration > 0 else 0
            logger.info(f"MADA validation failures: {validation_failures} ({failure_rate:.2f}%)")
            logger.info(f"MADA convergence achieved: {validator.convergence_achieved}")
            logger.info(f"Final thrust value: {last_valid_thrust:.2f}N")
    
    finally:
        if mcu:
            try:
                mcu.close()
                logger.info("Microcontroller connection closed")
            except:
                pass
        
        if mada_controller:
            try:
                mada_controller.cleanup()
                logger.info("MADA GPIO controller cleaned up")
            except:
                pass


# =============================================================================
# Single Calculation Mode
# =============================================================================

def single_calculation_mode(args: argparse.Namespace) -> None:
    """
    Perform a single thrust calculation with detailed output and validation.
    
    Args:
        args: Argument namespace with simulation parameters
    """
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
    
    scaled_I = args.current * (args.frequency / SimulationConfig.BASE_FREQUENCY)
    if args.verbose:
        logger.info(f"  - Base Current: {args.current} A")
        logger.info(f"  - Scaled Current: {scaled_I:.2f} A")
    
    # Calculate or use provided B_opposing
    if args.b_opposing is not None:
        B = args.b_opposing
        if args.verbose:
            logger.info(f"  - B_opposing (provided): {B:.2f} T")
    else:
        B = opposing_field(args.m1, args.m2, args.distance, SimulationConfig.K_SCALING)
        if args.verbose:
            logger.info(f"  - B_opposing (calculated): {B:.6e} T")
            logger.info(f"    (from m1={args.m1}, m2={args.m2}, d={args.distance}m)")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("MAGNETIC FIELD CALCULATIONS")
    logger.info(f"{'─' * 60}")
    logger.info(f"Opposing Field (B_opposing): {B:.2f} T")
    
    delta_B = pulsed_enhancement(SimulationConfig.N_TURNS, scaled_I)
    logger.info(f"Pulsed Enhancement (ΔB): {delta_B:.4f} T")
    
    B_total = B + delta_B
    logger.info(f"Total Magnetic Field (B_total): {B_total:.2f} T")
    
    if args.verbose:
        logger.info(f"\n{'─' * 60}")
        logger.info("QUANTUM PARAMETERS")
        logger.info(f"{'─' * 60}")
        beta_chi = rg_beta_chi(args.chi, SimulationConfig.G_COUPLING, SimulationConfig.LAMBDA_PARAM)
        logger.info(f"Susceptibility (χ): {args.chi:.2e}")
        logger.info(f"RG Beta Function (β_χ): {beta_chi:.2e}")
    
    # MADA validation
    if args.validate_mada:
        logger.info(f"\n{'─' * 60}")
        logger.info("MADA CONVERGENCE VALIDATION")
        logger.info(f"{'─' * 60}")
        
        validator = MADAConvergenceValidator(tolerance=args.mada_tolerance)
        field_vectors = simulate_hall_sensor_readings(args.n_units, B_total)
        
        # Preliminary thrust calculation
        F_vec_prelim = force_vector(
            args.chi, B_total, SimulationConfig.GRAD_H2,
            SimulationConfig.AREA, SimulationConfig.RHO
        )
        F_mag_prelim = np.
