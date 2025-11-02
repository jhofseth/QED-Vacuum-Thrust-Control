# testing/logging.py
# This module provides scripts for data logging during flights (simulated or real),
# post-flight analysis using Pandas, and visualization with Matplotlib (e.g., acceleration vs. power consumption).
# It includes a class for real-time logging and static methods for analysis and plotting.

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
import os
from typing import Dict, Optional

class FlightLogger:
    """
    Class for logging flight data in real-time using Pandas DataFrame.
    Columns include: timestamp, pos_x, pos_y, pos_z, vel_x, vel_y, vel_z,
    accel_x, accel_y, accel_z, power, temp, B_field_mag, B_opposing,
    thrust, frequency, mada_convergence_quality.
    """
    def __init__(self, log_dir: str = 'logs'):
        """
        Initialize the logger.
        
        :param log_dir: Directory to save log files.
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.columns = [
            'timestamp', 'pos_x', 'pos_y', 'pos_z',
            'vel_x', 'vel_y', 'vel_z',
            'accel_x', 'accel_y', 'accel_z',
            'power', 'temp', 
            'B_field_mag', 'B_opposing',  # Total field magnitude and opposing field strength
            'B1_x', 'B1_y', 'B1_z',  # Magnetic field vector 1 (MADA unit 1)
            'B2_x', 'B2_y', 'B2_z',  # Magnetic field vector 2 (MADA unit 2)
            'thrust', 'frequency', 
            'mada_convergence_quality'  # Quality metric for field convergence
        ]
        self.data = pd.DataFrame(columns=self.columns)
        self.start_time = time.time()
    
    def log(self, data_dict: Dict[str, float]):
        """
        Log a data point. Keys must match columns (partial dicts allowed; missing filled with NaN).
        
        :param data_dict: Dictionary with data (e.g., {'accel_x': 1.0, 'power': 100.0}).
        """
        current_time = time.time() - self.start_time
        row = pd.Series({'timestamp': current_time}, dtype=float)
        for col in self.columns[1:]:
            row[col] = data_dict.get(col, np.nan)
        
        # Calculate MADA convergence quality if field vectors are provided
        if all(key in data_dict for key in ['B1_x', 'B1_y', 'B1_z', 'B2_x', 'B2_y', 'B2_z']):
            convergence = self._calculate_convergence_quality(
                data_dict['B1_x'], data_dict['B1_y'], data_dict['B1_z'],
                data_dict['B2_x'], data_dict['B2_y'], data_dict['B2_z']
            )
            row['mada_convergence_quality'] = convergence
        
        self.data = pd.concat([self.data, row.to_frame().T], ignore_index=True)
    
    @staticmethod
    def _calculate_convergence_quality(B1_x: float, B1_y: float, B1_z: float,
                                       B2_x: float, B2_y: float, B2_z: float) -> float:
        """
        Calculate how well the magnetic fields are converging (opposing).
        Returns 1.0 for perfect opposition (pointing directly at each other),
        0.0 for perpendicular, -1.0 for parallel (both pointing same direction).
        
        :return: Convergence quality metric [-1, 1]
        """
        B1 = np.array([B1_x, B1_y, B1_z])
        B2 = np.array([B2_x, B2_y, B2_z])
        
        # Normalize vectors
        B1_mag = np.linalg.norm(B1)
        B2_mag = np.linalg.norm(B2)
        
        if B1_mag == 0 or B2_mag == 0:
            return 0.0
        
        B1_norm = B1 / B1_mag
        B2_norm = B2 / B2_mag
        
        # Dot product gives cos(angle): -1 means opposing (good), +1 means parallel (bad)
        dot_product = np.dot(B1_norm, B2_norm)
        
        # Return negative of dot product: 1.0 = opposing, -1.0 = parallel
        return -dot_product
    
    def save(self, filename: Optional[str] = None) -> str:
        """
        Save the logged data to CSV.
        
        :param filename: Optional filename; defaults to timestamped.
        :return: Path to saved file.
        """
        if filename is None:
            filename = f"flight_log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.log_dir, filename)
        self.data.to_csv(filepath, index=False)
        print(f"Data saved to {filepath}")
        return filepath
    
    @staticmethod
    def load_data(filepath: str) -> pd.DataFrame:
        """
        Load flight data from CSV.
        
        :param filepath: Path to CSV file.
        :return: Pandas DataFrame.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} not found.")
        df = pd.read_csv(filepath)
        
        # Compute magnitudes if not present
        if 'accel_mag' not in df.columns:
            df['accel_mag'] = np.sqrt(df['accel_x']**2 + df['accel_y']**2 + df['accel_z']**2)
        if 'vel_mag' not in df.columns:
            df['vel_mag'] = np.sqrt(df['vel_x']**2 + df['vel_y']**2 + df['vel_z']**2)
        
        # Recalculate convergence quality if vectors present but quality missing
        if 'mada_convergence_quality' not in df.columns or df['mada_convergence_quality'].isna().all():
            if all(col in df.columns for col in ['B1_x', 'B1_y', 'B1_z', 'B2_x', 'B2_y', 'B2_z']):
                df['mada_convergence_quality'] = df.apply(
                    lambda row: FlightLogger._calculate_convergence_quality(
                        row['B1_x'], row['B1_y'], row['B1_z'],
                        row['B2_x'], row['B2_y'], row['B2_z']
                    ), axis=1
                )
        
        return df
    
    @staticmethod
    def analyze_data(filepath: str, output_file: Optional[str] = None) -> Dict[str, float]:
        """
        Perform post-flight analysis: stats (mean, max, min), correlations, anomaly detection (e.g., temp >90°C).
        
        :param filepath: Path to CSV.
        :param output_file: Optional TXT file for report.
        :return: Dictionary of key stats.
        """
        df = FlightLogger.load_data(filepath)
        
        # Basic stats
        stats = {
            'mean_accel_mag': df['accel_mag'].mean(),
            'max_accel_mag': df['accel_mag'].max(),
            'mean_power': df['power'].mean(),
            'max_power': df['power'].max(),
            'mean_temp': df['temp'].mean(),
            'max_temp': df['temp'].max(),
            'mean_thrust': df['thrust'].mean(),
            'mean_B_opposing': df['B_opposing'].mean() if 'B_opposing' in df.columns else np.nan,
            'max_B_opposing': df['B_opposing'].max() if 'B_opposing' in df.columns else np.nan,
            'corr_accel_power': df['accel_mag'].corr(df['power']),
            'flight_duration': df['timestamp'].max() - df['timestamp'].min()
        }
        
        # MADA convergence analysis
        if 'mada_convergence_quality' in df.columns:
            stats['mean_convergence_quality'] = df['mada_convergence_quality'].mean()
            stats['min_convergence_quality'] = df['mada_convergence_quality'].min()
            poor_convergence = (df['mada_convergence_quality'] < 0.8).sum()
            stats['poor_convergence_events'] = poor_convergence
            if poor_convergence > 0:
                print(f"Warning: {poor_convergence} poor MADA convergence events (quality < 0.8).")
                print("This suggests magnetic fields may not be properly opposing!")
        
        # Anomaly detection
        high_temp_count = (df['temp'] > 90.0).sum()
        stats['high_temp_events'] = high_temp_count
        if high_temp_count > 0:
            print(f"Warning: {high_temp_count} high temperature events detected (>90°C).")
        
        # Save report if specified
        if output_file:
            with open(output_file, 'w') as f:
                for key, value in stats.items():
                    if isinstance(value, (int, float)) and not np.isnan(value):
                        f.write(f"{key}: {value:.2f}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            print(f"Analysis report saved to {output_file}")
        
        return stats
    
    @staticmethod
    def plot_accel_vs_power(filepath: str, save_fig: bool = True, fig_name: str = 'accel_vs_power.png'):
        """
        Plot acceleration magnitude vs. power consumption using Matplotlib.
        
        :param filepath: Path to CSV.
        :param save_fig: Whether to save the figure.
        :param fig_name: Filename for saved figure.
        """
        df = FlightLogger.load_data(filepath)
        
        plt.figure(figsize=(10, 6))
        plt.scatter(df['power'], df['accel_mag'], color='blue', alpha=0.5)
        plt.title('Acceleration vs. Power Consumption')
        plt.xlabel('Power (W)')
        plt.ylabel('Acceleration Magnitude (m/s²)')
        plt.grid(True)
        
        if save_fig:
            plt.savefig(fig_name)
            print(f"Plot saved to {fig_name}")
        plt.show()
    
    @staticmethod
    def plot_trajectory(filepath: str, save_fig: bool = True, fig_name: str = 'trajectory.png'):
        """
        3D plot of position trajectory.
        
        :param filepath: Path to CSV.
        :param save_fig: Whether to save.
        :param fig_name: Filename.
        """
        df = FlightLogger.load_data(filepath)
        
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.plot(df['pos_x'], df['pos_y'], df['pos_z'], 'b-')
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title('Flight Trajectory')
        
        if save_fig:
            plt.savefig(fig_name)
            print(f"Plot saved to {fig_name}")
        plt.show()
    
    @staticmethod
    def plot_temp_over_time(filepath: str, save_fig: bool = True, fig_name: str = 'temp_over_time.png'):
        """
        Plot temperature vs. time.
        
        :param filepath: Path to CSV.
        :param save_fig: Whether to save.
        :param fig_name: Filename.
        """
        df = FlightLogger.load_data(filepath)
        
        plt.figure(figsize=(10, 6))
        plt.plot(df['timestamp'], df['temp'], 'r-')
        plt.title('Temperature Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Temperature (°C)')
        plt.grid(True)
        
        if save_fig:
            plt.savefig(fig_name)
            print(f"Plot saved to {fig_name}")
        plt.show()
    
    @staticmethod
    def plot_mada_convergence(filepath: str, save_fig: bool = True, fig_name: str = 'mada_convergence.png'):
        """
        Plot MADA convergence quality over time to verify proper field opposition.
        
        :param filepath: Path to CSV.
        :param save_fig: Whether to save.
        :param fig_name: Filename.
        """
        df = FlightLogger.load_data(filepath)
        
        if 'mada_convergence_quality' not in df.columns:
            print("Warning: No MADA convergence data available in log file.")
            return
        
        plt.figure(figsize=(10, 6))
        plt.plot(df['timestamp'], df['mada_convergence_quality'], 'g-')
        plt.axhline(y=0.8, color='orange', linestyle='--', label='Minimum Quality Threshold')
        plt.axhline(y=1.0, color='blue', linestyle='--', label='Perfect Opposition')
        plt.title('MADA Magnetic Field Convergence Quality Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Convergence Quality (1.0 = perfect opposition)')
        plt.ylim(-1.1, 1.1)
        plt.legend()
        plt.grid(True)
        
        if save_fig:
            plt.savefig(fig_name)
            print(f"Plot saved to {fig_name}")
        plt.show()

# Example usage (demo)
if __name__ == "__main__":
    print("=" * 60)
    print("FLIGHT LOGGER DEMO - WITH MADA CONVERGENCE TRACKING")
    print("=" * 60)
    
    logger = FlightLogger()
    
    # Simulate logging 10 data points with proper opposing magnetic fields
    for i in range(10):
        # Simulate two MADA units with fields pointing toward center (opposing)
        # MADA 1 at position (+1, 0, 0) pointing toward origin: direction (-1, 0, 0)
        # MADA 2 at position (-1, 0, 0) pointing toward origin: direction (+1, 0, 0)
        B_magnitude = 50 + i
        
        demo_data = {
            'pos_x': i * 1.0, 'pos_y': i * 0.5, 'pos_z': i * 0.2,
            'vel_x': 1.0, 'vel_y': 0.5, 'vel_z': 0.2,
            'accel_x': 0.1 * i, 'accel_y': 0.05 * i, 'accel_z': 0.02 * i,
            'power': 100 + i * 10,
            'temp': 25 + i * 2,
            'B_field_mag': B_magnitude,
            'B_opposing': B_magnitude * 2,  # Combined opposing field strength
            'B1_x': -B_magnitude, 'B1_y': 0, 'B1_z': 0,  # Pointing left (toward center)
            'B2_x': B_magnitude, 'B2_y': 0, 'B2_z': 0,   # Pointing right (toward center)
            'thrust': 1000 + i * 100,
            'frequency': 100
        }
        logger.log(demo_data)
        time.sleep(0.1)  # Simulate time step
    
    filepath = logger.save('demo_log.csv')
    
    # Analyze
    stats = FlightLogger.analyze_data(filepath, 'demo_report.txt')
    print("\nKey Stats:")
    for key, value in stats.items():
        if isinstance(value, (int, float)) and not np.isnan(value):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Plots
    FlightLogger.plot_accel_vs_power(filepath)
    FlightLogger.plot_trajectory(filepath)
    FlightLogger.plot_temp_over_time(filepath)
    FlightLogger.plot_mada_convergence(filepath)
    
    print("\nDemo complete.")
