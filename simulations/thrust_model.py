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
    parser.add_argument("--b_opposing", type=float, default=50.0, help="Opposing magnetic field (T)")
    parser.add_argument("--frequency", type=float, default=100.0, help="Pulsing frequency (Hz)")
    
    args = parser.parse_args()
    
    # Note: Frequency isn't directly used in equations; could affect pulsing/I, but here we simulate enhancement
    # For demo, scale current with frequency (simplified assumption)
    scaled_I = DEFAULT_I * (args.frequency / 50.0)  # Scale from base 50 Hz
    
    print("Thrust Model Simulation")
    print(f"Input: B_opposing = {args.b_opposing} T, Frequency = {args.frequency} Hz")
    
    # Compute opposing field (override with arg if provided, else calculate)
    if args.b_opposing:
        B = args.b_opposing
    else:
        B = opposing_field(DEFAULT_M1, DEFAULT_M2, DEFAULT_D, DEFAULT_K)
    
    print(f"Computed/Provided B_opposing: {B:.2f} T")
    
    # Pulsed enhancement
    delta_B = pulsed_enhancement(DEFAULT_N_TURNS, scaled_I)
    print(f"Pulsed Enhancement Delta B: {delta_B:.2f} T")
    
    B_total = B + delta_B
    print(f"Total B: {B_total:.2f} T")
    
    # RG beta chi
    beta_chi = rg_beta_chi(DEFAULT_CHI, DEFAULT_G, DEFAULT_LAMBDA)
    print(f"RG Beta Chi: {beta_chi:.2e}")
    
    # Force vector (using B_total)
    F_vec = force_vector(DEFAULT_CHI, B_total, DEFAULT_GRAD_H2, DEFAULT_A, DEFAULT_RHO)
    F_mag = np.linalg.norm(F_vec)
    print(f"Force Magnitude: {F_mag:.2f} N")
    
    # Total thrust
    T = total_thrust(DEFAULT_N_UNITS, F_mag, DEFAULT_ETA, DEFAULT_THETA)
    print(f"Total Thrust: {T:.2f} N")
    
    # Acceleration
    a = acceleration(T, DEFAULT_MASS)
    print(f"Acceleration: {a:.2f} m/s² ({a / 9.81:.2f} g)")
    
    # Power consumption
    P = power_consumption(scaled_I, DEFAULT_R, DEFAULT_P_EDDY)
    print(f"Power Consumption: {P:.2f} W")
    
    # Efficiency
    eta_perc = efficiency(T, DEFAULT_V, P)
    print(f"Efficiency: {eta_perc:.2f}%")
    
    # Range
    R = range_calc(DEFAULT_V, DEFAULT_E, P)
    print(f"Estimated Range: {R / 1000:.2f} km")

if __name__ == "__main__":
    main()
