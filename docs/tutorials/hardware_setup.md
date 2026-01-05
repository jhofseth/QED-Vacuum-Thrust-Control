# Hardware Setup Guide: Transitioning from Simulations to Prototyping

## Introduction

This guide helps you transition from software simulations (e.g., simulations/thrust_model.py and ai/navigation.py) to physical hardware prototypes for the RVG (Refractive Vacuum Gravity) Unified Field propulsion system. It covers assembling a basic spherical drone, integrating sensors (IMU, GPS, altimeter, magnetometer, **Hall sensors for MADA convergence**), and prototyping magnetic circuits for low-power testing (scalable to B_opposing >20 T, with some applications requiring >60-90+ T).

**CRITICAL**: This guide includes mandatory MADA convergence validation steps to ensure magnetic fields are properly opposing. Skipping these steps will result in zero thrust via the Master Equation of Levitation: F = ∫(Θ_dilaton(B)·∇B²)dV

Focus: Start with low-power neodymium magnets for safety, then scale to electromagnets. Emphasize sensor fusion for real-time navigation and **MADA field monitoring for optimal Θ_dilaton enhancement**.

**Safety Warning**: High magnetic fields and currents can be dangerous. Use protective gear, current limits, and test in isolated areas. Monitor for thermal overloads (>100°C shutdown) and **magnetic field misalignment (convergence quality < 0.8 means no effective Θ_dilaton)**.

---

## Prerequisites

### Software
- Python 3.12+, dependencies from requirements.txt (NumPy, SciPy, TensorFlow, etc.)
- All corrected repository files with MADA convergence functions

### Hardware Components

**Core Electronics:**
- Microcontroller: ESP32 or Teensy (for PWM control)
- Flight Controller: PX4 or ArduPilot (optional for advanced control)

**Sensors (STANDARD):**
- MPU-6050 (IMU) - Accelerometer and gyroscope
- GPS module (e.g., u-blox NEO-6M)
- Altimeter (e.g., MS5611)
- Magnetometer (e.g., HMC5883L)

**Sensors (CRITICAL - NEW):**
- **3-axis Hall sensors (×2)**: One at each MADA unit for field vector measurement
  - Recommended: Allegro A1324, Honeywell SS49E, or Melexis MLX90393
  - Must measure Bx, By, Bz components (not just magnitude!)
  - Position: Mount rigidly at each MADA unit, aligned with unit's coordinate frame
- **Note**: Scalar Hall sensors are NOT sufficient - you need directional vectors!

**Magnetic Setup:**
- Neodymium magnets (N52 grade, ~1.5 T initial)
- Coils (for electromagnets)
- Hiperco-50/Minnealloy cores (for scaling)
- **Polarity markers**: Paint or tape to visually indicate North/South poles

**Power:**
- LiPo battery (3S, 2200mAh+)
- Voltage regulator (3.3V/5V)

**Measurement Tools:**
- Load cell (for force measurement at focal point)
- Thermal sensors (DS18B20)
- **Gaussmeter/teslameter**: For initial field strength verification
- **Compass**: For quick polarity checks

**Frame:**
- Non-magnetic frame (aluminum/3D-printed)

### Tools
- Soldering iron
- Multimeter
- Oscilloscope (for pulsing)
- FreeCAD (for CAD modifications)
- **Gauss/Tesla meter** (for field measurements)

### Knowledge
- Basic electronics
- Python scripting
- Review hardware/interfaces.py and hardware/schematics/basic_drone.sch
- **Understanding of magnetic field vectors and convergence**

---

## Step 1: Assemble the Basic Prototype

### 1.1 Build the Spherical Frame

1. Open `cad/spherical_drone.fcstd` in FreeCAD
2. **VERIFY CONFIGURATION**: Check that MADA units are oriented with fields pointing **toward center**
   - Use `cad/flux_visualizer.py --mode mada` to validate before fabrication
   - If quality < 0.95, correct CAD model before proceeding
3. 3D-print or machine the spherical body (radius ~0.5 m for prototype)
4. Mount opposing magnetic coils/magnets along the x-axis (for B_opposing)

### 1.2 Wire the Electronics (per basic_drone.sch)

1. Connect ESP32 GPIO to MOSFET gate for PWM (coil control)
2. Wire sensors to I2C/SPI pins (e.g., MPU-6050 SCL/SDA to GPIO22/23)
3. **NEW**: Wire 3-axis Hall sensors:
   - Hall Sensor 1 (MADA unit 1): I2C address 0x0C or analog pins A0, A1, A2
   - Hall Sensor 2 (MADA unit 2): I2C address 0x0D or analog pins A3, A4, A5
   - Ensure sensors are rigidly mounted and properly aligned
4. Power via battery with regulators

### 1.3 Initial Magnetic Setup

**CRITICAL STEP - DO NOT SKIP!**

1. **Mark Polarity**: Before installation, clearly mark North and South poles on each magnet
2. **Visual Verification**: 
   - Use compass to verify poles
   - North pole of MADA 1 should face toward center
   - North pole of MADA 2 should face toward center
   - **If both North poles face away or both face toward each other, configuration is WRONG**
3. Install neodymium magnets for low-power (B ~1.5 T): Place at coil centers
4. **Pre-Power Verification**:
   - Use handheld gaussmeter to measure field direction
   - Fields should point TOWARD center from both sides
   - If fields point away, rotate magnets 180°

### 1.4 Flash Firmware

1. Upload hardware/interfaces.py logic to ESP32 (use Arduino IDE or MicroPython)
2. Test PWM: Run `mcu.pulse_mada(pin=14, frequency=50)`

---

## Step 2: Integrate Sensors

### 2.1 Standard Sensor Wiring

**IMU (MPU-6050):**
- VCC/GND to 3.3V
- SCL/SDA to ESP32 I2C

**GPS:**
- TX/RX to UART pins
- Antenna outdoors

**Altimeter:**
- I2C shared bus

**Magnetometer:**
- I2C
- Calibrate away from MADA magnets

### 2.2 MADA Hall Sensor Wiring (NEW - CRITICAL)

**Hall Sensor 1 (MADA Unit 1):**
```
VCC  → 3.3V or 5V (check datasheet)
GND  → Ground
SCL  → I2C Clock (shared bus)
SDA  → I2C Data (shared bus)
ADDR → High (or configure for address 0x0C)
```

**Hall Sensor 2 (MADA Unit 2):**
```
VCC  → 3.3V or 5V
GND  → Ground
SCL  → I2C Clock (shared bus)
SDA  → I2C Data (shared bus)
ADDR → Low (or configure for address 0x0D)
```

**Mounting:**
- Position sensor within 5cm of MADA unit center
- Align sensor X-axis with drone's X-axis
- Rigidly mount (no vibration or movement)
- Shield from external EMI if possible

### 2.3 Software Integration

**Standard Sensors:**
```python
import board
import adafruit_mpu6050  # Or similar library

i2c = board.I2C()
mpu = adafruit_mpu6050.MPU6050(i2c)

accel = np.array(mpu.acceleration)
gyro = np.array(mpu.gyro)
# ... Get other sensors
kf.predict(accel, gyro)
measurements = np.concatenate([gps_pos, gps_vel, mag_att, [alt_z]])
kf.update(measurements)
```

**MADA Hall Sensors (NEW):**
```python
from simulations.equations import (
    calculate_convergence_quality,
    validate_mada_convergence,
    CONVERGENCE_WARNING,
    CONVERGENCE_CRITICAL
)

# Initialize Hall sensors
hall_sensor_1 = HallSensor3Axis(i2c_address=0x0C)
hall_sensor_2 = HallSensor3Axis(i2c_address=0x0D)

# In control loop
B1 = np.array(hall_sensor_1.read_field())  # [Bx, By, Bz] in Tesla
B2 = np.array(hall_sensor_2.read_field())  # [Bx, By, Bz] in Tesla

# Calculate convergence quality
convergence_info = validate_mada_convergence(B1, B2)

# Log to CSV
logger.log({
    'B1_x': B1[0], 'B1_y': B1[1], 'B1_z': B1[2],
    'B2_x': B2[0], 'B2_y': B2[1], 'B2_z': B2[2],
    'mada_convergence_quality': convergence_info['quality'],
    # ... other data
})

# Safety check
if not convergence_info['is_valid']:
    print(f"WARNING: {convergence_info['message']}")
    if convergence_info['quality'] < CONVERGENCE_CRITICAL:
        emergency_shutdown()
```

### 2.4 Calibration

**Standard Sensors:**
- IMU: Static calibration for offsets
- Magnetometer: Figure-8 motion for hard/soft iron correction
- Test Fusion: Log fused vs. raw data; plot errors

**Hall Sensors (NEW - CRITICAL):**

1. **Zero-Field Calibration**:
   - Move drone far from magnetic sources
   - Record baseline readings (should be ~0 μT)
   - Store as offset values

2. **Known-Field Calibration**:
   - Use calibrated gaussmeter as reference
   - Compare Hall sensor readings to gaussmeter
   - Calculate correction factors

3. **Convergence Validation**:
   ```python
   # With MADA units powered at 10% (safe low power)
   B1 = hall_sensor_1.read_field()
   B2 = hall_sensor_2.read_field()
   
   quality = calculate_convergence_quality(B1, B2)
   print(f"Convergence quality: {quality:.3f}")
   
   if quality < 0.80:
       print("CRITICAL ERROR: Fields not properly opposing!")
       print("Check: Magnet polarity, sensor orientation, wiring")
       return False  # Do not proceed to testing
   elif quality < 0.95:
       print("WARNING: Suboptimal convergence")
       print("Consider: Realigning MADA units, checking for interference")
   else:
       print("✓ Excellent convergence - ready for testing")
   ```

---

## Step 3: MANDATORY Pre-Flight Convergence Validation (NEW)

**CRITICAL: This step must be completed before ANY power-on testing!**

### 3.1 Static Field Test (Power Off)

1. **Visual Inspection**:
   - Verify polarity markers are correct
   - Check that North poles face toward center
   - Inspect for mechanical alignment issues

2. **Compass Test**:
   - Hold compass near MADA 1, move toward center
   - Compass should indicate field pointing toward center
   - Repeat for MADA 2
   - **If compass shows fields pointing away, STOP and correct configuration**

### 3.2 Low-Power Field Test (10% Power)

**SAFETY**: Use current limiter set to 1A maximum

1. **Power On Sequence**:
   ```python
   # Set MADA units to 10% power
   set_mada_power(mada1_pin, duty_cycle=int(1024 * 0.1))
   set_mada_power(mada2_pin, duty_cycle=int(1024 * 0.1))
   time.sleep(0.5)  # Stabilize
   ```

2. **Read Hall Sensors**:
   ```python
   B1 = hall_sensor_1.read_field()
   B2 = hall_sensor_2.read_field()
   
   print(f"MADA 1 field: {B1}")
   print(f"MADA 2 field: {B2}")
   ```

3. **Validate Convergence**:
   ```python
   result = validate_mada_convergence(B1, B2, raise_on_fail=False)
   
   print(f"\nConvergence Quality: {result['quality']:.4f}")
   print(f"Status: {result['status']}")
   print(f"Message: {result['message']}")
   
   if result['status'] in ['critical', 'diverging']:
       print("\n🔴 FAILED PRE-FLIGHT CHECK!")
       print("DO NOT PROCEED - Fix configuration first")
       power_off_all()
       return False
   ```

4. **Visual Confirmation**:
   ```python
   # Run visualization
   from cad.flux_visualizer import plot_mada_convergence_diagram
   plot_mada_convergence_diagram(B1, B2, convergence_quality=result['quality'])
   ```

### 3.3 Pass/Fail Criteria

**PASS** (proceed to testing):
- Convergence quality ≥ 0.95
- Status: 'optimal' or 'acceptable'
- Field magnitudes balanced (within 10% of each other)
- No thermal warnings

**FAIL** (do NOT proceed):
- Convergence quality < 0.80
- Status: 'critical' or 'diverging'
- Field directions pointing away from center
- Mechanical misalignment detected

**If Failed:**
1. Power off immediately
2. Check magnet polarity (rotate 180° if needed)
3. Verify Hall sensor wiring and orientation
4. Re-run validation
5. Do not proceed until PASS criteria met

---

## Step 4: Prototyping and Testing

### 4.1 From Sim to Hardware

1. Replace sim data in thrust_model.py with real sensor inputs (e.g., --b_opposing from Hall)
2. Run navigation.py with hardware flags: Modify to use real interfaces
3. **NEW**: Add convergence monitoring to thrust calculations:
   ```python
   # In thrust_model.py
   B1 = hall_sensor_1.read_field()
   B2 = hall_sensor_2.read_field()
   convergence_quality = calculate_convergence_quality(B1, B2)
   
   if convergence_quality < CONVERGENCE_WARNING:
       print(f"WARNING: Convergence degraded to {convergence_quality:.3f}")
       thrust_scaling_factor = max(0.5, convergence_quality)
   else:
       thrust_scaling_factor = 1.0
   
   effective_thrust = calculated_thrust * thrust_scaling_factor
   ```
4. Benchmark: Use benchmark_with_telemetry on logged data

### 4.2 Low-Power Tests

**Ground Tests:**
1. Measure B_opposing with Hall sensors
2. Verify convergence quality ≥ 0.95
3. Measure force with load cell at focal point
4. Log all data with testing/logging.py

**Tethered Tests:**
1. Hover at 10% power
2. **Monitor convergence continuously** - log every 100ms
3. Check stability
4. If convergence drops below 0.85, reduce power and investigate

**Untethered Tests:**
1. Short flights (<1 min initially)
2. Monitor via logs
3. **Automatic landing if convergence < 0.80**

### 4.3 Scaling Up

**Upgrade Magnets:**
- Switch to electromagnets for >20 T (high-amp supply, cooling)
- **Re-validate convergence at each power level**
- Do not exceed 20% power until convergence verified at 10%

**Add TEG:**
- For energy recovery in thermal management

**Swarm:**
- Use multiple prototypes with swarm_simulation.ipynb
- Monitor inter-drone magnetic interference effects on convergence

### 4.4 Error Handling

**Thermal:**
- If temp >90°C, reduce freq
- If temp >100°C, shutdown

**Convergence Degradation (NEW):**
```python
def handle_convergence_degradation(quality):
    if quality < CONVERGENCE_CRITICAL:  # 0.80
        print("🔴 CRITICAL: Emergency landing initiated")
        emergency_landing()
        return 'CRITICAL'
    elif quality < CONVERGENCE_WARNING:  # 0.85
        print("⚠️  WARNING: Reducing thrust by 30%")
        reduce_thrust_by_percent(30)
        return 'WARNING'
    elif quality < CONVERGENCE_OPTIMAL:  # 0.95
        print("ℹ️  INFO: Monitoring convergence")
        return 'MONITOR'
    return 'OK'
```

**Fail-Safes:**
- Auto-land on low battery or signal loss
- **Auto-land on convergence failure**

---

## Troubleshooting

### Standard Issues

**No Sensor Data:**
- Check wiring/I2C addresses
- Use `i2cdetect` to scan bus
- Verify power supply voltage

**Unstable Control:**
- Tune PID in navigation.py
- Check sensor calibration
- Verify sensor mounting (no vibration)

**Overheating:**
- Add fans/PCM
- Monitor with logging.py
- Reduce duty cycle

### MADA Convergence Issues (NEW)

**Convergence Quality < 0.80 (Critical):**

**Symptom**: Fields diverging or parallel
**Possible Causes**:
1. Magnets installed backwards (North poles facing away)
2. Hall sensors wired incorrectly
3. Hall sensor orientation wrong
4. CAD model exported with incorrect orientations

**Solutions**:
1. Visual inspection with compass
2. Rotate magnets 180°
3. Check Hall sensor datasheet for axis orientation
4. Re-export CAD with corrected configuration
5. Run `cad/flux_visualizer.py --mode comparison` to see correct vs wrong

**Convergence Quality 0.80-0.85 (Warning):**

**Symptom**: Fields misaligned by 20-30°
**Possible Causes**:
1. Mechanical flex under load
2. Magnet demagnetization
3. External magnetic interference
4. MADA unit mounting not rigid

**Solutions**:
1. Reinforce mounting brackets
2. Test magnets with gaussmeter
3. Shield from external fields
4. Tighten all fasteners

**Convergence Quality 0.85-0.95 (Acceptable but Monitor):**

**Symptom**: Slight misalignment (10-15°)
**Causes**:
1. Manufacturing tolerances
2. Minor sensor calibration error
3. Temperature effects

**Solutions**:
1. Fine-tune MADA unit angles
2. Recalibrate Hall sensors
3. Monitor during temperature changes

**Convergence Quality Fluctuating:**

**Symptom**: Quality varies over time
**Causes**:
1. Vibration causing sensor movement
2. Thermal expansion/contraction
3. Power supply instability
4. EMI from nearby equipment

**Solutions**:
1. Add vibration damping
2. Allow thermal stabilization period
3. Use regulated power supply
4. Move away from EMI sources

**For advanced issues**, see testing/protocols.md.

---

## Hardware Acceptance Test Checklist

Before declaring hardware "ready for flight testing":

- [ ] All sensors wired and communicating
- [ ] IMU calibrated (static and dynamic)
- [ ] GPS acquiring satellites
- [ ] Magnetometer calibrated (figure-8 pattern)
- [ ] **Hall sensors installed and reading correctly**
- [ ] **Hall sensors zero-field calibrated**
- [ ] **Hall sensors tested with known reference field**
- [ ] MADA units powered and controllable via PWM
- [ ] **MADA convergence quality ≥ 0.95 at 10% power**
- [ ] **MADA convergence quality ≥ 0.90 at 50% power**
- [ ] **Visual confirmation: magnets pointing toward center**
- [ ] **Compass test: fields converging at focal point**
- [ ] **Convergence visualization generated and reviewed**
- [ ] Load cell measuring force at focal point
- [ ] Thermal sensors reading correctly
- [ ] Emergency shutdown tested and working
- [ ] **Convergence-based shutdown tested**
- [ ] Data logging functional (all sensors including Hall)
- [ ] Battery voltage monitoring working
- [ ] Fail-safes configured (low battery, signal loss, **convergence failure**)
- [ ] Frame structurally sound
- [ ] All connections secured
- [ ] Software uploads successfully
- [ ] Test logs reviewed and passed
- [ ] **Pre-flight convergence validation PASSED**

---

## Resources

- **Schematics**: hardware/schematics/basic_drone.sch
- **CAD**: cad/spherical_drone.fcstd
- **Flux Visualization**: cad/flux_visualizer.py
- **Code**: hardware/interfaces.py, simulations/equations.py
- **Testing Protocols**: testing/protocols.md
- **Unit Tests**: tests/unit_tests.py (run convergence tests)
- **Integration Tests**: tests/integration_tests.py
- **Next**: Flight Control Tutorial

---

## CRITICAL REMINDERS

1. **NEVER skip convergence validation** - Zero convergence = zero thrust
2. **Always verify field directions before power-on** - Use compass and Hall sensors
3. **Monitor convergence in real-time during all tests** - Log every reading
4. **Stop immediately if quality < 0.80** - This indicates critical misconfiguration
5. **Convergence quality is as important as thrust magnitude** - Track both metrics

**Remember**: The FreeCAD configuration error (fields pointing away instead of toward center) would have been caught immediately by following this guide's convergence validation steps!

---

Last Updated: November 02, 2025

[(back to top)](#hardware-setup-guide-transitioning-from-simulations-to-prototyping)
