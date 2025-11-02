import numpy as np
from scipy.integrate import odeint
from scipy.optimize import curve_fit
import pandas as pd
import matplotlib.pyplot as plt
from typing import Callable, List, Tuple
import os
import sys

# Add parent directory to path for imports if needed
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
except NameError:
    # If __file__ not defined (e.g., in REPL), skip or set manually
    pass

# Constants and defaults
DEFAULT_CHI0 = 1e-10  # Initial χ at UV scale
DEFAULT_T_SPAN = np.linspace(0, -10, 100)  # ln μ from high (t=0) to low (negative t)
DATA_FILE = 'empirical_data.csv'  # Expected columns: 'ln_mu', 'chi', optionally 'error'

def beta_spin0(chi: float, params: Tuple[float, float]) -> float:
    """
    RG beta function for χ in spin-0 emergent gravity (EGDPP current version).
    β_χ = -4 χ + (g / 2π) (χ / (1 - 2λ))
    
    :param chi: Current value of χ
    :param params: (g, λ)
    :return: β_χ
    """
    g, lam = params
    return -4 * chi + (g / (2 * np.pi)) * (chi / (1 - 2 * lam))

def beta_spin2(chi: float, params: Tuple[float, float, float]) -> float:
    """
    RG beta function for χ in spin-2 emergent gravity (alternative/old version).
    β_χ = (4 + η_χ) χ + c g χ
    
    :param chi: Current value of χ
    :param params: (η_χ, c, g)
    :return: β_χ
    """
    eta, c, g = params
    return (4 + eta) * chi + c * g * chi

def beta_general(chi: float, params: Tuple[float, ...]) -> float:
    """
    General data-derived beta function, e.g., polynomial form β_χ = a χ + b χ² + ...
    Here, quadratic for demo: params = (a, b)
    
    :param chi: Current value of χ
    :param params: Coefficients (a, b) for β = a χ + b χ²
    :return: β_χ
    """
    a, b = params
    return a * chi + b * chi**2

def solve_rg_flow(beta_func: Callable, params: Tuple[float, ...], chi0: float, t: np.ndarray) -> np.ndarray:
    """
    Solve the RG flow ODE dχ/dt = β(χ) from t[0] (UV) to lower scales.
    
    :param beta_func: The beta function to use
    :param params: Parameters for beta_func
    :param chi0: Initial χ at t=0 (high scale)
    :param t: Array of ln μ values (decreasing for IR)
    :return: χ(t)
    """
    def ode(chi, t):
        return beta_func(chi, params)
    
    sol = odeint(ode, chi0, t)
    return sol[:, 0]

def model_func(t: np.ndarray, chi0: float, *param_args: float) -> np.ndarray:
    """
    Model for curve fitting: Solve RG flow with given beta and params.
    This is a wrapper to pass to curve_fit.
    
    :param t: ln μ data
    :param chi0: Initial χ (fit parameter)
    :param param_args: Parameters for beta_func
    :return: Predicted χ(t)
    """
    # Global beta_func must be set before calling
    global CURRENT_BETA_FUNC
    return solve_rg_flow(CURRENT_BETA_FUNC, param_args, chi0, t)

def fit_rg_model(t_data: np.ndarray, chi_data: np.ndarray, beta_func: Callable, initial_params: List[float], bounds: Tuple[List[float], List[float]] = None, sigma: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit the RG model to empirical data.
    
    :param t_data: ln μ values
    :param chi_data: χ values
    :param beta_func: The beta function to fit (sets global for model_func)
    :param initial_params: Initial guess [chi0, param1, param2, ...]
    :param bounds: Optional bounds for parameters
    :param sigma: Optional errors for weighted fit
    :return: Optimized parameters, covariance
    """
    global CURRENT_BETA_FUNC
    CURRENT_BETA_FUNC = beta_func
    
    # Fit
    popt, pcov = curve_fit(model_func, t_data, chi_data, p0=initial_params, bounds=bounds, sigma=sigma)
    
    return popt, pcov

def load_data(data_file: str) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Load and prepare data from CSV.
    
    :param data_file: Path to CSV
    :return: t_data, chi_data, sigma (None if no 'error' column)
    """
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Data file {data_file} not found. Please provide empirical_data.csv with columns 'ln_mu', 'chi'.")
    
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

def plot_fit(t_data: np.ndarray, chi_data: np.ndarray, popt: np.ndarray, beta_name: str):
    """
    Plot the fitted RG flow against data.
    
    :param t_data: ln μ
    :param chi_data: Measured χ
    :param popt: Optimized parameters [chi0, ...]
    :param beta_name: Name of the model (e.g., 'spin-0')
    """
    chi_pred = model_func(t_data, *popt)
    
    plt.figure(figsize=(8, 6))
    plt.scatter(t_data, chi_data, label='Empirical Data', color='red')
    plt.plot(t_data, chi_pred, label=f'Fitted {beta_name} Model', color='blue')
    plt.xlabel('ln μ (Energy Scale)')
    plt.ylabel('χ (Susceptibility)')
    plt.title(f'RG Flow Fit for {beta_name}')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'rg_fit_{beta_name.lower().replace("-", "_")}.png')
    plt.show()

def main():
    print("=" * 60)
    print("EGDPP RG EQUATION REFINEMENT SCRIPT")
    print("=" * 60)
    
    # Load data once
    try:
        t_data, chi_data, sigma = load_data(DATA_FILE)
    except FileNotFoundError as e:
        print(e)
        # Generate dummy data for demo if file missing
        print("Generating dummy data for demonstration...")
        t_data = DEFAULT_T_SPAN
        chi_data = np.exp(t_data / 2) * DEFAULT_CHI0 + np.random.normal(0, 1e-11, len(t_data))  # Dummy exponential decay
        sigma = None
    
    # Example usage for spin-0
    print("\nFitting Spin-0 Model...")
    initial_params_spin0 = [DEFAULT_CHI0, 1.0, 0.1]  # [chi0, g, λ]
    bounds_spin0 = ([1e-12, 0.1, 0.01], [1e-8, 10.0, 0.49])  # Avoid division by zero
    try:
        popt_spin0, pcov_spin0 = fit_rg_model(t_data, chi_data, beta_spin0, initial_params_spin0, bounds_spin0, sigma)
        print("Optimized Parameters (chi0, g, λ):", popt_spin0)
        print("Covariance:", pcov_spin0)
        plot_fit(t_data, chi_data, popt_spin0, 'Spin-0')
    except Exception as e:
        print(f"Error fitting spin-0: {e}")
    
    # Example usage for spin-2
    print("\nFitting Spin-2 Model...")
    initial_params_spin2 = [DEFAULT_CHI0, 0.0, 1.0, 1.0]  # [chi0, η_χ, c, g]
    bounds_spin2 = ([1e-12, -10, 0.1, 0.1], [1e-8, 10, 10, 10])
    try:
        popt_spin2, pcov_spin2 = fit_rg_model(t_data, chi_data, beta_spin2, initial_params_spin2, bounds_spin2, sigma)
        print("Optimized Parameters (chi0, η_χ, c, g):", popt_spin2)
        print("Covariance:", pcov_spin2)
        plot_fit(t_data, chi_data, popt_spin2, 'Spin-2')
    except Exception as e:
        print(f"Error fitting spin-2: {e}")
    
    # Example for data-derived (general quadratic)
    print("\nFitting General Data-Derived Model (Quadratic)...")
    initial_params_general = [DEFAULT_CHI0, -4.0, 0.0]  # [chi0, a, b]
    try:
        popt_general, pcov_general = fit_rg_model(t_data, chi_data, beta_general, initial_params_general, sigma=sigma)
        print("Optimized Parameters (chi0, a, b):", popt_general)
        print("Covariance:", pcov_general)
        plot_fit(t_data, chi_data, popt_general, 'General')
    except Exception as e:
        print(f"Error fitting general: {e}")
    
    print("\nRefinement complete. Plots saved as PNG files.")
    print("To use refined parameters in simulations, update equations.py accordingly.")
    print("For propulsion: Use fitted χ in force calculations, e.g., F ∝ χ B² ∇(h²) A ρ")
    print("Experimental data should include inferred χ from measured thrusts/forces at different energy scales (e.g., varying B or frequency).")

if __name__ == "__main__":
    main()
