# cad/flux_visualizer.py
# This module provides rendering scripts for visualizing magnetic flux maps,
# thermal dissipation, and interactive 3D views of the spherical drone prototype.
# CRITICAL: Added MADA convergence visualization to verify proper field opposition.
# Uses Matplotlib for static plots and Plotly for interactive visualizations.
# Assumes data from simulations (e.g., B fields from equations.py) or CAD exports.
# Example usage: python flux_visualizer.py --mode flux --input data.npy

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
import plotly.graph_objects as go
import argparse
import os
import sys

# Import convergence calculation from equations.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from simulations.equations import (
        calculate_convergence_quality,
        calculate_field_at_point,
        CONVERGENCE_OPTIMAL,
        CONVERGENCE_WARNING,
        CONVERGENCE_CRITICAL
    )
except ImportError:
    print("Warning: Could not import from simulations.equations. Using local implementations.")
    CONVERGENCE_OPTIMAL = 0.95
    CONVERGENCE_WARNING = 0.85
    CONVERGENCE_CRITICAL = 0.80
    
    def calculate_convergence_quality(B1, B2):
        B1_mag = np.linalg.norm(B1)
        B2_mag = np.linalg.norm(B2)
        if B1_mag == 0 or B2_mag == 0:
            return 0.0
        return -np.dot(B1 / B1_mag, B2 / B2_mag)


# Custom 3D arrow class for better visualization
class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def draw(self, renderer):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        FancyArrowPatch.draw(self, renderer)


# Example data generation functions (placeholders; integrate with equations.py or CAD)

def generate_dual_mada_flux_map(grid_size=50, B_mag=50.0, mada1_pos=(-0.3, 0, 0), 
                                mada2_pos=(0.3, 0, 0), converging=True):
    """
    Generate 3D magnetic flux map for dual MADA configuration.
    
    Parameters:
    grid_size (int): Grid resolution
    B_mag (float): Field strength (T)
    mada1_pos (tuple): Position of MADA unit 1 (x,y,z)
    mada2_pos (tuple): Position of MADA unit 2 (x,y,z)
    converging (bool): If True, fields point toward center (CORRECT).
                       If False, fields point away (WRONG - the FreeCAD bug!)
    
    Returns:
    tuple: (X, Y, Z, U, V, W, B1_center, B2_center, convergence_quality)
    """
    x = np.linspace(-1, 1, grid_size)
    y = np.linspace(-1, 1, grid_size)
    z = np.linspace(-1, 1, grid_size)
    X, Y, Z = np.meshgrid(x, y, z)
    
    # Initialize field arrays
    U = np.zeros_like(X)
    V = np.zeros_like(Y)
    W = np.zeros_like(Z)
    
    center = np.array([0, 0, 0])
    mada1_pos = np.array(mada1_pos)
    mada2_pos = np.array(mada2_pos)
    
    # Determine field directions
    if converging:
        # CORRECT: Fields point toward center
        mada1_dir = (center - mada1_pos) / np.linalg.norm(center - mada1_pos)
        mada2_dir = (center - mada2_pos) / np.linalg.norm(center - mada2_pos)
    else:
        # WRONG: Fields point away from center (the FreeCAD bug!)
        mada1_dir = (mada1_pos - center) / np.linalg.norm(mada1_pos - center)
        mada2_dir = (mada2_pos - center) / np.linalg.norm(mada2_pos - center)
    
    # Calculate magnetic moment magnitudes
    m1 = B_mag * 0.01  # Simplified: m ~ B * volume
    m2 = B_mag * 0.01
    
    # Calculate field from each MADA unit at each grid point
    for i in range(grid_size):
        for j in range(grid_size):
            for k in range(grid_size):
                point = np.array([X[i,j,k], Y[i,j,k], Z[i,j,k]])
                
                # Field from MADA 1
                r1 = point - mada1_pos
                r1_mag = np.linalg.norm(r1)
                if r1_mag > 0.01:  # Avoid singularity
                    r1_hat = r1 / r1_mag
                    dot1 = np.dot(m1 * mada1_dir, r1_hat)
                    B1 = (1e-7 / r1_mag**3) * (3 * dot1 * r1_hat - m1 * mada1_dir)
                else:
                    B1 = np.array([0, 0, 0])
                
                # Field from MADA 2
                r2 = point - mada2_pos
                r2_mag = np.linalg.norm(r2)
                if r2_mag > 0.01:
                    r2_hat = r2 / r2_mag
                    dot2 = np.dot(m2 * mada2_dir, r2_hat)
                    B2 = (1e-7 / r2_mag**3) * (3 * dot2 * r2_hat - m2 * mada2_dir)
                else:
                    B2 = np.array([0, 0, 0])
                
                # Total field
                B_total = B1 + B2
                U[i,j,k] = B_total[0]
                V[i,j,k] = B_total[1]
                W[i,j,k] = B_total[2]
    
    # Calculate field vectors at center for convergence quality
    B1_center = m1 * mada1_dir * B_mag  # Simplified
    B2_center = m2 * mada2_dir * B_mag
    
    convergence_quality = calculate_convergence_quality(B1_center, B2_center)
    
    return X, Y, Z, U, V, W, B1_center, B2_center, convergence_quality


def generate_flux_map(grid_size=50, B_opposing=50.0, position=(0,0,0)):
    """
    Generate a 3D magnetic flux map (vector field) around a point source.
    DEPRECATED: Use generate_dual_mada_flux_map() for proper MADA visualization.
    
    Parameters:
    grid_size (int): Grid resolution
    B_opposing (float): Opposing field strength (T)
    position (tuple): Center position (x,y,z)
    
    Returns:
    tuple: (X, Y, Z, U, V, W) for vector field
    """
    print("WARNING: Using legacy single-source flux map. Use generate_dual_mada_flux_map() instead.")
    x = np.linspace(-1, 1, grid_size)
    y = np.linspace(-1, 1, grid_size)
    z = np.linspace(-1, 1, grid_size)
    X, Y, Z = np.meshgrid(x, y, z)
    
    # Simple dipole approximation for flux: B ~ 1/r^3 along x for opposition
    r = np.sqrt((X - position[0])**2 + (Y - position[1])**2 + (Z - position[2])**2 + 1e-6)
    U = B_opposing * (X - position[0]) / r**3
    V = 0.1 * B_opposing * (Y - position[1]) / r**3  # Small y component for visualization
    W = 0.1 * B_opposing * (Z - position[2]) / r**3  # Small z
    return X, Y, Z, U, V, W


def generate_thermal_map(grid_size=50, heat_source=1000.0, position=(0,0,0)):
    """
    Generate a 3D thermal dissipation map (scalar field).
    
    Parameters:
    grid_size (int): Grid resolution
    heat_source (float): Heat power (W)
    position (tuple): Center position (x,y,z)
    
    Returns:
    tuple: (X, Y, Z, Temp) for contour plot
    """
    x = np.linspace(-1, 1, grid_size)
    y = np.linspace(-1, 1, grid_size)
    z = np.linspace(-1, 1, grid_size)
    X, Y, Z = np.meshgrid(x, y, z)
    
    # Simple inverse square dissipation: Temp ~ P / r^2
    r = np.sqrt((X - position[0])**2 + (Y - position[1])**2 + (Z - position[2])**2 + 1e-6)
    Temp = heat_source / (4 * np.pi * r**2)  # Like point source radiation
    return X, Y, Z, Temp


# Visualization Functions

def plot_mada_convergence_diagram(B1_center, B2_center, mada1_pos=(-0.3, 0, 0), 
                                   mada2_pos=(0.3, 0, 0), convergence_quality=None):
    """
    NEW: Plot MADA field convergence diagram with quality assessment.
    Shows both MADA units and their field vectors.
    """
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    mada1_pos = np.array(mada1_pos)
    mada2_pos = np.array(mada2_pos)
    center = np.array([0, 0, 0])
    
    # Plot MADA units as spheres
    u = np.linspace(0, 2 * np.pi, 20)
    v = np.linspace(0, np.pi, 20)
    radius = 0.05
    
    # MADA 1
    x1 = radius * np.outer(np.cos(u), np.sin(v)) + mada1_pos[0]
    y1 = radius * np.outer(np.sin(u), np.sin(v)) + mada1_pos[1]
    z1 = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + mada1_pos[2]
    ax.plot_surface(x1, y1, z1, color='blue', alpha=0.6, label='MADA 1')
    
    # MADA 2
    x2 = radius * np.outer(np.cos(u), np.sin(v)) + mada2_pos[0]
    y2 = radius * np.outer(np.sin(u), np.sin(v)) + mada2_pos[1]
    z2 = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + mada2_pos[2]
    ax.plot_surface(x2, y2, z2, color='red', alpha=0.6, label='MADA 2')
    
    # Plot center focal point
    ax.scatter(*center, color='green', s=100, marker='*', label='Focal Point')
    
    # Plot field vectors (normalized for visibility)
    B1_norm = B1_center / np.linalg.norm(B1_center) * 0.2
    B2_norm = B2_center / np.linalg.norm(B2_center) * 0.2
    
    # Determine colors based on convergence
    if convergence_quality is not None:
        if convergence_quality >= CONVERGENCE_OPTIMAL:
            arrow_color = 'green'
            status = 'OPTIMAL'
        elif convergence_quality >= CONVERGENCE_WARNING:
            arrow_color = 'yellow'
            status = 'ACCEPTABLE'
        elif convergence_quality >= CONVERGENCE_CRITICAL:
            arrow_color = 'orange'
            status = 'WARNING'
        else:
            arrow_color = 'red'
            status = 'CRITICAL/DIVERGING'
    else:
        arrow_color = 'gray'
        status = 'UNKNOWN'
    
    # Draw arrows
    arrow1 = Arrow3D([mada1_pos[0], mada1_pos[0] + B1_norm[0]],
                     [mada1_pos[1], mada1_pos[1] + B1_norm[1]],
                     [mada1_pos[2], mada1_pos[2] + B1_norm[2]],
                     mutation_scale=20, lw=3, arrowstyle='-|>', color=arrow_color)
    ax.add_artist(arrow1)
    
    arrow2 = Arrow3D([mada2_pos[0], mada2_pos[0] + B2_norm[0]],
                     [mada2_pos[1], mada2_pos[1] + B2_norm[1]],
                     [mada2_pos[2], mada2_pos[2] + B2_norm[2]],
                     mutation_scale=20, lw=3, arrowstyle='-|>', color=arrow_color)
    ax.add_artist(arrow2)
    
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    
    # Title with convergence info
    if convergence_quality is not None:
        title = f'MADA Field Convergence: {status}\nQuality = {convergence_quality:.3f}'
    else:
        title = 'MADA Field Configuration'
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    ax.legend()
    ax.set_xlim([-0.5, 0.5])
    ax.set_ylim([-0.3, 0.3])
    ax.set_zlim([-0.3, 0.3])
    
    # Add text annotation
    quality_text = f"Convergence Quality: {convergence_quality:.3f}\n"
    if convergence_quality >= CONVERGENCE_OPTIMAL:
        quality_text += "✓ Excellent - Fields properly opposing"
    elif convergence_quality >= CONVERGENCE_CRITICAL:
        quality_text += "⚠ Acceptable - Monitor alignment"
    else:
        quality_text += "✗ FAILED - Fields NOT opposing!"
    
    ax.text2D(0.05, 0.95, quality_text, transform=ax.transAxes,
              fontsize=10, verticalalignment='top',
              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.show()


def plot_flux_map_static(X, Y, Z, U, V, W, slice_plane='xy', z_slice=0.0):
    """
    Static Matplotlib plot of flux map (quiver for vectors).
    
    Parameters:
    X,Y,Z,U,V,W: From generate_flux_map
    slice_plane (str): 'xy', 'xz', 'yz'
    z_slice (float): Slice value for 2D view
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Subsample for clarity
    skip = 5
    ax.quiver(X[::skip, ::skip, ::skip], Y[::skip, ::skip, ::skip], Z[::skip, ::skip, ::skip],
              U[::skip, ::skip, ::skip], V[::skip, ::skip, ::skip], W[::skip, ::skip, ::skip],
              length=0.1, normalize=True, color='blue')
    
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Magnetic Flux Map')
    plt.show()


def plot_thermal_map_static(X, Y, Z, Temp):
    """
    Static Matplotlib contour plot of thermal dissipation.
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    # 2D slice at z=0
    z_idx = len(Z[0,0,:]) // 2
    contour = ax.contourf(X[:,:,z_idx], Y[:,:,z_idx], Temp[:,:,z_idx], cmap=cm.hot)
    fig.colorbar(contour, ax=ax, label='Temperature (°C)')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title('Thermal Dissipation Map (Z=0 Slice)')
    plt.show()


def plot_interactive_flux(X, Y, Z, U, V, W):
    """
    Interactive Plotly 3D vector field for flux map.
    """
    # Subsample
    skip = 5
    fig = go.Figure(data=go.Cone(
        x=X.flatten()[::skip], y=Y.flatten()[::skip], z=Z.flatten()[::skip],
        u=U.flatten()[::skip], v=V.flatten()[::skip], w=W.flatten()[::skip],
        colorscale='Blues',
        sizemode='absolute',
        sizeref=0.1
    ))
    fig.update_layout(title='Interactive Magnetic Flux Map',
                      scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'))
    fig.show()


def plot_interactive_mada_comparison(converging_data, diverging_data):
    """
    NEW: Side-by-side interactive comparison of converging vs diverging fields.
    """
    X_c, Y_c, Z_c, U_c, V_c, W_c, B1_c, B2_c, quality_c = converging_data
    X_d, Y_d, Z_d, U_d, V_d, W_d, B1_d, B2_d, quality_d = diverging_data
    
    skip = 8
    
    # Create subplots
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            f'CORRECT: Converging Fields (Quality={quality_c:.3f})',
            f'WRONG: Diverging Fields (Quality={quality_d:.3f})'
        ),
        specs=[[{'type': 'scatter3d'}, {'type': 'scatter3d'}]]
    )
    
    # Converging (correct)
    fig.add_trace(
        go.Cone(
            x=X_c.flatten()[::skip], y=Y_c.flatten()[::skip], z=Z_c.flatten()[::skip],
            u=U_c.flatten()[::skip], v=V_c.flatten()[::skip], w=W_c.flatten()[::skip],
            colorscale='Greens',
            sizemode='absolute',
            sizeref=0.05,
            name='Converging'
        ),
        row=1, col=1
    )
    
    # Diverging (wrong)
    fig.add_trace(
        go.Cone(
            x=X_d.flatten()[::skip], y=Y_d.flatten()[::skip], z=Z_d.flatten()[::skip],
            u=U_d.flatten()[::skip], v=V_d.flatten()[::skip], w=W_d.flatten()[::skip],
            colorscale='Reds',
            sizemode='absolute',
            sizeref=0.05,
            name='Diverging'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title_text='MADA Configuration Comparison: Correct vs Incorrect',
        height=600
    )
    
    fig.show()


def plot_interactive_thermal(X, Y, Z, Temp):
    """
    Interactive Plotly 3D isosurface for thermal dissipation.
    """
    fig = go.Figure(data=go.Isosurface(
        x=X.flatten(), y=Y.flatten(), z=Z.flatten(),
        value=Temp.flatten(),
        isomin=np.min(Temp) * 0.5,
        isomax=np.max(Temp),
        surface_count=5,
        colorscale='Hot',
        caps=dict(x_show=False, y_show=False, z_show=False)
    ))
    fig.update_layout(title='Interactive Thermal Dissipation Map',
                      scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'))
    fig.show()


# CLI for running visualizations
def main():
    parser = argparse.ArgumentParser(description="Flux and Thermal Visualizer for Spherical Drone")
    parser.add_argument("--mode", type=str, 
                        choices=['flux', 'thermal', 'mada', 'comparison'], 
                        required=True,
                        help="Visualization mode: flux, thermal, mada (convergence), or comparison")
    parser.add_argument("--interactive", action="store_true",
                        help="Use interactive Plotly view")
    parser.add_argument("--input", type=str, default=None,
                        help="Optional numpy file for data")
    parser.add_argument("--diverging", action="store_true",
                        help="Show diverging field configuration (WRONG - for educational purposes)")
    
    args = parser.parse_args()
    
    if args.mode == 'mada':
        # MADA convergence visualization
        print("Generating MADA convergence visualization...")
        converging = not args.diverging
        X, Y, Z, U, V, W, B1, B2, quality = generate_dual_mada_flux_map(
            grid_size=30, converging=converging
        )
        
        print(f"Convergence Quality: {quality:.3f}")
        if quality >= CONVERGENCE_OPTIMAL:
            print("✓ OPTIMAL: Fields properly opposing")
        elif quality >= CONVERGENCE_CRITICAL:
            print("⚠ WARNING: Suboptimal field alignment")
        else:
            print("✗ CRITICAL: Fields NOT properly opposing!")
        
        plot_mada_convergence_diagram(B1, B2, convergence_quality=quality)
        
        if args.interactive:
            plot_interactive_flux(X, Y, Z, U, V, W)
    
    elif args.mode == 'comparison':
        # Side-by-side comparison
        print("Generating comparison: Correct vs Incorrect MADA configuration...")
        converging_data = generate_dual_mada_flux_map(grid_size=20, converging=True)
        diverging_data = generate_dual_mada_flux_map(grid_size=20, converging=False)
        
        print(f"Converging (CORRECT) quality: {converging_data[-1]:.3f}")
        print(f"Diverging (WRONG) quality: {diverging_data[-1]:.3f}")
        
        if args.interactive:
            plot_interactive_mada_comparison(converging_data, diverging_data)
        else:
            # Show both diagrams
            plot_mada_convergence_diagram(
                converging_data[6], converging_data[7],
                convergence_quality=converging_data[8]
            )
            plot_mada_convergence_diagram(
                diverging_data[6], diverging_data[7],
                convergence_quality=diverging_data[8]
            )
    
    elif args.input:
        data = np.load(args.input)
        if args.mode == 'flux':
            X, Y, Z, U, V, W = data.reshape(6, -1)  # Assume flattened
        else:
            X, Y, Z, Temp = data.reshape(4, -1)
        
        if args.mode == 'flux':
            if args.interactive:
                plot_interactive_flux(X, Y, Z, U, V, W)
            else:
                plot_flux_map_static(X, Y, Z, U, V, W)
        else:
            if args.interactive:
                plot_interactive_thermal(X, Y, Z, Temp)
            else:
                plot_thermal_map_static(X, Y, Z, Temp)
    
    else:
        if args.mode == 'flux':
            X, Y, Z, U, V, W = generate_flux_map()
        else:
            X, Y, Z, Temp = generate_thermal_map()
        
        if args.mode == 'flux':
            if args.interactive:
                plot_interactive_flux(X, Y, Z, U, V, W)
            else:
                plot_flux_map_static(X, Y, Z, U, V, W)
        else:
            if args.interactive:
                plot_interactive_thermal(X, Y, Z, Temp)
            else:
                plot_thermal_map_static(X, Y, Z, Temp)


if __name__ == "__main__":
    main()
