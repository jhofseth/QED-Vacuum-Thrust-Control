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
