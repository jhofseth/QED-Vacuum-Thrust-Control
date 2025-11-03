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
from typing import Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import core equations
from simulations.equations import (
    opposing_field,
    pulsed_enhancement,
    rg_beta_chi,
    force_vector,
    total_thrust,
    acceleration,
    efficiency,
    power_consumption,
    range_calc
)

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
    from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    logging.warning("Hardware interfaces not available. Real-time mode limited.")

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
    frequency = frequency or args.frequency
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
    
    P = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
    eta_perc = efficiency(T, DEFAULT_V, P)
    R = range_calc(DEFAULT_V, DEFAULT_E, P)
    
    if verbose:
        logger.info(f"Thrust: {T:.2f} N, Accel: {a:.2f} m/s², Power: {P:.2f} W")
    
    return T, a, P, eta_perc, R, B_total


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
    
    # Simulation loop
    steps = int(simulation_time * 240)  # 240 Hz physics
    
    for step in range(steps):
        # Apply thrust forces
        for i, drone_id in enumerate(drone_ids):
            thrust = drone_thrusts[i]
            # Apply vertical thrust (hover) + small maneuvers
            thrust_vec = [0, 0, thrust + np.random.normal(0, 100)]
            p.applyExternalForce(drone_id, -1, thrust_vec, [0, 0, 0], p.LINK_FRAME)
        
        # Simulate asymmetric warfare events
        if scenario == 'asymmetric' and np.random.rand() < 0.005:  # 0.5% chance per step
            # Advanced drones "attack" standard drones
            if len(drone_ids) > num_drones // 2:
                target_id = np.random.choice(drone_ids[num_drones//2:])
                attack_force = [0, 0, -20000]  # Downward force
                p.applyExternalForce(target_id, -1, attack_force, [0, 0, 0], p.LINK_FRAME)
                if verbose:
                    logger.info(f"Step {step}: Attack on drone {drone_ids.index(target_id)}")
        
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


def benchmark_with_telemetry(telemetry_file: str, args, verbose: bool = False):
    """
    Benchmark simulation outputs against hardware telemetry data.
    
    Parameters:
    telemetry_file (str): Path to CSV file with telemetry data
    args: Argument namespace with simulation parameters
    verbose (bool): Enable verbose output
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
    
    # Calculate statistics
    avg_diff_T = np.mean([d[0] for d in differences if d[0] > 0])
    avg_diff_a = np.mean([d[1] for d in differences if d[1] > 0])
    
    logger.info("\n" + "=" * 60)
    logger.info("BENCHMARK RESULTS")
    logger.info("=" * 60)
    logger.info(f"Records processed: {len(data)}")
    logger.info(f"Average Thrust Difference: {avg_diff_T:.2f} N")
    logger.info(f"Average Acceleration Difference: {avg_diff_a:.2f} m/s²")
    
    if verbose:
        # Save detailed comparison
        data['sim_thrust'] = sim_thrusts
        data['sim_accel'] = sim_accels
        data['thrust_error'] = [d[0] for d in differences]
        data['accel_error'] = [d[1] for d in differences]
        
        output_file = 'benchmark_report.csv'
        data.to_csv(output_file, index=False)
        logger.info(f"Detailed report saved to {output_file}")


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
    fc = None
    
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
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    
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
    
    args = parser.parse_args()
    
    # Route to appropriate mode
    if args.mode == 'single':
        # Original single calculation mode
        logger.info("=" * 60)
        logger.info("QED VACUUM THRUST MODEL SIMULATION")
        logger.info("=" * 60)
        logger.info(f"\nInput Parameters:")
        logger.info(f"  - Pulsing Frequency: {args.frequency} Hz")
        logger.info(f"  - Drone Mass: {args.mass} kg")
        logger.info(f"  - Number of MADA Units: {args.n_units}")
        
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
        
        P = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
        logger.info(f"Power Consumption: {P:.2f} W ({P/1000:.2f} kW)")
        
        eta_perc = efficiency(T, DEFAULT_V, P)
        logger.info(f"System Efficiency: {eta_perc:.2f}%")
        logger.info(f"  (at v = {DEFAULT_V} m/s = Mach {DEFAULT_V/343:.2f})")
        
        R = range_calc(DEFAULT_V, DEFAULT_E, P)
        logger.info(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
        logger.info(f"  (with {DEFAULT_E/3600000:.0f} kWh energy)")
        
        logger.info(f"\n{'─' * 60}")
        logger.info("PERFORMANCE PROJECTIONS")
        logger.info(f"{'─' * 60}")
        mach_26_speed = 26 * 343
        time_to_mach26 = mach_26_speed / a
        logger.info(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
        logger.info(f"  (assuming constant acceleration)")
        
        weight = args.mass * 9.81
        twr = T / weight
        logger.info(f"Thrust-to-Weight Ratio: {twr:.2f}")
        
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


if __name__ == "__main__":
    main()
import scipy.optimize as opt
import scipy.stats as stats
import multiprocessing as mp
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import h5py
import json
import csv

# Optional imports with fallbacks
try:
    import qutip as qt
    QUTIP_AVAILABLE = True
except ImportError:
    QUTIP_AVAILABLE = False
    print("Warning: QuTiP not available. Cavity QED simulations will be disabled.")

try:
    import pyscf
    from pyscf import gto, scf
    # Note: pyscf.qed module may not be available in all versions
    try:
        from pyscf import qed
        PYSCF_QED_AVAILABLE = True
    except ImportError:
        PYSCF_QED_AVAILABLE = False
    PYSCF_AVAILABLE = True
except ImportError:
    PYSCF_AVAILABLE = False
    PYSCF_QED_AVAILABLE = False
    print("Warning: PySCF not available. QED polarization simulations will be disabled.")

# Constants
MU_0 = const.mu_0  # Vacuum permeability
G = const.G  # Gravitational constant (for emergent gravity analogies)
C = const.c  # Speed of light (for relativistic corrections if needed)

# EGDPP-specific constants (example values; refine via experiments)
CHI_UV = 1e-10  # UV-scale susceptibility
G_COUPLING = 1.0  # Coupling constant
LAMBDA_PARAM = 0.1  # Lambda in RG flow

# Battery constants (LiPo and solid-state)
LIPO_NOMINAL_V = 3.7  # V per cell
LIPO_PEUKERT_CONSTANT = 1.05  # Typical for LiPo
SSB_NOMINAL_V = 3.8  # Higher for solid-state
SSB_PEUKERT_CONSTANT = 1.02  # Lower due to better efficiency

# TEG constants for Bi2Te3
SEEBECK_COEFF = 200e-6  # V/K (typical for Bi2Te3)
THERMAL_COND = 1.5  # W/mK
ZT_BI2TE3 = 1.0  # Figure of merit at room temp
TEG_EFF_FACTOR = ZT_BI2TE3 / (4 + 2 * ZT_BI2TE3)  # Carnot-like approximation

# MADA convergence thresholds
CONVERGENCE_OPTIMAL = 0.95  # Quality for optimal operation
CONVERGENCE_WARNING = 0.85  # Warning threshold
CONVERGENCE_CRITICAL = 0.80  # Critical threshold - emergency shutdown

# Modular Equation Classes with Parameterization

class MagneticField:
    """
    Class for calculating magnetic fields with parameterization and validation.
    
    Attributes:
    B_r (float): Remanence field strength (T)
    L (float): Length (m)
    R (float): Radius (m)
    d (float): Distance (m)
    
    Methods:
    compute_surface(): Compute surface field.
    """
    def __init__(self, B_r, L, R, d):
        if B_r <= 0 or L <= 0 or R <= 0 or d < 0:
            raise ValueError("Parameters must be positive (B_r, L, R > 0; d >= 0)")
        self.B_r = B_r
        self.L = L
        self.R = R
        self.d = d
    
    def compute_surface(self):
        term1 = self.L / np.sqrt(self.R**2 + self.L**2)
        term2 = (self.L + self.d) / np.sqrt(self.R**2 + (self.L + self.d)**2)
        return (self.B_r / 2) * (term1 + term2)

class DisruptionLagrangian:
    """
    Class for disruption Lagrangian with parameterization.
    
    Attributes:
    chi (float): Susceptibility
    B (float): Magnetic field (T)
    h_mu_nu (np.array): Metric perturbation (4x4)
    h_mu_nu_inv (np.array): Inverse metric perturbation (4x4)
    
    Methods:
    compute(): Compute Lagrangian.
    """
    def __init__(self, chi, B, h_mu_nu, h_mu_nu_inv):
        if chi < 0 or B < 0:
            raise ValueError("chi and B must be non-negative")
        self.chi = chi
        self.B = B
        self.h_mu_nu = np.asarray(h_mu_nu)
        self.h_mu_nu_inv = np.asarray(h_mu_nu_inv)
        if self.h_mu_nu.shape != (4,4) or self.h_mu_nu_inv.shape != (4,4):
            raise ValueError("Metric tensors must be 4x4 arrays")
    
    def compute(self):
        contraction = np.einsum('ij,ij->', self.h_mu_nu, self.h_mu_nu_inv)
        return -0.5 * self.chi * self.B**2 * contraction

class ThrustForce:
    """
    Class for thrust force vector with parameterization.
    
    Attributes:
    chi (float): Susceptibility
    B (float): Magnetic field magnitude (T)
    grad_h2 (np.array): Gradient of h^2 (3D vector)
    A (float): Area (m²)
    rho (float): Density (kg/m³)
    
    Methods:
    compute(): Compute force vector.
    """
    def __init__(self, chi, B, grad_h2, A, rho):
        if chi < 0 or B < 0 or A <= 0 or rho <= 0:
            raise ValueError("Parameters must satisfy chi, B >= 0; A, rho > 0")
        self.chi = chi
        self.B = B
        self.grad_h2 = np.asarray(grad_h2)
        if self.grad_h2.shape != (3,):
            raise ValueError("grad_h2 must be a 3D vector")
        self.A = A
        self.rho = rho
    
    def compute(self):
        return self.chi * self.B**2 * self.grad_h2 * self.A * self.rho

# Existing functions remain, but can be called via classes where applicable

def surface_field(B_r, L, R, d):
    """
    Calculate the surface magnetic field. (Legacy function; prefer MagneticField class)
    """
    mf = MagneticField(B_r, L, R, d)
    return mf.compute_surface()

# Integration with Quantum Libraries

def simulate_cavity_qed_vacuum(omega_c=2*np.pi*5e9, omega_a=2*np.pi*5e9, g=2*np.pi*50e6, N=10):
    """
    Simulate cavity QED using QuTiP for vacuum Rabi splitting as approximation for QED vacuum effects.
    
    Parameters:
    omega_c (float): Cavity frequency (Hz)
    omega_a (float): Atom frequency (Hz)
    g (float): Coupling strength (Hz)
    N (int): Fock space dimension
    
    Returns:
    qt.Qobj: Jaynes-Cummings Hamiltonian
    qt.mesolve result: Time evolution from vacuum state
    """
    if not QUTIP_AVAILABLE:
        raise ImportError("QuTiP is required for cavity QED simulations")
    
    a = qt.destroy(N)
    sigma_m = qt.sigmam()
    sigma_p = qt.sigmap()
    H = omega_c * a.dag() * a + (omega_a / 2) * qt.sigmaz() + g * (a.dag() * sigma_m + a * sigma_p)
    
    # Initial vacuum state: ground atom + vacuum photons
    psi0 = qt.tensor(qt.basis(2, 1), qt.basis(N, 0))  # Atom in ground, cavity vacuum
    times = np.linspace(0, 1e-6, 1000)  # Microsecond scale
    result = qt.mesolve(H, psi0, times, [], [a.dag() * a])  # Expectation of photon number
    return H, result

def simulate_qed_polarization(mol_str='H 0 0 0; H 0 0 1.4', basis='sto-3g', field_strength=1e-2):
    """
    Simulate QED effects like vacuum polarization using PySCF.
    
    Parameters:
    mol_str (str): Molecule specification
    basis (str): Basis set
    field_strength (float): External field for polarization
    
    Returns:
    float: Energy with QED correction
    """
    if not PYSCF_AVAILABLE:
        raise ImportError("PySCF is required for QED polarization simulations")
    
    mol = gto.M(atom=mol_str, basis=basis)
    mf = scf.RHF(mol).run()
    
    if PYSCF_QED_AVAILABLE:
        # QED-TDDFT approximation for photon interactions
        # Note: This is a placeholder - actual implementation depends on PySCF version
        try:
            mf_qed = qed.RHF(mf).run()
            energy = mf_qed.energy_tot()
        except Exception as e:
            print(f"Warning: QED module error: {e}. Returning standard HF energy.")
            energy = mf.energy_tot()
    else:
        print("Warning: PySCF QED module not available. Returning standard HF energy.")
        energy = mf.energy_tot()
    
    return energy

def integrate_rg_flow(beta_func, chi_init=CHI_UV, t_span=(1e-10, 1e10), args=(G_COUPLING, LAMBDA_PARAM)):
    """
    Integrate RG flow for chi using scipy.integrate.
    
    Parameters:
    beta_func (callable): Beta function (e.g., rg_beta_chi_spin0)
    chi_init (float): Initial chi
    t_span (tuple): Energy scale range (log scale)
    args (tuple): Additional args for beta_func
    
    Returns:
    scipy.integrate result
    """
    from scipy.integrate import solve_ivp
    def dchi_dt(t, chi): return beta_func(chi[0], *args)
    return solve_ivp(dchi_dt, np.log(t_span), [chi_init], method='RK45')

# Real-Time Efficiency and Power Calculations (Vectorized and Parallel)

def power_consumption_vectorized(I, R, P_eddy):
    """
    Vectorized power consumption.
    """
    I = np.asarray(I)
    R = np.asarray(R)
    P_eddy = np.asarray(P_eddy)
    return I**2 * R + P_eddy

def efficiency_vectorized(T, v, P):
    """
    Vectorized efficiency.
    """
    T = np.asarray(T)
    v = np.asarray(v)
    P = np.asarray(P)
    mask = P > 0
    eta = np.zeros_like(P)
    eta[mask] = (T[mask] * v[mask] / P[mask]) * 100
    return eta

def parallel_monte_carlo_thrust(params, uncertainties, n_sim=1000, n_processes=4):
    """
    Parallel Monte Carlo using multiprocessing.
    """
    def sim_single(_):
        sim_params = {k: np.random.normal(v, uncertainties.get(k, 0)) for k, v in params.items()}
        B = sim_params.get('B_opposing', 50.0)
        scaled_I = sim_params.get('I', 15.0) * (sim_params.get('frequency', 100.0) / 50.0)
        delta_B = pulsed_enhancement(sim_params.get('n_turns', 100), scaled_I)
        B_total = B + delta_B
        F_vec = force_vector(sim_params.get('chi', 1e-10), B_total, sim_params.get('grad_h2', np.array([1.0, 0.0, 0.0])),
                             sim_params.get('A', 1.0), sim_params.get('rho', 1000.0))
        F_mag = np.linalg.norm(F_vec)
        T = total_thrust(sim_params.get('N', 24), F_mag, sim_params.get('eta', 0.95), sim_params.get('theta', 0.0))
        return T
    
    with mp.Pool(n_processes) as pool:
        thrusts = pool.map(sim_single, range(n_sim))
    return np.array(thrusts)

def thermal_dissipation_model(P_in, eta_thermal=0.95, Delta_T_max=50, area=0.01, thickness=0.001):
    """
    Enhanced thermal model with vectorization.
    """
    P_in = np.asarray(P_in)
    heat_generated = P_in * (1 - eta_thermal)
    Delta_T = np.minimum(heat_generated / THERMAL_COND, Delta_T_max)
    recovered = teg_power_recovery(Delta_T, area, thickness)
    return heat_generated - recovered, recovered

# Visualization and Export Tools

def plot_flux_gradient(grad_h2, filename=None):
    """
    Plot flux gradient using Matplotlib.
    """
    grad_h2 = np.asarray(grad_h2)
    if grad_h2.ndim == 1:
        grad_h2 = grad_h2.reshape(1, -1)
    fig, ax = plt.subplots()
    ax.quiver(np.zeros(grad_h2.shape[0]), np.zeros(grad_h2.shape[0]), grad_h2[:,0], grad_h2[:,1])
    ax.set_title('Flux Gradient Vectors')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    if filename:
        plt.savefig(filename)
    else:
        plt.show()

def plot_thrust_vectors(F_vec, filename=None):
    """
    Plot thrust vectors.
    """
    F_vec = np.asarray(F_vec)
    if F_vec.ndim == 1:
        F_vec = F_vec.reshape(1, -1)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.quiver(np.zeros(F_vec.shape[0]), np.zeros(F_vec.shape[0]), np.zeros(F_vec.shape[0]),
              F_vec[:,0], F_vec[:,1], F_vec[:,2])
    ax.set_title('Thrust Vectors')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    if filename:
        plt.savefig(filename)
    else:
        plt.show()

def plot_rg_modifier(chi_values, beta_values, filename=None):
    """
    Plot RG modifier.
    """
    plt.figure()
    plt.plot(chi_values, beta_values)
    plt.title('RG Beta Function for χ')
    plt.xlabel('χ')
    plt.ylabel('β_χ')
    plt.grid(True)
    if filename:
        plt.savefig(filename)
    else:
        plt.show()

def export_to_csv(data, filename, headers=None):
    """
    Export data to CSV.
    """
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        writer.writerows(data)

def export_to_json(data, filename):
    """
    Export to JSON.
    """
    # Convert numpy arrays to lists for JSON serialization
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_serializable(item) for item in obj]
        return obj
    
    serializable_data = convert_to_serializable(data)
    with open(filename, 'w') as f:
        json.dump(serializable_data, f, indent=4)

def export_to_hdf5(data, filename, key='dataset'):
    """
    Export to HDF5.
    """
    with h5py.File(filename, 'w') as f:
        f.create_dataset(key, data=data)

# Uncertainty and Sensitivity Analysis

def monte_carlo_thrust(params, uncertainties, n_sim=1000):
    """
    Monte Carlo simulation for thrust (uses parallel version by default).
    """
    thrusts = parallel_monte_carlo_thrust(params, uncertainties, n_sim)
    return thrusts

def sensitivity_analysis(params, func, perturbations=0.01, method='finite_diff'):
    """
    Sensitivity ranking using finite differences.
    
    Parameters:
    params (dict): Nominal parameters
    func (callable): Function to evaluate (e.g., lambda p: total_thrust(... with p))
    perturbations (float): Relative perturbation
    method (str): 'finite_diff'
    
    Returns:
    dict: Sensitivity rankings
    """
    nominal = func(params)
    sensitivities = {}
    for key, val in params.items():
        if val == 0:
            continue  # Skip zero values to avoid division by zero
        pert_params = params.copy()
        pert_params[key] = val * (1 + perturbations)
        pert_val = func(pert_params)
        sensitivities[key] = abs(pert_val - nominal) / (val * perturbations)
    # Rank by magnitude
    ranked = sorted(sensitivities.items(), key=lambda x: x[1], reverse=True)
    return dict(ranked)

# Documentation and Unit Testing
# All functions have comprehensive docstrings with derivations where applicable.
# For unit testing, integrate with pytest in separate test files, but example inline test:

def test_surface_field():
    """
    Example unit test for surface_field.
    """
    expected = (1.4 / 2) * (0.3 / np.sqrt(0.15**2 + 0.3**2) + 0.35 / np.sqrt(0.15**2 + 0.35**2))
    result = surface_field(1.4, 0.3, 0.15, 0.05)
    assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    print("test_surface_field PASSED")

# Core physics functions

def opposing_field(m1, m2, d, k=1.0):
    """
    Calculate the opposing magnetic field magnitude.
    
    IMPORTANT: This calculates the MAGNITUDE of the combined field strength
    when two magnetic moments are OPPOSING (pointing at each other).
    This function does NOT verify field direction - use validate_mada_convergence()
    to ensure fields are actually opposing before using this value.
    
    Parameters:
    m1 (float): Magnetic moment 1 (A m²)
    m2 (float): Magnetic moment 2 (A m²)
    d (float): Distance between MADA units (m)
    k (float): Scaling factor (default 1.0)
    
    Returns:
    float: Opposing field magnitude B_opposing (T)
    
    Note: Result is only valid if MADA units are properly configured with
          fields pointing toward each other (converging at focal point).
    """
    return (MU_0 * m1 * m2 / (2 * np.pi * d**2)) * k


def calculate_field_at_point(m, position_source, position_target, direction):
    """
    Calculate magnetic field vector at a target point from a magnetic dipole.
    
    Parameters:
    m (float): Magnetic moment magnitude (A m²)
    position_source (np.array): Position of magnetic source [x, y, z] (m)
    position_target (np.array): Position where field is calculated [x, y, z] (m)
    direction (np.array): Direction unit vector of magnetic moment [x, y, z]
    
    Returns:
    np.array: Magnetic field vector at target point [Bx, By, Bz] (T)
    """
    r_vec = position_target - position_source
    r = np.linalg.norm(r_vec)
    
    if r == 0:
        return np.array([0.0, 0.0, 0.0])
    
    r_hat = r_vec / r
    m_vec = m * direction
    
    # Magnetic dipole field: B = (μ₀/4π) * (3(m·r̂)r̂ - m) / r³
    dot_product = np.dot(m_vec, r_hat)
    B = (MU_0 / (4 * np.pi)) * (3 * dot_product * r_hat - m_vec) / r**3
    
    return B


def calculate_convergence_quality(B1, B2):
    """
    Calculate MADA convergence quality (how well fields oppose).
    
    This is CRITICAL for QED vacuum polarization propulsion.
    Fields must be OPPOSING (pointing at each other) to create
    the focal point where virtual pair production occurs.
    
    Parameters:
    B1 (np.array): Magnetic field vector from MADA unit 1 [Bx, By, Bz] (T)
    B2 (np.array): Magnetic field vector from MADA unit 2 [Bx, By, Bz] (T)
    
    Returns:
    float: Convergence quality [-1, 1]
           1.0 = Perfect opposition (fields pointing directly at each other) ✅
           0.0 = Perpendicular fields
          -1.0 = Parallel fields (both pointing same direction) ❌
    
    Raises:
    ValueError: If either field vector has zero magnitude
    """
    B1 = np.asarray(B1)
    B2 = np.asarray(B2)
    
    B1_mag = np.linalg.norm(B1)
    B2_mag = np.linalg.norm(B2)
    
    if B1_mag == 0 or B2_mag == 0:
        raise ValueError("Magnetic field vectors cannot have zero magnitude")
    
    # Normalize
    B1_norm = B1 / B1_mag
    B2_norm = B2 / B2_mag
    
    # Dot product: -1 means opposing (good), +1 means parallel (bad)
    dot_product = np.dot(B1_norm, B2_norm)
    
    # Return negative of dot product: 1.0 = opposing, -1.0 = parallel
    return -dot_product


def validate_mada_convergence(B1, B2, threshold=CONVERGENCE_WARNING, raise_on_fail=False):
    """
    Validate that MADA fields are properly converging (opposing).
    
    Parameters:
    B1 (np.array): Magnetic field vector from MADA unit 1 [Bx, By, Bz] (T)
    B2 (np.array): Magnetic field vector from MADA unit 2 [Bx, By, Bz] (T)
    threshold (float): Minimum acceptable convergence quality (default 0.85)
    raise_on_fail (bool): If True, raise ValueError on poor convergence
    
    Returns:
    dict: {
        'quality': float,
        'status': str ('optimal', 'acceptable', 'warning', 'critical'),
        'is_valid': bool,
        'message': str
    }
    
    Raises:
    ValueError: If raise_on_fail=True and convergence is below threshold
    """
    try:
        quality = calculate_convergence_quality(B1, B2)
    except ValueError as e:
        return {
            'quality': 0.0,
            'status': 'error',
            'is_valid': False,
            'message': f"Error calculating convergence: {str(e)}"
        }
    
    # Determine status
    if quality >= CONVERGENCE_OPTIMAL:
        status = 'optimal'
        is_valid = True
        message = f"Excellent field convergence (quality={quality:.3f})"
    elif quality >= CONVERGENCE_WARNING:
        status = 'acceptable'
        is_valid = True
        message = f"Acceptable field convergence (quality={quality:.3f})"
    elif quality >= CONVERGENCE_CRITICAL:
        status = 'warning'
        is_valid = quality >= threshold
        message = f"WARNING: Suboptimal field convergence (quality={quality:.3f})"
    elif quality >= 0:
        status = 'critical'
        is_valid = False
        message = f"CRITICAL: Poor field convergence (quality={quality:.3f})"
    else:
        status = 'diverging'
        is_valid = False
        message = f"FAILURE: Fields are diverging or parallel (quality={quality:.3f})"
    
    result = {
        'quality': quality,
        'status': status,
        'is_valid': is_valid,
        'message': message
    }
    
    if raise_on_fail and not is_valid:
        raise ValueError(f"MADA convergence validation failed: {message}")
    
    return result


def opposing_field_with_validation(m1, m2, d, B1_vec, B2_vec, k=1.0):
    """
    Calculate opposing field WITH convergence validation.
    This is the SAFE version that verifies fields are actually opposing.
    
    Parameters:
    m1 (float): Magnetic moment 1 (A m²)
    m2 (float): Magnetic moment 2 (A m²)
    d (float): Distance (m)
    B1_vec (np.array): Field vector from MADA unit 1 [Bx, By, Bz] (T)
    B2_vec (np.array): Field vector from MADA unit 2 [Bx, By, Bz] (T)
    k (float): Scaling factor (default 1.0)
    
    Returns:
    tuple: (B_opposing (float), convergence_info (dict))
    
    Raises:
    ValueError: If field convergence is below critical threshold
    """
    # Validate convergence
    convergence = validate_mada_convergence(B1_vec, B2_vec, raise_on_fail=True)
    
    # Calculate magnitude only if convergence is acceptable
    B_opp = opposing_field(m1, m2, d, k)
    
    return B_opp, convergence


def pulsed_enhancement(n, I):
    """
    Calculate the pulsed magnetic field enhancement.
    
    Parameters:
    n (float): Number of turns per unit length (1/m)
    I (float): Current (A)
    
    Returns:
    float: Delta B (T)
    """
    return MU_0 * n * I


def lagrangian_disrupt(chi, B, h_mu_nu, h_mu_nu_inv):
    """
    Calculate the disruption Lagrangian (numerical approximation).
    
    Parameters:
    chi (float): Susceptibility
    B (float): Magnetic field (T)
    h_mu_nu (np.array): Metric perturbation (4x4)
    h_mu_nu_inv (np.array): Inverse metric perturbation (4x4)
    
    Returns:
    float: L_disrupt
    """
    dl = DisruptionLagrangian(chi, B, h_mu_nu, h_mu_nu_inv)
    return dl.compute()


def rg_beta_chi_spin0(chi, g, lambda_val):
    """
    Calculate the RG beta function for chi (spin-0 emergent).
    
    Parameters:
    chi (float): Susceptibility
    g (float): Coupling constant
    lambda_val (float): Lambda parameter
    
    Returns:
    float: beta_chi
    
    Note: Requires |2*lambda_val| < 1 to avoid singularity
    """
    if abs(2 * lambda_val) >= 1:
        raise ValueError("Lambda parameter must satisfy |2*lambda| < 1 to avoid singularity")
    return -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lambda_val))


# Alias for backward compatibility
rg_beta_chi = rg_beta_chi_spin0


def rg_beta_chi_spin2(chi, eta_chi, c, g):
    """
    Alternative RG beta function for chi (spin-2 emergent).
    
    Parameters:
    chi (float): Susceptibility
    eta_chi (float): Anomalous dimension
    c (float): Constant
    g (float): Coupling constant
    
    Returns:
    float: beta_chi
    """
    return (4 + eta_chi) * chi + c * g * chi


def source_term(chi, B, h_mu_nu):
    """
    Calculate the source term delta T_mu_nu (approximation).
    
    Parameters:
    chi (float): Susceptibility
    B (float): Magnetic field (T)
    h_mu_nu (np.array): Metric perturbation (4x4)
    
    Returns:
    np.array: delta T_mu_nu (4x4)
    """
    return chi * B**2 * h_mu_nu


def force_vector(chi, B, grad_h2, A, rho):
    """
    Calculate the force vector.
    
    IMPORTANT: This force is only valid when B is from properly OPPOSING
    magnetic fields (converging at focal point). Use validate_mada_convergence()
    to verify field configuration before relying on this calculation.
    
    Parameters:
    chi (float): Susceptibility
    B (float): Magnetic field magnitude (T)
    grad_h2 (np.array): Gradient of h^2 (3D vector)
    A (float): Area (m²)
    rho (float): Density (kg/m³)
    
    Returns:
    np.array: Force F (3D vector, N)
    """
    tf = ThrustForce(chi, B, grad_h2, A, rho)
    return tf.compute()


def total_thrust(N, F, eta, theta):
    """
    Calculate the total thrust.
    
    Parameters:
    N (int): Number of MADA units
    F (float or np.array): Force magnitude (N) or force vector
    eta (float): Efficiency (0-1)
    theta (float): Angle (degrees)
    
    Returns:
    float: Thrust T (N)
    """
    # If F is a vector, use its magnitude
    F_mag = np.linalg.norm(F) if isinstance(F, np.ndarray) else F
    return N * F_mag * eta * np.cos(np.deg2rad(theta))


def acceleration(T, m):
    """
    Calculate acceleration.
    
    Parameters:
    T (float): Thrust (N)
    m (float): Mass (kg)
    
    Returns:
    float: Acceleration a (m/s²)
    """
    if m <= 0:
        raise ValueError("Mass must be positive")
    return T / m


def power_consumption(I, R, P_eddy):
    """
    Calculate power consumption. (Legacy; use vectorized version)
    """
    return power_consumption_vectorized(I, R, P_eddy)


def efficiency(T, v, P):
    """
    Calculate efficiency. (Legacy; use vectorized)
    """
    return efficiency_vectorized(T, v, P)


def range_calc(v, E, P):
    """
    Calculate range.
    
    Parameters:
    v (float): Velocity (m/s)
    E (float): Energy (J)
    P (float): Power (W)
    
    Returns:
    float: Range R (m)
    """
    if P <= 0:
        raise ValueError("Power must be positive")
    return v * (E / P)


# Expanded Tactical Toolkits from EGDPP Theory

def non_ballistic_trajectory(start_pos, target_pos, curvature=0.5, steps=100):
    """
    Generate a non-ballistic (curved) trajectory for radar evasion.
    Uses a simple parametric curve (e.g., Bezier-like) to avoid straight lines.
    
    Parameters:
    start_pos (np.array): Starting position [x, y, z]
    target_pos (np.array): Target position [x, y, z]
    curvature (float): Curvature factor (0: straight, >0: curved)
    steps (int): Number of points in trajectory
    
    Returns:
    np.array: Trajectory points (steps x 3)
    """
    start_pos = np.asarray(start_pos)
    target_pos = np.asarray(target_pos)
    t = np.linspace(0, 1, steps)
    diff = target_pos - start_pos
    mid_point = start_pos + diff / 2 + curvature * np.array([0, diff[2], -diff[1]])  # Perpendicular offset for curve
    traj = (1 - t)[:, np.newaxis] ** 2 * start_pos + 2 * (1 - t)[:, np.newaxis] * t[:, np.newaxis] * mid_point + t[:, np.newaxis] ** 2 * target_pos
    return traj


def radar_evasion_probability(traj, radar_pos, rcs=1.0):
    """
    Estimate radar evasion probability based on trajectory.
    Simplified model: Lower probability for closer approaches or higher RCS.
    
    Parameters:
    traj (np.array): Trajectory points (N x 3)
    radar_pos (np.array): Radar position [x, y, z]
    rcs (float): Radar cross-section (m²)
    
    Returns:
    float: Evasion probability (0-1; higher better)
    """
    radar_pos = np.asarray(radar_pos)
    distances = np.linalg.norm(traj - radar_pos, axis=1)
    min_dist = np.min(distances)
    # Simple inverse model: P_evade = 1 / (1 + RCS / min_dist^4) ~ radar equation approximation
    return 1 / (1 + rcs / min_dist**4)


# Battery Integration Models

def lipo_discharge_capacity(C_nom, I, t, peukert_k=LIPO_PEUKERT_CONSTANT):
    """
    LiPo battery discharge model using Peukert's law.
    
    Parameters:
    C_nom (float): Nominal capacity (Ah)
    I (float): Discharge current (A)
    t (float): Time (h)
    peukert_k (float): Peukert constant (default 1.05)
    
    Returns:
    float: Remaining capacity (Ah)
    """
    C_eff = C_nom * (C_nom / I)**(peukert_k - 1)
    discharged = I * t
    return max(0, C_eff - discharged)


def ssb_discharge_capacity(C_nom, I, t, peukert_k=SSB_PEUKERT_CONSTANT):
    """
    Solid-state battery discharge model (similar but better efficiency).
    
    Parameters: Same as lipo_discharge_capacity
    """
    C_eff = C_nom * (C_nom / I)**(peukert_k - 1)
    discharged = I * t
    return max(0, C_eff - discharged)


def battery_voltage_curve(soc, V_nom, V_min=3.0, V_max=4.2):
    """
    Simple voltage curve model (linear approximation).
    
    Parameters:
    soc (float): State of charge (0-1)
    V_nom (float): Nominal voltage (V)
    V_min (float): Min voltage
    V_max (float): Max voltage
    
    Returns:
    float: Voltage (V)
    """
    return V_min + soc * (V_max - V_min)


# Range Estimators for Stealth Operations

def stealth_range_calc(v_stealth, E, P_low, eta_stealth=0.8):
    """
    Range estimator for stealth operations (lower power/speed).
    
    Parameters:
    v_stealth (float): Stealth velocity (m/s)
    E (float): Energy (J)
    P_low (float): Low-power consumption (W)
    eta_stealth (float): Stealth efficiency factor (default 0.8)
    
    Returns:
    float: Stealth range (m)
    """
    if P_low <= 0:
        raise ValueError("Power must be positive")
    return eta_stealth * v_stealth * (E / P_low)


# Thermal Simulation Extensions with Bi2Te3 TEG

def teg_power_recovery(Delta_T, area, thickness, load_res=1.0):
    """
    Calculate power recovered from Bi2Te3 TEG.
    Simplified model: P = (alpha Delta_T)^2 / (4 R_int) for matched load.
    
    Parameters:
    Delta_T (float or np.array): Temperature difference (K)
    area (float): TEG area (m²)
    thickness (float): Thickness (m)
    load_res (float): Load resistance (Ohm, default matched)
    
    Returns:
    float or np.array: Recovered power (W)
    """
    R_int = thickness / (THERMAL_COND * area)  # Internal thermal resistance approx
    alpha = SEEBECK_COEFF  # Seebeck coefficient
    P_max = (alpha * Delta_T)**2 / (4 * R_int)
    return TEG_EFF_FACTOR * P_max  # Adjust with ZT efficiency


def thermal_dissipation(P_in, eta_thermal=0.95, Delta_T_max=50):
    """
    Simulate thermal dissipation with TEG recovery.
    
    Parameters:
    P_in (float): Input power (W)
    eta_thermal (float): Thermal efficiency
    Delta_T_max (float): Max allowable Delta T (K)
    
    Returns:
    tuple: (heat_dissipated (W), recovered (W))
    """
    return thermal_dissipation_model(P_in, eta_thermal, Delta_T_max)


# Symbolic versions using SymPy (for optional symbolic manipulation)
def symbolic_surface_field():
    """
    Return symbolic expression for surface field.
    
    Returns:
    sympy expression
    """
    B_r, L, R, d = sp.symbols('B_r L R d', positive=True, real=True)
    term1 = L / sp.sqrt(R**2 + L**2)
    term2 = (L + d) / sp.sqrt(R**2 + (L + d)**2)
    return (B_r / 2) * (term1 + term2)


def symbolic_opposing_field():
    """
    Return symbolic expression for opposing field.
    
    Returns:
    sympy expression
    """
    m1, m2, d, k = sp.symbols('m_1 m_2 d k', positive=True, real=True)
    mu_0 = sp.Symbol('mu_0', positive=True, real=True)
    return (mu_0 * m1 * m2 / (2 * sp.pi * d**2)) * k


def symbolic_force_vector():
    """
    Return symbolic expression for force vector.
    
    Returns:
    sympy expression
    """
    chi, B, A, rho = sp.symbols('chi B A rho', real=True)
    # Scalar version for symbolic computation
    grad_h2 = sp.Symbol('grad_h2', real=True)
    return chi * B**2 * grad_h2 * A * rho


def symbolic_rg_beta_chi_spin0():
    """
    Symbolic RG beta for spin-0.
    """
    chi, g, lam = sp.symbols('chi g lambda', real=True)
    return -4 * chi + (g / (2 * sp.pi)) * (chi / (1 - 2 * lam))


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("QED Vacuum Thrust Control - Equations Module (With MADA Validation)")
    print("=" * 70)
    
    print("\n1. Surface Field Example (using class):")
    mf = MagneticField(B_r=1.4, L=0.3, R=0.15, d=0.05)
    B_surf = mf.compute_surface()
    print(f"   B_surface = {B_surf:.4f} T")
    
    print("\n2. Opposing Field Example (WITHOUT validation - UNSAFE):")
    B_opp = opposing_field(m1=100, m2=100, d=0.1, k=1.0)
    print(f"   B_opposing = {B_opp:.6e} T")
    print("   WARNING: This value is only valid if fields are actually opposing!")
    
    print("\n3. MADA Convergence Validation Example:")
    # Correct configuration: fields pointing toward each other
    B1_correct = np.array([-50.0, 0.0, 0.0])  # At +X, pointing toward origin
    B2_correct = np.array([50.0, 0.0, 0.0])   # At -X, pointing toward origin
    convergence = validate_mada_convergence(B1_correct, B2_correct)
    print(f"   Correct config: {convergence['message']}")
    
    # Incorrect configuration: fields pointing away (the FreeCAD bug!)
    B1_wrong = np.array([50.0, 0.0, 0.0])   # At +X, pointing away
    B2_wrong = np.array([-50.0, 0.0, 0.0])  # At -X, pointing away
    convergence_wrong = validate_mada_convergence(B1_wrong, B2_wrong)
    print(f"   Wrong config: {convergence_wrong['message']}")
    
    print("\n4. Opposing Field WITH Validation (SAFE):")
    try:
        B_opp_safe, conv_info = opposing_field_with_validation(
            100, 100, 0.1, B1_correct, B2_correct, k=1.0
        )
        print(f"   B_opposing = {B_opp_safe:.6e} T")
        print(f"   {conv_info['message']}")
    except ValueError as e:
        print(f"   ERROR: {e}")
    
    print("\n5. Pulsed Enhancement Example:")
    delta_B = pulsed_enhancement(n=1000, I=10)
    print(f"   ΔB = {delta_B:.4f} T")
    
    print("\n6. RG Beta Chi (Spin-0) Example:")
    beta = rg_beta_chi_spin0(chi=1e-10, g=1.0, lambda_val=0.1)
    print(f"   β_χ = {beta:.6e}")
    
    print("\n7. Force Vector Example (using class):")
    tf = ThrustForce(chi=1e-10, B=20, grad_h2=np.array([1, 0, 0]), A=0.01, rho=2700)
    F_vec = tf.compute()
    print(f"   F = {F_vec} N")
    print("   NOTE: Only valid if B is from properly opposing fields!")
    
    print("\n8. Total Thrust Example:")
    T = total_thrust(N=10, F=100, eta=0.95, theta=0)
    print(f"   Thrust = {T:.2f} N")
    
    print("\n9. Acceleration Example:")
    a = acceleration(T=1000, m=50)
    print(f"   Acceleration = {a:.2f} m/s² ({a/9.81:.2f}g)")
    
    print("\n10. Convergence Quality Calculation:")
    quality = calculate_convergence_quality(B1_correct, B2_correct)
    print(f"   Quality (correct): {quality:.4f} (1.0 = perfect)")
    quality_wrong = calculate_convergence_quality(B1_wrong, B2_wrong)
    print(f"   Quality (wrong): {quality_wrong:.4f} (-1.0 = diverging)")
    
    print("\n11. Symbolic Surface Field:")
    print(f"   {symbolic_surface_field()}")
    
    print("\n12. Non-Ballistic Trajectory Example:")
    traj = non_ballistic_trajectory(np.array([0,0,0]), np.array([100,50,20]), curvature=0.5, steps=5)
    print(f"   Trajectory points (first 3):\n{traj[:3]}")
    
    print("\n13. Radar Evasion Probability Example:")
    prob = radar_evasion_probability(traj, np.array([50,25,10]))
    print(f"   Evasion Prob: {prob:.4f}")
    
    print("\n14. Parallel Monte Carlo Thrust Example:")
    params = {'B_opposing': 50, 'frequency': 100, 'I': 15, 'chi': 1e-10, 'grad_h2': np.array([1,0,0]),
              'A':1, 'rho':1000, 'N':24, 'eta':0.95, 'theta':0, 'n_turns':100}
    uncertainties = {'B_opposing': 2.0, 'frequency': 5.0, 'chi': 1e-11}
    thrusts = parallel_monte_carlo_thrust(params, uncertainties, n_sim=10, n_processes=2)
    print(f"   Mean Thrust: {np.mean(thrusts):.2f} N, Std: {np.std(thrusts):.2f} N")
    
    print("\n15. LiPo Discharge Example:")
    rem_cap = lipo_discharge_capacity(10, 5, 1)  # 10Ah, 5A, 1h
    print(f"   Remaining Capacity: {rem_cap:.2f} Ah")
    
    print("\n16. SSB Discharge Example:")
    rem_cap_ssb = ssb_discharge_capacity(12, 5, 1)
    print(f"   Remaining Capacity: {rem_cap_ssb:.2f} Ah")
    
    print("\n17. Battery Voltage Example:")
    v = battery_voltage_curve(0.8, LIPO_NOMINAL_V)
    print(f"   Voltage at 80% SOC: {v:.2f} V")
    
    print("\n18. Stealth Range Example:")
    stealth_r = stealth_range_calc(100, 1e6, 1000)
    print(f"   Stealth Range: {stealth_r:.2f} m")
    
    print("\n19. TEG Recovery Example:")
    recovered = teg_power_recovery(50, 0.01, 0.001)
    print(f"   Recovered Power: {recovered:.4f} W")
    
    print("\n20. Thermal Dissipation Model Example:")
    heat, rec = thermal_dissipation_model(5000, eta_thermal=0.95)
    print(f"   Heat Dissipated: {heat:.2f} W, Recovered: {rec:.4f} W")
    
    if QUTIP_AVAILABLE:
        print("\n21. Cavity QED Simulation Example:")
        H, result = simulate_cavity_qed_vacuum()
        print(f"   Hamiltonian shape: {H.shape}")
        print(f"   Average photons at end: {result.expect[0][-1]:.4f}")
    else:
        print("\n21. Cavity QED Simulation: SKIPPED (QuTiP not available)")
    
    if PYSCF_AVAILABLE:
        print("\n22. QED Polarization Simulation Example:")
        try:
            energy = simulate_qed_polarization()
            print(f"   QED Energy: {energy:.4f} a.u.")
        except Exception as e:
            print(f"   QED Polarization: ERROR - {e}")
    else:
        print("\n22. QED Polarization Simulation: SKIPPED (PySCF not available)")
    
    print("\n23. RG Flow Integration Example:")
    rg_result = integrate_rg_flow(rg_beta_chi_spin0)
    print(f"   Final chi: {rg_result.y[0][-1]:.6e}")
    
    print("\n24. Sensitivity Analysis Example:")
    def thrust_func(p): 
        tf = ThrustForce(p['chi'], p['B'], p['grad_h2'], p['A'], p['rho'])
        return np.linalg.norm(tf.compute())
    sens_params = {'chi': 1e-10, 'B': 20, 'grad_h2': np.array([1,0,0]), 'A': 0.01, 'rho': 2700}
    sens = sensitivity_analysis(sens_params, thrust_func)
    print(f"   Top 3 Sensitivities: {list(sens.items())[:3]}")
    
    print("\n" + "=" * 70)
    print("\nCRITICAL SAFETY REMINDERS:")
    print("=" * 70)
    print("1. ALWAYS validate MADA convergence before using opposing_field()")
    print("2. Use opposing_field_with_validation() for safety-critical calculations")
    print("3. Monitor convergence quality in real-time during flight")
    print("4. Fields must point TOWARD each other (converging), not away!")
    print("5. Quality < 0.8 indicates critical misconfiguration")
    print("=" * 70)
    
    # Run example test
    print("\n25. Running unit test:")
    test_surface_field()
