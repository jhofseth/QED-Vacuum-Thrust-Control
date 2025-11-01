import numpy as np
import scipy.constants as const
import sympy as sp

# Constants
MU_0 = const.mu_0  # Vacuum permeability

def surface_field(B_r, L, R, d):
    """
    Calculate the surface magnetic field.
    
    Parameters:
    B_r (float): Remanence field strength (T)
    L (float): Length (m)
    R (float): Radius (m)
    d (float): Distance (m)
    
    Returns:
    float: Surface field B (T)
    """
    term1 = L / np.sqrt(R**2 + L**2)
    term2 = (L + d) / np.sqrt(R**2 + (L + d)**2)
    return (B_r / 2) * (term1 + term2)

def opposing_field(m1, m2, d, k=1.0):
    """
    Calculate the opposing magnetic field.
    
    Parameters:
    m1 (float): Magnetic moment 1 (A m²)
    m2 (float): Magnetic moment 2 (A m²)
    d (float): Distance (m)
    k (float): Scaling factor (default 1.0)
    
    Returns:
    float: Opposing field B_opposing (T)
    """
    return (MU_0 * m1 * m2 / (2 * np.pi * d**2)) * k

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
    # Assuming h_mu_nu and h_mu_nu_inv are 4x4 matrices
    contraction = np.einsum('ij,ij->', h_mu_nu, h_mu_nu_inv)
    return -0.5 * chi * B**2 * contraction

def rg_beta_chi(chi, g, lambda_val):
    """
    Calculate the RG beta function for chi (spin-0 emergent).
    
    Parameters:
    chi (float): Susceptibility
    g (float): Coupling constant
    lambda_val (float): Lambda parameter
    
    Returns:
    float: beta_chi
    """
    return -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lambda_val))

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
    
    Parameters:
    chi (float): Susceptibility
    B (float): Magnetic field (T)
    grad_h2 (np.array): Gradient of h^2 (vector)
    A (float): Area (m²)
    rho (float): Density (kg/m³)
    
    Returns:
    np.array: Force F (vector, N)
    """
    return chi * B**2 * grad_h2 * A * rho

def total_thrust(N, F, eta, theta):
    """
    Calculate the total thrust.
    
    Parameters:
    N (int): Number of units
    F (float): Force magnitude (N)
    eta (float): Efficiency (0-1)
    theta (float): Angle (degrees)
    
    Returns:
    float: Thrust T (N)
    """
    return N * F * eta * np.cos(np.deg2rad(theta))

def acceleration(T, m):
    """
    Calculate acceleration.
    
    Parameters:
    T (float): Thrust (N)
    m (float): Mass (kg)
    
    Returns:
    float: Acceleration a (m/s²)
    """
    return T / m

def power_consumption(I, R, P_eddy):
    """
    Calculate power consumption.
    
    Parameters:
    I (float): Current (A)
    R (float): Resistance (Ohm)
    P_eddy (float): Eddy current losses (W)
    
    Returns:
    float: Power P (W)
    """
    return I**2 * R + P_eddy

def efficiency(T, v, P):
    """
    Calculate efficiency.
    
    Parameters:
    T (float): Thrust (N)
    v (float): Velocity (m/s)
    P (float): Power (W)
    
    Returns:
    float: Efficiency eta (%)
    """
    return (T * v / P) * 100

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
    return v * (E / P)

# Symbolic versions using SymPy (for optional symbolic manipulation)
def symbolic_surface_field():
    B_r, L, R, d = sp.symbols('B_r L R d')
    term1 = L / sp.sqrt(R**2 + L**2)
    term2 = (L + d) / sp.sqrt(R**2 + (L + d)**2)
    return (B_r / 2) * (term1 + term2)

# Add more symbolic functions as needed...

if __name__ == "__main__":
    # Example usage
    print("Example: Surface Field")
    print(surface_field(B_r=1.4, L=0.3, R=0.15, d=0.05))
    
    print("\nExample: RG Beta Chi")
    print(rg_beta_chi(chi=1e-10, g=1, lambda_val=0.1))

