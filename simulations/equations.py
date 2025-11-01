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
    
    Note: Requires |2*lambda_val| < 1 to avoid singularity
    """
    if abs(2 * lambda_val) >= 1:
        raise ValueError("Lambda parameter must satisfy |2*lambda| < 1 to avoid singularity")
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
    grad_h2 (np.array): Gradient of h^2 (3D vector)
    A (float): Area (m²)
    rho (float): Density (kg/m³)
    
    Returns:
    np.array: Force F (3D vector, N)
    """
    # Ensure grad_h2 is a numpy array
    grad_h2 = np.asarray(grad_h2)
    return chi * B**2 * grad_h2 * A * rho

def total_thrust(N, F, eta, theta):
    """
    Calculate the total thrust.
    
    Parameters:
    N (int): Number of units
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
    if P <= 0:
        raise ValueError("Power must be positive")
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
    if P <= 0:
        raise ValueError("Power must be positive")
    return v * (E / P)

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

if __name__ == "__main__":
    # Example usage
    print("=" * 50)
    print("QED Vacuum Thrust Control - Equations Module")
    print("=" * 50)
    
    print("\n1. Surface Field Example:")
    B_surf = surface_field(B_r=1.4, L=0.3, R=0.15, d=0.05)
    print(f"   B_surface = {B_surf:.4f} T")
    
    print("\n2. Opposing Field Example:")
    B_opp = opposing_field(m1=100, m2=100, d=0.1, k=1.0)
    print(f"   B_opposing = {B_opp:.6e} T")
    
    print("\n3. Pulsed Enhancement Example:")
    delta_B = pulsed_enhancement(n=1000, I=10)
    print(f"   ΔB = {delta_B:.4f} T")
    
    print("\n4. RG Beta Chi Example:")
    beta = rg_beta_chi(chi=1e-10, g=1.0, lambda_val=0.1)
    print(f"   β_χ = {beta:.6e}")
    
    print("\n5. Force Vector Example:")
    F_vec = force_vector(chi=1e-10, B=20, grad_h2=np.array([1, 0, 0]), 
                         A=0.01, rho=2700)
    print(f"   F = {F_vec} N")
    
    print("\n6. Total Thrust Example:")
    T = total_thrust(N=10, F=100, eta=0.95, theta=0)
    print(f"   Thrust = {T:.2f} N")
    
    print("\n7. Acceleration Example:")
    a = acceleration(T=1000, m=50)
    print(f"   Acceleration = {a:.2f} m/s² ({a/9.81:.2f}g)")
    
    print("\n8. Symbolic Surface Field:")
    print(f"   {symbolic_surface_field()}")
    
    print("\n" + "=" * 50)
