# hardware/interfaces.py
# This module provides interfaces for hardware components in the QED-Vacuum-Thrust-Control system.
# It includes support for flight controllers (PX4, ArduPilot via pymavlink), microcontroller interfacing
# (e.g., ESP32 for PWM control of magnetic coils/electromagnets), and real-time control using ROS2 for
# low-latency loops (1-10 ms).

import time
import serial
from pymavlink import mavutil
import rclpy
from rclpy.node import Node

# Flight Controller Interface using pymavlink for PX4 or ArduPilot
class FlightControllerInterface:
    def __init__(self, connection_string='udpin:0.0.0.0:14550', baudrate=115200):
        """
        Initialize connection to flight controller (e.g., PX4 or ArduPilot).
        :param connection_string: MAVLink connection string (e.g., 'udpin:0.0.0.0:14550' for UDP).
        :param baudrate: Baudrate for serial connections.
        """
        self.master = mavutil.mavlink_connection(connection_string, baud=baudrate)
        self.master.wait_heartbeat()
        print("Connected to flight controller.")

    def send_rc_override(self, channels):
        """
        Send RC channel override command (e.g., for controlling drone inputs).
        :param channels: List of 8 channel values (e.g., [1500, 1500, 1500, 1500, 0, 0, 0, 0]).
        """
        self.master.mav.rc_channels_override_send(
            self.master.target_system,
            self.master.target_component,
            *channels
        )

    def arm_vehicle(self):
        """Arm the vehicle."""
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 0, 0, 0, 0, 0, 0
        )

    def disarm_vehicle(self):
        """Disarm the vehicle."""
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 0, 0, 0, 0, 0, 0
        )

# Microcontroller Interface for PWM control (e.g., ESP32 or Teensy via serial)
class MicrocontrollerPWMInterface:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        """
        Initialize serial connection to microcontroller (e.g., ESP32) for PWM control.
        :param port: Serial port (e.g., '/dev/ttyUSB0').
        :param baudrate: Baudrate for serial communication.
        """
        self.ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to microcontroller on {port}.")

    def set_pwm(self, pin, frequency, duty_cycle):
        """
        Send command to set PWM on a specific pin.
        Assumes microcontroller is programmed to parse commands like 'PWM:<pin>:<freq>:<duty>\n'.
        :param pin: GPIO pin number.
        :param frequency: PWM frequency (e.g., 50-100 Hz for MADA pulsing).
        :param duty_cycle: Duty cycle (0-1023 for ESP32).
        """
        command = f"PWM:{pin}:{frequency}:{duty_cycle}\n"
        self.ser.write(command.encode())
        response = self.ser.readline().decode().strip()
        print(f"Response: {response}")

    def pulse_mada(self, pin, frequency=50, duration=1.0, bursts=10):
        """
        Example for MADA pulsing: Pulse at 50-100 Hz for efficiency.
        :param pin: GPIO pin connected to electromagnet.
        :param frequency: Pulsing frequency (Hz).
        :param duration: Total duration in seconds.
        :param bursts: Number of bursts (up to 1 kHz).
        """
        period = 1.0 / frequency
        for _ in range(bursts):
            self.set_pwm(pin, frequency, 512)  # 50% duty cycle for pulsing
            time.sleep(period / 2)
            self.set_pwm(pin, frequency, 0)    # Off
            time.sleep(period / 2)
        print("MADA pulsing complete.")

    def close(self):
        """Close serial connection."""
        self.ser.close()

# Real-Time Control Node using ROS2 for low-latency loops
class RealTimeControlNode(Node):
    def __init__(self, loop_period=0.01):  # Default 10 ms loop (100 Hz)
        """
        ROS2 Node for real-time control with low-latency loops (1-10 ms).
        :param loop_period: Timer period in seconds (e.g., 0.001 for 1 ms, 0.01 for 10 ms).
        """
        super().__init__('real_time_control_node')
        self.timer = self.create_timer(loop_period, self.control_loop_callback)
        self.get_logger().info(f"Real-time control node started with {loop_period * 1000} ms loop.")

    def control_loop_callback(self):
        """Callback for low-latency control loop. Implement custom logic here."""
        self.get_logger().info("Executing control loop...")
        # Add custom control logic, e.g., read sensors, adjust PWM, etc.

def main():
    """Example usage of the interfaces."""
    # Initialize ROS2 if using real-time node
    rclpy.init()

    # Example: Flight Controller
    fc = FlightControllerInterface()
    fc.arm_vehicle()
    time.sleep(1)
    fc.disarm_vehicle()

    # Example: Microcontroller PWM for electromagnets
    mcu = MicrocontrollerPWMInterface(port='/dev/ttyUSB0')
    mcu.pulse_mada(pin=14, frequency=100)  # Pulse on GPIO 14 at 100 Hz
    mcu.close()

    # Example: ROS2 Real-Time Node
    node = RealTimeControlNode(loop_period=0.005)  # 5 ms loop
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
