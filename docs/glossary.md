# Glossary

This glossary provides a comprehensive compilation of terms, acronyms, concepts, and technical vocabulary relevant to the QED-Vacuum-Thrust-Control project. It is derived from the project's theoretical foundations in quantum electrodynamics (QED), Refractive Vacuum Gravity (RVG), Disformal QED, the 95 GeV dilaton/radion resonance, vacuum refractive index engineering, electromagnetic propulsion systems, materials science, control engineering, and simulation tools. Entries are organized alphabetically for ease of reference, with cross-references where applicable. Each entry includes:

- **Definition**: A precise, formal explanation.
- **Project Context**: How the term applies to RVG-based vacuum refractive index manipulation for EMF propulsion, MADA/Bushman arrays, AI control, supra-saturation engineering, and related simulations.
- **Mathematical/Technical Details**: Relevant equations, parameters, or derivations (where applicable).
- **References**: Key sources, including project files, patents, or literature.

The glossary emphasizes practical metric engineering via high-gradient magnetic configurations and the non-linear enhancement of vacuum polarizability by the 95 GeV dilaton. Terms cover core physics, engineering, materials, and ancillary concepts to support researchers, engineers, and contributors in developing high-thrust, stealthy combat drones.

---

## A

### Acceleration (a)

- **Definition**: The rate of change of velocity of an object with respect to time, typically measured in meters per second squared (m/s²) or gravitational units (g, where 1 g ≈ 9.81 m/s²).
- **Project Context**: Essential for propulsion performance in spherical combat drones, enabling extreme maneuvers (>500 g) for non-ballistic trajectories and evasion in asymmetric warfare. Simulations predict acceleration from vacuum gradient forces in supra-saturation MADA/Bushman arrays.
- **Mathematical/Technical Details**: $a = \mathbf{F}_{\text{lift}} / m_{\text{system}}$, where $\mathbf{F}_{\text{lift}}$ is derived from the Master Equation of Levitation.
- **References**: `simulations/thrust_model.py`; RVG Unified Field (Hofseth, 2026).

### AI Navigation

- **Definition**: Artificial intelligence-driven systems for autonomous path planning, obstacle avoidance, and real-time decision-making in dynamic environments.
- **Project Context**: Implements MIMO neural networks for 6DOF control in RVG-propelled drones, integrating real-time flux mapping and threat modeling for stealth operations, hover, precision strikes, and swarm coordination with minimal radar/thermal signatures.
- **Mathematical/Technical Details**: Relies on multiple-input-multiple-output (MIMO) architectures; flux mapping uses sensor data for field gradients $\nabla B^2$.
- **References**: `ai/navigation.py`; TensorFlow dependencies in `requirements.txt`.

### α′-Fe₈(NC) (Alpha-Prime Iron Nitride Carbide, Minnealloy)

- **Definition**: A high-saturation, cobalt-free soft magnetic alloy variant with interstitial nitrogen and carbon in an α-iron lattice, optimized for magnetic circuit applications.
- **Project Context**: Preferred material for high-permeability magnetic circuits in MADA/Bushman arrays (score 95/100 overall), enabling efficient supra-saturation drive and intense localized fields (~2.8–2.9 T) for strong vacuum gradient forces.
- **Mathematical/Technical Details**: Saturation induction $B_s \sim 2.8–2.9$ T; used in supra-saturation regimes where opposing gap fields $\gg B_s$.
- **References**: `docs/materials_ranking.pdf`; RVG Unified Field Section on High-Saturation Materials (Hofseth, 2026).

### α″-Fe₁₆N₂ (Alpha-Double-Prime Iron Nitride)

- **Definition**: A body-centered tetragonal iron nitride phase exhibiting giant saturation magnetization due to lattice expansion and electron localization.
- **Project Context**: Advanced permanent magnet material (theoretical $B_s \sim 2.9$ T) for MADA stacks and Bushman arrays, enabling higher baseline fields and more efficient supra-saturation engineering compared to NdFeB.
- **Mathematical/Technical Details**: Experimental saturation ~2.8 ± 0.15 T; cluster + atom model for enhanced exchange splitting.
- **References**: `docs/materials_ranking.pdf`; RVG Unified Field Section on High-Saturation Magnetic Materials (Hofseth, 2026).

### ARMCO (American Rolling Mill Company Pure Iron)

- **Definition**: High-purity, low-carbon soft magnetic iron with minimal impurities (<0.005% carbon).
- **Project Context**: Baseline material (score 90/100) for prototype magnetic circuits; viable for supra-saturation effects via strong opposing drive despite lower $B_s \sim 2.1$ T.
- **Mathematical/Technical Details**: Maximum permeability $\mu_m \approx 10,000$; resistivity $\rho \approx 10 \mu\Omega \cdot \text{cm}$.
- **References**: `docs/materials_ranking.pdf`.

### Asymmetric Warfare

- **Definition**: Conflict involving non-state actors or weaker forces using unconventional tactics against superior conventional militaries.
- **Project Context**: Primary design driver for stealthy, high-maneuverability drones with RVG propulsion, prioritizing low observability and precision over conventional force.
- **Mathematical/Technical Details**: N/A; modeled via threat analysis in simulations.
- **References**: README.md project description.

---

## B

### Bi₂Te₃ TEG (Bismuth Telluride Thermoelectric Generator)

- **Definition**: A solid-state device converting heat differentials into electrical energy via the Seebeck effect.
- **Project Context**: Optional component for thermal management, recycling waste heat (10–40 kW) from high-power pulsing to power auxiliary systems.
- **Mathematical/Technical Details**: Efficiency $\eta = \frac{\Delta T}{T_h} \cdot \frac{\sqrt{1 + ZT} - 1}{\sqrt{1 + ZT} + 1}$, ZT ≈ 1–2 at 300–500 K.
- **References**: Key Features section; `hardware/interfaces.py`.

### B_opposing (Opposing Magnetic Field)

- **Definition**: The magnetic field strength in the convergence/frustration zone of opposing magnetic streams.
- **Project Context**: Critical parameter for supra-saturation engineering; must substantially exceed material saturation ($B_{\text{opposing}} \gg B_s$) to generate intense localized gradients $\nabla B^2$ and strong dilaton-enhanced vacuum forces.
- **Mathematical/Technical Details**: $B_{\text{gap}} \approx \frac{\mu_0 m_1 m_2}{2\pi d^2} \cdot k$, with MADA/Bushman geometry amplification $k \sim 200–500+$.
- **References**: RVG Unified Field Practical Toolkit; `simulations/thrust_model.py --b_opposing`.

### Bushman Array

- **Definition**: A magnetic configuration (U.S. Patent 5,929,732) using like-pole opposition and flux frustration to generate focused, extended-range magnetic beams.
- **Project Context**: Synonymous with advanced MADA implementations; core geometry for creating extreme $\nabla B^2$ ($\sim 10^{10}$ T²/m) required for macroscopic RVG effects. Supports stacking and nesting for compounded amplification.
- **Mathematical/Technical Details**: Amplification via flux frustration; nested configurations yield multiplicative gains in localized $B_{\text{opposing}}$.
- **References**: U.S. Patent #5,929,732; RVG Unified Field Section on Lockheed Martin Magnetic Beam (Hofseth, 2026).

---

## D

### Dilaton (Θ₉₅ or Φ)

- **Definition**: A light scalar boson (~95.4 GeV) arising from spontaneous breaking of conformal/scale symmetry, coupling to the trace of the energy-momentum tensor.
- **Project Context**: Central mediator in RVG; pumps non-linear vacuum response via trace anomaly, enabling macroscopic refractive index changes at achievable Tesla scales.
- **Mathematical/Technical Details**: Interaction Lagrangian $\mathcal{L}_{\text{int}} \propto \frac{\phi}{f_\phi} (B^2 - E^2)$; enhancement factor $\varTheta_{\text{dilaton}}(B)$.
- **References**: RVG Unified Field Sections 2–3 (Hofseth, 2026).

### Dilaton Enhancement Factor (Θ_dilaton(B))

- **Definition**: Non-linear function describing the strength of vacuum polarizability activated by intense local magnetic fields via the 95 GeV dilaton.
- **Project Context**: Determines the magnitude of refractive index gradients; weak at low $B$, grows strongly in supra-saturation regimes.
- **Mathematical/Technical Details**: Appears in Master Equation as $\mathbf{F}_{\text{lift}} = \int_V \left( \frac{1}{2\mu_0} \varTheta_{\text{dilaton}}(B) \cdot \nabla (B^2) \right) dV$.
- **References**: RVG Unified Field Master Equation derivation (Hofseth, 2026).

### Disformal QED

- **Definition**: Extension of QED incorporating disformal transformations that couple electromagnetic fields to spacetime metric via a scalar field.
- **Project Context**: Theoretical foundation linking Euler-Heisenberg nonlinearity, dilaton excitation, and metric distortion for directional thrust.
- **Mathematical/Technical Details**: Physical metric $\tilde{g}_{\mu\nu} = C(\phi) g_{\mu\nu} + D(\phi) \partial_\mu \phi \partial_\nu \phi$.
- **References**: RVG Unified Field Section on Disformal Gravity Coupling (Hofseth, 2026).

### Duty Cycle

- **Definition**: The fraction of time a periodic signal is active.
- **Project Context**: Variable parameter in MADA pulsing (50–100 Hz default, bursts to 1 kHz) to optimize efficiency (>95%), thermal load, and stealth via reduced average signature.
- **Mathematical/Technical Details**: Duty = $(t_{\text{on}} / T) \times 100\%$.
- **References**: Pulsing strategy in Practical Toolkit.

---

## E

### Efficiency (η)

- **Definition**: Ratio of useful output power to input power.
- **Project Context**: Target >95% for overall system; critical for extended range in stealth drone operations.
- **Mathematical/Technical Details**: $\eta = \left( \frac{|\mathbf{F}_{\text{lift}}| \cdot v}{P} \right) \times 100\%$.
- **References**: Practical Toolkit; Key Features.

### Electromagnetic Field (EMF) Propulsion

- **Definition**: Propellantless thrust generation via engineered gradients in the vacuum refractive index using electromagnetic configurations.
- **Project Context**: Core technology exploiting RVG and supra-saturation MADA/Bushman arrays for hypersonic (Mach 26) performance in combat drones.
- **Mathematical/Technical Details**: Thrust from Master Equation; directional opposite convergence point.
- **References**: Project title; RVG Unified Field (Hofseth, 2026).

---

## F

### Finemet Nanocrystalline Iron

- **Definition**: Soft magnetic alloy of iron-based nanocrystals in an amorphous matrix.
- **Project Context**: Top-ranked material (96/100) for high-frequency pulsing circuits with low losses.
- **Mathematical/Technical Details**: $B_s \approx 1.9$ T; core loss <0.5 W/kg at 50 Hz.
- **References**: Materials Ranking table.

### Flux Mapping

- **Definition**: Real-time 3D visualization and analysis of magnetic flux density.
- **Project Context**: AI input for 6DOF navigation and optimal gradient alignment in RVG propulsion.
- **Mathematical/Technical Details**: $\mathbf{B} = \nabla \times \mathbf{A}$.
- **References**: Key Features; `cad/flux_visualizer.py`.

---

## G

### Gordon Optical Metric

- **Definition**: Effective metric governing photon propagation in a medium with refractive index $n$, $\gamma_{\mu\nu} = g_{\mu\nu} + (1 - n^2)u_\mu u_\nu$.
- **Project Context**: Mathematical link between vacuum refractive index $K(B)$ and spacetime curvature in RVG.
- **Mathematical/Technical Details**: Equivalence to gravitational potentials via Shapiro delay.
- **References**: RVG Unified Field Section on Disformal QED (Hofseth, 2026).

### 6DOF (Six Degrees of Freedom)

- **Definition**: Full independent movement in 3D space (translation + rotation).
- **Project Context**: Achieved via MIMO AI control of vectorized RVG thrust in spherical drones.
- **Mathematical/Technical Details**: State vector $\mathbf{q} = [x, y, z, \phi, \theta, \psi]^T$.
- **References**: Key Features.

---

## H

### Heisenberg-Euler-Schwinger (HES) Effective Action

- **Definition**: One-loop effective Lagrangian describing nonlinear QED interactions in strong fields.
- **Project Context**: Basis for vacuum refractive index dependence on $B$; enhanced by 95 GeV dilaton in RVG.
- **Mathematical/Technical Details**: $\mathcal{L}_{\text{EH}} = -\frac{1}{4}F^2 + \frac{\alpha^2}{90m_e^4} \left[ (F^2)^2 + \frac{7}{4}(\tilde{F}F)^2 \right]$.
- **References**: RVG Unified Field Section on Euler-Heisenberg (Hofseth, 2026).

### Hiperco-50

- **Definition**: High-saturation cobalt-iron alloy (50% Co, 50% Fe + V).
- **Project Context**: Legacy high-performance option; traded for cobalt-free Minnealloy in scalable designs.
- **Mathematical/Technical Details**: $B_s \approx 2.4$ T.
- **References**: README.md; Materials Ranking.

---

## K

### K (Vacuum Refractive Index)

- **Definition**: Effective refractive index of the quantum vacuum, $K = \sqrt{\epsilon \mu / \epsilon_0 \mu_0}$.
- **Project Context**: Primary engineered parameter in RVG; gradients in $K$ produce gravitational-like forces.
- **Mathematical/Technical Details**: $K(\mathbf{r}) \approx 1 + \varTheta_{\text{dilaton}}(B) \frac{B^2}{B_{\text{crit}}^2}$; $\nabla K \propto \varTheta_{\text{dilaton}}(B) \nabla B^2$.
- **References**: RVG Unified Field Practical Toolkit (Hofseth, 2026).

---

## M

### MADA (Magnetic Amplification and Direction Assembly)

- **Definition**: Patented (U.S. #5,929,732) magnetic topology using like-pole opposition, flux frustration, and focusing for extended-range, high-gradient beams (also called Bushman Array).
- **Project Context**: Core hardware for generating supra-saturation $B_{\text{opposing}}$ and steep $\nabla B^2$; supports stacking (×10–12) and nesting for extreme amplification (200–500×+).
- **Mathematical/Technical Details**: Amplification $k = 200–529+$; nested configurations compound gradients.
- **References**: U.S. Patent #5,929,732; RVG Unified Field Section on Lockheed Martin Magnetic Beam (Hofseth, 2026).

### Mach 26

- **Definition**: Hypersonic velocity ~26 times the speed of sound (~8,900 m/s at sea level).
- **Project Context**: Target performance for optimized RVG propulsion with supra-saturation MADA arrays.
- **Mathematical/Technical Details**: Derived from $v = \sqrt{2 \cdot (E/m) \cdot \eta}$.
- **References**: README.md intro.

### Master Equation of Levitation

- **Definition**: Integrated force equation quantifying propellantless thrust from vacuum refractive index gradients.
- **Project Context**: Central predictive tool for RVG propulsion performance.
- **Mathematical/Technical Details**: $\mathbf{F}_{\text{lift}} = \int_V \left( \frac{1}{2\mu_0} \varTheta_{\text{dilaton}}(B) \cdot \nabla (B^2) \right) dV$; thrust directed opposite convergence point.
- **References**: RVG Unified Field Section 4 (Hofseth, 2026).

### Metglas Amorphous Iron

- **Definition**: Rapidly quenched iron-based metallic glass with high permeability and low losses.
- **Project Context**: High-ranking alternative (95/100) for cost-sensitive pulsing circuits.
- **Mathematical/Technical Details**: $\mu_r \approx 1,000,000$; thickness ~20–25 μm.
- **References**: Materials Ranking.

### MIMO (Multiple Input Multiple Output)

- **Definition**: Control paradigm for systems with multiple actuators/sensors.
- **Project Context**: Foundation of AI navigation for robust 6DOF control in high-gradient environments.
- **Mathematical/Technical Details**: Transfer matrix $\mathbf{G}(s)$.
- **References**: Key Features.

### Minnealloy

- **Definition**: Family of cobalt-free, high-saturation iron nitride/carbide alloys (primarily α′-Fe₈(NC) phase).
- **Project Context**: Optimal scalable material for magnetic circuits in supra-saturation RVG implementations.
- **Mathematical/Technical Details**: $B_s \sim 2.8–2.9$ T.
- **References**: RVG Unified Field Materials Section (Hofseth, 2026).

---

## N

### N52 Magnets

- **Definition**: High-grade NdFeB permanent magnets with remanence ~1.45 T.
- **Project Context**: Low-cost baseline for MADA stacks (6–12× stacks yield ~3–15 T base before amplification).
- **Mathematical/Technical Details**: $B_r \approx 1.45$ T.
- **References**: MADA Implementation.

---

## P

### PCM (Phase Change Material)

- **Definition**: Substances that absorb/release latent heat during phase transitions for thermal buffering.
- **Project Context**: Integrated channels for managing 10–40 kW heat loads from pulsing.
- **Mathematical/Technical Details**: $Q = m \cdot L_f$.
- **References**: Key Features.

### Pulsed Enhancement (ΔB)

- **Definition**: Incremental field increase from rapid current pulses.
- **Project Context**: Enables dynamic bursts (up to 1 kHz) for agility and asymmetric waveforms for net momentum.
- **Mathematical/Technical Details**: $\Delta B = \mu_0 n \Delta I$.
- **References**: Practical Toolkit.

---

## Q

### QED (Quantum Electrodynamics)

- **Definition**: Relativistic quantum field theory of electromagnetic interactions.
- **Project Context**: Foundation for vacuum polarization; extended via Disformal QED and dilaton enhancement in RVG.
- **Mathematical/Technical Details**: Euler-Heisenberg effective action for strong fields.
- **References**: Project core; RVG Unified Field (Hofseth, 2026).

---

## R

### Range (R)

- **Definition**: Maximum operational distance under power and velocity constraints.
- **Project Context**: Extended via high efficiency and low-signature pulsing.
- **Mathematical/Technical Details**: $R \approx v \cdot (E_{\text{stored}} / P)$.
- **References**: Practical Toolkit.

### Refractive Vacuum Gravity (RVG)

- **Definition**: Unified field framework positing that gravitational effects emerge from engineered gradients in the vacuum refractive index $K$, mediated by the 95 GeV dilaton and Disformal QED.
- **Project Context**: Current theoretical backbone replacing prior models; enables practical metric engineering for propellantless propulsion.
- **Mathematical/Technical Details**: Master Equation; Gordon metric; supra-saturation requirement.
- **References**: RVG Unified Field full manuscript (Hofseth, 2026).

---

## S

### Supra-Saturation

- **Definition**: Regime where opposing gap fields substantially exceed material saturation ($B_{\text{opposing}} \gg B_s$).
- **Project Context**: Universal requirement for macroscopic RVG effects; enables intense localized $B$ and steep $\nabla B^2$ in any ferromagnetic circuit via permeability amplification.
- **Mathematical/Technical Details**: Drives $\mu_{\text{eff}} \approx 1$ in high-stress zone; activates strong $\varTheta_{\text{dilaton}}(B)$.
- **References**: RVG Unified Field Sections on Materials and Master Equation (Hofseth, 2026).

### Shielding

- **Definition**: Protective measures against electromagnetic interference and high fields.
- **Project Context**: Critical for electronics protection in high-power RVG systems.
- **Mathematical/Technical Details**: Attenuation in dB.
- **References**: `docs/shielding.pdf`; README.md safety note.

### Stealth Operations

- **Definition**: Tactics minimizing detectability across spectra.
- **Project Context**: Enabled by pulsed operation (low average signature), spherical geometry, and material choices.
- **Mathematical/Technical Details**: RCS and IR reduction.
- **References**: About The Project.

---

## T

### Thermal Management

- **Definition**: Strategies for heat dissipation and recovery in high-power systems.
- **Project Context**: Handles 10–40 kW from pulsing via PCM and optional TEG.
- **Mathematical/Technical Details**: Eddy losses $\propto f^2 B^2 t^2$.
- **References**: Key Features.

### Thrust (T or F_lift)

- **Definition**: Propulsive force generated by vacuum refractive index gradients.
- **Project Context**: Vectorized for omnidirectional control; directed opposite magnetic convergence point.
- **Mathematical/Technical Details**: Master Equation; total $\mathbf{F}_{\text{net}} = |\mathbf{F}_{\text{lift}}| \cdot \eta_{\text{align}} \cdot \cos\theta$.
- **References**: RVG Unified Field Practical Toolkit; `simulations/thrust_model.py`.

---

## V

### Vacuum Polarization

- **Definition**: QED effect where virtual pairs modify field propagation in strong backgrounds.
- **Project Context**: Enhanced by 95 GeV dilaton to macroscopic scales in RVG; basis for refractive index $K(B)$.
- **Mathematical/Technical Details**: Euler-Heisenberg nonlinearity; trace anomaly coupling.
- **References**: RVG Unified Field (Hofseth, 2026).

### 95 GeV Resonance

- **Definition**: Scalar boson excess observed at ~95.4 GeV in LHC and LEP data.
- **Project Context**: Identified as dilaton/radion; enables non-linear vacuum response for metric engineering.
- **Mathematical/Technical Details**: Local significance >3σ combined; couples to $T^\mu_\mu$.
- **References**: RVG Unified Field Section 2 (Hofseth, 2026).

---

## Other Symbols and Parameters

### ∇B² (Gradient of Magnetic Energy Density)

- **Definition**: Spatial rate of change of $B \cdot B$.
- **Project Context**: Drives force geometry in Master Equation; maximized in Bushman/MADA convergence zones.
- **Mathematical/Technical Details**: Target ~10¹⁰–10¹² T²/m in nested configurations.
- **References**: Practical Toolkit.

### μ₀ (Vacuum Permeability)

- **Definition**: Magnetic constant $4\pi \times 10^{-7}$ H/m.
- **Project Context**: Fundamental in field calculations.
- **Mathematical/Technical Details**: SI unit.
- **References**: All field equations.

---

This glossary evolves with the project and the RVG framework; contributions via pull requests are encouraged (see `CONTRIBUTING.md`). For API-specific terms, consult Sphinx docs in `/docs/api`.

**Total entries**: 40+; a comprehensive reference for RVG-based QED-EMF propulsion development.
