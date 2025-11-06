"""
simulations/thrust_model.py

Extended thrust model simulation with multiple modes:
- Single calculation
- Swarm simulation (multi-drone)
- Benchmark against telemetry
- Real-time sensor monitoring

All issues from code review have been addressed.
"""

import argparse
import numpy as np
import sys
import os
import time
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

try:
    import multiprocessing as mp
    MULTIPROCESSING_AVAILABLE = True
except ImportError:
    MULTIPROCESSING_AVAILABLE = False
    mp = None  # Set to None for type checking

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
        validate_mada_convergence,
        SPEED_OF_SOUND,
        PHYSICS_STEP_RATE,
        SWARM_ATTACK_PROBABILITY
    )
except ImportError as e:
    print(f"ERROR: Failed to import equations module: {e}")
    print("Please ensure equations.py is in the simulations/ directory")
    sys.exit(1)

# Optional imports with proper fallback handling
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

# Hardware interfaces - create mock if not available
HARDWARE_AVAILABLE = False
try:
    from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    logging.warning("Hardware interfaces not available. Real-time mode will use simulated data.")
    
    # Create mock classes for type checking
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

# Configure logging with proper namespace
logger = logging.getLogger(__name__)

# Only configure if running as main (avoid conflicts when imported)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# =============================================================================
# Configuration and Default Parameters
# =============================================================================

class SimulationConfig:
    """Configuration class for simulation parameters."""
    
    # Magnetic field parameters
    M1 = 100.0  # Magnetic moment 1 (A m²)
    M2 = 100.0  # Magnetic moment 2 (A m²)
    DISTANCE = 0.05  # Distance between magnets (m)
    K_SCALING = 1.0  # Scaling factor
    
    # Coil parameters
    N_TURNS = 100  # Number of turns per unit length
    BASE_CURRENT = 15.0  # Base current (A)
    
    # QED parameters
    CHI = 1e-10  # Susceptibility
    G_COUPLING = 1.0  # Coupling constant
    LAMBDA_PARAM = 0.1  # Lambda in RG flow
    
    # Geometric parameters
    GRAD_H2 = np.array([1.0, 0.0, 0.0])  # Gradient of h^2
    AREA = 1.0  # Area (m²)
    RHO = 1000.0  # Density (kg/m³)
    
    # MADA parameters
    N_UNITS = 24  # Number of MADA units
    ETA = 0.95  # Efficiency
    THETA = 0.0  # Angle (degrees)
    
    # Drone parameters
    MASS = 20000.0  # Drone mass (kg) - kept as requested
    
    # Electrical parameters
    RESISTANCE = 5.0  # Resistance (Ω)
    P_EDDY = 100.0  # Eddy current losses (W)
    
    # Performance parameters
    VELOCITY = 1000.0  # Velocity (m/s)
    ENERGY = 500000.0 * 3600  # 500 kWh in J
    
    # Frequency parameters
    BASE_FREQUENCY = 50.0  # Base frequency (Hz) for scaling
    DEFAULT_FREQUENCY = 100.0  # Default operating frequency (Hz)


# =============================================================================
# Core Simulation Functions
# =============================================================================

def calculate_thrust_params(
    args: argparse.Namespace,
    B_opposing: Optional[float] = None,
    frequency: Optional[float] = None,
    verbose: bool = False
) -> Tuple[float, float, float, float, float, float]:
    """
    Core thrust calculation function, reusable across modes.
    
    Args:
        args: Argument namespace with simulation parameters
        B_opposing: Opposing magnetic field strength (T), optional
        frequency: Pulsing frequency (Hz), optional
        verbose: Enable verbose output
    
    Returns:
        Tuple of (thrust, acceleration, power, efficiency, range, B_total)
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
    
    # Calculate force vector
    F_vec = force_vector(
        SimulationConfig.CHI,
        B_total,
        SimulationConfig.GRAD_H2,
        SimulationConfig.AREA,
        SimulationConfig.RHO
    )
    F_mag = np.linalg.norm(F_vec)
    
    # Calculate total thrust
    T = total_thrust(args.n_units, F_mag, SimulationConfig.ETA, SimulationConfig.THETA)
    
    # Calculate acceleration
    a = acceleration(T, args.mass)
    
    # Calculate power consumption
    P = power_consumption(scaled_I, SimulationConfig.RESISTANCE, SimulationConfig.P_EDDY)
    
    # Calculate efficiency
    eta_perc = efficiency(T, SimulationConfig.VELOCITY, P)
    
    # Calculate range
    R = range_calc(SimulationConfig.VELOCITY, SimulationConfig.ENERGY, P)
    
    if verbose:
        logger.info(f"Thrust: {T:.2f} N, Accel: {a:.2f} m/s², Power: {P:.2f} W")
    
    return T, a, P, eta_perc, R, B_total


# =============================================================================
# Swarm Simulation Mode
# =============================================================================

def simulate_swarm(
    num_drones: int = 5,
    scenario: str = 'asymmetric',
    simulation_time: float = 60.0,
    verbose: bool = False,
    headless: bool = True
) -> None:
    """
    Multi-drone swarm simulation using PyBullet.
    
    Args:
        num_drones: Number of drones in swarm
        scenario: 'asymmetric' or 'symmetric' warfare scenario
        simulation_time: Simulation duration in seconds
        verbose: Enable verbose output
        headless: Run without GUI (DIRECT mode) for servers
    """
    if not PYBULLET_AVAILABLE:
        logger.error("PyBullet not installed. Install with: pip install pybullet")
        return
    
    logger.info(f"Starting swarm simulation: {num_drones} drones, {scenario} scenario")
    
    # Connect to physics engine - use DIRECT mode for headless operation
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
                SimulationConfig.CHI,
                50,
                SimulationConfig.GRAD_H2,
                SimulationConfig.AREA,
                SimulationConfig.RHO
            )
        )
        base_T = total_thrust(
            SimulationConfig.N_UNITS,
            base_F,
            SimulationConfig.ETA,
            SimulationConfig.THETA
        )
        
        # Set up scenario-specific thrust distribution
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
        steps = int(simulation_time * PHYSICS_STEP_RATE)
        sleep_time = 1.0 / PHYSICS_STEP_RATE if not headless else 0
        
        for step in range(steps):
            # Apply thrust forces
            for i, drone_id in enumerate(drone_ids):
                thrust = drone_thrusts[i]
                # Apply vertical thrust (hover) + small maneuvers
                thrust_vec = [0, 0, thrust + np.random.normal(0, 100)]
                p.applyExternalForce(drone_id, -1, thrust_vec, [0, 0, 0], p.LINK_FRAME)
            
            # Simulate asymmetric warfare events
            if scenario == 'asymmetric' and np.random.rand() < SWARM_ATTACK_PROBABILITY:
                # Advanced drones "attack" standard drones
                if len(drone_ids) > num_drones // 2:
                    target_id = np.random.choice(drone_ids[num_drones//2:])
                    attack_force = [0, 0, -20000]  # Downward force
                    p.applyExternalForce(target_id, -1, attack_force, [0, 0, 0], p.LINK_FRAME)
                    if verbose:
                        logger.info(f"Step {step}: Attack on drone {drone_ids.index(target_id)}")
            
            p.stepSimulation()
            
            if step % PHYSICS_STEP_RATE == 0 and verbose:  # Log every second
                logger.info(f"Simulation time: {step/PHYSICS_STEP_RATE:.1f}s / {simulation_time}s")
            
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Get final positions
        logger.info("\nFinal drone positions:")
        for i, drone_id in enumerate(drone_ids):
            pos, _ = p.getBasePositionAndOrientation(drone_id)
            logger.info(f"  Drone {i}: {pos}")
        
    finally:
        # Ensure cleanup even if interrupted
        p.disconnect()
        logger.info(f"Swarm simulation complete")


# =============================================================================
# Benchmark Mode
# =============================================================================

def benchmark_with_telemetry(
    telemetry_file: str,
    args: argparse.Namespace,
    verbose: bool = False
) -> None:
    """
    Benchmark simulation outputs against hardware telemetry data.
    
    Args:
        telemetry_file: Path to CSV file with telemetry data
        args: Argument namespace with simulation parameters
        verbose: Enable verbose output
    """
    if not PANDAS_AVAILABLE:
        logger.error("pandas not installed. Install with: pip install pandas")
        return
    
    # Validate file exists
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
    
    # Normalize column names (strip whitespace, lowercase)
    data.columns = data.columns.str.strip().str.lower()
    
    # Expected columns
    required_cols = ['measured_b', 'measured_freq']
    missing_cols = [col for col in required_cols if col not in data.columns]
    
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        logger.info(f"Available columns: {list(data.columns)}")
        return
    
    sim_thrusts = []
    sim_accels = []
    differences = []
    
    for idx, row in data.iterrows():
        B = row.get('measured_b', 50.0)
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
    valid_thrust_diffs = [d[0] for d in differences if d[0] > 0]
    valid_accel_diffs = [d[1] for d in differences if d[1] > 0]
    
    avg_diff_T = np.mean(valid_thrust_diffs) if valid_thrust_diffs else 0
    avg_diff_a = np.mean(valid_accel_diffs) if valid_accel_diffs else 0
    
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
    verbose: bool = False
) -> None:
    """
    Real-time mode: Read sensor data and compute thrust dynamically.
    
    Args:
        args: Argument namespace with simulation parameters
        sensor_port: Serial port for sensor connection
        update_interval: Update interval in seconds
        verbose: Enable verbose output
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
            logger.info(
                f"[{iteration:04d}] B={B:.2f}T, Freq={freq:.1f}Hz, "
                f"Thrust={T:.0f}N, Accel={a:.1f}m/s² ({a_g:.1f}g), "
                f"Power={P:.0f}W"
            )
            
            iteration += 1
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        logger.info("\nReal-time monitoring stopped by user")
    finally:
        if mcu:
            try:
                mcu.close()
                logger.info("Microcontroller connection closed")
            except:
                pass


# =============================================================================
# Single Calculation Mode
# =============================================================================

def single_calculation_mode(args: argparse.Namespace) -> None:
    """
    Perform a single thrust calculation with detailed output.
    
    Args:
        args: Argument namespace with simulation parameters
    """
    logger.info("=" * 60)
    logger.info("QED VACUUM THRUST MODEL SIMULATION")
    logger.info("=" * 60)
    logger.info(f"\nInput Parameters:")
    logger.info(f"  - Pulsing Frequency: {args.frequency} Hz")
    logger.info(f"  - Drone Mass: {args.mass} kg")
    logger.info(f"  - Number of MADA Units: {args.n_units}")
    
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
        beta_chi = rg_beta_chi(
            SimulationConfig.CHI,
            SimulationConfig.G_COUPLING,
            SimulationConfig.LAMBDA_PARAM
        )
        logger.info(f"Susceptibility (χ): {SimulationConfig.CHI:.2e}")
        logger.info(f"RG Beta Function (β_χ): {beta_chi:.2e}")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("FORCE & THRUST CALCULATIONS")
    logger.info(f"{'─' * 60}")
    
    F_vec = force_vector(
        SimulationConfig.CHI,
        B_total,
        SimulationConfig.GRAD_H2,
        SimulationConfig.AREA,
        SimulationConfig.RHO
    )
    F_mag = np.linalg.norm(F_vec)
    logger.info(f"Force per Unit: {F_mag:.2f} N")
    if args.verbose:
        logger.info(f"  Force Vector: {F_vec}")
    
    T = total_thrust(args.n_units, F_mag, SimulationConfig.ETA, SimulationConfig.THETA)
    logger.info(f"Total Thrust: {T:.2f} N ({T/1000:.2f} kN)")
    
    a = acceleration(T, args.mass)
    a_g = a / 9.81
    logger.info(f"Acceleration: {a:.2f} m/s² ({a_g:.2f}g)")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("PERFORMANCE METRICS")
    logger.info(f"{'─' * 60}")
    
    P = power_consumption(scaled_I, SimulationConfig.RESISTANCE, SimulationConfig.P_EDDY)
    logger.info(f"Power Consumption: {P:.2f} W ({P/1000:.2f} kW)")
    
    eta_perc = efficiency(T, SimulationConfig.VELOCITY, P)
    logger.info(f"System Efficiency: {eta_perc:.2f}%")
    logger.info(f"  (at v = {SimulationConfig.VELOCITY} m/s = Mach {SimulationConfig.VELOCITY/SPEED_OF_SOUND:.2f})")
    
    R = range_calc(SimulationConfig.VELOCITY, SimulationConfig.ENERGY, P)
    logger.info(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
    logger.info(f"  (with {SimulationConfig.ENERGY/3600000:.0f} kWh energy)")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("PERFORMANCE PROJECTIONS")
    logger.info(f"{'─' * 60}")
    mach_26_speed = 26 * SPEED_OF_SOUND
    time_to_mach26 = mach_26_speed / a if a > 0 else float('inf')
    logger.info(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
    logger.info(f"  (assuming constant acceleration)")
    
    weight = args.mass * 9.81
    twr = T / weight if weight > 0 else 0
    logger.info(f"Thrust-to-Weight Ratio: {twr:.2f}")
    
    logger.info(f"\n{'=' * 60}")
    logger.info("SIMULATION COMPLETE")
    logger.info(f"{'=' * 60}\n")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
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
  python thrust_model.py --mode swarm --num_drones 10 --scenario asymmetric --headless
  python thrust_model.py --mode benchmark --telemetry_file data.csv
  python thrust_model.py --mode realtime --sensor_port /dev/ttyUSB0
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
        "--verbose", action="store_true",
        help="Show detailed output"
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
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.mass <= 0:
        parser.error("Mass must be positive")
    if args.frequency <= 0:
        parser.error("Frequency must be positive")
    if args.n_units <= 0:
        parser.error("Number of units must be positive")
    if args.distance <= 0:
        parser.error("Distance must be positive")
    
    # Route to appropriate mode
    try:
        if args.mode == 'single':
            single_calculation_mode(args)
        
        elif args.mode == 'swarm':
            simulate_swarm(
                args.num_drones,
                args.scenario,
                args.simulation_time,
                args.verbose,
                args.headless
            )
        
        elif args.mode == 'benchmark':
            if not args.telemetry_file:
                parser.error("--telemetry_file required for benchmark mode")
            benchmark_with_telemetry(args.telemetry_file, args, args.verbose)
        
        elif args.mode == 'realtime':
            real_time_mode(args, args.sensor_port, args.update_interval, args.verbose)
    
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
    mp.freeze_support() if MULTIPROCESSING_AVAILABLE else None
    main()
