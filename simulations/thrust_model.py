"""
simulations/thrust_model.py (Version 7 - RVG Unified Field Framework - CALIBRATED)

Extended thrust model simulation with RVG (Refractive Vacuum Gravity) Unified Field:
- Dilaton enhancement factor Θ_dilaton(B) for 95 GeV resonance
- Master Equation of Levitation for thrust calculations
- Vacuum refractive index gradients (∇K)
- Supra-saturation gap field modeling
- Single calculation with comprehensive validation
- Swarm simulation (multi-drone) with trajectory planning
- Benchmark against telemetry with HIL validation
- Real-time sensor monitoring with MADA convergence tracking
- Parametric sweeps and optimization
- CFD integration capabilities
- Raspberry Pi GPIO control for physical MADA units

CRITICAL: Implements RVG Unified Field framework from:
"Refractive Vacuum Gravity (RVG) Unified Field: Disformal QED, the 95 GeV Resonance,
and the Metric Engineering of Static Levitation" (Hofseth, 2025)

CALIBRATED: Parameters aligned with equations.py for consistent results.
- THETA_95_BASE = 1e-8 (calibrated for physically reasonable forces)
- B threshold = 20.0 T (where dilaton enhancement activates)

Key Physics:
- F_lift = ∫(Θ_dilaton(B)·∇B²)dV  [Master Equation of Levitation]
- K(r) = 1 + Θ_95·B²/B_crit²      [Refractive Index]
- f_vac = -B²/(2μ₀)·∇K            [Vacuum Force Density]
"""

import argparse
import numpy as np
import sys
import os
import time
import logging
import signal
from typing import Tuple, Optional, Dict, List, Any
from pathlib import Path

# Conditional imports with proper guards
try:
    import multiprocessing as mp
    MULTIPROCESSING_AVAILABLE = True
except ImportError:
    MULTIPROCESSING_AVAILABLE = False
    mp = None

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not available. Config file support disabled.")

try:
    import dask.array as da
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
    logging.warning("Dask not available. Large-scale parallel computation disabled.")

try:
    from scipy import optimize
    from scipy.optimize import minimize
    SCIPY_OPTIMIZE_AVAILABLE = True
except ImportError:
    SCIPY_OPTIMIZE_AVAILABLE = False
    logging.warning("scipy.optimize not available. Optimization disabled.")

try:
    import subprocess
    import tempfile
    import shutil
    CFD_AVAILABLE = True
except ImportError:
    CFD_AVAILABLE = False
    logging.warning("CFD integration tools not available.")

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("scikit-learn not available. ML surrogates disabled.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Optional imports with proper fallback
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
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    logging.warning("Open3D not available. CFD visualizations limited.")

# Hardware interfaces - create mock if not available
HARDWARE_AVAILABLE = False
try:
    from hardware.interfaces import MicrocontrollerPWMInterface, FlightControllerInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    logging.warning("Hardware interfaces not available. Real-time mode will use simulated data.")
    
    class MicrocontrollerPWMInterface:
        def __init__(self, port: str):
            raise ImportError("Hardware interface not available")
        def send_command(self, cmd: str) -> Optional[str]:
            return None
        def close(self) -> None:
            pass
    
    class FlightControllerInterface:
        def __init__(self):
            raise ImportError("Hardware interface not available")

# MADA GPIO Controller
try:
    from hardware.mada_gpio_controller import MADAGPIOController, integrate_with_mada_validation
    MADA_GPIO_AVAILABLE = True
except ImportError:
    MADA_GPIO_AVAILABLE = False
    logging.warning("MADA GPIO controller not available")

# Configure logging with proper namespace
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )


# =============================================================================
# Physical Constants (RVG Unified Field Framework)
# =============================================================================

# Fundamental constants
MU_0 = 4 * np.pi * 1e-7          # Vacuum permeability (H/m)
EPSILON_0 = 8.854187817e-12      # Vacuum permittivity (F/m)
C = 299792458.0                  # Speed of light (m/s)
HBAR = 1.054571817e-34           # Reduced Planck constant (J·s)
M_E = 9.1093837015e-31           # Electron mass (kg)
E_CHARGE = 1.602176634e-19       # Elementary charge (C)
ALPHA = 1/137.035999084          # Fine structure constant

# Derived QED constants
B_SCHWINGER = (M_E**2 * C**2) / (E_CHARGE * HBAR)  # Schwinger critical field ~4.414×10^9 T
SPEED_OF_SOUND = 343.0           # Speed of sound in air (m/s)
EPSILON = 1e-10                  # Numerical stability threshold

# =============================================================================
# RVG Unified Field Constants (CALIBRATED)
# =============================================================================

# CALIBRATED: Changed from 1e-4 to 1e-8 for physically reasonable forces
# Paper Table II states: "Θ_95 - To be measured"
# This value produces forces in the range of 100s to 10,000s of Newtons
# which is "macroscopic" as the paper intends, without being absurdly large
THETA_95_BASE = 1e-8             # Base dilaton enhancement (CALIBRATED)

# Dilaton resonance parameters
DILATON_MASS_GEV = 95.4          # 95 GeV resonance mass (CMS/ATLAS observation)

# Trace anomaly coupling for piecewise enhancement model
# Used in supra-threshold regime of dilaton_enhancement_factor()
TRACE_ANOMALY_COUPLING = 0.1     # Dilaton-trace anomaly coupling strength

# Threshold field where dilaton enhancement becomes significant
# Paper states: "no strict universal B_crit" - this is a threshold, not critical field
B_THRESHOLD_DEFAULT = 20.0       # Tesla (where nonlinear response activates)

# Geometry factors for gradient calculations (T/m)
# These represent achievable ∇B² for different MADA configurations
DEFAULT_GEOMETRY_FACTOR = 1e8    # Optimized Bushman geometry
MADA_SINGLE_GEOMETRY = 5e6       # Single-stage MADA array
MADA_NESTED_GEOMETRY = 2e7       # Nested MADA configuration
BUSHMAN_MAX_GEOMETRY = 1e8       # Optimized Bushman geometry


# =============================================================================
# Configuration Classes
# =============================================================================

class SimulationConfig:
    """Configuration class for all simulation parameters."""
    
    # Magnetic field parameters
    M1 = 100.0                    # Magnetic moment 1 (A·m²)
    M2 = 100.0                    # Magnetic moment 2 (A·m²)
    DISTANCE = 0.05               # Distance between magnets (m)
    K_MADA = 1.0                # MADA amplification factor (possibly up to 200-529x)
    
    # Coil parameters
    N_TURNS = 100                 # Number of coil turns
    BASE_CURRENT = 15.0           # Base current (A)
    
    # RVG/QED parameters
    CHI = 1e-10                   # Magnetic susceptibility
    G_COUPLING = 1.0              # Gauge coupling
    LAMBDA_PARAM = 0.1            # Running coupling parameter
    THETA_95 = THETA_95_BASE      # Dilaton enhancement coefficient (CALIBRATED)
    
    # Material saturation (for supra-saturation calculations)
    B_SAT_IRON = 2.1              # Iron saturation (T)
    B_SAT_MINNEALLOY = 2.85       # Minnealloy saturation (T)
    B_SAT_HIPERCO50 = 2.4         # Hiperco-50 saturation (T)
    
    # Geometric parameters
    GRAD_H2 = np.array([1.0, 0.0, 0.0])  # Default field gradient direction
    EFFECTIVE_VOLUME = 0.001      # Effective interaction volume (m³)
    RHO = 1000.0                  # Material density (kg/m³)
    
    # MADA parameters
    N_UNITS = 24                  # Number of MADA units
    ETA_ALIGN = 0.95              # Alignment efficiency
    THETA_THRUST = 0.0            # Thrust vector angle (rad)
    
    # Drone parameters
    MASS = 20000.0                # System mass (kg)
    
    # Electrical parameters
    RESISTANCE = 5.0              # Coil resistance (Ω)
    P_EDDY = 100.0                # Eddy current losses (W)
    P_SWITCHING = 50.0            # Switching losses (W)
    
    # Performance parameters
    VELOCITY = 1000.0             # Reference velocity (m/s)
    ENERGY = 500000.0 * 3600      # 500 kWh in Joules
    
    # Frequency parameters
    BASE_FREQUENCY = 50.0         # Base pulsing frequency (Hz)
    DEFAULT_FREQUENCY = 100.0     # Default operating frequency (Hz)
    
    # PyBullet simulation
    PHYSICS_STEP_RATE = 240       # Physics steps per second
    SWARM_ATTACK_PROBABILITY = 0.005


class MADAValidationConfig:
    """MADA convergence validation thresholds."""
    
    MIN_FIELD = 0.1               # Minimum field (T)
    MAX_FIELD = 100.0             # Maximum field (T)
    MIN_ALIGNMENT = 0.9           # Minimum cosine similarity
    MAX_ASYMMETRY = 0.15          # Maximum asymmetry ratio
    MIN_GRADIENT = 0.01           # Minimum gradient magnitude
    CONVERGENCE_THRESHOLD = 0.05  # 5% convergence threshold
    MAX_ITERATIONS = 100
    HISTORY_SIZE = 50
    MIN_SAMPLES = 10


class RVGConfig:
    """RVG Unified Field specific configuration."""
    
    # Dilaton parameters
    DILATON_MASS = DILATON_MASS_GEV * 1e9 * E_CHARGE / C**2  # Convert GeV to kg
    TRACE_COUPLING = TRACE_ANOMALY_COUPLING
    
    # Enhancement thresholds (CALIBRATED)
    B_THRESHOLD = B_THRESHOLD_DEFAULT  # 20.0 T
    B_THRESHOLD_LOW = 2.0         # Low field threshold (T) - 0.1 * B_THRESHOLD
    B_THRESHOLD_HIGH = 20.0       # High field threshold (T) - B_THRESHOLD
    
    # Gradient requirements for macroscopic effects
    MIN_GRAD_B2 = 1e6             # Minimum ∇B² for observable effects (T²/m)
    TARGET_GRAD_B2 = 1e10         # Target ∇B² for Bushman geometry (T²/m)
    
    # Supra-saturation multiplier
    SUPRA_SAT_FACTOR = 1.5        # B_opposing > B_sat × this factor


# =============================================================================
# Custom Exceptions
# =============================================================================

class MADAValidationError(Exception):
    """Raised when MADA configuration fails validation."""
    pass


class RVGCalculationError(Exception):
    """Raised when RVG calculations fail."""
    pass


# =============================================================================
# RVG Unified Field Equations (CALIBRATED)
# =============================================================================

def dilaton_enhancement_factor(B: float, B_threshold: float = None) -> float:
    """
    Calculate the dilaton enhancement factor Θ_dilaton(B).
    
    CALIBRATED: Aligned with equations.py for consistent results.
    
    The 95 GeV dilaton/radion resonance couples to the trace anomaly,
    providing non-linear enhancement of vacuum polarization effects
    at high magnetic field intensities.
    
    Args:
        B: Local magnetic field strength (T)
        B_threshold: Threshold field for significant enhancement (T)
                     Default: B_THRESHOLD_DEFAULT (20.0 T)
    
    Returns:
        Θ_dilaton: Enhancement factor (dimensionless)
    
    Theory:
        - Weak at low B (approaches Euler-Heisenberg limit)
        - Grows non-linearly with intensity due to 95 GeV resonance pumping
        - Based on disformal gravity coupling to scalar field gradient
        
        Piecewise behavior:
        - Sub-threshold (x < 0.1): Euler-Heisenberg regime, minimal enhancement
        - Transition (0.1 ≤ x < 1.0): Growing enhancement
        - Supra-threshold (x ≥ 1.0): Strong nonlinear enhancement (resonant pumping)
    
    Reference:
        Hofseth (2025), Sections 2-3: 95 GeV resonance + trace anomaly
    """
    # Use runtime default to match equations.py behavior
    if B_threshold is None:
        B_threshold = B_THRESHOLD_DEFAULT
    
    if B < EPSILON:
        return THETA_95_BASE
    
    # Non-linear enhancement model based on trace anomaly coupling
    # Enhancement grows as B² relative to threshold
    x = B / B_threshold
    
    # Piecewise model matching equations.py
    if x < 0.1:
        # Sub-threshold: minimal enhancement (Euler-Heisenberg regime)
        theta = THETA_95_BASE * (1 + 0.1 * x**2)
    elif x < 1.0:
        # Transition region: growing enhancement
        theta = THETA_95_BASE * (1 + x**2)
    else:
        # Supra-threshold: strong non-linear enhancement
        # Models resonant pumping of dilaton field
        theta = THETA_95_BASE * (1 + x**2 + TRACE_ANOMALY_COUPLING * x**3)
    
    return theta


def vacuum_refractive_index(B: float, theta_dilaton: Optional[float] = None) -> float:
    """
    Calculate the vacuum refractive index K(r) in the RVG framework.
    
    K(r) = 1 + χ_vac(B) ≈ 1 + Θ_95 · B²/B_crit²
    
    Args:
        B: Local magnetic field strength (T)
        theta_dilaton: Pre-computed dilaton enhancement (optional)
    
    Returns:
        K: Vacuum refractive index (dimensionless, K > 1)
    
    Theory:
        Strong magnetic fields create virtual electron-positron pairs,
        modifying the vacuum's electromagnetic properties. The dilaton
        resonance amplifies this effect beyond standard QED predictions.
    """
    if theta_dilaton is None:
        theta_dilaton = dilaton_enhancement_factor(B)
    
    # Ratio to Schwinger critical field
    b_ratio = B / B_SCHWINGER
    
    # Vacuum susceptibility with dilaton enhancement
    chi_vac = theta_dilaton * b_ratio**2
    
    # Refractive index
    K = 1.0 + chi_vac
    
    return K


def gradient_refractive_index(B: float, grad_B2: np.ndarray, 
                               theta_dilaton: Optional[float] = None) -> np.ndarray:
    """
    Calculate the gradient of vacuum refractive index ∇K.
    
    ∇K ∝ Θ_dilaton(B) · ∇(B²)
    
    Args:
        B: Local magnetic field strength (T)
        grad_B2: Gradient of B² (T²/m), 3D vector
        theta_dilaton: Pre-computed dilaton enhancement (optional)
    
    Returns:
        grad_K: Gradient of refractive index (1/m), 3D vector
    
    Theory:
        The spatial variation of K creates an effective gravitational
        potential for photons (Gordon optical metric), which translates
        to mechanical force on the field-generating apparatus.
    """
    grad_B2 = np.asarray(grad_B2, dtype=float)
    
    if theta_dilaton is None:
        theta_dilaton = dilaton_enhancement_factor(B)
    
    # Gradient coefficient
    coeff = theta_dilaton / (B_SCHWINGER**2)
    
    # ∇K = Θ · ∇(B²) / B_crit²
    grad_K = coeff * grad_B2
    
    return grad_K


def vacuum_force_density(B: float, grad_K: np.ndarray) -> np.ndarray:
    """
    Calculate local vacuum force density in magnetic-dominant regime.
    
    f_vac = -B²/(2μ₀) · ∇K
    
    Args:
        B: Local magnetic field strength (T)
        grad_K: Gradient of refractive index (1/m)
    
    Returns:
        f_vac: Force density (N/m³), 3D vector
    
    Theory:
        The vacuum force arises from the gradient of electromagnetic
        energy density modulated by the spatially varying refractive index.
        Negative sign indicates force opposite to ∇K direction.
    """
    grad_K = np.asarray(grad_K, dtype=float)
    
    # Magnetic energy density coefficient
    B2_over_2mu0 = B**2 / (2 * MU_0)
    
    # Force density (negative gradient)
    f_vac = -B2_over_2mu0 * grad_K
    
    return f_vac


def master_equation_lift(B_total: float, grad_B2: np.ndarray, 
                         volume: float, theta_dilaton: Optional[float] = None) -> np.ndarray:
    """
    Master Equation of Levitation - Integrated thrust calculation.
    
    F_lift = ∫_V (1/(2μ₀) · Θ_dilaton(B) · ∇(B·B)) dV
    
    Args:
        B_total: Total magnetic field in interaction region (T)
        grad_B2: Gradient of B² in interaction region (T²/m)
        volume: Effective interaction volume (m³)
        theta_dilaton: Pre-computed dilaton enhancement (optional)
    
    Returns:
        F_lift: Lift/thrust force vector (N)
    
    Theory:
        This is the fundamental propulsion equation in the RVG framework.
        - ∇(B·B) = ∇B²: Gradient of magnetic energy density
        - Θ_dilaton(B): Non-linear enhancement from 95 GeV resonance
        - Force scales as T²/m; high localized B essential
        
    Reference:
        Hofseth (2025), Section 4: Force Density → Master Equation
    """
    grad_B2 = np.asarray(grad_B2, dtype=float)
    
    if theta_dilaton is None:
        theta_dilaton = dilaton_enhancement_factor(B_total)
    
    # Coefficient: 1/(2μ₀)
    coeff = 1.0 / (2 * MU_0)
    
    # Integrated force over volume
    # F = (1/2μ₀) · Θ · ∇B² · V
    F_lift = coeff * theta_dilaton * grad_B2 * volume
    
    return F_lift


def opposing_field(m1: float, m2: float, d: float, k: float = 200.0) -> float:
    """
    Calculate opposing magnetic field with MADA amplification.
    
    B_gap ≈ (μ₀ · m₁ · m₂) / (2π · d²) · k
    
    Args:
        m1: Magnetic moment of first magnet (A·m²)
        m2: Magnetic moment of second magnet (A·m²)
        d: Distance between magnets (m)
        k: MADA amplification factor (default 200.0)
           - Standard single magnet: k = 1
           - MADA array (field strength): k ≈ 200
           - MADA array (force): k ≈ 529
    
    Returns:
        B_gap: Opposing field in gap region (T)
    
    Theory:
        MADA (Magnetic Amplification and Direction Apparatus) from
        U.S. Patent 5,929,732 achieves 200-500x effective amplification
        through frustration and focusing effects in nested configurations.
        
    Note:
        For supra-saturation effects, B_gap should exceed material B_sat
        by factor of 1.5x or more.
    """
    if d <= 0:
        raise ValueError("Distance must be positive")
    
    # Base dipole-dipole interaction field
    B_base = (MU_0 * m1 * m2) / (2 * np.pi * d**2)
    
    # Apply MADA amplification
    B_gap = B_base * k
    
    return B_gap


def pulsed_enhancement(n_turns: int, current: float, 
                       duty_cycle: float = 0.5) -> float:
    """
    Calculate pulsed magnetic field enhancement.
    
    ΔB = μ₀ · n · I · η_duty
    
    Args:
        n_turns: Number of coil turns
        current: Peak current (A)
        duty_cycle: Duty cycle (0-1), default 0.5
    
    Returns:
        delta_B: Pulsed field contribution (T)
    
    Theory:
        Pulsing at 50-100 Hz (up to 1 kHz bursts) with variable duty
        cycle (20-80%) boosts efficiency 20-50% and aids radar evasion.
    """
    if n_turns <= 0:
        raise ValueError("Number of turns must be positive")
    if duty_cycle <= 0 or duty_cycle > 1:
        raise ValueError("Duty cycle must be in (0, 1]")
    
    # Effective current accounting for duty cycle
    I_eff = current * np.sqrt(duty_cycle)  # RMS equivalent
    
    # Solenoid approximation for field enhancement
    delta_B = MU_0 * n_turns * I_eff
    
    return delta_B


def gradient_B_squared(B: float, geometry_factor: float = None) -> np.ndarray:
    """
    Estimate gradient of B² for thrust calculations.
    
    CALIBRATED: Default geometry factor aligned with equations.py
    
    Args:
        B: Local magnetic field (T)
        geometry_factor: Geometry-dependent scaling (T/m equivalent)
            - DEFAULT_GEOMETRY_FACTOR (1e6): Simple opposing magnets
            - MADA_SINGLE_GEOMETRY (5e6): Single-stage MADA
            - MADA_NESTED_GEOMETRY (2e7): Nested MADA
            - BUSHMAN_MAX_GEOMETRY (1e8): Optimized Bushman geometry
    
    Returns:
        grad_B2: Gradient of B² (T²/m), 3D vector
    
    Theory:
        ∇B² is maximized in Bushman opposing-pole configurations
        where flux converges to a small gap region. Nested MADA
        can achieve gradients exceeding 10⁸ T²/m in optimized designs.
    """
    if geometry_factor is None:
        geometry_factor = DEFAULT_GEOMETRY_FACTOR
    
    # B² gradient scales with 2B·∇B
    # For opposing geometry, gradient points away from convergence
    grad_B2_magnitude = 2 * B * geometry_factor
    
    # Default: thrust direction along x-axis
    grad_B2 = np.array([grad_B2_magnitude, 0.0, 0.0])
    
    return grad_B2


def total_thrust(F_lift: np.ndarray, n_units: int, 
                 eta_align: float, theta: float) -> float:
    """
    Calculate total system thrust from MADA array.
    
    F_net = |F_lift| · N · η_align · cos(θ)
    
    Args:
        F_lift: Lift force per unit (N), 3D vector
        n_units: Number of MADA units
        eta_align: Alignment efficiency (0-1)
        theta: Thrust vector angle (rad)
    
    Returns:
        T: Total thrust (N)
    """
    F_mag = np.linalg.norm(F_lift)
    T = F_mag * n_units * eta_align * np.cos(theta)
    return max(0.0, T)  # Thrust cannot be negative


def acceleration(thrust: float, mass: float) -> float:
    """
    Calculate acceleration from thrust.
    
    a = F/m
    
    Args:
        thrust: Total thrust (N)
        mass: System mass (kg)
    
    Returns:
        a: Acceleration (m/s²)
    """
    if mass <= 0:
        raise ValueError("Mass must be positive")
    return thrust / mass


def power_consumption(current: float, resistance: float, 
                      p_eddy: float = 100.0, p_switching: float = 50.0) -> float:
    """
    Calculate total electrical power draw.
    
    P = I²R + P_eddy + P_switching
    
    Args:
        current: Operating current (A)
        resistance: Coil resistance (Ω)
        p_eddy: Eddy current losses (W)
        p_switching: Switching losses (W)
    
    Returns:
        P: Total power (W)
    """
    P_ohmic = current**2 * resistance
    return P_ohmic + p_eddy + p_switching


def efficiency(thrust: float, velocity: float, power: float) -> float:
    """
    Calculate overall propulsion efficiency.
    
    η = (F · v / P) × 100%
    
    Args:
        thrust: Total thrust (N)
        velocity: Operating velocity (m/s)
        power: Power consumption (W)
    
    Returns:
        eta: Efficiency (%)
    """
    if power <= 0:
        return 0.0
    return (thrust * velocity / power) * 100.0


def range_calc(velocity: float, energy: float, power: float) -> float:
    """
    Calculate endurance range.
    
    R = v · t_op = v · E/P
    
    Args:
        velocity: Cruising velocity (m/s)
        energy: Stored energy (J)
        power: Power consumption (W)
    
    Returns:
        R: Range (m)
    """
    if power <= 0:
        return float('inf')
    t_op = energy / power
    return velocity * t_op


def check_supra_saturation(B_opposing: float, B_sat: float, 
                           factor: float = 1.5) -> Tuple[bool, str]:
    """
    Check if operating in supra-saturation regime.
    
    Supra-saturation (B_opposing >> B_sat) is required for macroscopic
    vacuum effects in the RVG framework.
    
    Args:
        B_opposing: Opposing field strength (T)
        B_sat: Material saturation field (T)
        factor: Required overdrive factor (default 1.5)
    
    Returns:
        (is_supra, message): Tuple of status and description
    """
    ratio = B_opposing / B_sat if B_sat > 0 else float('inf')
    
    if ratio >= factor:
        return True, f"SUPRA-SATURATION: B/B_sat = {ratio:.2f} ≥ {factor}"
    else:
        return False, f"SUB-SATURATION: B/B_sat = {ratio:.2f} < {factor} (insufficient)"


def non_ballistic_trajectory(start: np.ndarray, end: np.ndarray, 
                             num_points: int = 100) -> np.ndarray:
    """
    Generate non-ballistic trajectory for stealth operations.
    
    Uses sinusoidal deviation from straight path to evade
    ballistic tracking algorithms.
    
    Args:
        start: Starting position [x, y, z] (m)
        end: Target position [x, y, z] (m)
        num_points: Number of trajectory points
    
    Returns:
        trajectory: Array of shape (num_points, 3)
    """
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    
    t = np.linspace(0, 1, num_points)
    
    # Base linear interpolation
    trajectory = np.outer(1 - t, start) + np.outer(t, end)
    
    # Add non-ballistic deviations
    deviation_amplitude = np.linalg.norm(end - start) * 0.1
    
    # Perpendicular deviation vectors
    direction = end - start
    norm_dir = np.linalg.norm(direction)
    if norm_dir > EPSILON:
        direction = direction / norm_dir
        
        # Find perpendicular vectors
        if abs(direction[0]) < 0.9:
            perp1 = np.cross(direction, np.array([1, 0, 0]))
        else:
            perp1 = np.cross(direction, np.array([0, 1, 0]))
        perp1 = perp1 / np.linalg.norm(perp1)
        perp2 = np.cross(direction, perp1)
        
        # Sinusoidal deviations
        dev1 = deviation_amplitude * np.sin(2 * np.pi * t * 3)
        dev2 = deviation_amplitude * np.sin(2 * np.pi * t * 2 + np.pi/4)
        
        trajectory += np.outer(dev1, perp1) + np.outer(dev2, perp2)
    
    return trajectory


def radar_evasion_probability(trajectory: np.ndarray, radar_pos: np.ndarray,
                               rcs: float = 0.01) -> float:
    """
    Calculate radar evasion probability.
    
    Args:
        trajectory: Flight path (N x 3)
        radar_pos: Radar position [x, y, z]
        rcs: Radar cross-section (m²)
    
    Returns:
        p_evade: Evasion probability (0-1)
    """
    radar_pos = np.asarray(radar_pos, dtype=float)
    
    # Calculate distances to radar
    distances = np.linalg.norm(trajectory - radar_pos, axis=1)
    min_distance = np.min(distances)
    
    # Simple evasion model based on RCS and distance
    # Lower RCS and higher distance = better evasion
    detection_range = 1000 * np.sqrt(rcs)  # Approximate detection range
    
    if min_distance > detection_range:
        p_evade = 0.95
    else:
        p_evade = 0.5 * (min_distance / detection_range)**2
    
    return np.clip(p_evade, 0.0, 1.0)
                                   

def calculate_mada_B(magnet_Bs: list[float], multiple_per_position: bool = False) -> float:
    """
    Calculate effective B for a MADA unit.
    
    Args:
        magnet_Bs: List of B values for 5 magnets (T).
        multiple_per_position: If True, apply 90% factor for >1 magnet per position.
    
    Returns:
        Effective B value (T).
    """
    if len(magnet_Bs) != 5:
        raise ValueError("Exactly 5 magnet B values required.")
    
    total_B = sum(magnet_Bs)
    
    if multiple_per_position:
        return 0.9 * total_B  # 90% sum if multiple per position
    else:
        return total_B  # Simple sum otherwise


# =============================================================================
# MADA Convergence Validator
# =============================================================================

class MADAConvergenceValidator:
    """
    Validates MADA (Magnetic Array Diamagnetic Amplifier) convergence.
    
    Critical checks:
    1. Field magnitude within operational range
    2. Field vector alignment across units
    3. Symmetry and uniformity validation
    4. Gradient consistency for RVG effects
    5. Convergence stability over time
    6. Supra-saturation verification
    """
    
    def __init__(self, 
                 tolerance: float = MADAValidationConfig.CONVERGENCE_THRESHOLD,
                 max_iterations: int = MADAValidationConfig.MAX_ITERATIONS,
                 b_sat: float = SimulationConfig.B_SAT_MINNEALLOY):
        """Initialize MADA validator with material parameters."""
        if tolerance <= 0 or tolerance >= 1:
            raise ValueError("Tolerance must be between 0 and 1")
        if max_iterations <= 0:
            raise ValueError("Max iterations must be positive")
        
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.b_sat = b_sat
        self.history: List[float] = []
        self.convergence_achieved = False
        
    def validate_field_magnitude(self, B_total: float) -> Tuple[bool, str]:
        """Validate that field magnitude is within operational range."""
        if B_total < MADAValidationConfig.MIN_FIELD:
            return False, f"Field too weak: {B_total:.4f}T < {MADAValidationConfig.MIN_FIELD}T"
        if B_total > MADAValidationConfig.MAX_FIELD:
            return False, f"Field too strong: {B_total:.4f}T > {MADAValidationConfig.MAX_FIELD}T"
        return True, f"Field magnitude OK: {B_total:.4f}T"
    
    def validate_field_vectors(self, field_vectors: List[np.ndarray]) -> Tuple[bool, str]:
        """Validate field vector alignment across MADA units."""
        if len(field_vectors) < 2:
            return True, "Single unit - alignment N/A"
        
        normalized = []
        for v in field_vectors:
            norm = np.linalg.norm(v)
            if norm > EPSILON:
                normalized.append(v / norm)
            else:
                return False, "Zero-magnitude field vector detected"
        
        alignments = []
        for i in range(len(normalized)):
            for j in range(i+1, len(normalized)):
                dot_prod = np.dot(normalized[i], normalized[j])
                alignments.append(dot_prod)
        
        if not alignments:
            return True, "Insufficient vectors for alignment check"
        
        min_alignment = min(alignments)
        
        if min_alignment < MADAValidationConfig.MIN_ALIGNMENT:
            return False, f"Poor field alignment: {min_alignment:.4f} < {MADAValidationConfig.MIN_ALIGNMENT}"
        
        return True, f"Field alignment OK: {min_alignment:.4f}"
    
    def validate_symmetry(self, field_vectors: List[np.ndarray]) -> Tuple[bool, str]:
        """Validate field symmetry across MADA array."""
        if len(field_vectors) < 4:
            return True, "Insufficient units for symmetry check"
        
        magnitudes = [np.linalg.norm(v) for v in field_vectors]
        mean_mag = np.mean(magnitudes)
        
        if mean_mag < EPSILON:
            return False, "Zero mean field magnitude"
        
        std_mag = np.std(magnitudes)
        asymmetry = std_mag / mean_mag
        
        if asymmetry > MADAValidationConfig.MAX_ASYMMETRY:
            return False, f"High asymmetry: {asymmetry:.4f} > {MADAValidationConfig.MAX_ASYMMETRY}"
        
        return True, f"Symmetry OK: asymmetry={asymmetry:.4f}"
    
    def validate_gradient(self, grad_B2: np.ndarray) -> Tuple[bool, str]:
        """Validate field gradient magnitude for RVG effects."""
        grad_B2 = np.asarray(grad_B2, dtype=float)
        grad_mag = np.linalg.norm(grad_B2)
        
        if grad_mag < RVGConfig.MIN_GRAD_B2:
            return False, f"∇B² too small: {grad_mag:.2e} < {RVGConfig.MIN_GRAD_B2:.2e} T²/m"
        
        if grad_mag >= RVGConfig.TARGET_GRAD_B2:
            return True, f"∇B² OPTIMAL: {grad_mag:.2e} T²/m (Bushman-class)"
        
        return True, f"∇B² acceptable: {grad_mag:.2e} T²/m"
    
    def validate_supra_saturation(self, B_total: float) -> Tuple[bool, str]:
        """Validate supra-saturation condition for macroscopic effects."""
        is_supra, msg = check_supra_saturation(
            B_total, self.b_sat, RVGConfig.SUPRA_SAT_FACTOR
        )
        return is_supra, msg
    
    def check_convergence(self, current_thrust: float) -> Tuple[bool, str]:
        """Check if thrust has converged to a stable value."""
        self.history.append(current_thrust)
        
        if len(self.history) < MADAValidationConfig.MIN_SAMPLES:
            return False, f"Collecting data: {len(self.history)}/{MADAValidationConfig.MIN_SAMPLES}"
        
        if len(self.history) > MADAValidationConfig.HISTORY_SIZE:
            self.history = self.history[-MADAValidationConfig.HISTORY_SIZE:]
        
        recent = self.history[-MADAValidationConfig.MIN_SAMPLES:]
        mean_thrust = np.mean(recent)
        std_thrust = np.std(recent)
        
        if abs(mean_thrust) < EPSILON:
            return False, "Zero thrust - configuration error"
        
        relative_std = std_thrust / abs(mean_thrust)
        
        if relative_std < self.tolerance:
            self.convergence_achieved = True
            return True, f"CONVERGED: σ/μ = {relative_std:.4f}"
        
        if len(self.history) >= self.max_iterations:
            return False, f"Failed to converge after {self.max_iterations} iterations"
        
        return False, f"Converging: σ/μ = {relative_std:.4f} (target < {self.tolerance})"
    
    def full_validation(self, B_total: float, field_vectors: List[np.ndarray],
                       grad_B2: np.ndarray, current_thrust: float) -> Dict[str, Any]:
        """Perform complete MADA validation suite with RVG checks."""
        results: Dict[str, Any] = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        # 1. Field magnitude check
        mag_valid, mag_msg = self.validate_field_magnitude(B_total)
        results['checks']['magnitude'] = {'valid': mag_valid, 'message': mag_msg}
        if not mag_valid:
            results['valid'] = False
            results['errors'].append(mag_msg)
        
        # 2. Field vector alignment check
        align_valid, align_msg = self.validate_field_vectors(field_vectors)
        results['checks']['alignment'] = {'valid': align_valid, 'message': align_msg}
        if not align_valid:
            results['valid'] = False
            results['errors'].append(align_msg)
        
        # 3. Symmetry check
        sym_valid, sym_msg = self.validate_symmetry(field_vectors)
        results['checks']['symmetry'] = {'valid': sym_valid, 'message': sym_msg}
        if not sym_valid:
            results['warnings'].append(sym_msg)
        
        # 4. Gradient check (RVG-specific)
        grad_valid, grad_msg = self.validate_gradient(grad_B2)
        results['checks']['gradient'] = {'valid': grad_valid, 'message': grad_msg}
        if not grad_valid:
            results['valid'] = False
            results['errors'].append(grad_msg)
        
        # 5. Supra-saturation check (RVG-specific)
        supra_valid, supra_msg = self.validate_supra_saturation(B_total)
        results['checks']['supra_saturation'] = {'valid': supra_valid, 'message': supra_msg}
        if not supra_valid:
            results['warnings'].append(supra_msg)
        
        # 6. Convergence check
        conv_valid, conv_msg = self.check_convergence(current_thrust)
        results['checks']['convergence'] = {'valid': conv_valid, 'message': conv_msg}
        results['converged'] = self.convergence_achieved
        
        # 7. Dilaton enhancement info
        theta = dilaton_enhancement_factor(B_total)
        results['checks']['dilaton'] = {
            'valid': True,
            'message': f"Θ_dilaton = {theta:.2e} at B = {B_total:.2f}T"
        }
        
        return results
    
    def reset(self) -> None:
        """Reset validator state."""
        self.history = []
        self.convergence_achieved = False


# =============================================================================
# Utility Functions
# =============================================================================

def simulate_hall_sensor_readings(n_units: int, B_total: float, 
                                  noise_level: float = 0.02) -> List[np.ndarray]:
    """
    Simulate Hall sensor readings for each MADA unit.
    
    Args:
        n_units: Number of MADA units
        B_total: Total magnetic field strength (T)
        noise_level: Sensor noise as fraction of signal
    
    Returns:
        List of 3D field vectors, one per unit
    """
    if n_units <= 0:
        raise ValueError("Number of units must be positive")
    if B_total < 0:
        raise ValueError("Magnetic field must be non-negative")
    if noise_level < 0:
        raise ValueError("Noise level must be non-negative")
    
    field_vectors = []
    base_direction = np.array([1.0, 0.0, 0.0])
    
    for i in range(n_units):
        misalignment = np.random.normal(0, 0.05, 3)
        direction = base_direction + misalignment
        direction_norm = np.linalg.norm(direction)
        
        if direction_norm > EPSILON:
            direction = direction / direction_norm
        else:
            direction = base_direction
        
        magnitude = B_total * (1.0 + np.random.normal(0, 0.1))
        magnitude = max(0, magnitude)
        
        noise = np.random.normal(0, noise_level * magnitude, 3)
        vector = direction * magnitude + noise
        field_vectors.append(vector)
    
    return field_vectors


def load_config_yaml(config_file: str) -> argparse.Namespace:
    """Load configuration from YAML file."""
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML required. Install with: pip install pyyaml")
    
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return argparse.Namespace(**config)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")


def handle_interrupt(signum: int, frame: Any) -> None:
    """Signal handler for graceful shutdown."""
    logger.info("\nSimulation interrupted. Cleaning up...")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_interrupt)


# =============================================================================
# Core Calculation Functions (RVG Framework - CALIBRATED)
# =============================================================================

def calculate_thrust_params_rvg(
    args: argparse.Namespace,
    B_opposing: Optional[float] = None,
    frequency: Optional[float] = None,
    geometry_factor: float = None,
    verbose: bool = False,
    validate_mada: bool = False,
    validator: Optional[MADAConvergenceValidator] = None
) -> Tuple[float, float, float, float, float, float, Dict[str, Any]]:
    """
    Core thrust calculation using RVG Unified Field framework.
    
    CALIBRATED: Uses calibrated parameters for physically reasonable forces.
    
    Implements Master Equation of Levitation:
    F_lift = ∫(Θ_dilaton(B)·∇B²)dV
    
    Args:
        args: Argument namespace with simulation parameters
        B_opposing: Opposing magnetic field strength (T), optional
        frequency: Pulsing frequency (Hz), optional
        geometry_factor: Gradient geometry factor (T/m), default DEFAULT_GEOMETRY_FACTOR
        verbose: Enable verbose output
        validate_mada: Enable MADA convergence validation
        validator: Validator instance for convergence tracking
    
    Returns:
        Tuple of (thrust, acceleration, power, efficiency, range, B_total, rvg_data)
    
    Raises:
        MADAValidationError: If MADA validation fails critically
        RVGCalculationError: If RVG calculations fail
    """
    if geometry_factor is None:
        geometry_factor = DEFAULT_GEOMETRY_FACTOR
    
    frequency = frequency if frequency is not None else args.frequency
    B = B_opposing if B_opposing is not None else args.b_opposing
    
    # Calculate opposing field if not provided
    if B is None:
        B = opposing_field(args.m1, args.m2, args.distance, SimulationConfig.K_MADA)
    
    # Scale current based on frequency
    scaled_I = args.current * (frequency / SimulationConfig.BASE_FREQUENCY)
    
    # Calculate pulsed enhancement
    delta_B = pulsed_enhancement(SimulationConfig.N_TURNS, scaled_I)
    B_total = B + delta_B
    
    # RVG calculations (using calibrated parameters)
    theta_dilaton = dilaton_enhancement_factor(B_total)
    K = vacuum_refractive_index(B_total, theta_dilaton)
    grad_B2 = gradient_B_squared(B_total, geometry_factor)
    grad_K = gradient_refractive_index(B_total, grad_B2, theta_dilaton)
    
    # Force calculations
    f_vac = vacuum_force_density(B_total, grad_K)
    F_lift = master_equation_lift(
        B_total, grad_B2, SimulationConfig.EFFECTIVE_VOLUME, theta_dilaton
    )
    
    # Total thrust from MADA array
    T = total_thrust(F_lift, args.n_units, SimulationConfig.ETA_ALIGN, 
                     SimulationConfig.THETA_THRUST)
    
    # Acceleration
    a = acceleration(T, args.mass)
    
    # Power and efficiency
    P = power_consumption(scaled_I, SimulationConfig.RESISTANCE,
                          SimulationConfig.P_EDDY, SimulationConfig.P_SWITCHING)
    eta_perc = efficiency(T, SimulationConfig.VELOCITY, P)
    R = range_calc(SimulationConfig.VELOCITY, SimulationConfig.ENERGY, P)
    
    # Collect RVG-specific data
    rvg_data = {
        'theta_dilaton': theta_dilaton,
        'K': K,
        'grad_B2': grad_B2,
        'grad_K': grad_K,
        'f_vac': f_vac,
        'F_lift': F_lift,
        'scaled_current': scaled_I,
        'delta_B': delta_B,
        'geometry_factor': geometry_factor
    }
    
    # MADA validation if enabled
    if validate_mada:
        field_vectors = simulate_hall_sensor_readings(args.n_units, B_total)
        val = validator if validator is not None else MADAConvergenceValidator()
        
        validation_result = val.full_validation(
            B_total, field_vectors, grad_B2, T
        )
        
        rvg_data['validation'] = validation_result
        
        if not validation_result['valid']:
            error_msg = "; ".join(validation_result['errors'])
            logger.error(f"MADA VALIDATION FAILED: {error_msg}")
            raise MADAValidationError(f"MADA configuration invalid: {error_msg}")
        
        if verbose:
            for check_name, check_result in validation_result['checks'].items():
                status = "✓" if check_result['valid'] else "✗"
                logger.info(f"  {status} {check_name}: {check_result['message']}")
    
    if verbose:
        logger.info(f"Thrust: {T:.2f}N, Accel: {a:.2f}m/s², Power: {P:.2f}W")
        logger.info(f"Θ_dilaton: {theta_dilaton:.2e}, K-1: {K-1:.2e}")
    
    return T, a, P, eta_perc, R, B_total, rvg_data


def compute_lift_drag_ratio() -> float:
    """Compute lift-to-drag ratio (placeholder for CFD integration)."""
    return 15.0


# =============================================================================
# Structural and Stealth Functions
# =============================================================================

def fea_structural_check(accel: float, mass: float = SimulationConfig.MASS, 
                         safety_factor: float = 1.5) -> bool:
    """
    Simple FEA hook: Check if structure can withstand acceleration.
    
    Args:
        accel: Acceleration (m/s²)
        mass: Mass (kg)
        safety_factor: Safety factor for design
    
    Returns:
        True if structure is safe
    """
    if accel < 0 or mass <= 0 or safety_factor < 1:
        return False
    
    force = mass * accel
    cross_section_area = 0.01  # 0.01 m² cross-section
    stress = force / cross_section_area
    yield_strength = 270e6 / safety_factor  # Aluminum with safety factor
    
    return stress < yield_strength


def stealth_ops_check(traj: np.ndarray, radar_pos: np.ndarray, 
                      rcs: float = 0.01) -> float:
    """Check radar evasion for stealth ops."""
    return radar_evasion_probability(traj, radar_pos, rcs)


def hil_validation(sim_thrust: float, bench_thrust: float, 
                  tolerance: float = 5.0) -> bool:
    """Hardware-in-the-loop validation."""
    if abs(bench_thrust) < EPSILON:
        logger.warning("Bench thrust is zero - cannot validate")
        return False
    
    error = abs((sim_thrust - bench_thrust) / bench_thrust * 100)
    logger.info(f"HIL: Sim {sim_thrust:.2f}N vs Bench {bench_thrust:.2f}N (Err: {error:.2f}%)")
    return error <= tolerance


# =============================================================================
# CFD Integration (Placeholder)
# =============================================================================

def run_cfd_simulation(mesh_file: str, thrust_vector: np.ndarray, 
                      speed: float = 26 * SPEED_OF_SOUND) -> Dict[str, Any]:
    """
    Integrate with OpenFOAM for CFD simulation.
    
    NOTE: Placeholder implementation.
    """
    if not CFD_AVAILABLE:
        logger.warning("CFD tools not available - returning placeholder data")
        return {'pressure': np.array([]), 'velocity': np.array([])}
    
    logger.info(f"CFD simulation requested: mesh={mesh_file}, speed={speed:.1f}m/s")
    
    return {
        'pressure': np.random.rand(100),
        'velocity': np.random.rand(100, 3),
        'note': 'Placeholder - integrate with OpenFOAM'
    }


# =============================================================================
# Parametric Sweep and Optimization
# =============================================================================

def parametric_sweep(param_name: str, values: List[float], 
                    args: argparse.Namespace) -> 'pd.DataFrame':
    """Perform parametric sweep for given parameter."""
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas required for parametric sweep")
    
    results = []
    for val in values:
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        
        try:
            T, a, P, eta, R, B, rvg_data = calculate_thrust_params_rvg(sweep_args)
            results.append({
                param_name: val,
                'thrust': T,
                'acceleration': a,
                'power': P,
                'efficiency': eta,
                'range': R,
                'B_total': B,
                'theta_dilaton': rvg_data['theta_dilaton']
            })
        except Exception as e:
            logger.warning(f"Sweep failed for {param_name}={val}: {e}")
    
    return pd.DataFrame(results)


def parallel_parametric_sweep(param_name: str, values: List[float], 
                             args: argparse.Namespace, 
                             n_processes: int = 4) -> 'pd.DataFrame':
    """Parallel parametric sweep using multiprocessing."""
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas required for parametric sweep")
    if not MULTIPROCESSING_AVAILABLE:
        logger.warning("Multiprocessing unavailable, using sequential")
        return parametric_sweep(param_name, values, args)
    
    def sweep_single(val: float) -> Dict[str, Any]:
        sweep_args = argparse.Namespace(**vars(args))
        setattr(sweep_args, param_name, val)
        try:
            T, a, P, eta, R, B, rvg_data = calculate_thrust_params_rvg(sweep_args)
            return {
                param_name: val,
                'thrust': T,
                'acceleration': a,
                'power': P,
                'efficiency': eta,
                'range': R,
                'B_total': B,
                'theta_dilaton': rvg_data['theta_dilaton']
            }
        except Exception as e:
            logger.warning(f"Sweep failed for {param_name}={val}: {e}")
            return {param_name: val, 'thrust': 0, 'acceleration': 0, 
                   'power': 0, 'efficiency': 0, 'range': 0, 'B_total': 0,
                   'theta_dilaton': 0}
    
    with mp.Pool(n_processes) as pool:
        results = pool.map(sweep_single, values)
    
    return pd.DataFrame(results)


def thrust_objective(params_dict: Dict[str, float], 
                    base_args: argparse.Namespace) -> float:
    """Objective function for thrust maximization (returns negative for minimization)."""
    args = argparse.Namespace(**vars(base_args))
    for key, val in params_dict.items():
        setattr(args, key, val)
    
    try:
        T, _, _, _, _, _, _ = calculate_thrust_params_rvg(args)
        return -T
    except Exception as e:
        logger.warning(f"Thrust calculation failed: {e}")
        return 0.0


def optimize_thrust(bounds: Dict[str, Tuple[float, float]], 
                   base_args: argparse.Namespace,
                   use_ml_surrogate: bool = False) -> Tuple[Dict[str, float], float]:
    """Gradient-based optimization with optional ML surrogate."""
    if not SCIPY_OPTIMIZE_AVAILABLE:
        raise ImportError("scipy.optimize required for optimization")
    
    param_names = list(bounds.keys())
    bounds_list = list(bounds.values())
    
    if use_ml_surrogate and ML_AVAILABLE:
        logger.info("Training ML surrogate model...")
        
        kernel = ConstantKernel() * RBF()
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
        
        n_samples = 100
        X_train = np.random.uniform(
            [b[0] for b in bounds_list],
            [b[1] for b in bounds_list],
            (n_samples, len(bounds))
        )
        
        y_train = []
        for x in X_train:
            params = dict(zip(param_names, x))
            y_train.append(thrust_objective(params, base_args))
        
        gp.fit(X_train, y_train)
        
        def surrogate_obj(x: np.ndarray) -> float:
            return float(gp.predict(x.reshape(1, -1))[0])
        
        obj_func = surrogate_obj
        logger.info("Surrogate model trained. Optimizing...")
    else:
        def obj_func(x: np.ndarray) -> float:
            params = dict(zip(param_names, x))
            return thrust_objective(params, base_args)
    
    initial_guess = np.array([(b[0] + b[1]) / 2 for b in bounds_list])
    result = minimize(obj_func, initial_guess, bounds=bounds_list, method='L-BFGS-B')
    
    opt_params = dict(zip(param_names, result.x))
    max_thrust = -result.fun
    
    return opt_params, max_thrust


# =============================================================================
# Swarm Simulation Mode
# =============================================================================

def simulate_swarm(
    num_drones: int = 5,
    scenario: str = 'asymmetric',
    simulation_time: float = 60.0,
    verbose: bool = False,
    validate_mada: bool = True,
    headless: bool = True
) -> None:
    """Multi-drone swarm simulation with RVG thrust model."""
    if not PYBULLET_AVAILABLE:
        logger.error("PyBullet not installed. Install with: pip install pybullet")
        return
    
    logger.info(f"Starting RVG swarm simulation: {num_drones} drones, {scenario}")
    logger.info(f"MADA validation: {'ENABLED' if validate_mada else 'DISABLED'}")
    
    validators = [MADAConvergenceValidator() for _ in range(num_drones)] if validate_mada else None
    
    connection_mode = p.DIRECT if headless else p.GUI
    physicsClient = p.connect(connection_mode)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    
    try:
        planeId = p.loadURDF("plane.urdf")
        
        drone_ids = []
        drone_masses = [SimulationConfig.MASS] * num_drones
        drone_thrusts = []
        
        # Calculate base thrust using RVG framework
        base_args = argparse.Namespace(
            m1=SimulationConfig.M1, m2=SimulationConfig.M2,
            distance=SimulationConfig.DISTANCE, current=SimulationConfig.BASE_CURRENT,
            frequency=SimulationConfig.DEFAULT_FREQUENCY,
            n_units=SimulationConfig.N_UNITS, mass=SimulationConfig.MASS,
            chi=SimulationConfig.CHI, b_opposing=50.0
        )
        
        base_T, _, _, _, _, _, _ = calculate_thrust_params_rvg(base_args)
        
        if scenario == 'asymmetric':
            for i in range(num_drones):
                if i < num_drones // 2:
                    drone_thrusts.append(1.5 * base_T)
                else:
                    drone_thrusts.append(0.5 * base_T)
            logger.info("Asymmetric: Advanced (50%) vs Standard (50%)")
        else:
            drone_thrusts = [base_T] * num_drones
            logger.info("Symmetric: All drones equal thrust")
        
        for i in range(num_drones):
            start_pos = [i * 5, 0, 2]
            drone_id = p.loadURDF("sphere2.urdf", start_pos, globalScaling=0.5)
            p.changeDynamics(drone_id, -1, mass=drone_masses[i])
            drone_ids.append(drone_id)
            logger.info(f"Drone {i}: pos={start_pos}, thrust={drone_thrusts[i]:.0f}N")
        
        targets = np.random.uniform(-50, 50, (num_drones, 3))
        trajectories = [
            non_ballistic_trajectory(np.array([i*5, 0, 2]), targets[i])
            for i in range(num_drones)
        ]
        traj_indices = [0] * num_drones
        
        steps = int(simulation_time * SimulationConfig.PHYSICS_STEP_RATE)
        sleep_time = 1.0 / SimulationConfig.PHYSICS_STEP_RATE if not headless else 0
        validation_failures = [0] * num_drones
        
        for step in range(steps):
            for i, drone_id in enumerate(drone_ids):
                if traj_indices[i] < len(trajectories[i]) - 1:
                    current_pos, _ = p.getBasePositionAndOrientation(drone_id)
                    target_pos = trajectories[i][traj_indices[i] + 1]
                    direction = target_pos - np.array(current_pos)
                    dir_norm = np.linalg.norm(direction)
                    
                    if dir_norm > EPSILON:
                        direction = direction / dir_norm
                    else:
                        direction = np.array([0, 0, 1])
                    
                    thrust_multiplier = 1.0
                    if validate_mada and validators:
                        B_total = 50.0 + step * 0.001
                        field_vectors = simulate_hall_sensor_readings(
                            SimulationConfig.N_UNITS, B_total
                        )
                        grad_B2 = gradient_B_squared(B_total)
                        
                        validation_result = validators[i].full_validation(
                            B_total, field_vectors, grad_B2, drone_thrusts[i]
                        )
                        
                        if not validation_result['valid']:
                            validation_failures[i] += 1
                            thrust_multiplier = 0.5
                            if verbose:
                                logger.warning(f"Drone {i} MADA failed: {validation_result['errors']}")
                    
                    thrust_vec = direction * drone_thrusts[i] * thrust_multiplier
                    p.applyExternalForce(drone_id, -1, list(thrust_vec), [0, 0, 0], p.LINK_FRAME)
                    traj_indices[i] += 1
            
            if scenario == 'asymmetric' and np.random.rand() < SimulationConfig.SWARM_ATTACK_PROBABILITY:
                if len(drone_ids) > num_drones // 2:
                    target_id = np.random.choice(drone_ids[num_drones//2:])
                    attack_force = [0, 0, -20000]
                    p.applyExternalForce(target_id, -1, attack_force, [0, 0, 0], p.LINK_FRAME)
                    if verbose:
                        logger.info(f"Step {step}: Attack on drone {drone_ids.index(target_id)}")
            
            p.stepSimulation()
            
            if step % SimulationConfig.PHYSICS_STEP_RATE == 0 and verbose:
                logger.info(f"Time: {step/SimulationConfig.PHYSICS_STEP_RATE:.1f}s / {simulation_time}s")
            
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        logger.info("\n" + "=" * 60)
        logger.info("SWARM SIMULATION RESULTS (RVG Framework - CALIBRATED)")
        logger.info("=" * 60)
        
        for i, drone_id in enumerate(drone_ids):
            pos, _ = p.getBasePositionAndOrientation(drone_id)
            logger.info(f"Drone {i}: Final pos={pos}")
            
            if validate_mada and validators:
                failure_rate = validation_failures[i] / steps * 100
                logger.info(f"  MADA failures: {validation_failures[i]} ({failure_rate:.2f}%)")
                logger.info(f"  Converged: {validators[i].convergence_achieved}")
    
    finally:
        p.disconnect()
        logger.info("Swarm simulation complete\n")


# =============================================================================
# Benchmark Mode
# =============================================================================

def benchmark_with_telemetry(
    telemetry_file: str,
    args: argparse.Namespace,
    verbose: bool = False,
    validate_mada: bool = True
) -> None:
    """Benchmark simulation against hardware telemetry with RVG model."""
    if not PANDAS_AVAILABLE:
        logger.error("pandas required. Install with: pip install pandas")
        return
    
    telemetry_path = Path(telemetry_file)
    if not telemetry_path.exists():
        logger.error(f"Telemetry file not found: {telemetry_file}")
        return
    
    logger.info(f"Benchmarking (RVG - CALIBRATED): {telemetry_file}")
    
    try:
        data = pd.read_csv(telemetry_file)
        logger.info(f"Loaded {len(data)} records")
    except Exception as e:
        logger.error(f"Failed to read telemetry: {e}")
        return
    
    data.columns = data.columns.str.strip().str.lower()
    
    required_cols = ['measured_b', 'measured_freq']
    missing_cols = [col for col in required_cols if col not in data.columns]
    
    if missing_cols:
        logger.error(f"Missing columns: {missing_cols}")
        return
    
    validator = MADAConvergenceValidator() if validate_mada else None
    
    sim_thrusts = []
    sim_accels = []
    differences = []
    hil_results = []
    mada_results = []
    theta_values = []
    
    for idx, row in data.iterrows():
        B = row.get('measured_b', 50.0)
        freq = row.get('measured_freq', args.frequency)
        
        try:
            T_sim, a_sim, _, _, _, _, rvg_data = calculate_thrust_params_rvg(
                args, B_opposing=B, frequency=freq, verbose=False
            )
            theta_values.append(rvg_data['theta_dilaton'])
        except Exception as e:
            logger.warning(f"Record {idx}: Calculation failed - {e}")
            T_sim, a_sim = 0, 0
            theta_values.append(0)
        
        sim_thrusts.append(T_sim)
        sim_accels.append(a_sim)
        
        measured_T = row.get('measured_thrust', 0)
        measured_a = row.get('measured_accel', 0)
        
        diff_T = abs(T_sim - measured_T) if measured_T > 0 else 0
        diff_a = abs(a_sim - measured_a) if measured_a > 0 else 0
        differences.append((diff_T, diff_a))
        
        if measured_T > 0:
            hil_valid = hil_validation(T_sim, measured_T)
            hil_results.append(hil_valid)
        
        if validate_mada and validator:
            field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            grad_B2 = gradient_B_squared(B)
            validation_result = validator.full_validation(B, field_vectors, grad_B2, T_sim)
            mada_results.append(validation_result)
    
    valid_thrust_diffs = [d[0] for d in differences if d[0] > 0]
    valid_accel_diffs = [d[1] for d in differences if d[1] > 0]
    
    avg_diff_T = np.mean(valid_thrust_diffs) if valid_thrust_diffs else 0
    avg_diff_a = np.mean(valid_accel_diffs) if valid_accel_diffs else 0
    hil_pass_rate = sum(hil_results) / len(hil_results) * 100 if hil_results else 0
    avg_theta = np.mean(theta_values) if theta_values else 0
    
    logger.info("\n" + "=" * 60)
    logger.info("BENCHMARK RESULTS (RVG Framework - CALIBRATED)")
    logger.info("=" * 60)
    logger.info(f"Records: {len(data)}")
    logger.info(f"Avg Thrust Error: {avg_diff_T:.2f} N")
    logger.info(f"Avg Accel Error: {avg_diff_a:.2f} m/s²")
    logger.info(f"HIL Pass Rate: {hil_pass_rate:.2f}%")
    logger.info(f"Avg Θ_dilaton: {avg_theta:.2e}")
    
    if validate_mada and mada_results:
        mada_pass = sum(1 for r in mada_results if r['valid']) / len(mada_results) * 100
        logger.info(f"MADA Pass Rate: {mada_pass:.2f}%")


# =============================================================================
# Real-Time Monitoring Mode
# =============================================================================

def real_time_mode(
    args: argparse.Namespace,
    sensor_port: str = '/dev/ttyUSB0',
    update_interval: float = 0.1,
    verbose: bool = False,
    validate_mada: bool = True
) -> None:
    """Real-time monitoring with RVG thrust calculations and GPIO control."""
    logger.info("=" * 60)
    logger.info("REAL-TIME RVG THRUST MONITORING (CALIBRATED)")
    logger.info("=" * 60)
    
    if not validate_mada:
        logger.warning("⚠️  MADA validation DISABLED")
    
    validator = MADAConvergenceValidator() if validate_mada else None
    
    mada_controller = None
    if MADA_GPIO_AVAILABLE:
        try:
            mada_controller = MADAGPIOController(num_madas=args.n_units)
            logger.info("✓ MADA GPIO controller initialized")
        except Exception as e:
            logger.warning(f"MADA GPIO init failed: {e}")
    
    mcu = None
    if HARDWARE_AVAILABLE:
        try:
            mcu = MicrocontrollerPWMInterface(port=sensor_port)
            logger.info(f"✓ Connected to {sensor_port}")
        except Exception as e:
            logger.warning(f"MCU connection failed: {e}")
            logger.info("Using simulated data")
    else:
        logger.info("Hardware unavailable. Using simulated data.")
    
    logger.info(f"Update interval: {update_interval}s")
    logger.info(f"MADA validation: {'ENABLED' if validate_mada else 'DISABLED'}")
    logger.info(f"GPIO control: {'ENABLED' if mada_controller else 'DISABLED'}")
    logger.info("Press Ctrl+C to stop\n")
    
    iteration = 0
    validation_failures = 0
    last_valid_thrust = 0.0
    
    try:
        while True:
            if mcu:
                try:
                    response = mcu.send_command('READ:SENSORS:HALL')
                    if response:
                        parts = response.split(':')
                        B = float(parts[0]) if len(parts) > 0 else 50.0
                        freq = float(parts[1]) if len(parts) > 1 else 100.0
                        field_vectors = simulate_hall_sensor_readings(args.n_units, B)
                    else:
                        raise ValueError("No response")
                except Exception as e:
                    logger.warning(f"Sensor error: {e}")
                    B = 50.0
                    freq = 100.0
                    field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            else:
                B = 50.0 + np.random.normal(0, 2.0)
                freq = 100.0 + np.random.normal(0, 5.0)
                field_vectors = simulate_hall_sensor_readings(args.n_units, B)
            
            validation_passed = True
            grad_B2 = gradient_B_squared(B)
            
            if validate_mada and validator:
                try:
                    # Preliminary calculation for validation
                    T_prelim, _, _, _, _, _, rvg_data = calculate_thrust_params_rvg(
                        args, B_opposing=B, frequency=freq, verbose=False
                    )
                    
                    validation_result = validator.full_validation(
                        B, field_vectors, grad_B2, T_prelim
                    )
                    
                    if not validation_result['valid']:
                        validation_passed = False
                        validation_failures += 1
                        logger.error(f"[{iteration:04d}] ✗ MADA FAILED:")
                        for error in validation_result['errors']:
                            logger.error(f"  - {error}")
                        
                        T, a, P, eta, R, B_total = (last_valid_thrust, 0, 0, 0, 0, B)
                        theta_dilaton = 0
                        
                        failure_rate = validation_failures / (iteration + 1) * 100
                        if failure_rate > 10:
                            logger.critical(f"⚠️  HIGH FAILURE RATE: {failure_rate:.1f}%")
                        
                        iteration += 1
                        time.sleep(update_interval)
                        continue
                    
                    if verbose or iteration % 10 == 0:
                        conv_msg = validation_result['checks']['convergence']['message']
                        logger.info(f"[{iteration:04d}] MADA: {conv_msg}")
                
                except MADAValidationError as e:
                    logger.error(f"[{iteration:04d}] CRITICAL: {e}")
                    validation_passed = False
                    validation_failures += 1
                    iteration += 1
                    time.sleep(update_interval)
                    continue
            
            # GPIO control
            if mada_controller and validate_mada and validation_passed:
                target_direction = np.array([1.0, 0.0, 0.0])
                try:
                    orientations = integrate_with_mada_validation(
                        mada_controller, field_vectors, target_direction
                    )
                    for mada_id, (az, el) in orientations.items():
                        mada_controller.rotate_mada(mada_id, az, el, blocking=False)
                except Exception as e:
                    logger.warning(f"GPIO error: {e}")
            
            # Full RVG calculation
            try:
                T, a, P, eta, R, B_total, rvg_data = calculate_thrust_params_rvg(
                    args, B_opposing=B, frequency=freq, verbose=False,
                    validate_mada=False
                )
                theta_dilaton = rvg_data['theta_dilaton']
                
                if validation_passed:
                    last_valid_thrust = T
            
            except Exception as e:
                logger.error(f"[{iteration:04d}] Calculation error: {e}")
                T, a, P, eta, R, B_total = (0, 0, 0, 0, 0, B)
                theta_dilaton = 0
            
            a_g = a / 9.81 if abs(a) > EPSILON else 0
            status = "✓" if validation_passed else "✗"
            
            logger.info(
                f"[{iteration:04d}] {status} B={B:.2f}T, Θ={theta_dilaton:.2e}, "
                f"T={T:.0f}N, a={a:.1f}m/s² ({a_g:.1f}g), P={P:.0f}W"
            )
            
            if validate_mada and iteration > 0 and iteration % 20 == 0 and validator:
                failure_rate = validation_failures / iteration * 100
                if failure_rate > 5:
                    logger.warning(f"⚠️  Failure rate: {failure_rate:.1f}%")
                if validator.convergence_achieved:
                    logger.info(f"✓ CONVERGED after {len(validator.history)} samples")
            
            iteration += 1
            time.sleep(update_interval)
    
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("Monitoring stopped")
        logger.info("=" * 60)
        logger.info(f"Total iterations: {iteration}")
        if validate_mada and validator:
            failure_rate = validation_failures / iteration * 100 if iteration > 0 else 0
            logger.info(f"MADA failures: {validation_failures} ({failure_rate:.2f}%)")
            logger.info(f"Converged: {validator.convergence_achieved}")
            logger.info(f"Final thrust: {last_valid_thrust:.2f}N")
    
    finally:
        if mcu:
            try:
                mcu.close()
            except:
                pass
        if mada_controller:
            try:
                mada_controller.cleanup()
            except:
                pass


# =============================================================================
# Single Calculation Mode
# =============================================================================

def single_calculation_mode(args: argparse.Namespace) -> None:
    """Single thrust calculation with RVG framework and detailed output."""
    logger.info("=" * 60)
    logger.info("QED VACUUM THRUST MODEL - RVG UNIFIED FIELD (CALIBRATED)")
    logger.info("=" * 60)
    
    logger.info("\nInput Parameters:")
    logger.info(f"  Frequency: {args.frequency} Hz")
    logger.info(f"  Mass: {args.mass} kg")
    logger.info(f"  MADA units: {args.n_units}")
    logger.info(f"  MADA amplification: {SimulationConfig.K_MADA}x")
    logger.info(f"  MADA Validation: {'ENABLED' if args.validate_mada else 'DISABLED'}")
    
    scaled_I = args.current * (args.frequency / SimulationConfig.BASE_FREQUENCY)
    if args.verbose:
        logger.info(f"  Base Current: {args.current} A")
        logger.info(f"  Scaled Current: {scaled_I:.2f} A")
    
    if args.b_opposing is not None:
        B = args.b_opposing
        logger.info(f"  B_opposing (provided): {B:.2f} T")
    else:
        B = opposing_field(args.m1, args.m2, args.distance, SimulationConfig.K_MADA)
        logger.info(f"  B_opposing (calculated): {B:.6e} T")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("MAGNETIC FIELD CALCULATIONS")
    logger.info(f"{'─' * 60}")
    
    delta_B = pulsed_enhancement(SimulationConfig.N_TURNS, scaled_I)
    B_total = B + delta_B
    
    logger.info(f"Opposing Field (B_opp): {B:.2f} T")
    logger.info(f"Pulsed Enhancement (ΔB): {delta_B:.4f} T")
    logger.info(f"Total Field (B_total): {B_total:.2f} T")
    
    # Check supra-saturation
    is_supra, supra_msg = check_supra_saturation(B_total, SimulationConfig.B_SAT_MINNEALLOY)
    logger.info(f"Supra-saturation: {supra_msg}")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("RVG UNIFIED FIELD PARAMETERS (CALIBRATED)")
    logger.info(f"{'─' * 60}")
    
    theta_dilaton = dilaton_enhancement_factor(B_total)
    K = vacuum_refractive_index(B_total, theta_dilaton)
    grad_B2 = gradient_B_squared(B_total)
    grad_K = gradient_refractive_index(B_total, grad_B2, theta_dilaton)
    
    logger.info(f"Θ_baseline: {THETA_95_BASE:.2e} (CALIBRATED)")
    logger.info(f"B_threshold: {B_THRESHOLD_DEFAULT:.1f} T")
    logger.info(f"Dilaton Enhancement (Θ): {theta_dilaton:.2e}")
    logger.info(f"Vacuum Refractive Index (K): {K:.10f}")
    logger.info(f"K - 1 (vacuum susceptibility): {K-1:.2e}")
    logger.info(f"∇B² magnitude: {np.linalg.norm(grad_B2):.2e} T²/m")
    logger.info(f"∇K magnitude: {np.linalg.norm(grad_K):.2e} 1/m")
    
    if args.verbose:
        logger.info(f"\n  Schwinger Field: {B_SCHWINGER:.2e} T")
        logger.info(f"  B/B_Schwinger: {B_total/B_SCHWINGER:.2e}")
        logger.info(f"  95 GeV Resonance: {DILATON_MASS_GEV} GeV")
    
    # MADA validation
    if args.validate_mada:
        logger.info(f"\n{'─' * 60}")
        logger.info("MADA CONVERGENCE VALIDATION")
        logger.info(f"{'─' * 60}")
        
        validator = MADAConvergenceValidator(tolerance=args.mada_tolerance)
        field_vectors = simulate_hall_sensor_readings(args.n_units, B_total)
        
        # Get preliminary thrust for validation
        F_lift = master_equation_lift(B_total, grad_B2, SimulationConfig.EFFECTIVE_VOLUME)
        T_prelim = total_thrust(F_lift, args.n_units, SimulationConfig.ETA_ALIGN,
                                SimulationConfig.THETA_THRUST)
        
        validation_result = validator.full_validation(
            B_total, field_vectors, grad_B2, T_prelim
        )
        
        for check_name, check_result in validation_result['checks'].items():
            status = "✓" if check_result['valid'] else "✗"
            logger.info(f"{status} {check_name.capitalize()}: {check_result['message']}")
        
        if not validation_result['valid']:
            logger.error("\n✗ MADA VALIDATION FAILED")
            for error in validation_result['errors']:
                logger.error(f"  - {error}")
            logger.error("\nCANNOT PROCEED - Fix MADA configuration!")
            sys.exit(1)
        else:
            logger.info("\n✓ MADA VALIDATION PASSED")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("FORCE & THRUST CALCULATIONS")
    logger.info(f"{'─' * 60}")
    
    try:
        T, a, P, eta, R, B_total, rvg_data = calculate_thrust_params_rvg(
            args, B_opposing=B, verbose=args.verbose,
            validate_mada=False
        )
    except Exception as e:
        logger.error(f"Calculation failed: {e}")
        sys.exit(1)
    
    F_lift = rvg_data['F_lift']
    f_vac = rvg_data['f_vac']
    
    logger.info(f"Vacuum Force Density: {np.linalg.norm(f_vac):.2e} N/m³")
    logger.info(f"Lift Force (per unit): {np.linalg.norm(F_lift):.2f} N")
    logger.info(f"Total Thrust: {T:.2f} N ({T/1000:.2f} kN)")
    
    a_g = a / 9.81
    logger.info(f"Acceleration: {a:.2f} m/s² ({a_g:.2f}g)")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("PERFORMANCE METRICS")
    logger.info(f"{'─' * 60}")
    
    logger.info(f"Power: {P:.2f} W ({P/1000:.2f} kW)")
    logger.info(f"Efficiency: {eta:.2f}%")
    logger.info(f"  (at v = {SimulationConfig.VELOCITY} m/s = Mach {SimulationConfig.VELOCITY/SPEED_OF_SOUND:.2f})")
    logger.info(f"Range: {R/1000:.2f} km ({R/1609.34:.2f} miles)")
    
    logger.info(f"\n{'─' * 60}")
    logger.info("PERFORMANCE PROJECTIONS")
    logger.info(f"{'─' * 60}")
    
    mach_26_speed = 26 * SPEED_OF_SOUND
    time_to_mach26 = mach_26_speed / a if a > EPSILON else float('inf')
    logger.info(f"Time to Mach 26: {time_to_mach26:.2f}s ({time_to_mach26/60:.2f}min)")
    
    weight = args.mass * 9.81
    twr = T / weight if weight > EPSILON else 0
    logger.info(f"Thrust-to-Weight: {twr:.2f}")
    
    ldr = compute_lift_drag_ratio()
    logger.info(f"Lift-to-Drag: {ldr:.2f}")
    
    structural_ok = fea_structural_check(a, args.mass)
    logger.info(f"Structural ({a_g:.1f}g): {'PASS' if structural_ok else 'FAIL'}")
    
    traj = non_ballistic_trajectory(np.array([0, 0, 0]), np.array([1000, 0, 0]))
    evasion_prob = stealth_ops_check(traj, np.array([500, 0, 0]))
    logger.info(f"Radar Evasion: {evasion_prob:.2%}")
    
    # Show configuration comparison
    logger.info(f"\n{'─' * 60}")
    logger.info("GEOMETRY FACTOR COMPARISON")
    logger.info(f"{'─' * 60}")
    
    for name, gf in [("Simple opposing", DEFAULT_GEOMETRY_FACTOR),
                     ("MADA single", MADA_SINGLE_GEOMETRY),
                     ("MADA nested", MADA_NESTED_GEOMETRY),
                     ("Bushman optimized", BUSHMAN_MAX_GEOMETRY)]:
        grad_B2_test = gradient_B_squared(B_total, gf)
        F_test = master_equation_lift(B_total, grad_B2_test, SimulationConfig.EFFECTIVE_VOLUME)
        T_test = total_thrust(F_test, args.n_units, SimulationConfig.ETA_ALIGN,
                              SimulationConfig.THETA_THRUST)
        twr_test = T_test / weight
        status = "✓ HOVER" if twr_test >= 1.0 else "insufficient"
        logger.info(f"  {name}: T = {T_test:.0f} N, T/W = {twr_test:.2f} ({status})")
    
    logger.info(f"\n{'=' * 60}")
    logger.info("SIMULATION COMPLETE (RVG Unified Field - CALIBRATED)")
    logger.info(f"{'=' * 60}\n")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """Main entry point for RVG thrust model simulations."""
    parser = argparse.ArgumentParser(
        description="QED Vacuum Thrust Model - RVG Unified Field Framework (CALIBRATED)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RVG Unified Field Framework (CALIBRATED):
  Based on "Refractive Vacuum Gravity Unified Field: Disformal QED, the 95 GeV
  Resonance, and the Metric Engineering of Static Levitation" (Hofseth, 2025)

CALIBRATED Parameters:
  - THETA_95_BASE = 1e-8 (produces physically reasonable forces)
  - B_THRESHOLD = 20.0 T (where dilaton enhancement activates)
  - Aligned with equations.py for consistent results

Key Physics:
  - Master Equation: F_lift = ∫(Θ_dilaton(B)·∇B²)dV
  - Dilaton Enhancement: Θ_dilaton(B) from 95 GeV resonance
  - Vacuum Refractive Index: K = 1 + Θ·B²/B_crit²
  - MADA Amplification: 200-529x field enhancement

Modes:
  single     - Single thrust calculation (default)
  swarm      - Multi-drone swarm simulation
  benchmark  - Compare vs hardware telemetry
  realtime   - Real-time sensor monitoring

Examples:
  python thrust_model.py --b_opposing 50 --frequency 100 --validate_mada
  python thrust_model.py --mode swarm --num_drones 10 --headless
  python thrust_model.py --optimize --use_ml
        """
    )
    
    # Basic parameters
    parser.add_argument("--b_opposing", type=float, default=None,
                        help="Opposing magnetic field (T)")
    parser.add_argument("--frequency", type=float, default=SimulationConfig.DEFAULT_FREQUENCY,
                        help=f"Pulsing frequency (Hz), default: {SimulationConfig.DEFAULT_FREQUENCY}")
    parser.add_argument("--geometry_factor", type=float, default=SimulationConfig.GEOMETRY_FACTOR,
                        help=f"Gradient Geometry Factor (T/m), default: {SimulationConfig.GEOMETRY_FACTOR:.1e}")
    parser.add_argument("--m1", type=float, default=SimulationConfig.M1,
                        help=f"Magnetic moment 1 (A·m²), default: {SimulationConfig.M1}")
    parser.add_argument("--m2", type=float, default=SimulationConfig.M2,
                        help=f"Magnetic moment 2 (A·m²), default: {SimulationConfig.M2}")
    parser.add_argument("--distance", type=float, default=SimulationConfig.DISTANCE,
                        help=f"Distance between magnets (m), default: {SimulationConfig.DISTANCE}")
    parser.add_argument("--current", type=float, default=SimulationConfig.BASE_CURRENT,
                        help=f"Base current (A), default: {SimulationConfig.BASE_CURRENT}")
    parser.add_argument("--mass", type=float, default=SimulationConfig.MASS,
                        help=f"System mass (kg), default: {SimulationConfig.MASS}")
    parser.add_argument("--n_units", type=int, default=SimulationConfig.N_UNITS,
                        help=f"Number of MADA units, default: {SimulationConfig.N_UNITS}")
    parser.add_argument("--chi", type=float, default=SimulationConfig.CHI,
                        help=f"Magnetic susceptibility, default: {SimulationConfig.CHI}")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    parser.add_argument("--config", type=str, default=None, help="YAML config file")
    
    # MADA validation
    parser.add_argument("--validate_mada", action="store_true",
                        help="Enable MADA convergence validation (RECOMMENDED)")
    parser.add_argument("--mada_tolerance", type=float, 
                        default=MADAValidationConfig.CONVERGENCE_THRESHOLD,
                        help=f"MADA tolerance, default: {MADAValidationConfig.CONVERGENCE_THRESHOLD}")
    
    # Mode selection
    parser.add_argument("--mode", type=str, default='single',
                        choices=['single', 'swarm', 'benchmark', 'realtime'],
                        help="Simulation mode (default: single)")
    
    # Swarm parameters
    parser.add_argument("--num_drones", type=int, default=5, help="Drones for swarm")
    parser.add_argument("--scenario", type=str, default='asymmetric',
                        choices=['asymmetric', 'symmetric'], help="Swarm scenario")
    parser.add_argument("--simulation_time", type=float, default=60.0, help="Sim time (s)")
    parser.add_argument("--headless", action="store_true", help="No GUI")
    
    # Benchmark parameters
    parser.add_argument("--telemetry_file", type=str, default=None, help="Telemetry CSV")
    
    # Real-time parameters
    parser.add_argument("--sensor_port", type=str, default='/dev/ttyUSB0', help="Serial port")
    parser.add_argument("--update_interval", type=float, default=0.1, help="Update interval (s)")
    
    # Optimization
    parser.add_argument("--optimize", action="store_true", help="Run optimization")
    parser.add_argument("--use_ml", action="store_true", help="Use ML surrogate")
    
    # Parametric sweep
    parser.add_argument("--sweep", type=str, default=None, help="Parameter to sweep")
    parser.add_argument("--sweep_values", type=str, default=None, help="Comma-separated values")
    
    args = parser.parse_args()
    
    # Load config file
    if args.config:
        if not YAML_AVAILABLE:
            logger.error("PyYAML required. Install: pip install pyyaml")
            sys.exit(1)
        try:
            config_args = load_config_yaml(args.config)
            for key, val in vars(config_args).items():
                if hasattr(args, key) and getattr(args, key) == parser.get_default(key):
                    setattr(args, key, val)
        except Exception as e:
            logger.error(f"Config load failed: {e}")
            sys.exit(1)
    
    # Validate inputs
    if args.mass <= 0:
        parser.error("Mass must be positive")
    if args.frequency <= 0:
        parser.error("Frequency must be positive")
    if args.n_units <= 0:
        parser.error("Number of units must be positive")
    if args.distance <= 0:
        parser.error("Distance must be positive")
    
    try:
        # Parametric sweep
        if args.sweep and args.sweep_values:
            if not PANDAS_AVAILABLE:
                logger.error("pandas required for sweep")
                sys.exit(1)
            
            sweep_vals = [float(v.strip()) for v in args.sweep_values.split(',')]
            logger.info(f"Parametric sweep: {args.sweep} = {sweep_vals}")
            
            results_df = parallel_parametric_sweep(args.sweep, sweep_vals, args)
            logger.info("\nSweep Results:")
            logger.info(results_df.to_string(index=False))
            
            output_file = f'sweep_{args.sweep}.csv'
            results_df.to_csv(output_file, index=False)
            logger.info(f"Saved to {output_file}")
            return
        
        # Optimization
        if args.optimize:
            if not SCIPY_OPTIMIZE_AVAILABLE:
                logger.error("scipy.optimize required")
                sys.exit(1)
            
            logger.info("Running RVG thrust optimization (CALIBRATED)...")
            bounds = {'frequency': (50.0, 150.0), 'current': (10.0, 20.0)}
            
            opt_params, max_thrust = optimize_thrust(bounds, args, args.use_ml)
            
            logger.info("\n" + "=" * 60)
            logger.info("OPTIMIZATION RESULTS (RVG - CALIBRATED)")
            logger.info("=" * 60)
            for param, val in opt_params.items():
                logger.info(f"  {param}: {val:.2f}")
            logger.info(f"  Max Thrust: {max_thrust:.2f} N")
            logger.info("=" * 60 + "\n")
            return
        
        # Route to mode
        if args.mode == 'single':
            single_calculation_mode(args)
        elif args.mode == 'swarm':
            simulate_swarm(args.num_drones, args.scenario, args.simulation_time,
                          args.verbose, args.validate_mada, args.headless)
        elif args.mode == 'benchmark':
            if not args.telemetry_file:
                parser.error("--telemetry_file required for benchmark")
            benchmark_with_telemetry(args.telemetry_file, args, args.verbose, args.validate_mada)
        elif args.mode == 'realtime':
            real_time_mode(args, args.sensor_port, args.update_interval,
                          args.verbose, args.validate_mada)
    
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if MULTIPROCESSING_AVAILABLE:
        mp.freeze_support()
    main()
