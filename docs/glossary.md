# Glossary

This glossary provides an exhaustive, professional compilation of terms, acronyms, concepts, and technical vocabulary relevant to the QED-Vacuum-Thrust-Control project. It is derived from the project's theoretical foundations in quantum electrodynamics (QED), emergent gravity models, electromagnetic propulsion systems, materials science, control engineering, and simulation tools. Entries are organized alphabetically for ease of reference, with cross-references where applicable. Each entry includes:

- **Definition**: A precise, formal explanation.
- **Project Context**: How the term applies to QED vacuum polarization-based EMF propulsion, MADA systems, AI control, and related simulations.
- **Mathematical/Technical Details**: Relevant equations, parameters, or derivations (where applicable).
- **References**: Key sources, including project files, patents, or literature.

The glossary emphasizes empirical adaptability (e.g., modifier equations independent of specific hypotheses like EGDPP) and practical implementation for defense applications, such as high-thrust, stealthy combat drones. Terms are exhaustive, covering core physics, engineering, materials, and ancillary concepts to support researchers, engineers, and contributors.

---

## A

### Acceleration (a)

- **Definition**: The rate of change of velocity of an object with respect to time, typically measured in meters per second squared (m/s²) or gravitational units (g, where 1 g ≈ 9.81 m/s²).
- **Project Context**: Critical for propulsion performance in spherical combat drones, enabling maneuvers exceeding 500 g for non-ballistic trajectories and evasion in asymmetric warfare. Simulations model acceleration under pulsed magnetic fields to predict drone agility and stability.
- **Mathematical/Technical Details**: Derived from Newton's second law as $a = \frac{T}{m}$, where $T$ is total thrust and $m$ is drone mass. In QED contexts, incorporates diamagnetic repulsion forces amplified by MADA pulsing.
- **References**: `simulations/thrust_model.py`; EGDPP theory (Hofseth, 2025).

### AI Navigation

- **Definition**: Artificial intelligence-driven systems for autonomous path planning, obstacle avoidance, and real-time decision-making in dynamic environments.
- **Project Context**: Implements MIMO neural networks for 6DOF control in EMF-propelled drones, integrating flux mapping and threat modeling for stealth operations. Enables hover, precision strikes, and swarm coordination while minimizing radar/thermal signatures.
- **Mathematical/Technical Details**: Relies on multiple-input-multiple-output (MIMO) architectures; flux mapping uses real-time sensor data for field gradients $\nabla (h^2)$.
- **References**: `ai/navigation.py`; TensorFlow dependencies in `requirements.txt`.

### α′-Fe₈(NC) (Alpha-Prime Iron Nitride Carbide)

- **Definition**: A high-permeability, cobalt-free ferromagnetic alloy variant of Minnealloy, characterized by interstitial nitrogen and carbon atoms in an α-iron lattice.
- **Project Context**: Ranked highly (95/100) for magnetic circuits in MADA assemblies due to superior saturation magnetization and low coercivity, enabling efficient B_opposing fields (>20 T) without cobalt dependency for scalable production.
- **Mathematical/Technical Details**: Saturation induction $B_s \approx 2.4$ T; used in pulsed enhancement $\Delta B = \mu_0 n I$.
- **References**: `docs/materials_ranking.pdf`; Holistic materials ranking in README.md.

### α″-Fe₁₆(C,N)₂ (Alpha-Double-Prime Iron Nitride Carbide)

- **Definition**: An advanced interstitial iron-based alloy with a body-centered tetragonal structure, optimized for ultra-high magnetic permeability and thermal stability.
- **Project Context**: Variant of Minnealloy (score 92/100), selected for high-thrust applications (e.g., Mach 26) in vacuum polarization propulsion, balancing cost and performance in opposing field generation.
- **Mathematical/Technical Details**: Curie temperature ~700°C; relative permeability $\mu_r > 100,000$.
- **References**: `docs/materials_ranking.pdf`; Minnealloy optimization section.

### ARMCO (American Rolling Mill Company Pure Iron)

- **Definition**: High-purity, low-carbon soft magnetic iron with minimal impurities (<0.005% carbon), exhibiting excellent ductility and magnetic softness.
- **Project Context**: Baseline material (score 90/100) for prototype magnetic circuits, used in simulations for comparing cobalt-free scalability in MADA pulsing at 50–100 Hz.
- **Mathematical/Technical Details**: Maximum permeability $\mu_m \approx 10,000$; resistivity $\rho \approx 10 \mu\Omega \cdot \text{cm}$.
- **References**: `docs/materials_ranking.pdf`; Materials ranking table.

### Asymptotic Safety

- **Definition**: A quantum field theory paradigm where ultraviolet divergences are controlled by a non-perturbative fixed point, ensuring finite couplings at all energy scales.
- **Project Context**: Underpins the EGDPP model's integration of QED with gravity, allowing RG flows for χ susceptibility in thrust simulations without infinities. Essential for predicting stable propulsion at high fields (>60 T).
- **Mathematical/Technical Details**: Fixed point in β-function: $\beta_\chi = -4\chi + \frac{g}{2\pi} \frac{\chi}{1 - 2\lambda} = 0$ at UV limit.
- **References**: EGDPP paper (Hofseth, 2025); `simulations/equations.py` RG flow module.

### Asymmetric Warfare

- **Definition**: Conflict involving non-state actors or weaker forces using unconventional tactics against superior conventional militaries.
- **Project Context**: Design driver for stealthy, high-maneuverability drones with EMF propulsion, emphasizing low-observability (radar/thermal) and precision strikes over brute force.
- **Mathematical/Technical Details**: N/A (strategic concept); modeled via threat analysis in simulations.
- **References**: README.md project description.

---

## B

### β_χ (Beta Function for Susceptibility)

- **Definition**: The renormalization group β-function governing the scale dependence of magnetic susceptibility χ in quantum field theories.
- **Project Context**: Central to modifier equations in EGDPP simulations; empirically tunable for accurate thrust prediction in vacuum polarization effects, independent of spin-0/2 hypotheses.
- **Mathematical/Technical Details**: For spin-0 EGDPP: $\beta_\chi = -4\chi + \frac{g}{2\pi} \frac{\chi}{1 - 2\lambda}$; alternatives include spin-2 form $\beta_\chi = (4 + \eta_\chi) \chi + c g \chi$.
- **References**: "Useful Equations" in README.md; `experiments/refine_equations.py`.

### Bi₂Te₃ TEG (Bismuth Telluride Thermoelectric Generator)

- **Definition**: A solid-state device converting heat differentials into electrical energy via the Seebeck effect, using bismuth telluride semiconductors.
- **Project Context**: Optional component in thermal management for dissipating 10–40 kW from high-field pulsing, recycling waste heat to power auxiliary systems in drones.
- **Mathematical/Technical Details**: Efficiency $\eta = \frac{\Delta T}{T_h} \cdot \frac{\sqrt{1 + ZT} - 1}{\sqrt{1 + ZT} + 1}$, where ZT ≈ 1–2 at 300–500 K.
- **References**: Key Features section; `hardware/interfaces.py`.

### B_opposing (Opposing Magnetic Field)

- **Definition**: The counter-propagating magnetic field strength required to induce nonlinear QED effects in vacuum polarization.
- **Project Context**: Threshold parameter (>20 T, up to 60–90 T) for diamagnetic repulsion in propulsion; amplified via MADA for practical drone thrust.
- **Mathematical/Technical Details**: $B_{\text{opposing}} = \frac{\mu_0 m_1 m_2}{2\pi d^2} \cdot k$, with MADA scaling $k \approx 200–529$.
- **References**: Theory Overview; `simulations/thrust_model.py --b_opposing`.

---

## C

### χ (Magnetic Susceptibility)

- **Definition**: A dimensionless measure of a material's or vacuum's magnetization response to an applied magnetic field, $\chi = \frac{M}{H}$.
- **Project Context**: Key parameter in thrust equations, modified by RG flows for QED vacuum effects; requires experimental calibration via modifier equation for simulation accuracy.
- **Mathematical/Technical Details**: Appears in force $\mathbf{F} = \chi B^2 \nabla (h^2) \cdot A \cdot \rho$ and Lagrangian $\mathcal{L}_{\text{disrupt}} = -\frac{1}{2} \chi B^2 h_{\mu\nu} h^{\mu\nu}$.
- **References**: Useful Equations; EGDPP model.

### Combat Drones

- **Definition**: Unmanned aerial vehicles (UAVs) designed for military engagement, reconnaissance, or strike missions.
- **Project Context**: Spherical form factor optimized for 360° EMF propulsion, enabling omnidirectional maneuvers, stealth, and integration with MADA for high-g operations.
- **Mathematical/Technical Details**: 6DOF control via $a = T / m$; mass $m$ includes PCM for thermal buffering.
- **References**: About The Project section.

---

## D

### Diamagnetic Repulsion

- **Definition**: The repulsive force experienced by a diamagnetic material (or induced vacuum) in a magnetic field gradient, due to induced opposing currents.
- **Project Context**: Primary mechanism for thrust in QED-based propulsion, arising from virtual e⁺e⁻ pairs in strong B_opposing fields.
- **Mathematical/Technical Details**: Force component in $\mathbf{F} \propto \chi B^2 \nabla B$; enhanced by pulsing.
- **References**: Theory Overview.

### Duty Cycle

- **Definition**: The fraction of time a periodic signal is active, expressed as a percentage (e.g., 20–80%).
- **Project Context**: Variable in MADA pulsing (50–100 Hz) to optimize efficiency (>95%), thermal load, and stealth by reducing average power signature.
- **Mathematical/Technical Details**: $\text{Duty} = \frac{t_{\text{on}}}{T} \times 100\%$, where T is pulse period (e.g., 20 ms at 50 Hz).
- **References**: Pulsing strategy in Theory Overview.

---

## E

### Efficiency (η)

- **Definition**: The ratio of useful output power to input power, often as a percentage.
- **Project Context**: Target >95% for propulsion systems; balances thrust, power consumption, and range in drone operations.
- **Mathematical/Technical Details**: $\eta = \left( \frac{T \cdot v}{P} \right) \times 100\%$, with $P = I^2 R + P_{\text{eddy}}$.
- **References**: Useful Equations; Key Features.

### EGDPP (Emergent Gravity from Disrupted Photon Pairs)

- **Definition**: A scalar-tensor quantum gravity model where spacetime curvature emerges from QED photon pair disruptions, unifying electromagnetism and gravity via asymptotic safety.
- **Project Context**: Theoretical backbone for simulations; neutral to hypothesis—focus on empirical modifier for χ in thrust models.
- **Mathematical/Technical Details**: Predicts 95 GeV spin-0 resonance; RG flows for χ as above.
- **References**: Hofseth (2025); Theory Overview.

### Electromagnetic Field (EMF) Propulsion

- **Definition**: Thrust generation via manipulation of electromagnetic fields, bypassing traditional reaction mass.
- **Project Context**: Core technology using QED vacuum polarization for propellantless, high-thrust (Mach 26) drone propulsion.
- **Mathematical/Technical Details**: Thrust $T = N \cdot F \cdot \eta \cdot \cos\theta$, with F from vacuum effects.
- **References**: Project title and description.

### Emergent Gravity

- **Definition**: Theories positing gravity as an effective phenomenon arising from underlying quantum or thermodynamic processes, rather than fundamental.
- **Project Context**: Spin-0 (scalar) or spin-2 (tensor) variants in EGDPP link QED disruptions to gravitational analogs in propulsion.
- **Mathematical/Technical Details**: Source term $\delta T_{\mu\nu} \approx \chi B^2 h_{\mu\nu}$.
- **References**: EGDPP model.

---

## F

### Finemet Nanocrystalline Iron

- **Definition**: A soft magnetic alloy composed of iron-based nanocrystals in an amorphous matrix, offering high saturation and low losses.
- **Project Context**: Top-ranked material (96/100) for MADA circuits, ideal for high-frequency pulsing (up to 1 kHz) with minimal eddy currents.
- **Mathematical/Technical Details**: $B_s \approx 1.9$ T; core loss <0.5 W/kg at 50 Hz.
- **References**: Materials Ranking table.

### Flux Mapping

- **Definition**: Real-time visualization and analysis of magnetic flux density distributions in 3D space.
- **Project Context**: AI input for 6DOF navigation, ensuring optimal field gradients for thrust vectoring in drones.
- **Mathematical/Technical Details**: Computed via $\mathbf{B} = \nabla \times \mathbf{A}$; integrated with Matplotlib/SciPy.
- **References**: Key Features; `cad/flux_visualizer.py`.

### Functional RG Flows

- **Definition**: Non-perturbative renormalization group methods using Wetterich equation for effective actions in quantum field theories.
- **Project Context**: Employed in simulations to evolve χ across scales, validating asymptotic safety in EGDPP for propulsion predictions.
- **Mathematical/Technical Details**: Wetterich flow: $\partial_t \Gamma_k = \frac{1}{2} \text{STr} \left[ (\Gamma_k^{(2)} + R_k)^{-1} \partial_t R_k \right]$.
- **References**: Simulation Tools; EGDPP paper.

---

## G

### 6DOF (Six Degrees of Freedom)

- **Definition**: Independent movements in 3D space: translation (x, y, z) and rotation (roll, pitch, yaw).
- **Project Context**: Full controllability for spherical drones, achieved via MIMO AI for omnidirectional EMF thrust.
- **Mathematical/Technical Details**: State vector $\mathbf{q} = [x, y, z, \phi, \theta, \psi]^T$; Jacobian for control.
- **References**: Key Features.

---

## H

### Heisenberg-Euler-Schwinger (HES) Effective Action

- **Definition**: One-loop effective Lagrangian in QED describing nonlinear photon interactions in strong fields, accounting for vacuum polarization.
- **Project Context**: Basis for modeling virtual e⁺e⁻ pair effects at 0.1–1 MHz pulsing, enabling diamagnetic thrust calculations.
- **Mathematical/Technical Details**: $\mathcal{L}_{\text{HES}} = -\frac{1}{8\pi^2} \int_0^\infty ds \frac{e^{-m^2 s}}{s} \left[ \cot(e s F) - 1 + \frac{e s F}{3} \right]$, approximated for constant fields.
- **References**: Theory Overview; `simulations/equations.py`.

### Hiperco-50

- **Definition**: A high-saturation cobalt-iron alloy (50% Co, 50% Fe) with vanadium additions for soft magnetic properties.
- **Project Context**: Mentioned for magnetic circuit optimization; traded off for cobalt-free alternatives like Minnealloy due to cost/scalability.
- **Mathematical/Technical Details**: $B_s \approx 2.4$ T; used in early prototypes.
- **References**: README.md intro.

### h_μν (Metric Perturbation)

- **Definition**: Small deviation from Minkowski metric in linearized gravity, $g_{\mu\nu} = \eta_{\mu\nu} + h_{\mu\nu}$.
- **Project Context**: Couples to QED disruptions in EGDPP, sourcing emergent gravitational effects in thrust gradients.
- **Mathematical/Technical Details**: In Lagrangian $\mathcal{L}_{\text{disrupt}} = -\frac{1}{2} \chi B^2 h_{\mu\nu} h^{\mu\nu}$; gauge-fixed via harmonic condition.
- **References**: Useful Equations.

---

## I

### Inverse Cube Law (Magnetic Field Decay)

- **Definition**: Approximation for dipole magnetic field falloff, $B \propto 1/r^3$.
- **Project Context**: Explains MADA amplification needs; 6x distance requires ~216x field strength for equivalent effect.
- **Mathematical/Technical Details**: $B(r) = \frac{\mu_0}{4\pi} \frac{2 m}{r^3}$ for axial dipole.
- **References**: MADA section.

---

## L

### Lagrangian (ℒ_disrupt)

- **Definition**: The disruption term in the effective action coupling electromagnetic fields to metric perturbations.
- **Project Context**: Models photon pair disruptions leading to emergent forces in propulsion simulations.
- **Mathematical/Technical Details**: $\mathcal{L}_{\text{disrupt}} = -\frac{1}{2} \chi B^2 h_{\mu\nu} h^{\mu\nu}$.
- **References**: Useful Equations.

---

## M

### MADA (Magnetic Amplification and Direction Assembly)

- **Definition**: Patented device for focusing and amplifying magnetic beams, overcoming inverse power laws for extended-range fields.
- **Project Context**: Core hardware for generating B_opposing (>600 T effective); simplifies EMF propulsion by 200–500x.
- **Mathematical/Technical Details**: Amplification $k = 200–529$; force decay counter via 1/r^7 scaling.
- **References**: U.S. Patent #5,929,732; Dedicated MADA section.

### Mach 26

- **Definition**: Velocity equivalent to 26 times the speed of sound (~8,900 m/s at sea level), indicating hypersonic regime.
- **Project Context**: Target performance metric for drone thrust under optimized vacuum polarization and MADA.
- **Mathematical/Technical Details**: Derived from $v = \sqrt{\frac{T \cdot R}{m}}$ in range equation.
- **References**: README.md intro.

### Metglas Amorphous Iron

- **Definition**: Rapidly quenched iron-based metallic glass with amorphous structure, providing high permeability and low losses.
- **Project Context**: Ranked 95/100 for pulsing circuits; alternative to nanocrystalline for cost-sensitive builds.
- **Mathematical/Technical Details**: $\mu_r \approx 1,000,000$; thickness ~20–25 μm.
- **References**: Materials Ranking.

### MIMO (Multiple Input Multiple Output)

- **Definition**: Control system paradigm handling multiple sensors/actuators for robust multivariable dynamics.
- **Project Context**: Backbone of AI navigation for flux-based 6DOF control in noisy, high-field environments.
- **Mathematical/Technical Details**: Transfer matrix $\mathbf{G}(s)$; optimized via neural nets.
- **References**: Key Features; TensorFlow.

### Minnealloy

- **Definition**: Family of cobalt-free, high-performance soft magnetic alloys based on iron nitrides/carbides for extreme permeability.
- **Project Context**: Best overall (95/100) for scalable MADA; enables >20 T fields without rare earths.
- **Mathematical/Technical Details**: Variants α′ and α″; $B_s > 2.0$ T.
- **References**: Materials Ranking; README.md.

### Modifier Equation

- **Definition**: Empirically derived renormalization factor adjusting theoretical predictions (e.g., for χ) to match experimental data.
- **Project Context**: Essential for simulation fidelity; decouples propulsion from EGDPP hypothesis, emphasizing truth over theory.
- **Mathematical/Technical Details**: Tunable β_χ form; public experiments urged.
- **References**: Theory Overview.

### μ_0 (Vacuum Permeability)

- **Definition**: Magnetic constant $4\pi \times 10^{-7}$ H/m, relating B and H fields in vacuum.
- **Project Context**: Fundamental in all field calculations, e.g., pulsed $\Delta B = \mu_0 n I$.
- **Mathematical/Technical Details**: SI base unit.
- **References**: Useful Equations.

---

## N

### N52 Magnets

- **Definition**: Neodymium-iron-boron (NdFeB) permanent magnets with grade 52, offering high remanence (~1.4 T).
- **Project Context**: Low-cost source for MADA stacks (6x stacks ~3 T base); amplified to 600+ T.
- **Mathematical/Technical Details**: $B_r \approx 1.45$ T; affordable ($25/stack).
- **References**: MADA Implementation.

---

## P

### PCM (Phase Change Material)

- **Definition**: Substances absorbing/releasing latent heat during phase transitions (e.g., solid-liquid) for thermal buffering.
- **Project Context**: Channels in drone design for managing 10–40 kW from pulsing, preventing overheating.
- **Mathematical/Technical Details**: Heat capacity $Q = m \cdot L_f$, L_f fusion latent heat.
- **References**: Key Features.

### Pulsed Enhancement (ΔB)

- **Definition**: Incremental magnetic field increase from rapid current pulses in solenoids or coils.
- **Project Context**: Boosts B_opposing efficiency at 50–100 Hz, enabling bursts up to 1 kHz for agility.
- **Mathematical/Technical Details**: $\Delta B = \mu_0 n I$, n turns density, I current.
- **References**: Useful Equations; Pulsing strategy.

---

## Q

### QED (Quantum Electrodynamics)

- **Definition**: Relativistic quantum field theory describing electromagnetic interactions via photons and charged particles.
- **Project Context**: Foundation for vacuum polarization in propulsion; nonlinear extensions via HES for strong fields.
- **Mathematical/Technical Details**: Feynman diagrams for virtual pairs; effective action as above.
- **References**: Project name; Theory Overview.

---

## R

### Range (R)

- **Definition**: Maximum operational distance under given power and velocity constraints.
- **Project Context**: Extended via high η and low detection pulsing for stealth missions.
- **Mathematical/Technical Details**: $R = v \cdot \left( \frac{E}{P} \right)$, E energy capacity.
- **References**: Useful Equations.

### Renormalization Group Flow (RG Flow)

- **Definition**: Framework tracking how coupling constants evolve with energy scale in QFTs.
- **Project Context**: Simulates χ evolution for asymptotic safety in EGDPP; critical for modifier tuning.
- **Mathematical/Technical Details**: β-function as for β_χ.
- **References**: Simulation Tools; EGDPP.

---

## S

### Shielding

- **Definition**: Protective measures (e.g., Faraday cages, mu-metal) against electromagnetic interference or high-voltage fields.
- **Project Context**: Vital for electronics in QED systems; failure risks hardware damage (e.g., power supplies).
- **Mathematical/Technical Details**: Attenuation $A = 20 \log_{10} (E_i / E_t)$ dB.
- **References**: `docs/shielding.pdf`; Safety note in README.md.

### Spin-0 Emergent Gravity

- **Definition**: Scalar-field mediated emergent gravity in EGDPP, contrasting tensor (spin-2) models.
- **Project Context**: Current EGDPP version; predicts resonance at 95 GeV, adaptable for simulations.
- **Mathematical/Technical Details**: Scalar h in $h_{\mu\nu}$; updated β_χ.
- **References**: Theory Overview; Forthcoming EGDPP update.

### Spin-2 Emergent Gravity

- **Definition**: Tensor-based emergent gravity from prior EGDPP iterations, akin to GR linearization.
- **Project Context**: Legacy option for modifier equations; system supports switch to data-derived forms.
- **Mathematical/Technical Details**: $\beta_\chi = (4 + \eta_\chi) \chi + c g \chi$.
- **References**: Theory Overview.

### Stealth Operations

- **Definition**: Tactics minimizing detectability across spectra (radar, IR, acoustic).
- **Project Context**: Achieved via pulsed EMF (low average signature) and material choices for thermal/radar absorption.
- **Mathematical/Technical Details**: RCS reduction via geometry; IR via PCM.
- **References**: About The Project.

### Surface Field (B)

- **Definition**: Magnetic field at the surface of a magnet or coil assembly.
- **Project Context**: Base for opposition in MADA; scaled for propulsion circuits.
- **Mathematical/Technical Details**: $B \approx \frac{B_r}{2} \left( \frac{L}{\sqrt{R^2 + L^2}} + \frac{L + d}{\sqrt{R^2 + (L + d)^2}} \right)$.
- **References**: Useful Equations.

### Susceptibility (χ)

See [χ (Magnetic Susceptibility)](#χ-magnetic-susceptibility)

---

## T

### Thermal Management

- **Definition**: Engineering strategies for heat dissipation, distribution, and recovery in high-power systems.
- **Project Context**: Handles 10–40 kW from pulsing; integrates PCM and TEG for efficiency.
- **Mathematical/Technical Details**: Power $P_{\text{eddy}} \propto f^2 B^2 t^2$.
- **References**: Key Features.

### Thrust (T)

- **Definition**: Propulsive force generated by the system, in newtons (N).
- **Project Context**: Vectorized for 6DOF; targets hypersonic speeds in drones.
- **Mathematical/Technical Details**: $T = N \cdot F \cdot \eta \cdot \cos\theta$, F from χ B².
- **References**: Useful Equations; `simulations/thrust_model.py`.

---

## V

### Vacuum Polarization

- **Definition**: QED effect where virtual particle-antiparticle pairs screen charges, modifying field propagators in strong backgrounds.
- **Project Context**: Induces diamagnetic repulsion for propellantless thrust; threshold at B > 20 T.
- **Mathematical/Technical Details**: Polarization tensor $\Pi^{\mu\nu}(q)$; HES approximation.
- **References**: Theory Overview; Project core.

### Virtual Electron-Positron Pairs (e⁺e⁻)

- **Definition**: Transient quark-antiquark or lepton pairs from vacuum fluctuations, per Heisenberg uncertainty.
- **Project Context**: Screen fields in B_opposing, enabling repulsion; frequency-dependent at 0.1–1 MHz.
- **Mathematical/Technical Details**: Loop contribution to HES action.
- **References**: Theory Overview.

---

## Other Symbols and Parameters

### δT_μν (Stress-Energy Perturbation)

- **Definition**: Sourced modification to the energy-momentum tensor from field disruptions.
- **Project Context**: Links QED to emergent gravity in force calculations.
- **Mathematical/Technical Details**: $\delta T_{\mu\nu} \approx \chi B^2 h_{\mu\nu}$.
- **References**: Useful Equations.

### g (Coupling Constant)

- **Definition**: Fine-structure-like constant in QED-gravity interactions.
- **Project Context**: In β_χ for RG flows.
- **Mathematical/Technical Details**: $\alpha = g^2 / 4\pi \approx 1/137$.
- **References**: RG for χ.

### λ (Lambda, RG Parameter)

- **Definition**: Fixed-point regulator in β-function.
- **Project Context**: Tunes asymptotic safety.
- **Mathematical/Technical Details**: Denominator in $1 - 2\lambda$.
- **References**: Useful Equations.

---

This glossary is designed to evolve with the project; contributions via pull requests are encouraged (see `CONTRIBUTING.md`). For API-specific terms, consult Sphinx docs in `/docs/api`. 

**Total entries**: 50+; a reference for QED-EMF propulsion development.
