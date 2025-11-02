# Incremental Flight Testing Protocols

## Overview
This document outlines a structured, incremental approach to testing the spherical combat drone prototype for QED vacuum polarization-based EMF propulsion. The protocols emphasize safety, data integrity, and progressive validation, starting from ground-based measurements to full untethered flights. Each stage builds on the previous, incorporating lessons from simulations (e.g., simulations/thrust_model.py) and bench tests (see experiments/bench_test_designs.md).

### Key Principles:
- **Safety First**: Always monitor for high magnetic fields (>20 T), thermal overloads (>100°C), and structural integrity. Use protective gear, emergency shutdowns, and operate in controlled environments.
- **Data Logging**: Use testing/logging.py for real-time data collection (e.g., acceleration, power, temperature, **MADA convergence**). Analyze post-test with Pandas and Matplotlib.
- **Prerequisites**: Calibrated sensors (IMU, Hall, thermal), charged batteries, and verified software (e.g., ai/navigation.py for 6DOF control).
- **Success Criteria**: Defined per stage; failures trigger rollback to prior stages.
- **Equipment**: Spherical drone CAD (cad/spherical_drone.fcstd), hardware interfaces (hardware/interfaces.py), low-power neodymium magnets (scalable to electromagnets for B_opposing >20 T).

**Regulatory Note**: Comply with local aviation laws (e.g., FAA for untethered flights). Test in isolated areas.

---

## Stage 1: Ground-Based Magnetic Field Measurements

### Objective
Validate magnetic circuit optimization on the ground, measuring B_opposing and diamagnetic repulsion without propulsion activation. **CRITICAL: Verify that magnetic fields are properly converging (opposing) at the focal point, not diverging.**

### Prerequisites
- Assembled prototype with magnetic coils/magnets (per hardware/schematics/basic_drone.sch).
- Hall sensors calibrated and positioned at:
  - **Each MADA unit** (to measure individual field vectors B1 and B2)
  - **Center focal point** (to measure B_opposing convergence)
- Power supply limited to low current (1-5 A).
- Data logger initialized with **magnetic field vector tracking** enabled.

### Procedure
1. **Setup**: Secure drone on non-magnetic stand. Position opposing coils/magnets to point **toward each other** at the center focal point (d=0.05 m separation).
   - **VERIFICATION**: Visually confirm coil/magnet orientations using polarization markers (e.g., compass test).
   
2. **Baseline Measurement**: Power off; record ambient B-field (should be ~50 μT).

3. **Polarity Check** (NEW): 
   - Power on at minimal current (0.1 A).
   - Use Hall sensors to measure field direction at each MADA unit.
   - **Verify**: B1 and B2 vectors point toward center (convergence quality ≥ 0.95).
   - **CRITICAL**: If convergence quality < 0.8, fields are misaligned - **STOP and reconfigure hardware**.

4. **Ramp-Up Test**: Gradually increase current (0.1 A increments) to target B_opposing. 
   - Monitor with Hall sensors at both MADA units AND center point.
   - **Log**: B1_x, B1_y, B1_z and B2_x, B2_y, B2_z for each measurement.

5. **Convergence Validation** (NEW):
   - Calculate real-time convergence quality: cos(angle) between B1 and B2.
   - **Target**: Convergence quality > 0.95 (fields within 18° of perfect opposition).
   - **Warning**: Quality 0.8-0.95 indicates suboptimal alignment.
   - **Failure**: Quality < 0.8 indicates improper configuration (fields may be parallel or diverging).

6. **Pulsing Check**: Apply 50 Hz PWM (via hardware/interfaces.py); measure pulsed enhancement ΔB.
   - **Monitor convergence stability** during pulsing - quality should remain > 0.9.

7. **Force Measurement**: Use load cell to detect repulsion at center point; compare to theoretical F ∝ χ B² ∇(h²) A ρ.
   - **Expected behavior**: Force should be concentrated at the convergence point, not distributed across the sphere.

8. **Data Logging**: Log B_field_mag, B_opposing, B1_x/y/z, B2_x/y/z, mada_convergence_quality, frequency, power, temp every 1 s. Run for 5-10 min.

9. **Shutdown**: Ramp down current; inspect for anomalies.

### Success Criteria
- B_opposing >20 T without overheating (temp <80°C).
- **MADA convergence quality ≥ 0.95** throughout test.
- Measured force within 10% of simulation (simulations/equations.py).
- Force concentrated at center focal point (verified by multi-point load cells).
- No structural damage.

### Potential Issues & Mitigations
- **Field Divergence** (NEW): If convergence quality < 0.8:
  - **Root cause**: Magnets/coils oriented incorrectly (pointing away from center or parallel).
  - **Fix**: Rotate MADA units 180° to reverse polarity. Retest polarity check.
  - **Verification**: Use compass or small ferromagnetic probe to trace field lines - they should converge at center.
- **Field Interference**: Shield electronics; use mu-metal barriers if needed.
- **Data Noise**: Average over 10 readings; apply low-pass filter to Hall sensor data.
- **Asymmetric Fields**: If B1 ≠ B2 magnitude, adjust current balance between MADA units.

---

## Stage 2: Tethered Hover Tests

### Objective
Test hover capabilities and 6DOF control in a constrained environment, validating thrust efficiency and stability **with proper MADA field convergence maintained dynamically**.

### Prerequisites
- Successful Stage 1 **with verified field convergence**.
- Tether system (e.g., nylon ropes or gimbals) limiting movement to 1-2 m.
- Full sensor suite (IMU, GPS, altimeter, **3-axis Hall sensors at each MADA unit**) fused via ai/navigation.py.
- Battery at 100%; emergency kill switch.

### Procedure
1. **Setup**: Anchor drone with tethers. Position in open area (e.g., lab with high ceiling).

2. **Power-On Check**: Initialize AI navigation; verify sensor fusion (Kalman filters).
   - **NEW**: Verify MADA convergence quality at startup (should be ≥ 0.95 at rest).

3. **Dynamic Convergence Test** (NEW):
   - With drone stationary, pulse MADA units at varying frequencies (50 Hz, 100 Hz, 1 kHz).
   - **Monitor**: Convergence quality should remain stable (> 0.9) across frequency changes.
   - **Log**: Any convergence degradation during pulsing indicates field instability.

4. **Low-Thrust Hover**: Activate MADA pulsing at 10-20% power; aim for neutral buoyancy (thrust = weight).
   - **Monitor convergence quality continuously** - any drop below 0.85 should trigger power reduction.

5. **Maneuver Tests**: Command small translations/rotations (e.g., 0.5 m up/down); monitor PID/MPC corrections.
   - **NEW**: During maneuvers, log how MADA convergence quality changes with thrust vectoring.
   - **Expected**: Quality may fluctuate 0.90-0.98 but should never drop below 0.85.

6. **Duration Test**: Maintain hover for 5-15 min; log telemetry including continuous convergence monitoring.

7. **Stress Test**: Introduce bursts (1 kHz) for high-accel (>50g) simulation.
   - **CRITICAL**: Monitor convergence quality during bursts - rapid pulsing can cause field misalignment.
   - **Abort condition**: Convergence < 0.8 for >1 second.

8. **Shutdown**: Gradually reduce thrust; secure drone.

### Success Criteria
- Stable hover ±0.1 m for >5 min.
- **MADA convergence quality ≥ 0.85** throughout flight (mean > 0.92).
- Acceleration vs. power matches benchmarks (simulations/thrust_model.py).
- Efficiency >90% (η = (T · v / P) × 100%).
- No tether strain overload.
- **No poor convergence events** (quality < 0.8) logged.

### Potential Issues & Mitigations
- **Dynamic Misalignment**: If convergence drops during maneuvers:
  - **Cause**: Unbalanced MADA power or mechanical flexing.
  - **Fix**: Implement dynamic convergence control - adjust individual MADA currents to maintain opposition.
  - **Software**: Add feedback loop in ai/navigation.py to maintain convergence quality.
- **Instability**: Tune PID gains in ai/navigation.py; consider adding convergence quality as control input.
- **Battery Drain**: Monitor voltage; abort if <20%.
- **Field Interference from Movement**: Shield control electronics; verify Hall sensor mounting rigidity.

---

## Stage 3: Untethered Flights

### Objective
Conduct full autonomous flights in open space, testing non-ballistic trajectories, stealth ops, and threat modeling **while maintaining optimal MADA field convergence**.

### Prerequisites
- Successful Stages 1-2 **with consistent convergence quality > 0.85**.
- FAA/equivalent approval for test site (e.g., remote field).
- Redundancy enabled (dual AI models in ai/navigation.py).
- Fail-safes active (e.g., auto-land on low battery **or convergence failure**).

### Procedure
1. **Pre-Flight Check**: Verify navigation targets, flux mapping, ML optimizations, and **baseline convergence quality ≥ 0.95**.

2. **Takeoff**: Command hover to 1 m; untether.
   - **Monitor**: Convergence quality during transition from tethered to free flight.

3. **Trajectory Tests**: Execute paths (e.g., figure-8, evasion maneuvers) using MIMO networks.
   - **NEW**: Log convergence quality throughout maneuvers; analyze correlation with thrust efficiency.

4. **High-Speed Run**: Ramp to Mach 1+ equivalents (scaled for prototype); measure range.
   - **CRITICAL**: High-speed flight may stress MADA alignment - monitor convergence continuously.
   - **Abort if**: Convergence < 0.8 for >2 seconds during high-speed run.

5. **Convergence-Optimized Flight** (NEW):
   - Use ML gradient optimization to find flight envelope that maximizes both thrust efficiency and convergence quality.
   - **Target**: Maintain quality > 0.92 while achieving >500g acceleration.

6. **Threat Simulation**: Introduce "obstacles" (e.g., markers); test adaptive pulsing.
   - **Monitor**: How evasive maneuvers affect MADA convergence.

7. **Landing**: Auto-descend; post-flight inspection.
   - **Check**: Mechanical alignment of MADA units - any physical shift indicates structural issues.

8. **Multi-Drone (Optional)**: Swarm test via simulations/thrust_model.py integration.
   - **NEW**: Monitor inter-drone magnetic interference effects on convergence quality.

### Success Criteria
- Flight duration >10 min without intervention.
- Trajectory accuracy ±1 m.
- **Mean MADA convergence quality > 0.90** throughout flight (min > 0.80).
- **Zero convergence failures** (quality < 0.8 for >2 seconds).
- Stealth: No radar/thermal detection (if equipped).
- Post-analysis: Corr(accel, power) >0.9 AND Corr(accel, convergence_quality) >0.7.

### Potential Issues & Mitigations
- **Loss of Control**: Implement GPS failover; add convergence-based failsafe (auto-land if quality drops).
- **Wind Interference**: Test in calm conditions first; monitor how wind affects MADA alignment.
- **High-Speed Convergence Degradation**: 
  - **Cause**: Aerodynamic forces causing MADA unit deflection.
  - **Fix**: Reinforce mounting structure; add active stabilization.
- **EMI from Environment**: If convergence fluctuates without power changes, check for external magnetic interference.

---

## Error Handling for Thermal Overloads

### Objective
Prevent damage from overheating (e.g., during high-thrust pulsing).

### Detection
- Monitor temp via sensors (Bi₂Te₃ TEG integration).
- Thresholds: Warning >90°C, Critical >100°C.

### Protocols
1. **Real-Time Monitoring**: In ai/navigation.py, check temp every loop (1-10 ms).

2. **Warning Response**: At >90°C, reduce pulsing freq (e.g., to 50 Hz) and power by 20%. Log event.

3. **Critical Shutdown**: At >100°C, immediate thrust cutoff, auto-land (untethered) or power-off (tethered/ground). Activate cooling (PCM channels).

4. **Post-Event Analysis**: Use testing/logging.py to plot temp_over_time; inspect for degradation (ML predictive maintenance).

5. **Redundancy**: Failover to secondary coils if available.

### Integration
**Code Hook**: In control loops, add:
```python
if current_temp > TEMP_THRESHOLD:
    # Reduce power
    reduce_thrust_by_percent(20)
    log_warning("Thermal warning triggered")

if current_temp > MAX_TEMP:
    # Shutdown
    emergency_landing()
    log_critical("Thermal overload - emergency shutdown")

# NEW: Add convergence monitoring
if mada_convergence_quality < CONVERGENCE_THRESHOLD:
    # Convergence failure - possible hardware issue
    reduce_thrust_by_percent(30)
    log_warning("MADA convergence degraded - reducing power")

if mada_convergence_quality < CRITICAL_CONVERGENCE:
    # Critical convergence failure
    emergency_landing()
    log_critical("MADA field misalignment - emergency shutdown")
```

**Logging**: Flag overloads AND convergence failures in CSV for easy filtering.

---

## Error Handling for MADA Convergence Failures (NEW)

### Objective
Detect and respond to magnetic field misalignment that would compromise QED vacuum polarization propulsion.

### Detection
- Monitor mada_convergence_quality via Hall sensors at each MADA unit.
- Thresholds: 
  - **Optimal**: Quality ≥ 0.95
  - **Acceptable**: Quality 0.85-0.95
  - **Warning**: Quality 0.80-0.85
  - **Critical**: Quality < 0.80 (fields not properly opposing)

### Protocols
1. **Real-Time Monitoring**: In ai/navigation.py, calculate convergence quality every loop (1-10 ms) using Hall sensor data.

2. **Warning Response** (Quality 0.80-0.85):
   - Log event with timestamp, field vectors, and current flight state.
   - Reduce thrust by 30% to minimize structural stress.
   - Attempt auto-correction: Adjust individual MADA currents to rebalance fields.
   - If quality doesn't improve within 5 seconds, proceed to critical shutdown.

3. **Critical Shutdown** (Quality < 0.80):
   - **Ground/Tethered**: Immediate power cutoff; inspect hardware for misalignment.
   - **Untethered**: Controlled emergency landing with minimal thrust.
   - **Root Cause Analysis**: Hardware failure (coil shift, magnet demagnetization) or software configuration error.

4. **Post-Event Analysis**:
   - Use testing/logging.py to plot_mada_convergence() over time.
   - Identify when degradation began and correlate with flight events (acceleration, temperature, vibration).
   - Inspect MADA units for:
     - Physical displacement/rotation
     - Magnet demagnetization (test with gaussmeter)
     - Coil damage or winding shorts

5. **Prevention**:
   - Pre-flight convergence calibration at multiple power levels.
   - Structural reinforcement to prevent MADA unit movement.
   - Regular magnet field strength verification.

### Integration
**Code Hook**: See thermal overload code above for combined monitoring.

### Root Cause Examples
- **Quality suddenly drops to -0.5**: Both MADA units pointing same direction (parallel fields) - **hardware wiring error**.
- **Quality gradually degrades 0.95 → 0.75**: Magnet demagnetization from overheating - **thermal management issue**.
- **Quality oscillates 0.85-0.95**: Structural vibration causing MADA unit wobble - **mechanical resonance**.
- **Quality stable but low (0.7)**: MADA units misaligned by 45° - **CAD/assembly error**.

---

## Appendix: Data Analysis & Visualization

**Load logs**:
```python
df = FlightLogger.load_data('log.csv')
```

**Analyze**:
```python
stats = FlightLogger.analyze_data('log.csv')
# Now includes convergence statistics
```

**Plots**:
```python
FlightLogger.plot_accel_vs_power('log.csv')
FlightLogger.plot_mada_convergence('log.csv')  # NEW
```

**Advanced Analysis** (NEW):
```python
# Correlation between convergence quality and thrust efficiency
import pandas as pd
import matplotlib.pyplot as plt

df = FlightLogger.load_data('log.csv')
df['thrust_efficiency'] = df['thrust'] / df['power']

plt.figure(figsize=(10, 6))
plt.scatter(df['mada_convergence_quality'], df['thrust_efficiency'], alpha=0.5)
plt.xlabel('MADA Convergence Quality')
plt.ylabel('Thrust Efficiency (N/W)')
plt.title('Impact of Field Convergence on Propulsion Efficiency')
plt.grid(True)
plt.show()
```

---

**For expansions, contribute via PRs. Last updated: November 01, 2025.**
