# cad/flux_visualizer.py
# This module provides rendering scripts for visualizing magnetic flux maps,
# thermal dissipation, and interactive 3D views of the spherical drone prototype.
# Uses Matplotlib for static plots and Plotly for interactive visualizations.
# Assumes data from simulations (e.g., B fields from equations.py) or CAD exports.
# Example usage: python flux_visualizer.py --mode flux --input data.npy

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import plotly.graph_objects as go
import argparse
import os

# Example data generation functions (placeholders; integrate with equations.py or CAD)

def generate_flux_map(grid_size=50, B_opposing=50.0, position=(0,0,0)):
    """
    Generate a 3D magnetic flux map (vector field) around a point source.
    
    Parameters:
    grid_size (int): Grid resolution
    B_opposing (float): Opposing field strength (T)
    position (tuple): Center position (x,y,z)
    
    Returns:
    tuple: (X, Y, Z, U, V, W) for vector field
    """
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
    parser.add_argument("--mode", type=str, choices=['flux', 'thermal'], required=True,
                        help="Visualization mode: flux or thermal")
    parser.add_argument("--interactive", action="store_true",
                        help="Use interactive Plotly view")
    parser.add_argument("--input", type=str, default=None,
                        help="Optional numpy file for data (shape: (grid_size^3, 6) for flux or 4 for thermal)")
    
    args = parser.parse_args()
    
    if args.input:
        data = np.load(args.input)
        if args.mode == 'flux':
            X, Y, Z, U, V, W = data.reshape(6, -1)  # Assume flattened
        else:
            X, Y, Z, Temp = data.reshape(4, -1)
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
