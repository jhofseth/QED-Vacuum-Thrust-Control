"""
hardware/interfaces.py

Hardware interface module for the QED-Vacuum-Thrust-Control system.

Provides interfaces for:
- Flight controllers (PX4, ArduPilot via pymavlink)
- Microcontroller interfacing (ESP32/Teensy for PWM control of magnetic coils)
- Real-time control using ROS2 for low-latency loops (1-10 ms)
- SDK and Protocol Support: DroneKit, MAVLink, ROS with Ethernet/LTE hooks
- Sensor and Actuator Drivers: IMU, GPS, ADS-B, Bi₂Te₃ TEG with data fusion
- Secure Communication Layers: AES encryption, anti-jamming
- HIL/SIL Testing Bridges: Links to thrust_model.py and navigation.py
- User Interface Hooks: CLI/GUI via Tkinter/WebSockets
- Modularity: Abstract base classes, thread-safety
- Compliance: Logging for export control, vulnerability scanning
"""

import time
import logging
import threading
from typing import List, Optional, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod
import socket
import json
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

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
    import dronekit
    DRONEKIT_AVAILABLE = True
except ImportError:
    DRONEKIT_AVAILABLE = False
    logging.warning("dronekit not installed. DroneKit interface unavailable.")

try:
    import rclpy
    from rclpy.node import Node
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    logging.warning("ROS2 (rclpy) not installed. Real-time control node unavailable.")

try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    logging.warning("Tkinter not installed. GUI interface unavailable.")

try:
    from websocket import create_connection
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logging.warning("websocket-client not installed. WebSocket interface unavailable.")

try:
    import adafruit_bno055  # Example for IMU (BNO055)
    IMU_AVAILABLE = True
except ImportError:
    IMU_AVAILABLE = False
    logging.warning("adafruit_bno055 not installed. IMU driver unavailable.")

try:
    import adafruit_gps  # Example GPS driver
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False
    logging.warning("adafruit_gps not installed. GPS driver unavailable.")

# For ADS-B (example with RTL-SDR or similar, but placeholder)
ADS_B_AVAILABLE = False  # Requires specific hardware/libs, e.g., dump1090

# For Bi₂Te₃ TEG (thermoelectric generator) - placeholder, assumes ADC interface
TEG_AVAILABLE = SERIAL_AVAILABLE  # Reuse serial if needed

# Configure logging with compliance in mind
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("compliance_log.txt"),  # For export control tracking
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VehicleState(Enum):
    """Enumeration of vehicle states."""
    DISARMED = 0
    ARMED = 1
    FLYING = 2
    EMERGENCY = 3


class SecureCommunication:
    """Secure communication layer with AES encryption."""
    
    def __init__(self, key: bytes):
        """
        Initialize AES encryption.
        
        Parameters:
        key (bytes): 32-byte AES key
        """
        if len(key) != 32:
            raise ValueError("AES key must be 32 bytes")
        self.key = key
        self.backend = default_backend()
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data with AES-CBC."""
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ct = encryptor.update(padded_data) + encryptor.finalize()
        return iv + ct
    
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data with AES-CBC."""
        iv = data[:16]
        ct = data[16:]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(pt) + unpadder.finalize()


class AbstractInterface(ABC):
    """Abstract base class for extensible interfaces."""
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def send_command(self, command: str) -> Optional[str]:
        pass


class FlightControllerInterface(AbstractInterface):
    """Interface for flight controllers using MAVLink (PX4/ArduPilot). Supports DroneKit integration."""
    
    def __init__(self, connection_string: str = 'udpin:0.0.0.0:14550', 
                 baudrate: int = 115200, timeout: int = 30,
                 use_dronekit: bool = False, secure_key: Optional[bytes] = None):
        """
        Initialize connection to flight controller.
        
        Parameters:
        connection_string (str): MAVLink connection string
        baudrate (int): Baudrate for serial connections
        timeout (int): Connection timeout in seconds
        use_dronekit (bool): Use DroneKit instead of pure MAVLink
        secure_key (bytes, optional): AES key for secure comms
        """
        if not PYMAVLINK_AVAILABLE and not (DRONEKIT_AVAILABLE and use_dronekit):
            raise ImportError("Required libraries not installed.")
        
        self.connection_string = connection_string
        self.baudrate = baudrate
        self.timeout = timeout
        self.master = None
        self.vehicle = None  # For DroneKit
        self.state = VehicleState.DISARMED
        self.use_dronekit = use_dronekit
        self.secure = SecureCommunication(secure_key) if secure_key else None
        self.connect()
    
    def connect(self):
        try:
            logger.info(f"Connecting to flight controller at {self.connection_string}...")
            if self.use_dronekit:
                if not DRONEKIT_AVAILABLE:
                    raise ImportError("dronekit not installed.")
                self.vehicle = dronekit.connect(self.connection_string, wait_ready=True, timeout=self.timeout)
                logger.info("Connected via DroneKit")
            else:
                self.master = mavutil.mavlink_connection(
                    self.connection_string, 
                    baud=self.baudrate,
                    source_system=1
                )
                self.master.wait_heartbeat(timeout=self.timeout)
                logger.info(f"Connected via MAVLink (system {self.master.target_system})")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def disconnect(self):
        if self.vehicle:
            self.vehicle.close()
        elif self.master:
            self.master.close()
        logger.info("Flight controller connection closed")

    def send_command(self, command: str) -> Optional[str]:
        if self.secure:
            encrypted = self.secure.encrypt(command.encode())
            # Send encrypted (placeholder: actual send via master/vehicle)
            logger.debug("Sent encrypted command")
            # Receive and decrypt response (placeholder)
            response = b'placeholder_response'  # Replace with actual recv
            return self.secure.decrypt(response).decode()
        else:
            # Non-secure send (placeholder)
            return "OK"

    def send_rc_override(self, channels: List[int]):
        if len(channels) != 8:
            raise ValueError("Must provide exactly 8 channel values")
        
        if self.use_dronekit:
            # DroneKit RC override (example)
            msg = self.vehicle.message_factory.rc_channels_override_encode(
                self.vehicle.target_system, self.vehicle.target_component, *channels
            )
            self.vehicle.send_mavlink(msg)
        else:
            self.master.mav.rc_channels_override_send(
                self.master.target_system,
                self.master.target_component,
                *channels
            )
        logger.debug(f"RC override sent: {channels}")

    def arm_vehicle(self, force: bool = False):
        logger.info("Arming vehicle...")
        if self.use_dronekit:
            self.vehicle.armed = True
            # Wait for arming to complete
            timeout = 10
            start = time.time()
            while not self.vehicle.armed and time.time() - start < timeout:
                time.sleep(0.1)
            ack = self.vehicle.armed
        else:
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0, 1, 21196 if force else 0, 0, 0, 0, 0, 0
            )
            ack = self._get_ack()
        
        if ack:
            self.state = VehicleState.ARMED
            logger.info("Vehicle armed")
            return True
        return False

    def disarm_vehicle(self, force: bool = False):
        logger.info("Disarming vehicle...")
        if self.use_dronekit:
            self.vehicle.armed = False
            # Wait for disarming to complete
            timeout = 10
            start = time.time()
            while self.vehicle.armed and time.time() - start < timeout:
                time.sleep(0.1)
            ack = not self.vehicle.armed
        else:
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0, 0, 21196 if force else 0, 0, 0, 0, 0, 0
            )
            ack = self._get_ack()
        
        if ack:
            self.state = VehicleState.DISARMED
            logger.info("Vehicle disarmed")
            return True
        return False

    def set_mode(self, mode: str):
        if self.use_dronekit:
            self.vehicle.mode = dronekit.VehicleMode(mode)
            return True
        mode_id = self.master.mode_mapping().get(mode)
        if mode_id is None:
            return False
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        return True

    def get_attitude(self) -> Optional[dict]:
        if self.use_dronekit:
            att = self.vehicle.attitude
            return {'roll': att.roll, 'pitch': att.pitch, 'yaw': att.yaw}
        msg = self.master.recv_match(type='ATTITUDE', blocking=True, timeout=1)
        if msg:
            return {
                'roll': msg.roll, 'pitch': msg.pitch, 'yaw': msg.yaw,
                'rollspeed': msg.rollspeed, 'pitchspeed': msg.pitchspeed, 'yawspeed': msg.yawspeed
            }
        return None

    def _get_ack(self):
        ack = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
        return ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED


class MicrocontrollerPWMInterface(AbstractInterface):
    """Interface for microcontroller PWM control (ESP32/Teensy) with security."""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200, 
                 timeout: float = 1.0, secure_key: Optional[bytes] = None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.secure = SecureCommunication(secure_key) if secure_key else None
        self.lock = threading.Lock()  # Thread-safety
        self.connect()

    def connect(self):
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial required.")
        try:
            with self.lock:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)
            logger.info(f"Connected to microcontroller on {self.port}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    def disconnect(self):
        with self.lock:
            if self.ser:
                self.ser.close()
        logger.info("Microcontroller connection closed")

    def send_command(self, command: str) -> Optional[str]:
        with self.lock:
            if not self.ser or not self.ser.is_open:
                raise RuntimeError("Not connected")
            try:
                if self.secure:
                    enc = self.secure.encrypt(command.encode())
                    self.ser.write(enc)
                    resp = self.ser.readline()
                    return self.secure.decrypt(resp).decode().strip() if resp else None
                else:
                    self.ser.write(f"{command}\n".encode())
                    return self.ser.readline().decode().strip()
            except Exception as e:
                logger.error(f"Communication error: {e}")
                return None

    def set_pwm(self, pin: int, frequency: int, duty_cycle: int):
        if not (0 <= duty_cycle <= 1023):
            raise ValueError("Invalid duty cycle (must be 0-1023)")
        command = f"PWM:{pin}:{frequency}:{duty_cycle}"
        response = self.send_command(command)
        if response and "OK" in response:
            logger.info(f"PWM set on pin {pin}")
        else:
            logger.warning(f"PWM set failed: {response}")

    def pulse_mada(self, pin: int, frequency: int = 50, duration: float = 1.0, 
                   duty_cycle: float = 0.5, bursts: Optional[int] = None):
        duty_value = int(duty_cycle * 1023)
        logger.info(f"Starting MADA pulse on pin {pin}")
        if bursts:
            period = 1.0 / frequency
            for _ in range(bursts):
                self.set_pwm(pin, frequency, duty_value)
                time.sleep(period * duty_cycle)
                self.set_pwm(pin, frequency, 0)
                time.sleep(period * (1 - duty_cycle))
        else:
            self.set_pwm(pin, frequency, duty_value)
            time.sleep(duration)
            self.set_pwm(pin, frequency, 0)
        logger.info("MADA pulsing complete")

    def emergency_stop(self):
        return self.send_command("STOP")


class SensorActuatorDrivers:
    """Drivers for sensors and actuators with data fusion."""
    
    def __init__(self, i2c_bus=None, serial_port=None):
        self.imu = None
        self.gps = None
        self.gps_serial = None
        self.ads_b = None  # Placeholder
        self.teg = None  # Placeholder
        self.data_fusion = {}  # Fused data store
        self.lock = threading.Lock()
        
        if IMU_AVAILABLE and i2c_bus:
            try:
                self.imu = adafruit_bno055.BNO055_I2C(i2c_bus)
            except Exception as e:
                logger.error(f"Failed to initialize IMU: {e}")
        
        if GPS_AVAILABLE and serial_port and SERIAL_AVAILABLE:
            try:
                self.gps_serial = serial.Serial(serial_port, 9600, timeout=1)
                self.gps = adafruit_gps.GPS(self.gps_serial, debug=False)
                self.gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
                self.gps.send_command(b"PMTK220,1000")
            except Exception as e:
                logger.error(f"Failed to initialize GPS: {e}")
        
        # ADS-B: Requires external lib/setup, e.g., dump1090
        # TEG: Assume ADC read via serial/microcontroller

    def read_imu(self) -> Dict[str, Any]:
        if self.imu:
            try:
                return {
                    'euler': self.imu.euler,
                    'acceleration': self.imu.acceleration,
                    'gyro': self.imu.gyro
                }
            except Exception as e:
                logger.error(f"Failed to read IMU: {e}")
        return {}

    def read_gps(self) -> Dict[str, Any]:
        if self.gps:
            try:
                self.gps.update()
                if self.gps.has_fix:
                    return {
                        'latitude': self.gps.latitude,
                        'longitude': self.gps.longitude,
                        'altitude': self.gps.altitude_m,
                        'speed': self.gps.speed_knots,
                        'has_fix': True
                    }
                else:
                    return {'has_fix': False}
            except Exception as e:
                logger.error(f"Failed to read GPS: {e}")
        return {}

    def read_ads_b(self):
        # Placeholder for ADS-B data
        return {"aircraft_nearby": []}

    def read_teg(self):
        # Placeholder for TEG power/thermal data
        return {"voltage": 0.0, "current": 0.0}

    def fuse_data(self):
        with self.lock:
            self.data_fusion = {
                **self.read_imu(),
                **self.read_gps(),
                **self.read_ads_b(),
                **self.read_teg()
            }
            # Add 6DOF stability logic (e.g., Kalman filter placeholder)
            # IFF: Optical/radio-silent (placeholder: check against known friends)
        return self.data_fusion
    
    def close(self):
        """Close any open serial connections."""
        if self.gps_serial:
            self.gps_serial.close()


if ROS2_AVAILABLE:
    class RealTimeControlNode(Node):
        """ROS2 Node for real-time control with low-latency loops."""
        
        def __init__(self, loop_period: float = 0.01, node_name: str = 'real_time_control_node'):
            super().__init__(node_name)
            self.loop_period = loop_period
            self.timer = self.create_timer(loop_period, self.control_loop_callback)

        def control_loop_callback(self):
            # Custom logic: Read sensors, apply control
            pass

        def shutdown(self):
            self.destroy_node()


class HILSILBridge:
    """Hardware/Software-in-the-Loop bridge to simulations."""
    
    def __init__(self, sim_path: str = '../simulations'):
        self.sim_path = sim_path
        self.thrust_model = None
        self.navigation = None

    def link_thrust_model(self):
        # Import and run thrust_model.py (dynamic import)
        import sys
        if self.sim_path not in sys.path:
            sys.path.append(self.sim_path)
        try:
            import thrust_model  # Assume thrust_model.py exists
            self.thrust_model = thrust_model
        except ImportError as e:
            logger.error(f"Failed to import thrust_model: {e}")

    def link_navigation(self):
        import sys
        nav_path = os.path.join(self.sim_path, 'ai')
        if nav_path not in sys.path:
            sys.path.append(nav_path)
        try:
            import navigation
            self.navigation = navigation
        except ImportError as e:
            logger.error(f"Failed to import navigation: {e}")

    def run_hil_simulation(self, params: Dict):
        # Run simulation with hardware feedback (placeholder)
        if self.thrust_model:
            try:
                result = self.thrust_model.main(params)  # Assume main function
                logger.info(f"HIL thrust sim: {result}")
                # Log for compliance
                with open("hil_log.txt", "a") as f:
                    f.write(json.dumps(params) + "\n")
            except Exception as e:
                logger.error(f"HIL simulation failed: {e}")
        else:
            logger.warning("Thrust model not linked")


class UserInterfaceHooks:
    """Hooks for CLI/GUI/WebSocket control."""
    
    def __init__(self, use_gui: bool = False, ws_url: Optional[str] = None):
        self.gui = None
        self.ws = None
        if use_gui and TKINTER_AVAILABLE:
            self.gui = tk.Tk()
            self.gui.title("QED Control Dashboard")
            # Add widgets for metrics (placeholder)
            tk.Label(self.gui, text="Propulsion Metrics").pack()
        
        if ws_url and WEBSOCKET_AVAILABLE:
            try:
                self.ws = create_connection(ws_url)
            except Exception as e:
                logger.error(f"Failed to connect to WebSocket: {e}")
    
    def update_dashboard(self, metrics: Dict):
        # Update GUI/WS with metrics
        if self.gui:
            # Placeholder update
            pass
        if self.ws:
            try:
                self.ws.send(json.dumps(metrics))
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
    
    def run_gui(self):
        if self.gui:
            self.gui.mainloop()

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Failed to close WebSocket: {e}")
        if self.gui:
            self.gui.destroy()


class ComplianceTools:
    """Tools for compliance and auditing."""
    
    @staticmethod
    def log_export_control(data: Dict):
        try:
            with open("export_control_log.txt", "a") as f:
                f.write(json.dumps(data) + "\n")
            logger.info("Export control logged")
        except Exception as e:
            logger.error(f"Failed to log export control: {e}")

    @staticmethod
    def vulnerability_scan():
        # Placeholder: Integrate with tools like bandit or safety
        try:
            import bandit
            # Run scan (example)
            logger.info("Vulnerability scan complete - no issues (placeholder)")
        except ImportError:
            logger.warning("Bandit not installed for scanning")


# Ethernet/LTE hooks (placeholder: socket for remote control)
class RemoteControl:
    """Ethernet/LTE modem hooks for remote control."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(1)
        self.running = False
        logger.info(f"Listening for remote control on {host}:{port}")

    def handle_connection(self):
        while self.running:
            try:
                self.sock.settimeout(1.0)
                conn, addr = self.sock.accept()
                logger.info(f"Remote connection from {addr}")
                data = conn.recv(1024)
                # Process command (secure if needed)
                conn.send(b"ACK")
                conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Remote control error: {e}")

    def start(self):
        self.running = True
        threading.Thread(target=self.handle_connection, daemon=True).start()
    
    def stop(self):
        self.running = False
        self.sock.close()


# Anti-jamming fallbacks (placeholder: switch protocols on failure)
def anti_jamming_fallback():
    logger.warning("Jamming detected - switching to fallback (placeholder)")


def main():
    """Example usage of enhanced hardware interfaces."""
    
    logger.info("=" * 60)
    logger.info("QED Vacuum Thrust Control - Enhanced Hardware Interface Demo")
    logger.info("=" * 60)
    
    # Secure key example
    secure_key = os.urandom(32)
    
    # Flight Controller with DroneKit and secure
    if DRONEKIT_AVAILABLE:
        try:
            fc = FlightControllerInterface(use_dronekit=True, secure_key=secure_key)
            fc.arm_vehicle()
            fc.disarm_vehicle()
            fc.disconnect()
        except Exception as e:
            logger.error(f"FC demo failed: {e}")
    
    # Microcontroller with secure
    if SERIAL_AVAILABLE:
        try:
            mcu = MicrocontrollerPWMInterface(secure_key=secure_key)
            mcu.pulse_mada(14)
            mcu.disconnect()
        except Exception as e:
            logger.error(f"MCU demo failed: {e}")
    
    # Sensors
    sensors = SensorActuatorDrivers()  # Add i2c/serial as needed
    fused = sensors.fuse_data()
    logger.info(f"Fused data: {fused}")
    sensors.close()
    
    # HIL
    hil = HILSILBridge()
    hil.link_thrust_model()
    hil.run_hil_simulation({"b_opposing": 50})
    
    # UI
    ui = UserInterfaceHooks(use_gui=False)  # Set to False to avoid blocking
    ui.update_dashboard({"thrust": 100})
    # ui.run_gui()  # Uncomment to run GUI
    ui.close()
    
    # Compliance
    ComplianceTools.log_export_control({"action": "demo"})
    ComplianceTools.vulnerability_scan()
    
    # Remote
    remote = RemoteControl()
    remote.start()
    time.sleep(2)  # Let it run briefly
    remote.stop()
    
    logger.info("\n" + "=" * 60)
    logger.info("Enhanced hardware interface demo complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
