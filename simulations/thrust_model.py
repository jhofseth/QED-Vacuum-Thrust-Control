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
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("QED VACUUM THRUST MODEL SIMULATION")
    print("=" * 60)
    print(f"\nInput Parameters:")
    print(f"  - Pulsing Frequency: {args.frequency} Hz")
    print(f"  - Drone Mass: {args.mass} kg")
    print(f"  - Number of MADA Units: {args.n_units}")
    
    # Scale current with frequency (simplified assumption: higher freq = higher effective current)
    # Base frequency is 50 Hz per design specs
    scaled_I = args.current * (args.frequency / 50.0)
    if args.verbose:
        print(f"  - Base Current: {args.current} A")
        print(f"  - Scaled Current: {scaled_I:.2f} A")
    
    # Compute opposing field
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
    
    # Pulsed enhancement
    delta_B = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
    print(f"Pulsed Enhancement (ΔB): {delta_B:.4f} T")
    
    B_total = B + delta_B
    print(f"Total Magnetic Field (B_total): {B_total:.2f} T")
    
    # RG beta chi
    if args.verbose:
        print(f"\n{'─' * 60}")
        print("QUANTUM PARAMETERS")
        print(f"{'─' * 60}")
        beta_chi = rg_beta_chi(DEFAULT_CHI, DEFAULT_G, DEFAULT_LAMBDA)
        print(f"Susceptibility (χ): {DEFAULT_CHI:.2e}")
        print(f"RG Beta Function (β_χ): {beta_chi:.2e}")
    
    # Force vector (using B_total)
    print(f"\n{'─' * 60}")
    print("FORCE & THRUST CALCULATIONS")
    print(f"{'─' * 60}")
    
    F_vec = force_vector(DEFAULT_CHI, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
    F_mag = np.linalg.norm(F_vec)
    print(f"Force per Unit: {F_mag:.2f} N")
    if args.verbose:
        print(f"  Force Vector: {F_vec}")
    
    # Total thrust
    T = total_thrust(args.n_units, F_mag, DEFAULT_ETA, DEFAULT_THETA)
    print(f"Total Thrust: {T:.2f} N ({T/1000:.2f} kN)")
    
    # Acceleration
    a = acceleration(T, args.mass)
    a_g = a / 9.81
    print(f"Acceleration: {a:.2f} m/s² ({a_g:.2f}g)")
    
    # Performance metrics
    print(f"\n{'─' * 60}")
    print("PERFORMANCE METRICS")
    print(f"{'─' * 60}")
    
    # Power consumption
    P = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
    print(f"Power Consumption: {P:.2f} W ({P/1000:.2f} kW)")
    
    # Efficiency (at example velocity)
    eta_perc = efficiency(T, DEFAULT_V, P)
    print(f"System Efficiency: {eta_perc:.2f}%")
    print(f"  (at v = {DEFAULT_V} m/s = Mach {DEFAULT_V/343:.2f})")
    
    # Range
    R = range_calc(DEFAULT_V, DEFAULT_E, P)
    print(f"Estimated Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
    print(f"  (with {DEFAULT_E/3600000:.0f} kWh energy)")
    
    # Time to Mach 26 (example)
    print(f"\n{'─' * 60}")
    print("PERFORMANCE PROJECTIONS")
    print(f"{'─' * 60}")
    mach_26_speed = 26 * 343  # m/s
    time_to_mach26 = mach_26_speed / a
    print(f"Time to Mach 26: {time_to_mach26:.2f} seconds ({time_to_mach26/60:.2f} minutes)")
    print(f"  (assuming constant acceleration)")
    
    # Thrust-to-weight ratio
    weight = args.mass * 9.81
    twr = T / weight
    print(f"Thrust-to-Weight Ratio: {twr:.2f}")
    
    print(f"\n{'=' * 60}")
    print("SIMULATION COMPLETE")
    print(f"{'=' * 60}\n")

if __name__ == "__main__":
    main()
