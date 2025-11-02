"""
hardware/interfaces.py

Hardware interface module for the QED-Vacuum-Thrust-Control system.

Provides interfaces for:
- Flight controllers (PX4, ArduPilot via pymavlink)
- Microcontroller interfacing (ESP32/Teensy for PWM control of magnetic coils)
- Real-time control using ROS2 for low-latency loops (1-10 ms)
"""

import time
import logging
from typing import List, Optional
from enum import Enum

# Optional imports - gracefully handle if not installed
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logging.warning("pyserial not installed. Microcontroller interface unavailable.")

try:
    from pymavlink import mavutil
    PYMAVLINK_AVAILABLE = True
except ImportError:
    PYMAVLINK_AVAILABLE = False
    logging.warning("pymavlink not installed. Flight controller interface unavailable.")

try:
    import rclpy
    from rclpy.node import Node
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    logging.warning("ROS2 (rclpy) not installed. Real-time control node unavailable.")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VehicleState(Enum):
    """Enumeration of vehicle states."""
    DISARMED = 0
    ARMED = 1
    FLYING = 2
    EMERGENCY = 3


class FlightControllerInterface:
    """Interface for flight controllers using MAVLink (PX4/ArduPilot)."""
    
    def __init__(self, connection_string: str = 'udpin:0.0.0.0:14550', 
                 baudrate: int = 115200, timeout: int = 30):
        """
        Initialize connection to flight controller.
        
        Parameters:
        connection_string (str): MAVLink connection string
            Examples:
            - UDP: 'udpin:0.0.0.0:14550'
            - Serial: '/dev/ttyUSB0'
            - TCP: 'tcp:127.0.0.1:5760'
        baudrate (int): Baudrate for serial connections
        timeout (int): Connection timeout in seconds
        """
        if not PYMAVLINK_AVAILABLE:
            raise ImportError("pymavlink not installed. Install with: pip install pymavlink")
        
        self.connection_string = connection_string
        self.baudrate = baudrate
        self.master = None
        self.state = VehicleState.DISARMED
        
        try:
            logger.info(f"Connecting to flight controller at {connection_string}...")
            self.master = mavutil.mavlink_connection(
                connection_string, 
                baud=baudrate,
                source_system=1
            )
            
            # Wait for heartbeat with timeout
            logger.info("Waiting for heartbeat...")
            self.master.wait_heartbeat(timeout=timeout)
            logger.info(f"Connected to flight controller (system {self.master.target_system}, "
                       f"component {self.master.target_component})")
        except Exception as e:
            logger.error(f"Failed to connect to flight controller: {e}")
            raise

    def send_rc_override(self, channels: List[int]):
        """
        Send RC channel override command.
        
        Parameters:
        channels (List[int]): List of 8 channel values (1000-2000, or 0 to release)
            Example: [1500, 1500, 1500, 1500, 0, 0, 0, 0]
        """
        if len(channels) != 8:
            raise ValueError("Must provide exactly 8 channel values")
        
        if not all(0 <= ch <= 2000 for ch in channels):
            raise ValueError("Channel values must be between 0 and 2000")
        
        self.master.mav.rc_channels_override_send(
            self.master.target_system,
            self.master.target_component,
            *channels
        )
        logger.debug(f"RC override sent: {channels}")

    def arm_vehicle(self, force: bool = False):
        """
        Arm the vehicle.
        
        Parameters:
        force (bool): Force arming (bypass pre-arm checks)
        """
        logger.info("Arming vehicle...")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            1,  # arm
            21196 if force else 0,  # force arm magic number
            0, 0, 0, 0, 0
        )
        
        # Wait for ACK
        ack = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
        if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            self.state = VehicleState.ARMED
            logger.info("Vehicle armed successfully")
            return True
        else:
            logger.error("Failed to arm vehicle")
            return False

    def disarm_vehicle(self, force: bool = False):
        """
        Disarm the vehicle.
        
        Parameters:
        force (bool): Force disarming
        """
        logger.info("Disarming vehicle...")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            0,  # disarm
            21196 if force else 0,  # force disarm magic number
            0, 0, 0, 0, 0
        )
        
        # Wait for ACK
        ack = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
        if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            self.state = VehicleState.DISARMED
            logger.info("Vehicle disarmed successfully")
            return True
        else:
            logger.error("Failed to disarm vehicle")
            return False

    def set_mode(self, mode: str):
        """
        Set flight mode.
        
        Parameters:
        mode (str): Flight mode name (e.g., 'GUIDED', 'STABILIZE', 'LOITER')
        """
        # Get mode ID
        mode_id = self.master.mode_mapping().get(mode)
        if mode_id is None:
            logger.error(f"Unknown mode: {mode}")
            return False
        
        logger.info(f"Setting mode to {mode}...")
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        return True

    def get_attitude(self) -> Optional[dict]:
        """
        Get current attitude (roll, pitch, yaw).
        
        Returns:
        dict: {'roll': float, 'pitch': float, 'yaw': float} in radians
        """
        msg = self.master.recv_match(type='ATTITUDE', blocking=True, timeout=1)
        if msg:
            return {
                'roll': msg.roll,
                'pitch': msg.pitch,
                'yaw': msg.yaw,
                'rollspeed': msg.rollspeed,
                'pitchspeed': msg.pitchspeed,
                'yawspeed': msg.yawspeed
            }
        return None

    def close(self):
        """Close the MAVLink connection."""
        if self.master:
            self.master.close()
            logger.info("Flight controller connection closed")


class MicrocontrollerPWMInterface:
    """Interface for microcontroller PWM control (ESP32/Teensy)."""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200, 
                 timeout: float = 1.0):
        """
        Initialize serial connection to microcontroller.
        
        Parameters:
        port (str): Serial port (e.g., '/dev/ttyUSB0', 'COM3')
        baudrate (int): Baudrate for serial communication
        timeout (float): Read timeout in seconds
        """
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial not installed. Install with: pip install pyserial")
        
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
        try:
            logger.info(f"Connecting to microcontroller on {port}...")
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # Wait for microcontroller to initialize
            
            # Flush buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            logger.info(f"Connected to microcontroller on {port}")
        except serial.SerialException as e:
            logger.error(f"Failed to connect to microcontroller: {e}")
            raise

    def send_command(self, command: str) -> Optional[str]:
        """
        Send command to microcontroller and read response.
        
        Parameters:
        command (str): Command string to send
        
        Returns:
        str: Response from microcontroller
        """
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial connection not open")
        
        try:
            # Send command
            self.ser.write(f"{command}\n".encode())
            self.ser.flush()
            
            # Read response
            response = self.ser.readline().decode().strip()
            logger.debug(f"Sent: {command}, Received: {response}")
            return response
        except Exception as e:
            logger.error(f"Error communicating with microcontroller: {e}")
            return None

    def set_pwm(self, pin: int, frequency: int, duty_cycle: int):
        """
        Set PWM on a specific pin.
        
        Parameters:
        pin (int): GPIO pin number
        frequency (int): PWM frequency in Hz (e.g., 50-100 Hz for MADA pulsing)
        duty_cycle (int): Duty cycle (0-1023 for ESP32, 0-255 for Arduino)
        
        Note: Assumes microcontroller is programmed to parse 'PWM:<pin>:<freq>:<duty>'
        """
        if not (0 <= duty_cycle <= 1023):
            raise ValueError("Duty cycle must be between 0 and 1023")
        
        if frequency < 0:
            raise ValueError("Frequency must be positive")
        
        command = f"PWM:{pin}:{frequency}:{duty_cycle}"
        response = self.send_command(command)
        
        if response and "OK" in response:
            logger.info(f"Set PWM on pin {pin}: {frequency}Hz, duty={duty_cycle}")
        else:
            logger.warning(f"PWM command may have failed: {response}")

    def pulse_mada(self, pin: int, frequency: int = 50, duration: float = 1.0, 
                   duty_cycle: float = 0.5, bursts: Optional[int] = None):
        """
        Pulse MADA (Magnetic Amplification and Direction Assembly).
        
        Parameters:
        pin (int): GPIO pin connected to electromagnet driver
        frequency (int): Pulsing frequency (50-100 Hz nominal, up to 1 kHz for bursts)
        duration (float): Total pulsing duration in seconds
        duty_cycle (float): Duty cycle (0.0-1.0, typically 0.2-0.8)
        bursts (int, optional): Number of discrete bursts (if None, continuous)
        """
        if not (0.0 <= duty_cycle <= 1.0):
            raise ValueError("Duty cycle must be between 0.0 and 1.0")
        
        logger.info(f"Starting MADA pulse: {frequency}Hz, {duration}s, "
                   f"duty={duty_cycle*100:.1f}%")
        
        duty_value = int(duty_cycle * 1023)  # Convert to ESP32 range
        
        if bursts:
            # Discrete bursts
            period = 1.0 / frequency
            for i in range(bursts):
                self.set_pwm(pin, frequency, duty_value)
                time.sleep(period * duty_cycle)
                self.set_pwm(pin, frequency, 0)
                time.sleep(period * (1 - duty_cycle))
                
                if (i + 1) % 10 == 0:
                    logger.debug(f"Completed {i+1}/{bursts} bursts")
        else:
            # Continuous pulsing
            self.set_pwm(pin, frequency, duty_value)
            time.sleep(duration)
            self.set_pwm(pin, frequency, 0)
        
        logger.info("MADA pulsing complete")

    def emergency_stop(self):
        """Emergency stop - set all PWM outputs to zero."""
        logger.warning("EMERGENCY STOP - Disabling all PWM outputs")
        response = self.send_command("STOP")
        return response

    def close(self):
        """Close serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Microcontroller connection closed")


if ROS2_AVAILABLE:
    class RealTimeControlNode(Node):
        """ROS2 Node for real-time control with low-latency loops."""
        
        def __init__(self, loop_period: float = 0.01, node_name: str = 'real_time_control_node'):
            """
            Initialize real-time control node.
            
            Parameters:
            loop_period (float): Timer period in seconds (0.001=1ms, 0.01=10ms)
            node_name (str): ROS2 node name
            """
            super().__init__(node_name)
            
            self.loop_period = loop_period
            self.loop_count = 0
            self.timer = self.create_timer(loop_period, self.control_loop_callback)
            
            loop_freq = 1.0 / loop_period
            self.get_logger().info(
                f"Real-time control node started: {loop_period*1000:.2f}ms "
                f"({loop_freq:.1f}Hz)"
            )

        def control_loop_callback(self):
            """
            Low-latency control loop callback.
            
            Override this method to implement custom control logic:
            - Read sensors
            - Update control outputs
            - Adjust PWM signals
            - Log telemetry
            """
            self.loop_count += 1
            
            # Example: Log every second
            if self.loop_count % int(1.0 / self.loop_period) == 0:
                self.get_logger().info(
                    f"Control loop running: {self.loop_count} iterations"
                )
            
            # TODO: Add custom control logic here
            # Example:
            # - sensor_data = self.read_sensors()
            # - control_output = self.compute_control(sensor_data)
            # - self.apply_control(control_output)

        def shutdown(self):
            """Graceful shutdown."""
            self.get_logger().info("Shutting down real-time control node")
            self.destroy_node()


def main():
    """Example usage of hardware interfaces."""
    
    logger.info("=" * 60)
    logger.info("QED Vacuum Thrust Control - Hardware Interface Demo")
    logger.info("=" * 60)
    
    # Example 1: Flight Controller Interface
    if PYMAVLINK_AVAILABLE:
        try:
            logger.info("\n--- Flight Controller Interface ---")
            fc = FlightControllerInterface(connection_string='udpin:0.0.0.0:14550')
            
            # Get attitude
            attitude = fc.get_attitude()
            if attitude:
                logger.info(f"Current attitude: {attitude}")
            
            # Arm and disarm
            fc.arm_vehicle()
            time.sleep(2)
            fc.disarm_vehicle()
            
            fc.close()
        except Exception as e:
            logger.error(f"Flight controller demo failed: {e}")
    
    # Example 2: Microcontroller PWM Interface
    if SERIAL_AVAILABLE:
        try:
            logger.info("\n--- Microcontroller PWM Interface ---")
            mcu = MicrocontrollerPWMInterface(port='/dev/ttyUSB0')
            
            # Pulse MADA at 100 Hz
            mcu.pulse_mada(pin=14, frequency=100, duration=2.0, duty_cycle=0.5)
            
            mcu.close()
        except Exception as e:
            logger.error(f"Microcontroller demo failed: {e}")
    
    # Example 3: ROS2 Real-Time Control
    if ROS2_AVAILABLE:
        try:
            logger.info("\n--- ROS2 Real-Time Control Node ---")
            rclpy.init()
            
            node = RealTimeControlNode(loop_period=0.005)  # 5ms loop (200Hz)
            
            # Run for 5 seconds
            rclpy.spin_once(node, timeout_sec=5.0)
            
            node.shutdown()
            rclpy.shutdown()
        except Exception as e:
            logger.error(f"ROS2 demo failed: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Hardware interface demo complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
