"""
hardware/mada_gpio_controller.py

Raspberry Pi GPIO controller for MADA (Magnetic Amplification and Direction Assembly) units.
Provides independent control of azimuth and elevation stepper motors for each MADA.

HARDWARE REQUIREMENTS:
- Raspberry Pi 5 (or 4/3B+ with GPIO)
- DRV8825 or A4988 stepper drivers (one per axis)
- NEMA 17 stepper motors (200 steps/rev recommended)
- 12V/24V power supply for motors

PIN ASSIGNMENTS:
- Dynamically generated based on num_madas
- Uses BCM GPIO numbering
- Avoids reserved pins (I2C: 2,3; SPI: 7-11)
- 4 pins per MADA: az_dir, az_step, el_dir, el_step

INTEGRATION WITH THRUST_MODEL.PY:
- Import and use in real-time mode for physical MADA control
- Validates alignment with MADAConvergenceValidator
- Coordinates with Hall sensor readings for closed-loop control
"""

import logging
import threading
import time
from typing import Dict, List, Tuple, Optional
import numpy as np

# Conditional GPIO import (mock for non-RPi systems)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available. Running in simulation mode.")
    
    # Mock GPIO for testing on non-RPi systems
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        
        @staticmethod
        def setmode(mode):
            pass
        
        @staticmethod
        def setup(pins, mode):
            pass
        
        @staticmethod
        def output(pin, value):
            pass
        
        @staticmethod
        def cleanup():
            pass
    
    GPIO = MockGPIO()

logger = logging.getLogger(__name__)


class MADAGPIOController:
    """
    GPIO controller for multiple MADA units with independent stepper control.
    
    Features:
    - Dynamic pin assignment for 1-6 MADA units
    - Simultaneous azimuth/elevation control via threading
    - Microstepping support (configurable, default 1/16)
    - Safety limits and position tracking
    - Integration with MADA validation system
    """
    
    # Hardware constants
    STEPS_PER_REV = 200  # Standard NEMA 17
    DEFAULT_MICROSTEPS = 16  # 1/16 microstepping
    DEFAULT_STEP_DELAY = 0.001  # seconds (adjustable for speed/torque)
    
    # Safety limits
    MIN_ELEVATION = -90  # degrees
    MAX_ELEVATION = 90   # degrees
    
    # Available GPIO pins (BCM mode, avoiding reserved pins)
    # I2C: 2,3 | SPI: 7-11 | UART: 14,15 (included but use with caution)
    PIN_POOL = [4, 5, 6, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
    
    def __init__(self, num_madas: int, microsteps: int = DEFAULT_MICROSTEPS,
                 step_delay: float = DEFAULT_STEP_DELAY):
        """
        Initialize MADA GPIO controller.
        
        Args:
            num_madas: Number of MADA units (1-6 supported)
            microsteps: Microstepping resolution (1, 2, 4, 8, 16, 32)
            step_delay: Delay between steps in seconds
        
        Raises:
            ValueError: If num_madas exceeds available pins or invalid parameters
            RuntimeError: If GPIO initialization fails
        """
        if num_madas < 1:
            raise ValueError("num_madas must be at least 1")
        
        if num_madas * 4 > len(self.PIN_POOL):
            raise ValueError(
                f"Not enough GPIO pins for {num_madas} MADAs. "
                f"Max supported: {len(self.PIN_POOL) // 4}"
            )
        
        if microsteps not in [1, 2, 4, 8, 16, 32]:
            raise ValueError("microsteps must be 1, 2, 4, 8, 16, or 32")
        
        if step_delay < 0:
            raise ValueError("step_delay must be non-negative")
        
        self.num_madas = num_madas
        self.microsteps = microsteps
        self.step_delay = step_delay
        self.gpio_available = GPIO_AVAILABLE
        
        # Generate pin assignments
        self.mada_pins = self._generate_pin_assignments()
        
        # Position tracking (degrees)
        self.positions = {
            i: {'azimuth': 0.0, 'elevation': 0.0}
            for i in range(1, num_madas + 1)
        }
        
        # Thread locks for concurrent access
        self.locks = {
            i: threading.Lock()
            for i in range(1, num_madas + 1)
        }
        
        # Active movement threads
        self.active_threads: List[threading.Thread] = []
        
        # Initialize GPIO
        self._init_gpio()
        
        logger.info(f"MADAGPIOController initialized: {num_madas} MADAs, "
                   f"{microsteps}x microstepping, {step_delay}s step delay")
        
        if not self.gpio_available:
            logger.warning("Running in SIMULATION mode (no actual GPIO control)")
    
    def _generate_pin_assignments(self) -> Dict[int, Dict[str, int]]:
        """
        Generate GPIO pin assignments for all MADAs.
        
        Returns:
            Dict mapping MADA ID to pin assignments
        """
        pins = {}
        idx = 0
        
        for i in range(1, self.num_madas + 1):
            pins[i] = {
                'az_dir': self.PIN_POOL[idx],
                'az_step': self.PIN_POOL[idx + 1],
                'el_dir': self.PIN_POOL[idx + 2],
                'el_step': self.PIN_POOL[idx + 3]
            }
            idx += 4
            
            logger.debug(f"MADA {i} pins: AZ_DIR={pins[i]['az_dir']}, "
                        f"AZ_STEP={pins[i]['az_step']}, "
                        f"EL_DIR={pins[i]['el_dir']}, "
                        f"EL_STEP={pins[i]['el_step']}")
        
        return pins
    
    def _init_gpio(self) -> None:
        """Initialize GPIO pins."""
        if not self.gpio_available:
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup all pins as outputs
            for pins in self.mada_pins.values():
                for pin in pins.values():
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, 0)  # Initialize low
            
            logger.info("GPIO initialization successful")
        
        except Exception as e:
            logger.error(f"GPIO initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize GPIO: {e}")
    
    def _calculate_steps(self, angle_deg: float, full_rotation: bool = True) -> Tuple[int, int]:
        """
        Calculate number of steps and direction for given angle.
        
        Args:
            angle_deg: Target angle in degrees
            full_rotation: If True, 360° = full rotation; if False, 180° range
        
        Returns:
            Tuple of (steps, direction) where direction is 0 or 1
        """
        rotation_deg = 360.0 if full_rotation else 180.0
        steps = int(abs(angle_deg) / rotation_deg * self.STEPS_PER_REV * self.microsteps)
        direction = 1 if angle_deg >= 0 else 0
        
        return steps, direction
    
    def _execute_movement(self, mada_id: int, axis: str, steps: int, direction: int) -> None:
        """
        Execute stepper motor movement.
        
        Args:
            mada_id: MADA unit ID
            axis: 'azimuth' or 'elevation'
            steps: Number of steps to move
            direction: Direction (0 or 1)
        """
        pins = self.mada_pins[mada_id]
        
        if axis == 'azimuth':
            dir_pin = pins['az_dir']
            step_pin = pins['az_step']
        else:  # elevation
            dir_pin = pins['el_dir']
            step_pin = pins['el_step']
        
        # Set direction
        GPIO.output(dir_pin, direction)
        time.sleep(0.0001)  # Direction setup time
        
        # Execute steps
        for _ in range(steps):
            GPIO.output(step_pin, 1)
            time.sleep(self.step_delay)
            GPIO.output(step_pin, 0)
            time.sleep(self.step_delay)
    
    def rotate_mada(self, mada_id: int, azimuth_deg: float = 0.0,
                   elevation_deg: float = 0.0, blocking: bool = False) -> None:
        """
        Rotate a specific MADA to target angles.
        
        Args:
            mada_id: MADA unit ID (1 to num_madas)
            azimuth_deg: Azimuth angle in degrees (wraps at 360°)
            elevation_deg: Elevation angle in degrees (-90 to +90)
            blocking: If True, wait for movement to complete
        
        Raises:
            ValueError: If mada_id is invalid
        """
        if mada_id not in self.mada_pins:
            raise ValueError(
                f"MADA ID {mada_id} not configured. Valid IDs: 1 to {self.num_madas}"
            )
        
        # Clamp elevation to safety limits
        elevation_deg = max(self.MIN_ELEVATION, min(self.MAX_ELEVATION, elevation_deg))
        
        # Normalize azimuth to 0-360 range
        azimuth_deg = azimuth_deg % 360.0
        
        # Calculate relative movements from current position
        with self.locks[mada_id]:
            current_az = self.positions[mada_id]['azimuth']
            current_el = self.positions[mada_id]['elevation']
            
            delta_az = azimuth_deg - current_az
            delta_el = elevation_deg - current_el
            
            # Update positions
            self.positions[mada_id]['azimuth'] = azimuth_deg
            self.positions[mada_id]['elevation'] = elevation_deg
        
        # Calculate steps
        az_steps, az_dir = self._calculate_steps(delta_az, full_rotation=True)
        el_steps, el_dir = self._calculate_steps(delta_el, full_rotation=False)
        
        logger.debug(f"MADA {mada_id}: AZ {current_az:.1f}°→{azimuth_deg:.1f}° "
                    f"({az_steps} steps), EL {current_el:.1f}°→{elevation_deg:.1f}° "
                    f"({el_steps} steps)")
        
        if not self.gpio_available:
            logger.info(f"[SIMULATION] MADA {mada_id} rotated to AZ={azimuth_deg:.1f}°, "
                       f"EL={elevation_deg:.1f}°")
            return
        
        # Create movement threads
        def az_thread():
            if az_steps > 0:
                self._execute_movement(mada_id, 'azimuth', az_steps, az_dir)
        
        def el_thread():
            if el_steps > 0:
                self._execute_movement(mada_id, 'elevation', el_steps, el_dir)
        
        # Start threads
        threads = []
        if az_steps > 0:
            t_az = threading.Thread(target=az_thread, daemon=True)
            t_az.start()
            threads.append(t_az)
        
        if el_steps > 0:
            t_el = threading.Thread(target=el_thread, daemon=True)
            t_el.start()
            threads.append(t_el)
        
        self.active_threads.extend(threads)
        
        # Wait if blocking
        if blocking:
            for t in threads:
                t.join()
    
    def rotate_all_madas(self, azimuth_deg: float = 0.0, elevation_deg: float = 0.0,
                        blocking: bool = False) -> None:
        """
        Rotate all MADAs to the same orientation.
        
        Args:
            azimuth_deg: Azimuth angle for all MADAs
            elevation_deg: Elevation angle for all MADAs
            blocking: If True, wait for all movements to complete
        """
        threads = []
        
        for mada_id in range(1, self.num_madas + 1):
            t = threading.Thread(
                target=self.rotate_mada,
                args=(mada_id, azimuth_deg, elevation_deg, False),
                daemon=True
            )
            t.start()
            threads.append(t)
        
        if blocking:
            for t in threads:
                t.join()
    
    def get_positions(self) -> Dict[int, Dict[str, float]]:
        """
        Get current positions of all MADAs.
        
        Returns:
            Dict mapping MADA ID to {'azimuth': deg, 'elevation': deg}
        """
        positions_copy = {}
        for mada_id in range(1, self.num_madas + 1):
            with self.locks[mada_id]:
                positions_copy[mada_id] = self.positions[mada_id].copy()
        return positions_copy
    
    def home_all_madas(self, blocking: bool = True) -> None:
        """
        Home all MADAs to 0° azimuth, 0° elevation.
        
        Args:
            blocking: If True, wait for homing to complete
        """
        logger.info("Homing all MADAs to 0°, 0°...")
        self.rotate_all_madas(0.0, 0.0, blocking)
        logger.info("Homing complete")
    
    def set_microstepping(self, microsteps: int) -> None:
        """
        Update microstepping resolution.
        
        Args:
            microsteps: New microstepping value (1, 2, 4, 8, 16, 32)
        
        Note: This only updates the software setting. Hardware DIP switches
        on the stepper driver must be set accordingly.
        """
        if microsteps not in [1, 2, 4, 8, 16, 32]:
            raise ValueError("microsteps must be 1, 2, 4, 8, 16, or 32")
        
        self.microsteps = microsteps
        logger.info(f"Microstepping updated to 1/{microsteps}")
    
    def set_step_delay(self, step_delay: float) -> None:
        """
        Update step delay (affects speed).
        
        Args:
            step_delay: Delay in seconds (min ~0.0001 for fast, max ~0.01 for slow)
        """
        if step_delay < 0:
            raise ValueError("step_delay must be non-negative")
        
        self.step_delay = step_delay
        logger.info(f"Step delay updated to {step_delay}s")
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all active movements to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (None = no timeout)
        
        Returns:
            True if all movements completed, False if timeout occurred
        """
        start_time = time.time()
        
        for thread in self.active_threads:
            if thread.is_alive():
                remaining_time = None if timeout is None else timeout - (time.time() - start_time)
                
                if remaining_time is not None and remaining_time <= 0:
                    logger.warning("Timeout waiting for MADA movements")
                    return False
                
                thread.join(timeout=remaining_time)
                
                if thread.is_alive():
                    logger.warning("Timeout waiting for MADA movements")
                    return False
        
        self.active_threads.clear()
        return True
    
    def emergency_stop(self) -> None:
        """
        Emergency stop: immediately halt all movements.
        
        Note: This doesn't actually stop running threads, but prevents
        new movements. For true emergency stop, implement hardware E-stop.
        """
        logger.warning("EMERGENCY STOP called")
        
        # Clear active threads (they'll complete current step and stop)
        self.active_threads.clear()
        
        # Set all step pins low
        if self.gpio_available:
            for pins in self.mada_pins.values():
                GPIO.output(pins['az_step'], 0)
                GPIO.output(pins['el_step'], 0)
    
    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        logger.info("Cleaning up GPIO resources...")
        
        # Wait for movements to complete
        self.wait_for_completion(timeout=5.0)
        
        # Cleanup GPIO
        if self.gpio_available:
            try:
                GPIO.cleanup()
                logger.info("GPIO cleanup complete")
            except Exception as e:
                logger.error(f"GPIO cleanup failed: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
    
    def __del__(self):
        """Destructor."""
        self.cleanup()


# =============================================================================
# Integration with thrust_model.py
# =============================================================================

def integrate_with_mada_validation(controller: MADAGPIOController,
                                   field_vectors: List[np.ndarray],
                                   target_direction: np.ndarray) -> Dict[int, Tuple[float, float]]:
    """
    Calculate optimal MADA orientations based on field vectors.
    Integrates with MADAConvergenceValidator from thrust_model.py
    
    Args:
        controller: MADAGPIOController instance
        field_vectors: List of 3D field vectors from Hall sensors
        target_direction: Desired thrust direction [x, y, z]
    
    Returns:
        Dict mapping MADA ID to (azimuth, elevation) in degrees
    """
    if len(field_vectors) != controller.num_madas:
        raise ValueError(f"Expected {controller.num_madas} field vectors, got {len(field_vectors)}")
    
    # Normalize target direction
    target_norm = np.linalg.norm(target_direction)
    if target_norm < 1e-10:
        raise ValueError("Target direction is zero vector")
    target_unit = target_direction / target_norm
    
    orientations = {}
    
    for i, field_vec in enumerate(field_vectors):
        mada_id = i + 1
        
        # Convert field vector to spherical coordinates
        field_norm = np.linalg.norm(field_vec)
        
        if field_norm < 1e-10:
            logger.warning(f"MADA {mada_id}: Zero field vector, using default orientation")
            orientations[mada_id] = (0.0, 0.0)
            continue
        
        field_unit = field_vec / field_norm
        
        # Calculate alignment with target
        alignment = np.dot(field_unit, target_unit)
        
        # Calculate azimuth (0-360°)
        azimuth = np.degrees(np.arctan2(field_vec[1], field_vec[0]))
        if azimuth < 0:
            azimuth += 360.0
        
        # Calculate elevation (-90 to +90°)
        elevation = np.degrees(np.arcsin(np.clip(field_vec[2] / field_norm, -1.0, 1.0)))
        
        orientations[mada_id] = (azimuth, elevation)
        
        logger.debug(f"MADA {mada_id}: Field={field_vec}, Target alignment={alignment:.3f}, "
                    f"AZ={azimuth:.1f}°, EL={elevation:.1f}°")
    
    return orientations


# =============================================================================
# Example Usage
# =============================================================================

def example_usage():
    """Example usage demonstrating MADA control."""
    logger.info("=" * 60)
    logger.info("MADA GPIO CONTROLLER EXAMPLE")
    logger.info("=" * 60)
    
    # Create controller for 4 MADAs
    with MADAGPIOController(num_madas=4, microsteps=16) as controller:
        
        # Home all MADAs
        logger.info("\n1. Homing all MADAs...")
        controller.home_all_madas(blocking=True)
        
        # Individual control
        logger.info("\n2. Individual MADA control...")
        controller.rotate_mada(1, azimuth_deg=45.0, elevation_deg=30.0, blocking=True)
        controller.rotate_mada(3, azimuth_deg=-90.0, elevation_deg=0.0, blocking=True)
        
        # Simultaneous control (MIMO)
        logger.info("\n3. Simultaneous multi-MADA control...")
        controller.rotate_mada(1, azimuth_deg=90.0, elevation_deg=15.0, blocking=False)
        controller.rotate_mada(2, azimuth_deg=180.0, elevation_deg=-15.0, blocking=False)
        controller.rotate_mada(4, azimuth_deg=270.0, elevation_deg=0.0, blocking=False)
        controller.wait_for_completion(timeout=10.0)
        
        # All MADAs to same orientation
        logger.info("\n4. Aligning all MADAs...")
        controller.rotate_all_madas(azimuth_deg=0.0, elevation_deg=45.0, blocking=True)
        
        # Get current positions
        logger.info("\n5. Current positions:")
        positions = controller.get_positions()
        for mada_id, pos in positions.items():
            logger.info(f"  MADA {mada_id}: AZ={pos['azimuth']:.1f}°, EL={pos['elevation']:.1f}°")
        
        logger.info("\nExample complete!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    example_usage()
