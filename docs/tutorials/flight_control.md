Hardware Setup Guide: Transitioning from Simulations to Prototyping
Introduction
This guide helps you transition from software simulations (e.g., simulations/thrust_model.py and ai/navigation.py) to physical hardware prototypes for the QED Vacuum Thrust Control system. It covers assembling a basic spherical drone, integrating sensors (IMU, GPS, altimeter, magnetometer), and prototyping magnetic circuits for low-power testing (scalable to B_opposing >20 T).
Focus: Start with low-power neodymium magnets for safety, then scale to electromagnets. Emphasize sensor fusion for real-time navigation.
Safety Warning: High magnetic fields and currents can be dangerous. Use protective gear, current limits, and test in isolated areas. Monitor for thermal overloads (>100°C shutdown).
Prerequisites
	•	Software: Python 3.12+, dependencies from requirements.txt (NumPy, SciPy, TensorFlow, etc.).
	•	Hardware Components:
	◦	Microcontroller: ESP32 or Teensy (for PWM control).
	◦	Flight Controller: PX4 or ArduPilot (optional for advanced control).
	◦	Sensors: MPU-6050 (IMU), GPS module (e.g., u-blox NEO-6M), altimeter (e.g., MS5611), magnetometer (e.g., HMC5883L).
	◦	Magnetic Setup: Neodymium magnets (N52 grade, ~1.5 T initial), coils (for electromagnets), Hiperco-50/Minnealloy cores (for scaling).
	◦	Power: LiPo battery (3S, 2200mAh+), voltage regulator (3.3V/5V).
	◦	Other: Load cell (for force measurement), thermal sensors (DS18B20), non-magnetic frame (aluminum/3D-printed).
	•	Tools: Soldering iron, multimeter, oscilloscope (for pulsing), FreeCAD (for CAD modifications).
	•	Knowledge: Basic electronics, Python scripting. Review hardware/interfaces.py and hardware/schematics/basic_drone.sch.
Step 1: Assemble the Basic Prototype
	1	Build the Spherical Frame:
	◦	Open cad/spherical_drone.fcstd in FreeCAD.
	◦	3D-print or machine the spherical body (radius ~0.5 m for prototype).
	◦	Mount opposing magnetic coils/magnets along the x-axis (for B_opposing).
	2	Wire the Electronics (per basic_drone.sch):
	◦	Connect ESP32 GPIO to MOSFET gate for PWM (coil control).
	◦	Wire sensors to I2C/SPI pins (e.g., MPU-6050 SCL/SDA to GPIO22/23).
	◦	Add Hall sensor near coils for B-field feedback.
	◦	Power via battery with regulators.
	3	Initial Magnetic Setup:
	◦	Use neodymium magnets for low-power (B ~1.5 T): Place at coil centers.
	◦	Test opposition: Measure B with Hall sensor; aim for >20 T scaling by upgrading to electromagnets (high-current supply needed).
	4	Flash Firmware:
	◦	Upload hardware/interfaces.py logic to ESP32 (use Arduino IDE or MicroPython).
	◦	Test PWM: Run mcu.pulse_mada(pin=14, frequency=50).
Step 2: Integrate Sensors
	1	Sensor Wiring:
	◦	IMU (MPU-6050): VCC/GND to 3.3V, SCL/SDA to ESP32 I2C.
	◦	GPS: TX/RX to UART pins, antenna outdoors.
	◦	Altimeter: I2C shared bus.
	◦	Magnetometer: I2C, calibrate away from magnets.
	2	Software Integration:
	◦	Use ai/navigation.py: simulate_sensors for testing, replace with real reads.
	◦	Implement fusion: In loop, call kf.predict(accel, gyro) then kf.update(measurements).
	◦	Example Code Snippet: import board
	◦	import adafruit_mpu6050  # Or similar library
	◦	
	◦	i2c = board.I2C()
	◦	mpu = adafruit_mpu6050.MPU6050(i2c)
	◦	
	◦	accel = np.array(mpu.acceleration)
	◦	gyro = np.array(mpu.gyro)
	◦	# ... Get other sensors
	◦	kf.predict(accel, gyro)
	◦	measurements = np.concatenate([gps_pos, gps_vel, mag_att, [alt_z]])
	◦	kf.update(measurements)
	◦	
	3	Calibration:
	◦	IMU: Static calibration for offsets.
	◦	Magnetometer: Figure-8 motion for hard/soft iron correction.
	◦	Test Fusion: Log fused vs. raw data; plot errors.
Step 3: Prototyping and Testing
	1	From Sim to Hardware:
	◦	Replace sim data in thrust_model.py with real sensor inputs (e.g., --b_opposing from Hall).
	◦	Run navigation.py with hardware flags: Modify to use real interfaces.
	◦	Benchmark: Use benchmark_with_telemetry on logged data.
	2	Low-Power Tests:
	◦	Ground: Measure B_opposing, force with load cell.
	◦	Tethered: Hover at 10% power; check stability.
	◦	Untethered: Short flights; monitor via logs.
	3	Scaling Up:
	◦	Upgrade Magnets: Switch to electromagnets for >20 T (high-amp supply, cooling).
	◦	Add TEG: For energy recovery in thermal management.
	◦	Swarm: Use multiple prototypes with swarm_simulation.ipynb.
	4	Error Handling:
	◦	Thermal: If temp >90°C, reduce freq; >100°C shutdown.
	◦	Fail-Safes: Auto-land on low battery or signal loss.
Troubleshooting
	•	No Sensor Data: Check wiring/I2C addresses.
	•	Unstable Control: Tune PID in navigation.py.
	•	Overheating: Add fans/PCM; monitor with logging.py.
	•	Errors: Run with --verbose; check console.
For advanced issues, see testing/protocols.md.
Resources
	•	Schematics: hardware/schematics/basic_drone.sch
	•	CAD: cad/spherical_drone.fcstd
	•	Code: hardware/interfaces.py
	•	Next: Flight Control Tutorial
Last Updated: November 01, 2025
(back to top)
