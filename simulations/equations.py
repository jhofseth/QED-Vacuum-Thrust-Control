import numpy as np
import scipy.constants as const
import sympy as sp
import scipy.optimize as opt

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
    distances = np.linalg.norm(traj - radar_pos, axis=1)
    min_dist = np.min(distances)
    # Simple inverse model: P_evade = 1 / (1 + RCS / min_dist^4) ~ radar equation approximation
    return 1 / (1 + rcs / min_dist**4)

# Monte Carlo Simulations

def monte_carlo_thrust(params, uncertainties, n_sim=1000):
    """
    Monte Carlo simulation for thrust with uncertainties.
    
    Parameters:
    params (dict): Nominal parameters {'B_opposing': , 'frequency': , 'chi': , ...} (keys matching calc needs)
    uncertainties (dict): Std devs {'B_opposing': 1.0, 'frequency': 5.0, ...}
    n_sim (int): Number of simulations
    
    Returns:
    np.array: Array of simulated thrusts (N)
    """
    thrusts = []
    for _ in range(n_sim):
        sim_params = {k: np.random.normal(v, uncertainties.get(k, 0)) for k, v in params.items()}
        
        # Compute B_total with uncertainty
        B = sim_params.get('B_opposing', 50.0)
        scaled_I = sim_params.get('I', 15.0) * (sim_params.get('frequency', 100.0) / 50.0)
        delta_B = pulsed_enhancement(sim_params.get('n_turns', 100), scaled_I)
        B_total = B + delta_B
        
        F_vec = force_vector(sim_params.get('chi', 1e-10), B_total, sim_params.get('grad_h2', np.array([1.0, 0.0, 0.0])),
                             sim_params.get('A', 1.0), sim_params.get('rho', 1000.0))
        F_mag = np.linalg.norm(F_vec)
        T = total_thrust(sim_params.get('N', 24), F_mag, sim_params.get('eta', 0.95), sim_params.get('theta', 0.0))
        thrusts.append(T)
    
    return np.array(thrusts)

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
    Delta_T (float): Temperature difference (K)
    area (float): TEG area (m²)
    thickness (float): Thickness (m)
    load_res (float): Load resistance (Ohm, default matched)
    
    Returns:
    float: Recovered power (W)
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
    heat_generated = P_in * (1 - eta_thermal)
    Delta_T = min(heat_generated / THERMAL_COND, Delta_T_max)  # Simplified
    recovered = teg_power_recovery(Delta_T, area=0.01, thickness=0.001)  # Example dims
    return heat_generated - recovered, recovered

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
    print("=" * 50)
    print("QED Vacuum Thrust Control - Equations Module (Expanded)")
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
    
    print("\n4. RG Beta Chi (Spin-0) Example:")
    beta = rg_beta_chi_spin0(chi=1e-10, g=1.0, lambda_val=0.1)
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
    
    print("\n9. Non-Ballistic Trajectory Example:")
    traj = non_ballistic_trajectory(np.array([0,0,0]), np.array([100,50,20]), curvature=0.5, steps=5)
    print(f"   Trajectory points: {traj}")
    
    print("\n10. Radar Evasion Probability Example:")
    prob = radar_evasion_probability(traj, np.array([50,25,10]))
    print(f"   Evasion Prob: {prob:.4f}")
    
    print("\n11. Monte Carlo Thrust Example:")
    params = {'B_opposing': 50, 'frequency': 100, 'I': 15, 'chi': 1e-10, 'grad_h2': np.array([1,0,0]),
              'A':1, 'rho':1000, 'N':24, 'eta':0.95, 'theta':0, 'n_turns':100}
    uncertainties = {'B_opposing': 2.0, 'frequency': 5.0, 'chi': 1e-11}
    thrusts = monte_carlo_thrust(params, uncertainties, n_sim=10)
    print(f"   Mean Thrust: {np.mean(thrusts):.2f} N")
    
    print("\n12. LiPo Discharge Example:")
    rem_cap = lipo_discharge_capacity(10, 5, 1)  # 10Ah, 5A, 1h
    print(f"   Remaining Capacity: {rem_cap:.2f} Ah")
    
    print("\n13. SSB Discharge Example:")
    rem_cap_ssb = ssb_discharge_capacity(12, 5, 1)
    print(f"   Remaining Capacity: {rem_cap_ssb:.2f} Ah")
    
    print("\n14. Battery Voltage Example:")
    v = battery_voltage_curve(0.8, LIPO_NOMINAL_V)
    print(f"   Voltage at 80% SOC: {v:.2f} V")
    
    print("\n15. Stealth Range Example:")
    stealth_r = stealth_range_calc(100, 1e6, 1000)
    print(f"   Stealth Range: {stealth_r:.2f} m")
    
    print("\n16. TEG Recovery Example:")
    recovered = teg_power_recovery(50, 0.01, 0.001)
    print(f"   Recovered Power: {recovered:.4f} W")
    
    print("\n17. Thermal Dissipation Example:")
    heat, rec = thermal_dissipation(5000, eta_thermal=0.95)
    print(f"   Heat Dissipated: {heat:.2f} W, Recovered: {rec:.4f} W")
    
    print("\n" + "=" * 50)
