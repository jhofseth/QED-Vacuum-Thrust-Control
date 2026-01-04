"""
simulations/refine_equations.py

RG Equation Refinement and Parameter Fitting for QED Vacuum Propulsion.

Updated for the Refractive Vacuum Gravity (RVG) Unified Field Framework:
- Disformal QED with 95 GeV dilaton/radion resonance coupling
- Dilaton enhancement factor Θ_dilaton(B) fitting from experimental data
- Vacuum refractive index K(r) scaling validation
- Master Equation of Levitation parameter optimization
- Trace anomaly coupling calibration

This script provides tools for:
1. Fitting RG beta functions for vacuum susceptibility χ
2. Calibrating the dilaton enhancement Θ_dilaton(B) from thrust measurements
3. Validating vacuum refractive index models against experimental data
4. Parameter optimization for the Master Equation of Levitation

References:
- Refractive Vacuum Gravity (RVG) Unified Field Theory (Hofseth, 2025): https://dx.doi.org/10.2139/ssrn.5381654
- U.S. Patent #5,929,732 (Lockheed Martin Corporation): https://patents.google.com/patent/US5929732A/en
- CMS/ATLAS 95.4 GeV di-photon resonance (3.1σ combined significance)
"""

import numpy as np
from scipy.integrate import odeint
from scipy.optimize import curve_fit, minimize
import pandas as pd
import matplotlib.pyplot as plt
from typing import Callable, List, Tuple, Optional, Dict
import os
import sys
import warnings

# Add parent directory to path for imports if needed
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
except NameError:
    # If __file__ not defined (e.g., in REPL), skip or set manually
    pass

# =============================================================================
# Physical Constants
# =============================================================================

MU_0 = 4 * np.pi * 1e-7  # Vacuum permeability (H/m)
EPSILON_0 = 8.854187817e-12  # Vacuum permittivity (F/m)
C = 299792458.0  # Speed of light (m/s)
HBAR = 1.054571817e-34  # Reduced Planck constant (J·s)
M_E = 9.10938370e-31  # Electron mass (kg)
E_CHARGE = 1.602176634e-19  # Elementary charge (C)
ALPHA = 1/137.035999084  # Fine structure constant

# QED critical field (Schwinger limit)
B_SCHWINGER = (M_E**2 * C**3) / (E_CHARGE * HBAR)  # ~4.414e9 T

# =============================================================================
# RVG Framework Constants
# =============================================================================

# 95 GeV Dilaton/Radion Resonance Parameters
DILATON_MASS = 95.4  # GeV - observed CMS/ATLAS resonance
DILATON_MASS_EV = 95.4e9  # eV
DILATON_SIGMA = 3.1  # Combined significance (σ)

# Default model parameters (require experimental calibration)
DEFAULT_CHI0 = 1e-10  # Initial χ at UV scale
DEFAULT_THETA_BASE = 1e-6  # Base dilaton enhancement (placeholder)
DEFAULT_B_CRIT = 20.0  # Effective critical field for dilaton activation (T)

# RG flow parameters
DEFAULT_T_SPAN = np.linspace(0, -10, 100)  # ln μ from high (t=0) to low (negative t)

# Data file paths
DATA_FILE = 'empirical_data.csv'  # Expected columns: 'ln_mu', 'chi', optionally 'error'
THRUST_DATA_FILE = 'thrust_data.csv'  # Expected columns: 'B_field', 'thrust', optionally 'error'
THETA_DATA_FILE = 'theta_calibration.csv'  # Expected columns: 'B_field', 'theta_measured'

# Global variable for curve fitting
CURRENT_BETA_FUNC = None


# =============================================================================
# RG Beta Functions for Vacuum Susceptibility χ
# =============================================================================

def beta_spin0(chi: float, params: Tuple[float, float]) -> float:
    """
    RG beta function for χ in spin-0 emergent gravity (EGDPP framework).
    
    β_χ = -4 χ + (g / 2π) (χ / (1 - 2λ))
    
    Parameters:
    chi (float): Current value of χ
    params (tuple): (g, λ) - coupling constant and scalar field parameter
    
    Returns:
    float: β_χ value
    """
    g, lam = params
    if abs(1 - 2 * lam) < 1e-10:
        warnings.warn("λ close to 0.5, potential singularity in beta_spin0")
        return -4 * chi
    return -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lam))


def beta_spin2(chi: float, params: Tuple[float, float, float]) -> float:
    """
    RG beta function for χ in spin-2 emergent gravity.
    
    β_χ = (4 + η_χ) χ + c g χ
    
    Parameters:
    chi (float): Current value of χ
    params (tuple): (η_χ, c, g) - anomalous dimension, coefficient, coupling
    
    Returns:
    float: β_χ value
    """
    eta_chi, c, g = params
    return (4 + eta_chi) * chi + c * g * chi


def beta_general(chi: float, params: Tuple[float, ...]) -> float:
    """
    General data-derived beta function, polynomial form.
    
    β_χ = a χ + b χ² + ...
    
    Parameters:
    chi (float): Current value of χ
    params (tuple): Coefficients (a, b) for β = a χ + b χ²
    
    Returns:
    float: β_χ value
    """
    a, b = params
    return a * chi + b * chi**2


def beta_rvg_dilaton(chi: float, params: Tuple[float, float, float]) -> float:
    """
    RG beta function for χ with RVG dilaton coupling.
    
    Incorporates the 95 GeV resonance trace anomaly coupling:
    β_χ = -4 χ + α_d (χ² / χ_crit) + g_tr χ
    
    where α_d is the dilaton coupling and g_tr is the trace anomaly strength.
    
    Parameters:
    chi (float): Current value of χ
    params (tuple): (α_d, χ_crit, g_tr)
    
    Returns:
    float: β_χ value
    """
    alpha_d, chi_crit, g_tr = params
    if chi_crit < 1e-15:
        chi_crit = 1e-15
    return -4 * chi + alpha_d * (chi**2 / chi_crit) + g_tr * chi


# =============================================================================
# Dilaton Enhancement Models for Θ_dilaton(B)
# =============================================================================

def theta_dilaton_simple(B: float, params: Tuple[float, float]) -> float:
    """
    Simple dilaton enhancement model.
    
    Θ_dilaton(B) = θ_base * (1 + (B / B_crit)²)
    
    Parameters:
    B (float): Magnetic field strength (T)
    params (tuple): (θ_base, B_crit)
    
    Returns:
    float: Dilaton enhancement factor
    """
    theta_base, B_crit = params
    if B_crit < 1e-10:
        B_crit = 1e-10
    return theta_base * (1 + (B / B_crit)**2)


def theta_dilaton_resonance(B: float, params: Tuple[float, float, float, float]) -> float:
    """
    Dilaton enhancement with 95 GeV resonance structure.
    
    Θ_dilaton(B) = θ_base * (1 + (B/B_crit)²) * exp(-γ / (B/B_crit + ε))
    
    The exponential factor models the "activation" behavior where
    effects are weak at low B and grow strongly with intensity.
    
    Parameters:
    B (float): Magnetic field strength (T)
    params (tuple): (θ_base, B_crit, γ, ε)
    
    Returns:
    float: Dilaton enhancement factor
    """
    theta_base, B_crit, gamma, epsilon = params
    if B_crit < 1e-10:
        B_crit = 1e-10
    ratio = B / B_crit
    activation = np.exp(-gamma / (ratio + epsilon))
    return theta_base * (1 + ratio**2) * activation


def theta_dilaton_trace_anomaly(B: float, params: Tuple[float, float, float, float, float]) -> float:
    """
    Full dilaton enhancement with trace anomaly coupling.
    
    Based on the RVG framework where the 95 GeV dilaton couples to
    the trace anomaly of the energy-momentum tensor:
    
    Θ_dilaton(B) = θ_base * [1 + α_T (B/B_crit)² + β_T (B/B_crit)⁴] * f_res(B)
    
    where f_res(B) is a resonance factor from the dilaton coupling.
    
    Parameters:
    B (float): Magnetic field strength (T)
    params (tuple): (θ_base, B_crit, α_T, β_T, f_res_strength)
    
    Returns:
    float: Dilaton enhancement factor
    """
    theta_base, B_crit, alpha_T, beta_T, f_res = params
    if B_crit < 1e-10:
        B_crit = 1e-10
    ratio = B / B_crit
    polynomial = 1 + alpha_T * ratio**2 + beta_T * ratio**4
    resonance_factor = 1 + f_res * np.tanh(ratio - 1)  # Activates around B_crit
    return theta_base * polynomial * resonance_factor


def theta_dilaton_saturation(B: float, params: Tuple[float, float, float, float]) -> float:
    """
    Dilaton enhancement with material saturation effects.
    
    Accounts for the supra-saturation requirement where B_opposing >> B_sat
    for macroscopic vacuum effects.
    
    Θ_dilaton(B, B_sat) = θ_base * (B/B_sat)^n * [1 + (B/B_crit)²]
    
    where n determines the saturation scaling exponent.
    
    Parameters:
    B (float): Magnetic field strength (T)
    params (tuple): (θ_base, B_crit, B_sat, n)
    
    Returns:
    float: Dilaton enhancement factor
    """
    theta_base, B_crit, B_sat, n = params
    if B_crit < 1e-10:
        B_crit = 1e-10
    if B_sat < 1e-10:
        B_sat = 1e-10
    
    # Saturation factor: grows as (B/B_sat)^n when B > B_sat
    sat_ratio = max(B / B_sat, 0.1)
    sat_factor = sat_ratio**n if sat_ratio > 1.0 else sat_ratio**(n/2)
    
    # Standard enhancement
    enhancement = 1 + (B / B_crit)**2
    
    return theta_base * sat_factor * enhancement


# =============================================================================
# Vacuum Refractive Index Models
# =============================================================================

def vacuum_refractive_index_simple(B: float, params: Tuple[float, float]) -> float:
    """
    Simple vacuum refractive index model.
    
    K(r) = 1 + χ_vac(B) ≈ 1 + Θ_95 * B² / B_crit²
    
    Parameters:
    B (float): Magnetic field strength (T)
    params (tuple): (Θ_95, B_crit)
    
    Returns:
    float: Vacuum refractive index K
    """
    theta_95, B_crit = params
    if B_crit < 1e-10:
        B_crit = 1e-10
    chi_vac = theta_95 * (B / B_crit)**2
    return 1.0 + chi_vac


def vacuum_refractive_index_full(B: float, params: Tuple[float, float, float, float]) -> float:
    """
    Full vacuum refractive index with dilaton enhancement.
    
    K(r) = 1 + Θ_dilaton(B) * (B / B_crit)²
    
    Uses the resonance model for Θ_dilaton.
    
    Parameters:
    B (float): Magnetic field strength (T)
    params (tuple): (θ_base, B_crit, γ, ε) for theta_dilaton_resonance
    
    Returns:
    float: Vacuum refractive index K
    """
    theta = theta_dilaton_resonance(B, params)
    B_crit = params[1]
    chi_vac = theta * (B / B_crit)**2
    return 1.0 + chi_vac


# =============================================================================
# Master Equation of Levitation Models
# =============================================================================

def master_equation_thrust(B: float, grad_B2: float, volume: float, 
                           params: Tuple[float, float, float]) -> float:
    """
    Master Equation of Levitation thrust calculation.
    
    F_lift = (1 / 2μ₀) * Θ_dilaton(B) * ∇(B²) * V * η
    
    Parameters:
    B (float): Magnetic field strength (T)
    grad_B2 (float): Gradient of B² (T²/m)
    volume (float): Integration volume (m³)
    params (tuple): (θ_base, B_crit, η_align)
    
    Returns:
    float: Thrust force magnitude (N)
    """
    theta_base, B_crit, eta_align = params
    theta = theta_dilaton_simple(B, (theta_base, B_crit))
    F = (1 / (2 * MU_0)) * theta * grad_B2 * volume * eta_align
    return F


def master_equation_thrust_full(B: float, grad_B2: float, volume: float,
                                 params: Tuple[float, ...]) -> float:
    """
    Full Master Equation with trace anomaly coupling.
    
    F_lift = (1 / 2μ₀) * Θ_dilaton(B) * ∇(B²) * V * η * cos(θ)
    
    Parameters:
    B (float): Magnetic field strength (T)
    grad_B2 (float): Gradient of B² (T²/m)
    volume (float): Integration volume (m³)
    params (tuple): (θ_base, B_crit, α_T, β_T, f_res, η_align, θ_angle)
    
    Returns:
    float: Thrust force magnitude (N)
    """
    theta_base, B_crit, alpha_T, beta_T, f_res, eta_align, theta_angle = params
    theta = theta_dilaton_trace_anomaly(B, (theta_base, B_crit, alpha_T, beta_T, f_res))
    F = (1 / (2 * MU_0)) * theta * grad_B2 * volume * eta_align * np.cos(np.deg2rad(theta_angle))
    return F


# =============================================================================
# RG Flow Solvers
# =============================================================================

def solve_rg_flow(beta_func: Callable, params: Tuple[float, ...], 
                  chi0: float, t: np.ndarray) -> np.ndarray:
    """
    Solve the RG flow ODE dχ/dt = β(χ) from t[0] (UV) to lower scales.
    
    Parameters:
    beta_func (Callable): The beta function to use
    params (tuple): Parameters for beta_func
    chi0 (float): Initial χ at t=0 (high scale)
    t (np.ndarray): Array of ln μ values (decreasing for IR)
    
    Returns:
    np.ndarray: χ(t) solution
    """
    def ode(chi, t):
        return beta_func(chi, params)
    
    sol = odeint(ode, chi0, t)
    return sol[:, 0]


def model_func(t: np.ndarray, chi0: float, *param_args: float) -> np.ndarray:
    """
    Model for curve fitting: Solve RG flow with given beta and params.
    
    This is a wrapper to pass to curve_fit.
    Global CURRENT_BETA_FUNC must be set before calling.
    
    Parameters:
    t (np.ndarray): ln μ data
    chi0 (float): Initial χ (fit parameter)
    param_args (float): Parameters for beta_func
    
    Returns:
    np.ndarray: Predicted χ(t)
    """
    global CURRENT_BETA_FUNC
    return solve_rg_flow(CURRENT_BETA_FUNC, param_args, chi0, t)


# =============================================================================
# Fitting Functions
# =============================================================================

def fit_rg_model(t_data: np.ndarray, chi_data: np.ndarray, beta_func: Callable, 
                 initial_params: List[float], 
                 bounds: Optional[Tuple[List[float], List[float]]] = None, 
                 sigma: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit the RG model to empirical data.
    
    Parameters:
    t_data (np.ndarray): ln μ values
    chi_data (np.ndarray): χ values
    beta_func (Callable): The beta function to fit
    initial_params (list): Initial guess [chi0, param1, param2, ...]
    bounds (tuple, optional): Bounds for parameters
    sigma (np.ndarray, optional): Errors for weighted fit
    
    Returns:
    tuple: (optimized_parameters, covariance_matrix)
    """
    global CURRENT_BETA_FUNC
    CURRENT_BETA_FUNC = beta_func
    
    try:
        if bounds is not None:
            popt, pcov = curve_fit(model_func, t_data, chi_data, 
                                   p0=initial_params, bounds=bounds, sigma=sigma,
                                   maxfev=5000)
        else:
            popt, pcov = curve_fit(model_func, t_data, chi_data, 
                                   p0=initial_params, sigma=sigma,
                                   maxfev=5000)
    except RuntimeError as e:
        warnings.warn(f"Curve fitting failed: {e}")
        popt = np.array(initial_params)
        pcov = np.eye(len(initial_params)) * np.inf
    
    return popt, pcov


def fit_theta_dilaton(B_data: np.ndarray, theta_data: np.ndarray,
                      model: str = 'resonance',
                      initial_params: Optional[List[float]] = None,
                      sigma: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit dilaton enhancement Θ_dilaton(B) to experimental data.
    
    This is the key function for calibrating the RVG framework from
    experimental thrust measurements.
    
    Parameters:
    B_data (np.ndarray): Magnetic field values (T)
    theta_data (np.ndarray): Measured/inferred Θ values
    model (str): Model type - 'simple', 'resonance', 'trace_anomaly', 'saturation'
    initial_params (list, optional): Initial parameter guess
    sigma (np.ndarray, optional): Measurement errors
    
    Returns:
    tuple: (optimized_parameters, covariance_matrix)
    """
    model_funcs = {
        'simple': theta_dilaton_simple,
        'resonance': theta_dilaton_resonance,
        'trace_anomaly': theta_dilaton_trace_anomaly,
        'saturation': theta_dilaton_saturation
    }
    
    default_params = {
        'simple': [1e-6, 20.0],
        'resonance': [1e-6, 20.0, 0.1, 0.01],
        'trace_anomaly': [1e-6, 20.0, 1.0, 0.1, 0.5],
        'saturation': [1e-6, 20.0, 2.85, 2.0]
    }
    
    if model not in model_funcs:
        raise ValueError(f"Unknown model: {model}. Choose from {list(model_funcs.keys())}")
    
    func = model_funcs[model]
    p0 = initial_params if initial_params else default_params[model]
    
    # Wrapper for curve_fit
    def fit_func(B, *params):
        return np.array([func(b, params) for b in B])
    
    try:
        popt, pcov = curve_fit(fit_func, B_data, theta_data, p0=p0, sigma=sigma,
                               maxfev=5000)
    except RuntimeError as e:
        warnings.warn(f"Theta fitting failed: {e}")
        popt = np.array(p0)
        pcov = np.eye(len(p0)) * np.inf
    
    return popt, pcov


def fit_master_equation(B_data: np.ndarray, grad_B2_data: np.ndarray,
                        volume: float, thrust_data: np.ndarray,
                        initial_params: Optional[List[float]] = None,
                        sigma: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit the Master Equation of Levitation parameters to thrust data.
    
    F_lift = (1 / 2μ₀) * Θ_dilaton(B) * ∇(B²) * V * η
    
    Parameters:
    B_data (np.ndarray): Magnetic field values (T)
    grad_B2_data (np.ndarray): ∇(B²) values (T²/m)
    volume (float): Integration volume (m³)
    thrust_data (np.ndarray): Measured thrust values (N)
    initial_params (list, optional): [θ_base, B_crit, η_align]
    sigma (np.ndarray, optional): Measurement errors
    
    Returns:
    tuple: (optimized_parameters, covariance_matrix)
    """
    p0 = initial_params if initial_params else [1e-6, 20.0, 0.95]
    
    def fit_func(X, theta_base, B_crit, eta_align):
        B, grad_B2 = X
        thrust = np.zeros_like(B)
        for i in range(len(B)):
            thrust[i] = master_equation_thrust(B[i], grad_B2[i], volume,
                                               (theta_base, B_crit, eta_align))
        return thrust
    
    X_data = np.vstack([B_data, grad_B2_data])
    
    try:
        popt, pcov = curve_fit(fit_func, X_data, thrust_data, p0=p0, sigma=sigma,
                               maxfev=5000)
    except RuntimeError as e:
        warnings.warn(f"Master equation fitting failed: {e}")
        popt = np.array(p0)
        pcov = np.eye(len(p0)) * np.inf
    
    return popt, pcov


def infer_theta_from_thrust(B: float, grad_B2: float, volume: float, 
                            thrust: float, eta_align: float = 0.95) -> float:
    """
    Infer Θ_dilaton from a measured thrust value.
    
    Rearranging the Master Equation:
    Θ_dilaton = F_lift * 2μ₀ / (∇(B²) * V * η)
    
    Parameters:
    B (float): Magnetic field strength (T)
    grad_B2 (float): Gradient of B² (T²/m)
    volume (float): Integration volume (m³)
    thrust (float): Measured thrust (N)
    eta_align (float): Alignment efficiency
    
    Returns:
    float: Inferred Θ_dilaton value
    """
    if abs(grad_B2) < 1e-15 or volume < 1e-15:
        warnings.warn("grad_B2 or volume too small for inference")
        return 0.0
    
    theta = thrust * 2 * MU_0 / (grad_B2 * volume * eta_align)
    return theta


# =============================================================================
# Data Loading Functions
# =============================================================================

def load_chi_data(data_file: str) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Load χ(μ) data from CSV.
    
    Parameters:
    data_file (str): Path to CSV with columns 'ln_mu', 'chi', optionally 'error'
    
    Returns:
    tuple: (t_data, chi_data, sigma)
    """
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Data file {data_file} not found.")
    
    df = pd.read_csv(data_file)
    t_data = df['ln_mu'].values
    chi_data = df['chi'].values
    sigma = df['error'].values if 'error' in df.columns else None
    
    # Sort by t
    sort_idx = np.argsort(t_data)
    t_data = t_data[sort_idx]
    chi_data = chi_data[sort_idx]
    if sigma is not None:
        sigma = sigma[sort_idx]
    
    return t_data, chi_data, sigma


def load_thrust_data(data_file: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Load thrust measurement data from CSV.
    
    Parameters:
    data_file (str): Path to CSV with columns 'B_field', 'grad_B2', 'thrust', optionally 'error'
    
    Returns:
    tuple: (B_data, grad_B2_data, thrust_data, sigma)
    """
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Data file {data_file} not found.")
    
    df = pd.read_csv(data_file)
    B_data = df['B_field'].values
    grad_B2_data = df['grad_B2'].values if 'grad_B2' in df.columns else df['B_field'].values * 1e9  # Default estimate
    thrust_data = df['thrust'].values
    sigma = df['error'].values if 'error' in df.columns else None
    
    return B_data, grad_B2_data, thrust_data, sigma


def load_theta_data(data_file: str) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Load Θ_dilaton calibration data from CSV.
    
    Parameters:
    data_file (str): Path to CSV with columns 'B_field', 'theta_measured', optionally 'error'
    
    Returns:
    tuple: (B_data, theta_data, sigma)
    """
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Data file {data_file} not found.")
    
    df = pd.read_csv(data_file)
    B_data = df['B_field'].values
    theta_data = df['theta_measured'].values
    sigma = df['error'].values if 'error' in df.columns else None
    
    return B_data, theta_data, sigma


def generate_synthetic_data(model: str = 'resonance', 
                            noise_level: float = 0.1,
                            n_points: int = 50) -> Dict[str, np.ndarray]:
    """
    Generate synthetic data for testing fitting routines.
    
    Parameters:
    model (str): Model type for generating data
    noise_level (float): Relative noise level
    n_points (int): Number of data points
    
    Returns:
    dict: Dictionary with 'B', 'theta', 'thrust', 'grad_B2', 'error'
    """
    B_data = np.linspace(5, 60, n_points)
    
    # True parameters
    if model == 'resonance':
        true_params = (1e-6, 20.0, 0.1, 0.01)
        theta_true = np.array([theta_dilaton_resonance(b, true_params) for b in B_data])
    else:
        true_params = (1e-6, 20.0)
        theta_true = np.array([theta_dilaton_simple(b, true_params) for b in B_data])
    
    # Add noise
    noise = np.random.normal(0, noise_level * np.mean(theta_true), n_points)
    theta_data = theta_true + noise
    
    # Generate thrust data
    volume = 0.1  # m³
    grad_B2 = 2 * B_data * 1e9  # T²/m (assuming ~1e9 T/m gradient)
    thrust_true = np.array([master_equation_thrust(B_data[i], grad_B2[i], volume,
                                                   (true_params[0], true_params[1], 0.95))
                           for i in range(n_points)])
    thrust_noise = np.random.normal(0, noise_level * np.mean(thrust_true), n_points)
    thrust_data = thrust_true + thrust_noise
    
    return {
        'B': B_data,
        'theta': theta_data,
        'theta_true': theta_true,
        'thrust': thrust_data,
        'thrust_true': thrust_true,
        'grad_B2': grad_B2,
        'error': np.abs(noise),
        'true_params': true_params
    }


# =============================================================================
# Plotting Functions
# =============================================================================

def plot_rg_fit(t_data: np.ndarray, chi_data: np.ndarray, 
                popt: np.ndarray, beta_name: str,
                save: bool = True):
    """
    Plot the fitted RG flow against data.
    
    Parameters:
    t_data (np.ndarray): ln μ values
    chi_data (np.ndarray): Measured χ
    popt (np.ndarray): Optimized parameters [chi0, ...]
    beta_name (str): Name of the model
    save (bool): Whether to save the plot
    """
    chi_pred = model_func(t_data, *popt)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(t_data, chi_data, label='Empirical Data', color='red', alpha=0.7)
    plt.plot(t_data, chi_pred, label=f'Fitted {beta_name} Model', color='blue', linewidth=2)
    plt.xlabel('ln μ (Energy Scale)', fontsize=12)
    plt.ylabel('χ (Vacuum Susceptibility)', fontsize=12)
    plt.title(f'RG Flow Fit: {beta_name}', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if save:
        filename = f'rg_fit_{beta_name.lower().replace("-", "_").replace(" ", "_")}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Plot saved: {filename}")
    
    plt.show()


def plot_theta_fit(B_data: np.ndarray, theta_data: np.ndarray,
                   popt: np.ndarray, model: str,
                   save: bool = True):
    """
    Plot the fitted Θ_dilaton(B) against data.
    
    Parameters:
    B_data (np.ndarray): Magnetic field values (T)
    theta_data (np.ndarray): Measured Θ values
    popt (np.ndarray): Optimized parameters
    model (str): Model name
    save (bool): Whether to save the plot
    """
    model_funcs = {
        'simple': theta_dilaton_simple,
        'resonance': theta_dilaton_resonance,
        'trace_anomaly': theta_dilaton_trace_anomaly,
        'saturation': theta_dilaton_saturation
    }
    
    func = model_funcs[model]
    B_fine = np.linspace(min(B_data), max(B_data), 200)
    theta_pred = np.array([func(b, tuple(popt)) for b in B_fine])
    
    plt.figure(figsize=(10, 6))
    plt.scatter(B_data, theta_data, label='Measured Data', color='red', alpha=0.7, s=50)
    plt.plot(B_fine, theta_pred, label=f'Fitted {model} Model', color='blue', linewidth=2)
    plt.xlabel('Magnetic Field B (T)', fontsize=12)
    plt.ylabel('Θ_dilaton (Dilaton Enhancement)', fontsize=12)
    plt.title(f'Dilaton Enhancement Factor: {model} Model', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    if save:
        filename = f'theta_fit_{model}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Plot saved: {filename}")
    
    plt.show()


def plot_master_equation_fit(B_data: np.ndarray, thrust_data: np.ndarray,
                             grad_B2_data: np.ndarray, volume: float,
                             popt: np.ndarray, save: bool = True):
    """
    Plot the fitted Master Equation thrust against data.
    
    Parameters:
    B_data (np.ndarray): Magnetic field values (T)
    thrust_data (np.ndarray): Measured thrust (N)
    grad_B2_data (np.ndarray): ∇(B²) values (T²/m)
    volume (float): Integration volume (m³)
    popt (np.ndarray): Optimized parameters [θ_base, B_crit, η_align]
    save (bool): Whether to save the plot
    """
    thrust_pred = np.array([master_equation_thrust(B_data[i], grad_B2_data[i], volume, tuple(popt))
                           for i in range(len(B_data))])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Thrust vs B
    axes[0].scatter(B_data, thrust_data, label='Measured', color='red', alpha=0.7, s=50)
    axes[0].scatter(B_data, thrust_pred, label='Predicted', color='blue', alpha=0.7, s=30, marker='x')
    axes[0].set_xlabel('Magnetic Field B (T)', fontsize=12)
    axes[0].set_ylabel('Thrust (N)', fontsize=12)
    axes[0].set_title('Master Equation: Thrust vs B', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Predicted vs Measured
    axes[1].scatter(thrust_data, thrust_pred, color='green', alpha=0.7, s=50)
    max_thrust = max(max(thrust_data), max(thrust_pred))
    axes[1].plot([0, max_thrust], [0, max_thrust], 'k--', label='Perfect fit')
    axes[1].set_xlabel('Measured Thrust (N)', fontsize=12)
    axes[1].set_ylabel('Predicted Thrust (N)', fontsize=12)
    axes[1].set_title('Predicted vs Measured', fontsize=12, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.suptitle('Master Equation of Levitation Fit', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save:
        plt.savefig('master_equation_fit.png', dpi=150, bbox_inches='tight')
        print("Plot saved: master_equation_fit.png")
    
    plt.show()


def plot_comparison(data: Dict[str, np.ndarray], save: bool = True):
    """
    Plot comparison of models and data.
    
    Parameters:
    data (dict): Dictionary from generate_synthetic_data
    save (bool): Whether to save the plot
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Theta comparison
    axes[0, 0].scatter(data['B'], data['theta'], label='Noisy Data', alpha=0.5)
    axes[0, 0].plot(data['B'], data['theta_true'], 'r-', label='True Model', linewidth=2)
    axes[0, 0].set_xlabel('B (T)')
    axes[0, 0].set_ylabel('Θ_dilaton')
    axes[0, 0].set_title('Dilaton Enhancement')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Thrust comparison
    axes[0, 1].scatter(data['B'], data['thrust'], label='Noisy Data', alpha=0.5)
    axes[0, 1].plot(data['B'], data['thrust_true'], 'r-', label='True Model', linewidth=2)
    axes[0, 1].set_xlabel('B (T)')
    axes[0, 1].set_ylabel('Thrust (N)')
    axes[0, 1].set_title('Master Equation Thrust')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Theta scaling
    B_range = np.linspace(1, 100, 200)
    theta_simple = [theta_dilaton_simple(b, (1e-6, 20.0)) for b in B_range]
    theta_res = [theta_dilaton_resonance(b, (1e-6, 20.0, 0.1, 0.01)) for b in B_range]
    axes[1, 0].plot(B_range, theta_simple, label='Simple Model')
    axes[1, 0].plot(B_range, theta_res, label='Resonance Model')
    axes[1, 0].set_xlabel('B (T)')
    axes[1, 0].set_ylabel('Θ_dilaton')
    axes[1, 0].set_title('Model Comparison')
    axes[1, 0].set_yscale('log')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Supra-saturation effect
    B_sat_values = [2.1, 2.4, 2.85]  # Iron, Hiperco-50, Minnealloy
    labels = ['Iron (2.1 T)', 'Hiperco-50 (2.4 T)', 'Minnealloy (2.85 T)']
    for B_sat, label in zip(B_sat_values, labels):
        theta_sat = [theta_dilaton_saturation(b, (1e-6, 20.0, B_sat, 2.0)) for b in B_range]
        axes[1, 1].plot(B_range, theta_sat, label=label)
    axes[1, 1].set_xlabel('B (T)')
    axes[1, 1].set_ylabel('Θ_dilaton')
    axes[1, 1].set_title('Saturation Effect by Material')
    axes[1, 1].set_yscale('log')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.suptitle('RVG Unified Field Model Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save:
        plt.savefig('rvg_model_comparison.png', dpi=150, bbox_inches='tight')
        print("Plot saved: rvg_model_comparison.png")
    
    plt.show()


# =============================================================================
# Main Function
# =============================================================================

def main():
    print("=" * 70)
    print("RVG UNIFIED FIELD - EQUATION REFINEMENT SCRIPT")
    print("=" * 70)
    print("\nFramework: Refractive Vacuum Gravity (RVG) Unified Field")
    print("  - 95 GeV dilaton/radion resonance (CMS/ATLAS 3.1σ)")
    print("  - Disformal QED with trace anomaly coupling")
    print("  - Master Equation: F = ∫(Θ_dilaton(B)·∇B²)dV")
    print("-" * 70)
    
    # Try to load real data, fall back to synthetic
    use_synthetic = False
    
    # Load χ(μ) data
    try:
        t_data, chi_data, sigma = load_chi_data(DATA_FILE)
        print(f"\nLoaded χ data from {DATA_FILE}: {len(t_data)} points")
    except FileNotFoundError:
        print(f"\n{DATA_FILE} not found. Generating synthetic data...")
        use_synthetic = True
        t_data = DEFAULT_T_SPAN
        chi_data = np.exp(t_data / 2) * DEFAULT_CHI0 + np.random.normal(0, 1e-11, len(t_data))
        sigma = None
    
    # ==========================================================================
    # RG Flow Fitting
    # ==========================================================================
    
    print("\n" + "=" * 50)
    print("PART 1: RG FLOW FITTING FOR χ(μ)")
    print("=" * 50)
    
    # Fit Spin-0 model
    print("\n[1.1] Fitting Spin-0 Model...")
    initial_params_spin0 = [DEFAULT_CHI0, 1.0, 0.1]  # [chi0, g, λ]
    bounds_spin0 = ([1e-12, 0.1, 0.01], [1e-8, 10.0, 0.49])
    try:
        popt_spin0, pcov_spin0 = fit_rg_model(t_data, chi_data, beta_spin0, 
                                              initial_params_spin0, bounds_spin0, sigma)
        print(f"  Optimized (chi0, g, λ): {popt_spin0}")
        print(f"  Parameter uncertainties: {np.sqrt(np.diag(pcov_spin0))}")
        plot_rg_fit(t_data, chi_data, popt_spin0, 'Spin-0')
    except Exception as e:
        print(f"  Error fitting spin-0: {e}")
    
    # Fit RVG Dilaton model
    print("\n[1.2] Fitting RVG Dilaton Model...")
    initial_params_rvg = [DEFAULT_CHI0, 1e-8, 1e-10, 0.5]  # [chi0, α_d, χ_crit, g_tr]
    try:
        popt_rvg, pcov_rvg = fit_rg_model(t_data, chi_data, beta_rvg_dilaton,
                                          initial_params_rvg, sigma=sigma)
        print(f"  Optimized (chi0, α_d, χ_crit, g_tr): {popt_rvg}")
        plot_rg_fit(t_data, chi_data, popt_rvg, 'RVG-Dilaton')
    except Exception as e:
        print(f"  Error fitting RVG dilaton: {e}")
    
    # ==========================================================================
    # Dilaton Enhancement Fitting
    # ==========================================================================
    
    print("\n" + "=" * 50)
    print("PART 2: DILATON ENHANCEMENT Θ_dilaton(B) FITTING")
    print("=" * 50)
    
    # Generate or load theta data
    if use_synthetic:
        print("\nGenerating synthetic Θ_dilaton data...")
        synth_data = generate_synthetic_data(model='resonance', noise_level=0.1, n_points=50)
        B_theta = synth_data['B']
        theta_measured = synth_data['theta']
        print(f"  True parameters: {synth_data['true_params']}")
    else:
        try:
            B_theta, theta_measured, theta_sigma = load_theta_data(THETA_DATA_FILE)
            print(f"Loaded Θ data from {THETA_DATA_FILE}: {len(B_theta)} points")
        except FileNotFoundError:
            print(f"{THETA_DATA_FILE} not found. Using synthetic data...")
            synth_data = generate_synthetic_data(model='resonance', noise_level=0.1, n_points=50)
            B_theta = synth_data['B']
            theta_measured = synth_data['theta']
    
    # Fit simple model
    print("\n[2.1] Fitting Simple Θ_dilaton Model...")
    try:
        popt_theta_simple, pcov_theta_simple = fit_theta_dilaton(B_theta, theta_measured, 
                                                                  model='simple')
        print(f"  Optimized (θ_base, B_crit): {popt_theta_simple}")
        plot_theta_fit(B_theta, theta_measured, popt_theta_simple, 'simple')
    except Exception as e:
        print(f"  Error fitting simple model: {e}")
    
    # Fit resonance model
    print("\n[2.2] Fitting Resonance Θ_dilaton Model...")
    try:
        popt_theta_res, pcov_theta_res = fit_theta_dilaton(B_theta, theta_measured,
                                                           model='resonance')
        print(f"  Optimized (θ_base, B_crit, γ, ε): {popt_theta_res}")
        plot_theta_fit(B_theta, theta_measured, popt_theta_res, 'resonance')
    except Exception as e:
        print(f"  Error fitting resonance model: {e}")
    
    # ==========================================================================
    # Master Equation Fitting
    # ==========================================================================
    
    print("\n" + "=" * 50)
    print("PART 3: MASTER EQUATION OF LEVITATION FITTING")
    print("=" * 50)
    
    # Use synthetic thrust data
    if use_synthetic or not os.path.exists(THRUST_DATA_FILE):
        print("\nUsing synthetic thrust data...")
        B_thrust = synth_data['B']
        grad_B2_thrust = synth_data['grad_B2']
        thrust_measured = synth_data['thrust']
    else:
        B_thrust, grad_B2_thrust, thrust_measured, _ = load_thrust_data(THRUST_DATA_FILE)
    
    volume = 0.1  # m³
    
    print("\n[3.1] Fitting Master Equation Parameters...")
    try:
        popt_master, pcov_master = fit_master_equation(B_thrust, grad_B2_thrust, volume,
                                                       thrust_measured)
        print(f"  Optimized (θ_base, B_crit, η_align): {popt_master}")
        print(f"  Parameter uncertainties: {np.sqrt(np.diag(pcov_master))}")
        plot_master_equation_fit(B_thrust, thrust_measured, grad_B2_thrust, volume, popt_master)
    except Exception as e:
        print(f"  Error fitting Master Equation: {e}")
    
    # ==========================================================================
    # Model Comparison
    # ==========================================================================
    
    print("\n" + "=" * 50)
    print("PART 4: MODEL COMPARISON")
    print("=" * 50)
    
    print("\nGenerating model comparison plots...")
    plot_comparison(synth_data)
    
    # ==========================================================================
    # Summary
    # ==========================================================================
    
    print("\n" + "=" * 70)
    print("REFINEMENT COMPLETE")
    print("=" * 70)
    print("\nKey outputs:")
    print("  - rg_fit_*.png: RG flow fits for χ(μ)")
    print("  - theta_fit_*.png: Dilaton enhancement Θ_dilaton(B) fits")
    print("  - master_equation_fit.png: Master Equation thrust fit")
    print("  - rvg_model_comparison.png: Model comparison plots")
    
    print("\nTo use refined parameters in simulations:")
    print("  1. Update equations.py with fitted θ_base, B_crit values")
    print("  2. Update navigation.py DEFAULT_THETA_BASE and B_CRIT_EFFECTIVE")
    print("  3. For propulsion: F ∝ Θ_dilaton(B) ∇(B²) V η")
    
    print("\nExperimental validation requirements:")
    print("  - Measure thrust at varying B fields (5-90 T range)")
    print("  - Record ∇(B²) gradient values from MADA configuration")
    print("  - Verify supra-saturation regime (B_opposing >> B_sat)")
    print("  - Provide data in CSV format for fitting")
    
    print("\nReferences:")
    print("  - RVG Theory: https://dx.doi.org/10.2139/ssrn.5381654")
    print("  - MADA Patent: https://patents.google.com/patent/US5929732A/en")


if __name__ == "__main__":
    main()
