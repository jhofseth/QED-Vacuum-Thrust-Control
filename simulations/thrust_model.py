import argparse
import numpy as np
from equations import (
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
import sys
import os
import time
import pandas as pd
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Try to import PyBullet for 3D physics simulation
try:
    import pybullet as p
    import pybullet_data
    PYBULLET_AVAILABLE = True
except ImportError:
    print("Warning: PyBullet not available. Swarm simulations disabled.")
    PYBULLET_AVAILABLE = False

# Import from hardware for real-time sensor inputs
try:
    from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    print("Warning: Hardware interfaces not available. Using mock for real-time.")
    HARDWARE_AVAILABLE = False

# Default parameters (based on document specs)
DEFAULT_M1 = 100.0  # Magnetic moment 1 (A m²), example value
DEFAULT_M2 = 100.0  # Magnetic moment 2 (A m²), example value
DEFAULT_D = 0.05    # Distance (m)
DEFAULT_K = 1.0     # Scaling factor
DEFAULT_N_TURNS = 100  # Turns per unit length (1/m)
DEFAULT_I = 15.0    # Current (A)
DEFAULT_CHI = 1e-10 # Susceptibility (example small value)
DEFAULT_G = 1.0     # Coupling constant
DEFAULT_LAMBDA = 0.1 # Lambda parameter
DEFAULT_GRAD_H2 = np.array([1.0, 0.0, 0.0])  # Gradient of h^2 (vector, example)
DEFAULT_A = 1.0     # Area (m²)
DEFAULT_RHO = 1000.0 # Density (kg/m³)
DEFAULT_N_UNITS = 24 # Number of MADA units
DEFAULT_ETA = 0.95  # Efficiency (0-1)
DEFAULT_THETA = 0.0 # Angle (degrees)
DEFAULT_MASS = 20000.0  # Mass (kg)
DEFAULT_R = 5.0     # Resistance (Ohm)
DEFAULT_P_EDDY = 100.0  # Eddy losses (W)
DEFAULT_V = 1000.0  # Velocity (m/s, example for efficiency/range)
DEFAULT_E = 500000.0 * 3600  # Energy (J, e.g., 500 kWh converted to J)

def calculate_thrust_params(args, B_opposing=None, frequency=None, verbose=False):
    """Core thrust calculation function, reusable across modes."""
    frequency = frequency or args.frequency
    B = B_opposing or args.b_opposing
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
        print(f"Thrust: {T:.2f} N, Acceleration: {a:.2f} m/s², Power: {P:.2f} W")
    
    return T, a, P, eta_perc, R, B_total

def simulate_swarm(num_drones=5, scenario='asymmetric', simulation_time=60, verbose=False):
    """Multi-drone swarm simulation using PyBullet for asymmetric warfare scenarios."""
    if not PYBULLET_AVAILABLE:
        print("Error: PyBullet not installed. Cannot run swarm simulation.")
        return
    
    physicsClient = p.connect(p.GUI)  # Or p.DIRECT for non-GUI
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    
    # Load ground plane
    planeId = p.loadURDF("plane.urdf")
    
    # Drone parameters (simple sphere model for demo; replace with URDF for real drone)
    drone_ids = []
    drone_masses = [DEFAULT_MASS] * num_drones
    drone_thrusts = [0] * num_drones
    
    if scenario == 'asymmetric':
        # Asymmetric: Half the drones have higher thrust (e.g., advanced side)
        for i in range(num_drones // 2):
            drone_thrusts[i] = 1.5 * total_thrust(DEFAULT_N_UNITS, np.linalg.norm(force_vector(DEFAULT_CHI, 50, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)), DEFAULT_ETA, DEFAULT_THETA)
        for i in range(num_drones // 2, num_drones):
            drone_thrusts[i] = 0.5 * drone_thrusts[0]  # Weaker side
    
    for i in range(num_drones):
        start_pos = [i * 5, 0, 1]  # Staggered start
        drone_id = p.loadURDF("sphere2.urdf", start_pos, globalScaling=0.5)  # Simple sphere; use custom URDF for drone
        p.changeDynamics(drone_id, -1, mass=drone_masses[i])
        drone_ids.append(drone_id)
    
    # Simulation loop
    for _ in range(int(simulation_time / (1/240))):  # 240 Hz physics
        for i, drone_id in enumerate(drone_ids):
            # Apply thrust as force (upward for hover, adjust for warfare maneuvers)
            thrust = drone_thrusts[i]
            p.applyExternalForce(drone_id, -1, [0, 0, thrust], [0, 0, 0], p.LINK_FRAME)  # Simple upward thrust
        
        # Simulate asymmetric warfare: e.g., "attacks" by applying forces
        if scenario == 'asymmetric' and np.random.rand() < 0.01:  # Random "attack" events
            target_id = np.random.choice(drone_ids[num_drones//2:])  # Attack weaker side
            p.applyExternalForce(target_id, -1, [0, 0, -10000], [0, 0, 0], p.LINK_FRAME)  # Downward force simulating hit
        
        p.stepSimulation()
        time.sleep(1/240)
    
    p.disconnect()
    print(f"Swarm simulation complete for {num_drones} drones in {scenario} scenario.")

def benchmark_with_telemetry(telemetry_file, args, verbose=False):
    """Benchmark simulation outputs against hardware telemetry data."""
    if not os.path.exists(telemetry_file):
        print(f"Error: Telemetry file {telemetry_file} not found.")
        return
    
    data = pd.read_csv(telemetry_file)  # Assume columns: time, measured_B, measured_freq, measured_thrust, measured_accel, etc.
    
    sim_thrusts = []
    sim_accels = []
    differences = []
    
    for _, row in data.iterrows():
        T_sim, a_sim, _, _, _, _ = calculate_thrust_params(args, B_opposing=row.get('measured_B', None), frequency=row.get('measured_freq', args.frequency))
        sim_thrusts.append(T_sim)
        sim_accels.append(a_sim)
        
        measured_T = row.get('measured_thrust', 0)
        measured_a = row.get('measured_accel', 0)
        diff_T = abs(T_sim - measured_T)
        diff_a = abs(a_sim - measured_a)
        differences.append((diff_T, diff_a))
    
    avg_diff_T = np.mean([d[0] for d in differences])
    avg_diff_a = np.mean([d[1] for d in differences])
    
    print(f"Benchmark Results:")
    print(f"  Average Thrust Difference: {avg_diff_T:.2f} N")
    print(f"  Average Acceleration Difference: {avg_diff_a:.2f} m/s²")
    
    if verbose:
        print("Detailed comparisons saved to benchmark_report.csv")
        data['sim_thrust'] = sim_thrusts
        data['sim_accel'] = sim_accels
        data.to_csv('benchmark_report.csv', index=False)

def real_time_mode(args, sensor_port='/dev/ttyUSB0', update_interval=0.1, verbose=False):
    """Real-time mode: Read sensor data and compute thrust dynamically."""
    if HARDWARE_AVAILABLE:
        mcu = MicrocontrollerPWMInterface(port=sensor_port)
        fc = FlightControllerInterface()  # For telemetry if available
    else:
        print("Using mock sensor data.")
        mcu = None
        fc = None
    
    def sensor_reader():
        while True:
            if mcu:
                # Mock: Read B, freq from serial (assume command 'READ:SENSORS\n' returns 'B:freq')
                mcu.ser.write(b'READ:SENSORS\n')
                response = mcu.ser.readline().decode().strip()
                try:
                    B, freq = map(float, response.split(':'))
                except:
                    B, freq = 50.0, 100.0  # Fallback
            else:
                B = 50.0 + np.random.uniform(-5, 5)  # Mock fluctuation
                freq = 100.0 + np.random.uniform(-10, 10)
            
            yield B, freq
            time.sleep(update_interval)
    
    reader = sensor_reader()
    
    print("Real-time thrust monitoring started. Press Ctrl+C to stop.")
    try:
        while True:
            B, freq = next(reader)
            T, a, P, eta, R, _ = calculate_thrust_params(args, B_opposing=B, frequency=freq, verbose=verbose)
            print(f"Real-time: B={B:.2f}T, Freq={freq:.2f}Hz, Thrust={T:.2f}N, Accel={a:.2f}m/s², Power={P:.2f}W")
            time.sleep(update_interval)
    except KeyboardInterrupt:
        print("Real-time mode stopped.")
    finally:
        if mcu:
            mcu.close()

def main():
    parser = argparse.ArgumentParser(description="Thrust Model for QED Vacuum Propulsion")
    parser.add_argument("--b_opposing", type=float, default=None, 
                        help="Opposing magnetic field (T). If not provided, will be calculated.")
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
                        help="Show detailed calculations")
    parser.add_argument("--mode", type=str, default='single',
                        help="Simulation mode: single (default), swarm, benchmark, realtime")
    parser.add_argument("--num_drones", type=int, default=5,
                        help="Number of drones for swarm mode")
    parser.add_argument("--scenario", type=str, default='asymmetric',
                        help="Scenario for swarm: asymmetric (default), symmetric")
    parser.add_argument("--simulation_time", type=int, default=60,
                        help="Simulation time (s) for swarm")
    parser.add_argument("--telemetry_file", type=str, default=None,
                        help="CSV file for benchmark mode")
    parser.add_argument("--sensor_port", type=str, default='/dev/ttyUSB0',
                        help="Serial port for real-time sensor input")
    parser.add_argument("--update_interval", type=float, default=0.1,
                        help="Update interval (s) for real-time mode")
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        # Original single calculation mode
        print("=" * 60)
        print("QED VACUUM THRUST MODEL SIMULATION")
        print("=" * 60)
        print(f"\nInput Parameters:")
        print(f"  - Pulsing Frequency: {args.frequency} Hz")
        print(f"  - Drone Mass: {args.mass} kg")
        print(f"  - Number of MADA Units: {args.n_units}")
        
        scaled_I = args.current * (args.frequency / 50.0)
        if args.verbose:
            print(f"  - Base Current: {args.current} A")
            print(f"  - Scaled Current: {scaled_I:.2f} A")
        
        if args.b_opposing is not None:
            B = args.b_opposing
            if args.verbose:
                print(f"  - B_opposing (provided): {B:.2f} T")
        else:
            B = opposing_field(args.m1, args.m2, args.distance, DEFAULT_K)
            if args.verbose:
                print(f"  - B_opposing (calculated): {B:.6e} T")
                print(f"    (from m1={args.m1}, m2={args.m2}, d={args.distance}m)")
        
        print(f"\n{'─' * 60}")
        print("MAGNETIC FIELD CALCULATIONS")
        print(f"{'─' * 60}")
        print(f"Opposing Field (B_opposing): {B:.2f} T")
        
        delta_B = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
        print(f"Pulsed Enhancement (ΔB): {delta_B:.4f} T")
        
        B_total = B + delta_B
        print(f"Total Magnetic Field (B_total): {B_total:.2f} T")
        
        if args.verbose:
            print(f"\n{'─' * 60}")
            print("QUANTUM PARAMETERS")
            print(f"{'─' * 60}")
            beta_chi = rg_beta_chi(DEFAULT_CHI, DEFAULT_G, DEFAULT_LAMBDA)
            print(f"Susceptibility (χ): {DEFAULT_CHI:.2e}")
            print(f"RG Beta Function (β_χ): {beta_chi:.2e}")
        
        print(f"\n{'─' * 60}")
        print("FORCE & THRUST CALCULATIONS")
        print(f"{'─' * 60}")
        
        F_vec = force_vector(DEFAULT_CHI, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
        F_mag = np.linalg.norm(F_vec)
        print(f"Force per Unit: {F_mag:.2f} N")
        if args.verbose:
            print(f"  Force Vector: {F_vec}")
        
        T = total_thrust(args.n_units, F_mag, DEFAULT_ETA, DEFAULT_THETA)
        print(f"Total Thrust: {T:.2f} N ({T/1000:.2f} kN)")
        
        a = acceleration(T, args.mass)
        a_g = a / 9.81
        print(f"Acceleration: {a:.2f} m/s² ({a_g:.2f}g)")
        
        print(f"\n{'─' * 60}")
        print("PERFORMANCE METRICS")
        print(f"{'─' * 60}")
        
        P = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
        print(f"Power Consumption: {P:.2f} W ({P/1000:.2f} kW)")
        
        eta_perc = efficiency(T, DEFAULT_V, P)
        print(f"System Efficiency: {eta_perc:.2f}%")
        print(f"  (at v = {DEFAULT_V} m/s = Mach {DEFAULT_V/343:.2f})")
        
        R = range_calc(DEFAULT_V, DEFAULT_E, P)
        print(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
        print(f"  (with {DEFAULT_E/3600000:.0f} kWh energy)")
        
        print(f"\n{'─' * 60}")
        print("PERFORMANCE PROJECTIONS")
        print(f"{'─' * 60}")
        mach_26_speed = 26 * 343  # m/s
        time_to_mach26 = mach_26_speed / a
        print(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
        print(f"  (assuming constant acceleration)")
        
        weight = args.mass * 9.81
        twr = T / weight
        print(f"Thrust-to-Weight Ratio: {twr:.2f}")
        
        print(f"\n{'=' * 60}")
        print("SIMULATION COMPLETE")
        print(f"{'=' * 60}\n")
    
    elif args.mode == 'swarm':
        simulate_swarm(args.num_drones, args.scenario, args.simulation_time, args.verbose)
    
    elif args.mode == 'benchmark':
        if not args.telemetry_file:
            print("Error: --telemetry_file required for benchmark mode.")
            sys.exit(1)
        benchmark_with_telemetry(args.telemetry_file, args, args.verbose)
    
    elif args.mode == 'realtime':
        real_time_mode(args, args.sensor_port, args.update_interval, args.verbose)
    
    else:
        print(f"Error: Invalid mode '{args.mode}'. Options: single, swarm, benchmark, realtime")
        sys.exit(1)

if __name__ == "__main__":
    main()
