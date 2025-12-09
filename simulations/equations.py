"""
simulations/equations.py

Core physics equations for QED vacuum thrust calculations.
Includes magnetic field calculations, RG flow, force vectors, and performance metrics.

All equations derived from theoretical framework with proper validation and error handling.
"""

import numpy as np
import sympy as sp
from scipy import constants as const
from typing import Tuple, Optional, Union, Dict, Any, Callable
import warnings

# Optional imports with proper fallback handling
try:
    import scipy.optimize as opt
    import scipy.stats as stats
    from scipy.integrate import solve_ivp
    SCIPY_FULL_AVAILABLE = True
except ImportError:
    SCIPY_FULL_AVAILABLE = False
    warnings.warn("Full scipy features not available. Some functions will be limited.")

try:
    import multiprocessing as mp
    MULTIPROCESSING_AVAILABLE = True
except ImportError:
    MULTIPROCESSING_AVAILABLE = False
    warnings.warn("Multiprocessing not available. Parallel operations will be disabled.")

try:
    import matplotlib
    matplotlib.use('Agg')  # Set non-GUI backend by default
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    warnings.warn("Matplotlib not available. Visualization functions disabled.")

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False
    warnings.warn("h5py not available. HDF5 export disabled.")

try:
    import qutip as qt
    QUTIP_AVAILABLE = True
except ImportError:
    QUTIP_AVAILABLE = False
    warnings.warn("QuTiP not available. Cavity QED simulations will be disabled.")

try:
    import pyscf
    from pyscf import gto, scf
    PYSCF_AVAILABLE = True
    try:
        from pyscf import qed
        PYSCF_QED_AVAILABLE = True
    except ImportError:
        PYSCF_QED_AVAILABLE = False
except ImportError:
    PYSCF_AVAILABLE = False
    PYSCF_QED_AVAILABLE = False
    warnings.warn("PySCF not available. QED polarization simulations will be disabled.")

import json
import csv

# Physical Constants
MU_0 = const.mu_0  # Vacuum permeability (H/m)
G = const.G  # Gravitational constant (m³/kg/s²)
C = const.c  # Speed of light (m/s)
EPSILON_0 = const.epsilon_0  # Vacuum permittivity (F/m)

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

# Simulation constants
SPEED_OF_SOUND = 343.0  # m/s at sea level
PHYSICS_STEP_RATE = 240  # Hz for PyBullet simulation
SWARM_ATTACK_PROBABILITY = 0.005  # Per step probability
EPSILON = 1e-12  # Small value for numerical stability

# =============================================================================
# Modular Equation Classes with Parameterization
# =============================================================================

class MagneticField:
    """
    Class for calculating magnetic fields with parameterization and validation.
    
    Attributes:
        B_r (float): Remanence field strength (T)
        L (float): Length (m)
        R (float): Radius (m)
        d (float): Distance (m)
    """
    
    def __init__(self, B_r: float, L: float, R: float, d: float):
        """Initialize magnetic field calculator with validation."""
        if B_r <= 0 or L <= 0 or R <= 0 or d < 0:
            raise ValueError("Parameters must be positive (B_r, L, R > 0; d >= 0)")
        if B_r > 3.0:  # Physical limit for permanent magnets
            warnings.warn(f"B_r={B_r}T is unusually high for permanent magnets (typical < 2T)")
        
        self.B_r = B_r
        self.L = L
        self.R = R
        self.d = d
    
    def compute_surface(self) -> float:
        """Compute surface magnetic field strength."""
        term1 = self.L / np.sqrt(self.R**2 + self.L**2)
        term2 = (self.L + self.d) / np.sqrt(self.R**2 + (self.L + self.d)**2)
        return (self.B_r / 2) * (term1 + term2)


class DisruptionLagrangian:
    """
    Class for disruption Lagrangian with parameterization.
    
    Attributes:
        chi (float): Susceptibility
        B (float): Magnetic field (T)
        h_mu_nu (np.ndarray): Metric perturbation (4x4)
        h_mu_nu_inv (np.ndarray): Inverse metric perturbation (4x4)
    """
    
    def __init__(self, chi: float, B: float, h_mu_nu: np.ndarray, h_mu_nu_inv: np.ndarray):
        """Initialize Lagrangian calculator with validation."""
        if chi < 0 or B < 0:
            raise ValueError("chi and B must be non-negative")
        
        self.chi = chi
        self.B = B
        self.h_mu_nu = np.asarray(h_mu_nu, dtype=float)
        self.h_mu_nu_inv = np.asarray(h_mu_nu_inv, dtype=float)
        
        if self.h_mu_nu.shape != (4, 4) or self.h_mu_nu_inv.shape != (4, 4):
            raise ValueError("Metric tensors must be 4x4 arrays")
    
    def compute(self) -> float:
        """Compute Lagrangian value."""
        contraction = np.einsum('ij,ij->', self.h_mu_nu, self.h_mu_nu_inv)
        return -0.5 * self.chi * self.B**2 * contraction


class ThrustForce:
    """
    Class for thrust force vector with parameterization.
    
    Attributes:
        chi (float): Susceptibility
        B (float): Magnetic field magnitude (T)
        grad_h2 (np.ndarray): Gradient of h^2 (3D vector)
        A (float): Area (m²)
        rho (float): Density (kg/m³)
    """
    
    def __init__(self, chi: float, B: float, grad_h2: np.ndarray, A: float, rho: float):
        """Initialize thrust force calculator with validation."""
        if chi < 0 or B < 0 or A <= 0 or rho <= 0:
            raise ValueError("Parameters must satisfy chi, B >= 0; A, rho > 0")
        
        self.chi = chi
        self.B = B
        self.grad_h2 = np.asarray(grad_h2, dtype=float)
        
        if self.grad_h2.shape != (3,):
            raise ValueError("grad_h2 must be a 3D vector")
        
        self.A = A
        self.rho = rho
    
    def compute(self) -> np.ndarray:
        """Compute force vector."""
        return self.chi * self.B**2 * self.grad_h2 * self.A * self.rho


# =============================================================================
# Core Physics Functions
# =============================================================================

def surface_field(B_r: float, L: float, R: float, d: float) -> float:
    """
    Calculate the surface magnetic field.
    
    Args:
        B_r: Remanence field strength (T)
        L: Length (m)
        R: Radius (m)
        d: Distance (m)
    
    Returns:
        Surface field strength (T)
    """
    mf = MagneticField(B_r, L, R, d)
    return mf.compute_surface()


def opposing_field(m1: float, m2: float, d: float, k: float = 200.0) -> float:
    """
    Calculate the opposing magnetic field magnitude.
    
    IMPORTANT: This calculates the MAGNITUDE of the combined field strength
    when two magnetic moments are OPPOSING (pointing at each other).
    This function does NOT verify field direction - use validate_mada_convergence()
    to ensure fields are actually opposing before using this value.
    
    Args:
        m1: Magnetic moment 1 (A m²)
        m2: Magnetic moment 2 (A m²)
        d: Distance between MADA units (m)
        k: Scaling factor for MADA amplification (default 200.0 for ~200x vs. single magnet)
    
    Returns:
        Opposing field magnitude B_opposing (T)
    
    Note:
        Result is only valid if MADA units are properly configured with
        fields pointing toward each other (converging at focal point).
    """
    if m1 <= 0 or m2 <= 0 or d <= 0:
        raise ValueError("Magnetic moments and distance must be positive")
    
    return (MU_0 * m1 * m2 / (2 * np.pi * d**2)) * k


def calculate_field_at_point(m: float, position_source: np.ndarray, 
                             position_target: np.ndarray, 
                             direction: np.ndarray) -> np.ndarray:
    """
    Calculate magnetic field vector at a target point from a magnetic dipole.
    
    Args:
        m: Magnetic moment magnitude (A m²)
        position_source: Position of magnetic source [x, y, z] (m)
        position_target: Position where field is calculated [x, y, z] (m)
        direction: Direction unit vector of magnetic moment [x, y, z]
    
    Returns:
        Magnetic field vector at target point [Bx, By, Bz] (T)
    """
    position_source = np.asarray(position_source, dtype=float)
    position_target = np.asarray(position_target, dtype=float)
    direction = np.asarray(direction, dtype=float)
    
    r_vec = position_target - position_source
    r = np.linalg.norm(r_vec)
    
    if r < EPSILON:
        return np.array([0.0, 0.0, 0.0])
    
    r_hat = r_vec / r
    m_vec = m * direction
    
    # Magnetic dipole field: B = (μ₀/4π) * (3(m·r̂)r̂ - m) / r³
    dot_product = np.dot(m_vec, r_hat)
    B = (MU_0 / (4 * np.pi)) * (3 * dot_product * r_hat - m_vec) / r**3
    
    return B


def calculate_convergence_quality(B1: np.ndarray, B2: np.ndarray) -> float:
    """
    Calculate MADA convergence quality (how well fields oppose).
    
    This is CRITICAL for QED vacuum polarization propulsion.
    Fields must be OPPOSING (pointing at each other) to create
    the focal point where virtual pair production occurs.
    
    Args:
        B1: Magnetic field vector from MADA unit 1 [Bx, By, Bz] (T)
        B2: Magnetic field vector from MADA unit 2 [Bx, By, Bz] (T)
    
    Returns:
        Convergence quality [-1, 1]
        1.0 = Perfect opposition (fields pointing directly at each other) ✅
        0.0 = Perpendicular fields
        -1.0 = Parallel fields (both pointing same direction) ❌
    
    Raises:
        ValueError: If either field vector has zero magnitude
    """
    B1 = np.asarray(B1, dtype=float)
    B2 = np.asarray(B2, dtype=float)
    
    B1_mag = np.linalg.norm(B1)
    B2_mag = np.linalg.norm(B2)
    
    if B1_mag < EPSILON or B2_mag < EPSILON:
        raise ValueError("Magnetic field vectors cannot have zero magnitude")
    
    # Normalize
    B1_norm = B1 / B1_mag
    B2_norm = B2 / B2_mag
    
    # Dot product: -1 means opposing (good), +1 means parallel (bad)
    dot_product = np.dot(B1_norm, B2_norm)
    
    # Return negative of dot product: 1.0 = opposing, -1.0 = parallel
    return -dot_product


def validate_mada_convergence(B1: np.ndarray, B2: np.ndarray, 
                              threshold: float = CONVERGENCE_WARNING, 
                              raise_on_fail: bool = False) -> Dict[str, Any]:
    """
    Validate that MADA fields are properly converging (opposing).
    
    Args:
        B1: Magnetic field vector from MADA unit 1 [Bx, By, Bz] (T)
        B2: Magnetic field vector from MADA unit 2 [Bx, By, Bz] (T)
        threshold: Minimum acceptable convergence quality (default 0.85)
        raise_on_fail: If True, raise ValueError on poor convergence
    
    Returns:
        Dictionary with keys:
            'quality': float - convergence quality score
            'status': str - 'optimal', 'acceptable', 'warning', 'critical', 'diverging', 'error'
            'is_valid': bool - whether convergence is acceptable
            'message': str - human-readable status message
    
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


def opposing_field_with_validation(m1: float, m2: float, d: float, 
                                   B1_vec: np.ndarray, B2_vec: np.ndarray, 
                                   k: float = 1.0) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate opposing field WITH convergence validation.
    This is the SAFE version that verifies fields are actually opposing.
    
    Args:
        m1: Magnetic moment 1 (A m²)
        m2: Magnetic moment 2 (A m²)
        d: Distance (m)
        B1_vec: Field vector from MADA unit 1 [Bx, By, Bz] (T)
        B2_vec: Field vector from MADA unit 2 [Bx, By, Bz] (T)
        k: Scaling factor (default 1.0)
    
    Returns:
        Tuple of (B_opposing (float), convergence_info (dict))
    
    Raises:
        ValueError: If field convergence is below critical threshold
    """
    # Validate convergence
    convergence = validate_mada_convergence(B1_vec, B2_vec, raise_on_fail=True)
    
    # Calculate magnitude only if convergence is acceptable
    B_opp = opposing_field(m1, m2, d, k)
    
    return B_opp, convergence


def pulsed_enhancement(n: float, I: float) -> float:
    """
    Calculate the pulsed magnetic field enhancement.
    
    Args:
        n: Number of turns per unit length (1/m)
        I: Current (A)
    
    Returns:
        Delta B (T)
    """
    if n < 0 or I < 0:
        raise ValueError("Turns and current must be non-negative")
    
    return MU_0 * n * I


def lagrangian_disrupt(chi: float, B: float, h_mu_nu: np.ndarray, 
                      h_mu_nu_inv: np.ndarray) -> float:
    """
    Calculate the disruption Lagrangian (numerical approximation).
    
    Args:
        chi: Susceptibility
        B: Magnetic field (T)
        h_mu_nu: Metric perturbation (4x4)
        h_mu_nu_inv: Inverse metric perturbation (4x4)
    
    Returns:
        L_disrupt
    """
    dl = DisruptionLagrangian(chi, B, h_mu_nu, h_mu_nu_inv)
    return dl.compute()


def rg_beta_chi_spin0(chi: float, g: float, lambda_val: float) -> float:
    """
    Calculate the RG beta function for chi (spin-0 emergent).
    
    Args:
        chi: Susceptibility
        g: Coupling constant
        lambda_val: Lambda parameter
    
    Returns:
        beta_chi
    
    Raises:
        ValueError: If |2*lambda_val| >= 1 (singularity)
    """
    if abs(2 * lambda_val) >= 1:
        raise ValueError("Lambda parameter must satisfy |2*lambda| < 1 to avoid singularity")
    
    return -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lambda_val))


# Alias for backward compatibility
rg_beta_chi = rg_beta_chi_spin0


def rg_beta_chi_spin2(chi: float, eta_chi: float, c: float, g: float) -> float:
    """
    Alternative RG beta function for chi (spin-2 emergent).
    
    Args:
        chi: Susceptibility
        eta_chi: Anomalous dimension
        c: Constant
        g: Coupling constant
    
    Returns:
        beta_chi
    """
    return (4 + eta_chi) * chi + c * g * chi


def source_term(chi: float, B: float, h_mu_nu: np.ndarray) -> np.ndarray:
    """
    Calculate the source term delta T_mu_nu (approximation).
    
    Args:
        chi: Susceptibility
        B: Magnetic field (T)
        h_mu_nu: Metric perturbation (4x4)
    
    Returns:
        delta T_mu_nu (4x4 array)
    """
    h_mu_nu = np.asarray(h_mu_nu, dtype=float)
    if h_mu_nu.shape != (4, 4):
        raise ValueError("Metric tensor must be 4x4 array")
    
    return chi * B**2 * h_mu_nu


def force_vector(chi: float, B: float, grad_h2: np.ndarray, 
                A: float, rho: float) -> np.ndarray:
    """
    Calculate the force vector.
    
    IMPORTANT: This force is only valid when B is from properly OPPOSING
    magnetic fields (converging at focal point). Use validate_mada_convergence()
    to verify field configuration before relying on this calculation.
    
    Args:
        chi: Susceptibility
        B: Magnetic field magnitude (T)
        grad_h2: Gradient of h^2 (3D vector)
        A: Area (m²)
        rho: Density (kg/m³)
    
    Returns:
        Force F (3D vector, N)
    """
    tf = ThrustForce(chi, B, grad_h2, A, rho)
    return tf.compute()


def total_thrust(N: int, F: Union[float, np.ndarray], 
                eta: float, theta: float) -> float:
    """
    Calculate the total thrust.
    
    Args:
        N: Number of MADA units
        F: Force magnitude (N) or force vector
        eta: Efficiency (0-1)
        theta: Angle (degrees)
    
    Returns:
        Thrust T (N)
    """
    if N <= 0:
        raise ValueError("Number of units must be positive")
    if not 0 <= eta <= 1:
        raise ValueError("Efficiency must be between 0 and 1")
    
    # If F is a vector, use its magnitude
    F_mag = np.linalg.norm(F) if isinstance(F, np.ndarray) else float(F)
    
    if F_mag < 0:
        raise ValueError("Force magnitude must be non-negative")
    
    return N * F_mag * eta * np.cos(np.deg2rad(theta))


def acceleration(T: float, m: float) -> float:
    """
    Calculate acceleration.
    
    Args:
        T: Thrust (N)
        m: Mass (kg)
    
    Returns:
        Acceleration a (m/s²)
    """
    if m <= 0:
        raise ValueError("Mass must be positive")
    
    return T / m


def power_consumption_vectorized(I: Union[float, np.ndarray], 
                                R: Union[float, np.ndarray], 
                                P_eddy: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Calculate power consumption (vectorized).
    
    Args:
        I: Current (A)
        R: Resistance (Ω)
        P_eddy: Eddy current losses (W)
    
    Returns:
        Power consumption (W)
    """
    I = np.asarray(I)
    R = np.asarray(R)
    P_eddy = np.asarray(P_eddy)
    return I**2 * R + P_eddy


def power_consumption(I: float, R: float, P_eddy: float) -> float:
    """Calculate power consumption (scalar version)."""
    return float(power_consumption_vectorized(I, R, P_eddy))


def efficiency_vectorized(T: Union[float, np.ndarray], 
                         v: Union[float, np.ndarray], 
                         P: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Calculate efficiency (vectorized).
    
    Args:
        T: Thrust (N)
        v: Velocity (m/s)
        P: Power (W)
    
    Returns:
        Efficiency (%)
    """
    T = np.asarray(T)
    v = np.asarray(v)
    P = np.asarray(P)
    
    mask = P > EPSILON
    eta = np.zeros_like(P, dtype=float)
    eta[mask] = (T[mask] * v[mask] / P[mask]) * 100
    
    return eta


def efficiency(T: float, v: float, P: float) -> float:
    """Calculate efficiency (scalar version)."""
    return float(efficiency_vectorized(T, v, P))


def range_calc(v: float, E: float, P: float) -> float:
    """
    Calculate range.
    
    Args:
        v: Velocity (m/s)
        E: Energy (J)
        P: Power (W)
    
    Returns:
        Range R (m)
    """
    if P <= EPSILON:
        raise ValueError("Power must be positive")
    if E < 0:
        raise ValueError("Energy must be non-negative")
    
    return v * (E / P)


# =============================================================================
# Advanced Physics Functions
# =============================================================================

def integrate_rg_flow(beta_func: Callable, chi_init: float = CHI_UV, 
                     t_span: Tuple[float, float] = (1e-10, 1e10), 
                     args: Tuple = (G_COUPLING, LAMBDA_PARAM)) -> Any:
    """
    Integrate RG flow for chi using scipy.integrate.
    
    Args:
        beta_func: Beta function (e.g., rg_beta_chi_spin0)
        chi_init: Initial chi
        t_span: Energy scale range (will be log-scaled)
        args: Additional args for beta_func
    
    Returns:
        scipy.integrate.solve_ivp result
    """
    if not SCIPY_FULL_AVAILABLE:
        raise ImportError("scipy.integrate required for RG flow integration")
    
    def dchi_dt(t, chi):
        return beta_func(chi[0], *args)
    
    log_t_span = (np.log(t_span[0]), np.log(t_span[1]))
    return solve_ivp(dchi_dt, log_t_span, [chi_init], method='RK45', dense_output=True)


def non_ballistic_trajectory(start_pos: np.ndarray, target_pos: np.ndarray, 
                            curvature: float = 0.5, steps: int = 100) -> np.ndarray:
    """
    Generate a non-ballistic (curved) trajectory for radar evasion.
    Uses a simple parametric curve (Bezier-like) to avoid straight lines.
    
    Args:
        start_pos: Starting position [x, y, z]
        target_pos: Target position [x, y, z]
        curvature: Curvature factor (0: straight, >0: curved)
        steps: Number of points in trajectory
    
    Returns:
        Trajectory points (steps x 3)
    """
    start_pos = np.asarray(start_pos, dtype=float)
    target_pos = np.asarray(target_pos, dtype=float)
    
    if steps <= 0:
        raise ValueError("Steps must be positive")
    
    t = np.linspace(0, 1, steps)
    diff = target_pos - start_pos
    
    # Create perpendicular offset for curve
    mid_point = start_pos + diff / 2 + curvature * np.array([0, diff[2], -diff[1]])
    
    # Quadratic Bezier curve
    traj = ((1 - t)[:, np.newaxis] ** 2 * start_pos + 
            2 * (1 - t)[:, np.newaxis] * t[:, np.newaxis] * mid_point + 
            t[:, np.newaxis] ** 2 * target_pos)
    
    return traj


def radar_evasion_probability(traj: np.ndarray, radar_pos: np.ndarray, 
                              rcs: float = 1.0) -> float:
    """
    Estimate radar evasion probability based on trajectory.
    Simplified model: Lower probability for closer approaches or higher RCS.
    
    Args:
        traj: Trajectory points (N x 3)
        radar_pos: Radar position [x, y, z]
        rcs: Radar cross-section (m²)
    
    Returns:
        Evasion probability (0-1; higher is better)
    """
    radar_pos = np.asarray(radar_pos, dtype=float)
    traj = np.asarray(traj, dtype=float)
    
    distances = np.linalg.norm(traj - radar_pos, axis=1)
    min_dist = np.min(distances)
    
    if min_dist < EPSILON:
        return 0.0
    
    # Simple inverse model: P_evade = 1 / (1 + RCS / min_dist^4)
    return 1.0 / (1.0 + rcs / min_dist**4)


# =============================================================================
# Battery Models
# =============================================================================

def lipo_discharge_capacity(C_nom: float, I: float, t: float, 
                           peukert_k: float = LIPO_PEUKERT_CONSTANT) -> float:
    """
    LiPo battery discharge model using Peukert's law.
    
    Args:
        C_nom: Nominal capacity (Ah)
        I: Discharge current (A)
        t: Time (h)
        peukert_k: Peukert constant (default 1.05)
    
    Returns:
        Remaining capacity (Ah)
    """
    if C_nom <= 0 or I < 0 or t < 0:
        raise ValueError("Capacity, current, and time must be non-negative")
    
    if I < EPSILON:
        return C_nom  # No discharge
    
    C_eff = C_nom * (C_nom / I)**(peukert_k - 1)
    discharged = I * t
    
    return max(0.0, C_eff - discharged)


def ssb_discharge_capacity(C_nom: float, I: float, t: float, 
                          peukert_k: float = SSB_PEUKERT_CONSTANT) -> float:
    """
    Solid-state battery discharge model (similar but better efficiency).
    
    Args:
        C_nom: Nominal capacity (Ah)
        I: Discharge current (A)
        t: Time (h)
        peukert_k: Peukert constant (default 1.02)
    
    Returns:
        Remaining capacity (Ah)
    """
    return lipo_discharge_capacity(C_nom, I, t, peukert_k)


def battery_voltage_curve(soc: float, V_nom: float, 
                         V_min: float = 3.0, V_max: float = 4.2) -> float:
    """
    Simple voltage curve model (linear approximation).
    
    Args:
        soc: State of charge (0-1)
        V_nom: Nominal voltage (V)
        V_min: Min voltage (V)
        V_max: Max voltage (V)
    
    Returns:
        Voltage (V)
    """
    if not 0 <= soc <= 1:
        raise ValueError("State of charge must be between 0 and 1")
    
    return V_min + soc * (V_max - V_min)


def stealth_range_calc(v_stealth: float, E: float, P_low: float, 
                       eta_stealth: float = 0.8) -> float:
    """
    Range estimator for stealth operations (lower power/speed).
    
    Args:
        v_stealth: Stealth velocity (m/s)
        E: Energy (J)
        P_low: Low-power consumption (W)
        eta_stealth: Stealth efficiency factor (default 0.8)
    
    Returns:
        Stealth range (m)
    """
    if P_low <= EPSILON:
        raise ValueError("Power must be positive")
    if not 0 <= eta_stealth <= 1:
        raise ValueError("Efficiency must be between 0 and 1")
    
    return eta_stealth * v_stealth * (E / P_low)


# =============================================================================
# Thermal Management
# =============================================================================

def teg_power_recovery(Delta_T: Union[float, np.ndarray], area: float, 
                      thickness: float, load_res: float = 1.0) -> Union[float, np.ndarray]:
    """
    Calculate power recovered from Bi2Te3 TEG.
    Simplified model: P = (alpha Delta_T)^2 / (4 R_int) for matched load.
    
    Args:
        Delta_T: Temperature difference (K)
        area: TEG area (m²)
        thickness: Thickness (m)
        load_res: Load resistance (Ω, default matched)
    
    Returns:
        Recovered power (W)
    """
    if area <= 0 or thickness <= 0:
        raise ValueError("Area and thickness must be positive")
    
    R_int = thickness / (THERMAL_COND * area)  # Internal thermal resistance
    alpha = SEEBECK_COEFF  # Seebeck coefficient
    P_max = (alpha * np.asarray(Delta_T))**2 / (4 * R_int)
    
    return TEG_EFF_FACTOR * P_max


def thermal_dissipation_model(P_in: Union[float, np.ndarray], 
                              eta_thermal: float = 0.95, 
                              Delta_T_max: float = 50, 
                              area: float = 0.01, 
                              thickness: float = 0.001) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """
    Enhanced thermal model with vectorization and TEG recovery.
    
    Args:
        P_in: Input power (W)
        eta_thermal: Thermal efficiency (0-1)
        Delta_T_max: Max allowable Delta T (K)
        area: TEG area (m²)
        thickness: TEG thickness (m)
    
    Returns:
        Tuple of (net_heat_dissipated (W), recovered_power (W))
    """
    P_in = np.asarray(P_in)
    heat_generated = P_in * (1 - eta_thermal)
    Delta_T = np.minimum(heat_generated / THERMAL_COND, Delta_T_max)
    recovered = teg_power_recovery(Delta_T, area, thickness)
    
    return heat_generated - recovered, recovered


def thermal_dissipation(P_in: float, eta_thermal: float = 0.95, 
                       Delta_T_max: float = 50) -> Tuple[float, float]:
    """
    Simulate thermal dissipation with TEG recovery (scalar version).
    
    Args:
        P_in: Input power (W)
        eta_thermal: Thermal efficiency
        Delta_T_max: Max allowable Delta T (K)
    
    Returns:
        Tuple of (heat_dissipated (W), recovered (W))
    """
    heat, rec = thermal_dissipation_model(P_in, eta_thermal, Delta_T_max)
    return float(heat), float(rec)


# =============================================================================
# Monte Carlo and Sensitivity Analysis
# =============================================================================

def parallel_monte_carlo_thrust(params: Dict[str, Any], 
                               uncertainties: Dict[str, float], 
                               n_sim: int = 1000, 
                               n_processes: int = 4,
                               random_seed: Optional[int] = None) -> np.ndarray:
    """
    Parallel Monte Carlo using multiprocessing with reproducibility.
    
    Args:
        params: Nominal parameters dictionary
        uncertainties: Uncertainty (std dev) for each parameter
        n_sim: Number of simulations
        n_processes: Number of parallel processes
        random_seed: Random seed for reproducibility
    
    Returns:
        Array of thrust values from simulations
    """
    if not MULTIPROCESSING_AVAILABLE:
        warnings.warn("Multiprocessing not available, running sequentially")
        n_processes = 1
    
    if random_seed is not None:
        np.random.seed(random_seed)
    
    def sim_single(sim_id: int) -> float:
        """Single simulation with local random state."""
        local_rng = np.random.RandomState(random_seed + sim_id if random_seed is not None else None)
        
        sim_params = {}
        for k, v in params.items():
            uncertainty = uncertainties.get(k, 0)
            sim_params[k] = local_rng.normal(v, uncertainty)
        
        B = sim_params.get('B_opposing', 50.0)
        scaled_I = sim_params.get('I', 15.0) * (sim_params.get('frequency', 100.0) / 50.0)
        delta_B = pulsed_enhancement(sim_params.get('n_turns', 100), scaled_I)
        B_total = B + delta_B
        
        F_vec = force_vector(
            sim_params.get('chi', 1e-10), 
            B_total, 
            sim_params.get('grad_h2', np.array([1.0, 0.0, 0.0])),
            sim_params.get('A', 1.0), 
            sim_params.get('rho', 1000.0)
        )
        F_mag = np.linalg.norm(F_vec)
        T = total_thrust(
            sim_params.get('N', 24), 
            F_mag, 
            sim_params.get('eta', 0.95), 
            sim_params.get('theta', 0.0)
        )
        return T
    
    if n_processes > 1 and MULTIPROCESSING_AVAILABLE:
        with mp.Pool(n_processes) as pool:
            thrusts = pool.map(sim_single, range(n_sim))
    else:
        thrusts = [sim_single(i) for i in range(n_sim)]
    
    return np.array(thrusts)


def monte_carlo_thrust(params: Dict[str, Any], 
                      uncertainties: Dict[str, float], 
                      n_sim: int = 1000,
                      random_seed: Optional[int] = None) -> np.ndarray:
    """
    Monte Carlo simulation for thrust (uses parallel version by default).
    
    Args:
        params: Nominal parameters dictionary
        uncertainties: Uncertainty (std dev) for each parameter
        n_sim: Number of simulations
        random_seed: Random seed for reproducibility
    
    Returns:
        Array of thrust values
    """
    return parallel_monte_carlo_thrust(params, uncertainties, n_sim, 
                                      n_processes=4, random_seed=random_seed)


def sensitivity_analysis(params: Dict[str, Any], 
                        func: Callable, 
                        perturbations: float = 0.01, 
                        method: str = 'finite_diff') -> Dict[str, float]:
    """
    Sensitivity ranking using finite differences.
    
    Args:
        params: Nominal parameters
        func: Function to evaluate (must accept params dict)
        perturbations: Relative perturbation (default 1%)
        method: 'finite_diff' (only method currently)
    
    Returns:
        Dictionary of parameter: sensitivity (sorted by magnitude)
    """
    if method != 'finite_diff':
        raise ValueError("Only 'finite_diff' method currently supported")
    
    nominal = func(params)
    sensitivities = {}
    
    for key, val in params.items():
        if abs(val) < EPSILON:
            continue  # Skip near-zero values
        
        pert_params = params.copy()
        pert_params[key] = val * (1 + perturbations)
        pert_val = func(pert_params)
        sensitivities[key] = abs(pert_val - nominal) / (abs(val) * perturbations)
    
    # Rank by magnitude
    ranked = sorted(sensitivities.items(), key=lambda x: x[1], reverse=True)
    return dict(ranked)


# =============================================================================
# Visualization Functions
# =============================================================================

def plot_flux_gradient(grad_h2: np.ndarray, filename: Optional[str] = None) -> None:
    """
    Plot flux gradient using Matplotlib.
    
    Args:
        grad_h2: Gradient vector(s) - shape (3,) or (N, 3)
        filename: If provided, save to file instead of showing
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("Matplotlib required for visualization")
    
    grad_h2 = np.asarray(grad_h2, dtype=float)
    if grad_h2.ndim == 1:
        grad_h2 = grad_h2.reshape(1, -1)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.quiver(np.zeros(grad_h2.shape[0]), np.zeros(grad_h2.shape[0]), 
             grad_h2[:, 0], grad_h2[:, 1], scale=20)
    ax.set_title('Flux Gradient Vectors')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.grid(True)
    ax.set_aspect('equal')
    
    if filename:
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def plot_thrust_vectors(F_vec: np.ndarray, filename: Optional[str] = None) -> None:
    """
    Plot thrust vectors in 3D.
    
    Args:
        F_vec: Force vector(s) - shape (3,) or (N, 3)
        filename: If provided, save to file instead of showing
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("Matplotlib required for visualization")
    
    F_vec = np.asarray(F_vec, dtype=float)
    if F_vec.ndim == 1:
        F_vec = F_vec.reshape(1, -1)
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.quiver(np.zeros(F_vec.shape[0]), np.zeros(F_vec.shape[0]), np.zeros(F_vec.shape[0]),
              F_vec[:, 0], F_vec[:, 1], F_vec[:, 2], length=1.0, normalize=True)
    ax.set_title('Thrust Vectors')
    ax.set_xlabel('X (N)')
    ax.set_ylabel('Y (N)')
    ax.set_zlabel('Z (N)')
    
    if filename:
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def plot_rg_modifier(chi_values: np.ndarray, beta_values: np.ndarray, 
                    filename: Optional[str] = None) -> None:
    """
    Plot RG modifier (beta function).
    
    Args:
        chi_values: Array of chi values
        beta_values: Corresponding beta values
        filename: If provided, save to file instead of showing
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("Matplotlib required for visualization")
    
    plt.figure(figsize=(10, 6))
    plt.plot(chi_values, beta_values, linewidth=2)
    plt.title('RG Beta Function for χ')
    plt.xlabel('χ')
    plt.ylabel('β_χ')
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    
    if filename:
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


# =============================================================================
# Export Functions
# =============================================================================

def export_to_csv(data: list, filename: str, headers: Optional[list] = None) -> None:
    """
    Export data to CSV with validation.
    
    Args:
        data: List of rows (each row is a list)
        filename: Output filename (will add .csv if not present)
        headers: Column headers (required)
    """
    if not filename.endswith('.csv'):
        filename += '.csv'
    
    if headers is None:
        raise ValueError("Headers are required for CSV export")
    
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
    except IOError as e:
        raise IOError(f"Failed to write CSV file: {e}")


def export_to_json(data: Any, filename: str) -> None:
    """
    Export to JSON with proper serialization.
    
    Args:
        data: Data to export (dict, list, etc.)
        filename: Output filename (will add .json if not present)
    """
    if not filename.endswith('.json'):
        filename += '.json'
    
    def convert_to_serializable(obj: Any) -> Any:
        """Convert numpy types to Python native types."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_serializable(item) for item in obj]
        return obj
    
    serializable_data = convert_to_serializable(data)
    
    try:
        with open(filename, 'w') as f:
            json.dump(serializable_data, f, indent=4)
    except IOError as e:
        raise IOError(f"Failed to write JSON file: {e}")


def export_to_hdf5(data: np.ndarray, filename: str, key: str = 'dataset', 
                  mode: str = 'w') -> None:
    """
    Export to HDF5 with mode control.
    
    Args:
        data: Data array to export
        filename: Output filename (will add .h5 if not present)
        key: Dataset key/name
        mode: 'w' (overwrite), 'a' (append)
    """
    if not H5PY_AVAILABLE:
        raise ImportError("h5py required for HDF5 export")
    
    if not filename.endswith('.h5') and not filename.endswith('.hdf5'):
        filename += '.h5'
    
    if mode not in ['w', 'a']:
        raise ValueError("Mode must be 'w' (write) or 'a' (append)")
    
    try:
        with h5py.File(filename, mode) as f:
            if key in f and mode == 'a':
                warnings.warn(f"Key '{key}' exists and will be overwritten")
                del f[key]
            f.create_dataset(key, data=data)
    except IOError as e:
        raise IOError(f"Failed to write HDF5 file: {e}")


# =============================================================================
# Quantum Simulations (Optional Dependencies)
# =============================================================================

def simulate_cavity_qed_vacuum(omega_c: float = 2*np.pi*5e9, 
                              omega_a: float = 2*np.pi*5e9, 
                              g: float = 2*np.pi*50e6, 
                              N: int = 10) -> Tuple[Any, Any]:
    """
    Simulate cavity QED using QuTiP for vacuum Rabi splitting.
    
    Args:
        omega_c: Cavity frequency (Hz)
        omega_a: Atom frequency (Hz)
        g: Coupling strength (Hz)
        N: Fock space dimension
    
    Returns:
        Tuple of (Hamiltonian, time_evolution_result)
    """
    if not QUTIP_AVAILABLE:
        raise ImportError("QuTiP is required for cavity QED simulations")
    
    a = qt.destroy(N)
    sigma_m = qt.sigmam()
    sigma_p = qt.sigmap()
    H = omega_c * a.dag() * a + (omega_a / 2) * qt.sigmaz() + g * (a.dag() * sigma_m + a * sigma_p)
    
    # Initial vacuum state: ground atom + vacuum photons
    psi0 = qt.tensor(qt.basis(2, 1), qt.basis(N, 0))
    times = np.linspace(0, 1e-6, 1000)  # Microsecond scale
    result = qt.mesolve(H, psi0, times, [], [a.dag() * a])
    
    return H, result


def simulate_qed_polarization(mol_str: str = 'H 0 0 0; H 0 0 1.4', 
                              basis: str = 'sto-3g', 
                              field_strength: float = 1e-2) -> float:
    """
    Simulate QED effects using PySCF.
    
    Args:
        mol_str: Molecule specification
        basis: Basis set
        field_strength: External field for polarization
    
    Returns:
        Energy with QED correction (a.u.)
    """
    if not PYSCF_AVAILABLE:
        raise ImportError("PySCF is required for QED polarization simulations")
    
    mol = gto.M(atom=mol_str, basis=basis)
    mf = scf.RHF(mol).run()
    
    if PYSCF_QED_AVAILABLE:
        try:
            mf_qed = qed.RHF(mf).run()
            energy = mf_qed.energy_tot()
        except Exception as e:
            warnings.warn(f"QED module error: {e}. Returning standard HF energy.")
            energy = mf.energy_tot()
    else:
        warnings.warn("PySCF QED module not available. Returning standard HF energy.")
        energy = mf.energy_tot()
    
    return energy


# =============================================================================
# Symbolic Mathematics (SymPy)
# =============================================================================

def symbolic_surface_field() -> sp.Expr:
    """Return symbolic expression for surface field."""
    B_r, L, R, d = sp.symbols('B_r L R d', positive=True, real=True)
    term1 = L / sp.sqrt(R**2 + L**2)
    term2 = (L + d) / sp.sqrt(R**2 + (L + d)**2)
    return (B_r / 2) * (term1 + term2)


def symbolic_opposing_field() -> sp.Expr:
    """Return symbolic expression for opposing field."""
    m1, m2, d, k = sp.symbols('m_1 m_2 d k', positive=True, real=True)
    mu_0 = sp.Symbol('mu_0', positive=True, real=True)
    return (mu_0 * m1 * m2 / (2 * sp.pi * d**2)) * k


def symbolic_force_vector() -> sp.Expr:
    """Return symbolic expression for force vector (scalar version)."""
    chi, B, A, rho = sp.symbols('chi B A rho', real=True)
    grad_h2 = sp.Symbol('grad_h2', real=True)
    return chi * B**2 * grad_h2 * A * rho


def symbolic_rg_beta_chi_spin0() -> sp.Expr:
    """Symbolic RG beta for spin-0."""
    chi, g, lam = sp.symbols('chi g lambda', real=True)
    return -4 * chi + (g / (2 * sp.pi)) * (chi / (1 - 2 * lam))


# =============================================================================
# Unit Tests
# =============================================================================

def test_surface_field() -> None:
    """Unit test for surface_field calculation."""
    expected = (1.4 / 2) * (0.3 / np.sqrt(0.15**2 + 0.3**2) + 
                            0.35 / np.sqrt(0.15**2 + 0.35**2))
    result = surface_field(1.4, 0.3, 0.15, 0.05)
    assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    print("✓ test_surface_field PASSED")


def test_convergence_quality() -> None:
    """Unit test for convergence quality calculation."""
    # Perfect opposition
    B1 = np.array([1.0, 0.0, 0.0])
    B2 = np.array([-1.0, 0.0, 0.0])
    quality = calculate_convergence_quality(B1, B2)
    assert np.isclose(quality, 1.0), f"Expected 1.0, got {quality}"
    
    # Perfect parallel (bad)
    B3 = np.array([1.0, 0.0, 0.0])
    B4 = np.array([1.0, 0.0, 0.0])
    quality2 = calculate_convergence_quality(B3, B4)
    assert np.isclose(quality2, -1.0), f"Expected -1.0, got {quality2}"
    
    print("✓ test_convergence_quality PASSED")


def test_pulsed_enhancement() -> None:
    """Unit test for pulsed enhancement."""
    result = pulsed_enhancement(100, 10)
    expected = MU_0 * 100 * 10
    assert np.isclose(result, expected), f"Expected {expected}, got {result}"
    print("✓ test_pulsed_enhancement PASSED")


def run_all_tests() -> None:
    """Run all unit tests."""
    print("\n" + "=" * 70)
    print("Running Unit Tests")
    print("=" * 70)
    test_surface_field()
    test_convergence_quality()
    test_pulsed_enhancement()
    print("=" * 70)
    print("All tests passed!")
    print("=" * 70 + "\n")


# =============================================================================
# Main Execution (for testing/demonstration)
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("QED Vacuum Thrust Control - Equations Module")
    print("=" * 70)
    
    print("\nModule Information:")
    print(f"  NumPy version: {np.__version__}")
    print(f"  SciPy available: {SCIPY_FULL_AVAILABLE}")
    print(f"  Multiprocessing available: {MULTIPROCESSING_AVAILABLE}")
    print(f"  Matplotlib available: {MATPLOTLIB_AVAILABLE}")
    print(f"  h5py available: {H5PY_AVAILABLE}")
    print(f"  QuTiP available: {QUTIP_AVAILABLE}")
    print(f"  PySCF available: {PYSCF_AVAILABLE}")
    
    # Run unit tests
    run_all_tests()
    
    # Example calculations
    print("\nExample Calculations:")
    print("-" * 70)
    
    print("\n1. Surface Field:")
    B_surf = surface_field(B_r=1.4, L=0.3, R=0.15, d=0.05)
    print(f"   B_surface = {B_surf:.4f} T")
    
    print("\n2. Opposing Field (magnitude only - validation required):")
    B_opp = opposing_field(m1=100, m2=100, d=0.1, k=1.0)
    print(f"   B_opposing = {B_opp:.6e} T")
    
    print("\n3. MADA Convergence Validation:")
    B1_correct = np.array([-50.0, 0.0, 0.0])
    B2_correct = np.array([50.0, 0.0, 0.0])
    conv = validate_mada_convergence(B1_correct, B2_correct)
    print(f"   {conv['message']}")
    
    print("\n4. Force Vector:")
    F = force_vector(chi=1e-10, B=20, grad_h2=np.array([1, 0, 0]), A=0.01, rho=2700)
    print(f"   F = {F} N")
    print(f"   |F| = {np.linalg.norm(F):.4f} N")
    
    print("\n5. Total Thrust:")
    T = total_thrust(N=10, F=100, eta=0.95, theta=0)
    print(f"   Thrust = {T:.2f} N")
    
    print("\n6. Acceleration:")
    a = acceleration(T=1000, m=50)
    print(f"   Acceleration = {a:.2f} m/s² ({a/9.81:.2f}g)")
    
    print("\n" + "=" * 70)
    print("Module loaded successfully!")
    print("=" * 70)
