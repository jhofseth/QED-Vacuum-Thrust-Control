# Glossary

This glossary provides a compilation of terms, acronyms, concepts, and technical vocabulary relevant to the QED-Vacuum-Thrust-Control project. It is derived from the project's theoretical foundations in the Refractive Vacuum Gravity (RVG) Unified Field framework, quantum electrodynamics (QED), Disformal Gravity, electromagnetic propulsion systems, materials science, control engineering, and simulation tools. Entries are organized alphabetically for ease of reference, with cross-references where applicable. Each entry includes:

- **Definition**: A precise, formal explanation.
- **Project Context**: How the term applies to QED vacuum polarization-based EMF propulsion, MADA systems, AI control, and related simulations.
- **Mathematical/Technical Details**: Relevant equations, parameters, or derivations (where applicable).
- **References**: Key sources, including project files, patents, or literature.

The glossary emphasizes empirical adaptability (e.g., modifier equations independent of specific hypotheses) and practical implementation for defense applications, such as high-thrust, stealthy combat drones. Terms cover core physics, engineering, materials, and ancillary concepts to support researchers, engineers, and contributors.

---

## Numerical

### 95 GeV Resonance (Dilaton/Radion)

- **Definition**: A scalar boson (spin-0) observed at the Large Hadron Collider with 3.1σ combined significance (CMS + ATLAS) in the di-photon channel, identified within the RVG framework as a dilaton/radion that couples to the trace anomaly of the energy-momentum tensor.
- **Project Context**: The fundamental mediator governing the vacuum's refractive index; its excitation via strong magnetic fields enables macroscopic metric engineering for propulsion. Acts as a "softening agent" lowering the energy threshold for vacuum modification from Planck scales to Tesla scales.
- **Mathematical/Technical Details**: Mass m_φ = 95.4 GeV; couples to electromagnetic invariant via interaction Lagrangian: `ℒ_int ∝ (φ/f_φ)(B² − E²)`. Signal strength ~0.33 in CMS di-photon data.
- **References**: RVG Unified Field paper (Hofseth, 2025); CMS/ATLAS collaboration data; Table 1 in manuscript.

### 6DOF (Six Degrees of Freedom)

- **Definition**: Independent movements in 3D space: translation (x, y, z) and rotation (roll, pitch, yaw).
- **Project Context**: Full controllability for spherical drones, achieved via MIMO AI for omnidirectional EMF thrust vectoring.
- **Mathematical/Technical Details**: State vector $\mathbf{q} = [x, y, z, \phi, \theta, \psi]^T$; Jacobian for control.
- **References**: Key Features; `ai/navigation.py`.

---

## A

### Acceleration (a)

- **Definition**: The rate of change of velocity of an object with respect to time, typically measured in meters per second squared (m/s²) or gravitational units (g, where 1 g ≈ 9.81 m/s²).
- **Project Context**: Critical for propulsion performance in spherical combat drones, enabling maneuvers exceeding 500 g for non-ballistic trajectories and evasion in asymmetric warfare. Simulations model acceleration under pulsed magnetic fields to predict drone agility and stability.
- **Mathematical/Technical Details**: Derived from Master Equation as: `a = F_lift / m_system`, where F_lift is the integrated vacuum gradient force.
- **References**: `simulations/thrust_model.py`; RVG Unified Field paper Section 4.

### AI Navigation

- **Definition**: Artificial intelligence-driven systems for autonomous path planning, obstacle avoidance, and real-time decision-making in dynamic environments.
- **Project Context**: Implements MIMO neural networks for 6DOF control in EMF-propelled drones, integrating flux mapping and threat modeling for stealth operations. Enables hover, precision strikes, and swarm coordination while minimizing radar/thermal signatures.
- **Mathematical/Technical Details**: Relies on multiple-input-multiple-output (MIMO) architectures; flux mapping uses real-time sensor data for field gradients $\nabla B^2$.
- **References**: `ai/navigation.py`; TensorFlow dependencies in `requirements.txt`.

### α′-Fe₈(NC) (Alpha-Prime Iron Nitride Carbide / Minnealloy)

- **Definition**: A high-permeability, cobalt-free ferromagnetic alloy variant of Minnealloy, characterized by interstitial nitrogen and carbon atoms in an α-iron lattice, optimized for magnetic circuit applications.
- **Project Context**: Ranked highly (95/100) for magnetic circuits in MADA assemblies due to superior saturation magnetization (~2.8–2.9 T) and low coercivity, enabling efficient supra-saturation fields without cobalt dependency for scalable production.
- **Mathematical/Technical Details**: Saturation induction B_s ≈ 2.8–2.9 T; enables equivalent peak B with lower overdrive requirements compared to standard iron (B_s ≈ 2.1 T).
- **References**: `docs/materials_ranking.pdf`; RVG paper Section 5; Holistic materials ranking in README.md.

### α″-Fe₁₆N₂ (Alpha-Double-Prime Iron Nitride)

- **Definition**: A body-centered tetragonal (bct) martensitic phase of iron nitride exhibiting "giant" saturation magnetization due to lattice expansion and electron localization effects.
- **Project Context**: High-saturation permanent magnet material (~2.9 T) for optimized MADA configurations; enables intense localized fields for strong dilaton enhancement Θ_dilaton(B).
- **Mathematical/Technical Details**: Theoretical $M_s = 2.9$ T (250 emu/g); experimentally confirmed via polarized neutron reflectometry at $2.8 \pm 0.15$ T.
- **References**: `docs/materials_ranking.pdf`; RVG paper Section 5; Wang et al. research.

### ARMCO (American Rolling Mill Company Pure Iron)

- **Definition**: High-purity, low-carbon soft magnetic iron with minimal impurities (<0.005% carbon), exhibiting excellent ductility and magnetic softness.
- **Project Context**: Baseline material (score 90/100) for prototype magnetic circuits; demonstrates that vacuum effects manifest in any ferromagnetic material when supra-saturation conditions are achieved.
- **Mathematical/Technical Details**: Maximum permeability $\mu_m \approx 10,000$; saturation $B_s \approx 2.1$ T; requires higher overdrive for equivalent peak fields.
- **References**: `docs/materials_ranking.pdf`; Materials ranking table.

### Asymmetric Warfare

- **Definition**: Conflict involving non-state actors or weaker forces using unconventional tactics against superior conventional militaries.
- **Project Context**: Design driver for stealthy, high-maneuverability drones with EMF propulsion, emphasizing low-observability (radar/thermal) and precision strikes over brute force.
- **Mathematical/Technical Details**: N/A (strategic concept); modeled via threat analysis in simulations.
- **References**: README.md project description.

### Asymptotic Safety

- **Definition**: A quantum field theory paradigm where ultraviolet divergences are controlled by a non-perturbative fixed point, ensuring finite couplings at all energy scales.
- **Project Context**: Theoretical foundation ensuring the RVG framework remains consistent at high energies; validates dilaton coupling behavior across scales for propulsion predictions.
- **Mathematical/Technical Details**: Fixed point in β-function ensures finite vacuum response at all field strengths.
- **References**: RVG Unified Field paper; `simulations/equations.py`.

---

## B

### β_χ (Beta Function for Susceptibility)

- **Definition**: The renormalization group β-function governing the scale dependence of vacuum susceptibility in quantum field theories.
- **Project Context**: Historical parameter from earlier EGDPP formulations; superseded by dilaton enhancement factor Θ_dilaton(B) in current RVG framework.
- **Mathematical/Technical Details**: Legacy forms: spin-0 $\beta_\chi = -4\chi + \frac{g}{2\pi} \frac{\chi}{1 - 2\lambda}$; spin-2 $\beta_\chi = (4 + \eta_\chi) \chi + c g \chi$.
- **References**: Historical; see Θ_dilaton for current formulation.

### Bi₂Te₃ TEG (Bismuth Telluride Thermoelectric Generator)

- **Definition**: A solid-state device converting heat differentials into electrical energy via the Seebeck effect, using bismuth telluride semiconductors.
- **Project Context**: Optional component in thermal management for dissipating 10–40 kW from high-field pulsing, recycling waste heat to power auxiliary systems in drones.
- **Mathematical/Technical Details**: Efficiency $\eta = \frac{\Delta T}{T_h} \cdot \frac{\sqrt{1 + ZT} - 1}{\sqrt{1 + ZT} + 1}$, where ZT ≈ 1–2 at 300–500 K.
- **References**: Key Features section; `hardware/interfaces.py`.

### B_opposing (Opposing Magnetic Field)

- **Definition**: The magnetic field strength in opposing-pole configurations required to induce nonlinear QED vacuum effects and significant dilaton enhancement.
- **Project Context**: Threshold parameter (>20 T, up to 60–90+ T depending on mass) for activating macroscopic vacuum refractive index changes; must substantially exceed material saturation $B_s$ for supra-saturation regime.
- **Mathematical/Technical Details**: $B_{\text{gap}} \approx \frac{\mu_0 m_1 m_2}{2\pi d^2} \cdot k$, with MADA amplification $k \approx 200$–$529$.
- **References**: Theory Overview; `simulations/thrust_model.py --b_opposing`; RVG paper Section 6.

### Bushman Array

- **Definition**: The opposing-pole magnet geometry described in U.S. Patent 5,929,732, creating flux frustration and compressed magnetic beams.
- **Project Context**: Optimal geometric solution for generating the steep $\nabla B^2$ gradients required by the Master Equation; creates quasi-singularities in field gradients approaching $10^{10}$ T²/m.
- **Mathematical/Technical Details**: Like-poles-opposing configuration forces lateral flux compression; central magnet fires through compressed zone.
- **References**: U.S. Patent #5,929,732; MADA section; RVG paper Section 6.

---

## C

### Combat Drones

- **Definition**: Unmanned aerial vehicles (UAVs) designed for military engagement, reconnaissance, or strike missions.
- **Project Context**: Spherical form factor optimized for 360° EMF propulsion, enabling omnidirectional maneuvers, stealth, and integration with MADA for high-g operations.
- **Mathematical/Technical Details**: 6DOF control via Master Equation thrust; mass $m$ includes PCM for thermal buffering.
- **References**: About The Project section.

### Conformal Symmetry Breaking

- **Definition**: The spontaneous or explicit breaking of scale invariance in quantum field theories, giving rise to massive scalar particles like the dilaton.
- **Project Context**: The 95 GeV dilaton/radion arises from spontaneous breaking of conformal symmetry; this breaking enables its coupling to the trace anomaly and thus to electromagnetic energy density.
- **Mathematical/Technical Details**: Dilaton couples to $T^\mu_\mu$ (trace of stress-energy tensor); conformal anomaly generates non-zero trace in QED.
- **References**: RVG paper Section 2.2.

---

## D

### Diamagnetic Repulsion

- **Definition**: The repulsive force experienced by a diamagnetic material (or induced vacuum polarization) in a magnetic field gradient, due to induced opposing currents or virtual pair effects.
- **Project Context**: Phenomenological description of thrust mechanism; more precisely described in RVG as vacuum gradient force from refractive index modification.
- **Mathematical/Technical Details**: Force density $\mathbf{f}_{\text{vac}} \approx -\frac{B^2}{2\mu_0} \nabla K$.
- **References**: Theory Overview; RVG paper Section 4.

### Dilaton

- **Definition**: A scalar particle arising from the spontaneous breaking of conformal (scale) symmetry, coupling universally to the trace of the energy-momentum tensor.
- **Project Context**: The 95 GeV resonance identified as a dilaton mediates vacuum refractive index changes; its excitation via magnetic fields enables metric engineering.
- **Mathematical/Technical Details**: Interaction Lagrangian: `ℒ_int ∝ (φ/f_φ)(B² − E²)`. Couples to trace anomaly T^μ_μ (trace of stress-energy tensor).
- **References**: RVG paper Sections 2–3; see also [95 GeV Resonance](#95-gev-resonance-dilatonradion).

### Dilaton Enhancement Factor (Θ_dilaton)

- **Definition**: The non-linear vacuum response function characterizing how strongly the vacuum's refractive index responds to magnetic field intensity, mediated by the 95 GeV dilaton resonance.
- **Project Context**: Central parameter in the Master Equation; weak at low B, grows strongly with field intensity as the dilaton is "pumped" by electromagnetic energy density. Replaces earlier χ-based formulations.
- **Mathematical/Technical Details**: Appears in Master Equation: `F_lift = ∫ (1/2μ₀) Θ_dilaton(B) · ∇B² dV`. Functional form to be determined experimentally.
- **References**: RVG paper Sections 4, 7; Useful Equations in README.md; `simulations/equations.py`.

### Disformal Gravity

- **Definition**: A generalization of scalar-tensor gravity where the physical metric couples to both the scalar field value and its gradient, enabling directional (not just conformal) metric distortions.
- **Project Context**: Mechanism translating scalar field gradients (from ∇B²) into directional thrust vectors; the "Magnetic Beam" is essentially a "Disformal Beam" projecting modified metric along the gradient axis.
- **Mathematical/Technical Details**: Physical metric: `g̃_μν = C(φ)g_μν + D(φ)∂_μφ ∂_νφ`. Conformal term C(φ) rescales volumes; disformal term D(φ) distorts along gradient.
- **References**: RVG paper Section 3.3; Beltrán Jiménez et al. (2018).

### Disformal QED

- **Definition**: The synthesis of Quantum Electrodynamics (specifically the Euler-Heisenberg effective action) with Disformal Gravity, using the Gordon Optical Metric as the unifying mathematical framework.
- **Project Context**: The theoretical foundation of the RVG Unified Field; describes how electromagnetic field configurations modify the effective spacetime metric experienced by matter and light.
- **Mathematical/Technical Details**: Combines EH nonlinearity with disformal coupling; photons follow geodesics of Gordon metric $\gamma_{\mu\nu} = g_{\mu\nu} + (1 - n^2)u_\mu u_\nu$.
- **References**: RVG paper Section 3; project Theory Overview.

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
- **Mathematical/Technical Details**: `η = (|F_lift| · v / P) × 100%`, where P = I²R_coil + P_eddy + P_switching.
- **References**: Useful Equations; Key Features.

### EGDPP (Emergent Gravity from Disrupted Photon Pairs)

- **Definition**: Earlier designation for the theoretical framework now called Refractive Vacuum Gravity (RVG) Unified Field; a scalar-tensor quantum gravity model where spacetime curvature emerges from QED photon pair disruptions.
- **Project Context**: Historical term; current framework uses RVG terminology emphasizing vacuum refractive index engineering and the 95 GeV dilaton mechanism.
- **Mathematical/Technical Details**: See [Refractive Vacuum Gravity (RVG)](#refractive-vacuum-gravity-rvg-unified-field).
- **References**: Legacy references; superseded by RVG paper (Hofseth, 2025).

### Electromagnetic Field (EMF) Propulsion

- **Definition**: Thrust generation via manipulation of electromagnetic fields to modify vacuum properties, bypassing traditional reaction mass.
- **Project Context**: Core technology using QED vacuum polarization enhanced by dilaton coupling for propellantless, high-thrust (Mach 26) drone propulsion.
- **Mathematical/Technical Details**: Thrust from Master Equation: `F_lift = ∫ (1/2μ₀) Θ_dilaton(B) · ∇B² dV`.
- **References**: Project title and description; RVG paper.

### Emergent Gravity

- **Definition**: Theories positing gravity as an effective phenomenon arising from underlying quantum or thermodynamic processes, rather than as a fundamental force.
- **Project Context**: The RVG framework treats gravity as emergent from vacuum polarization effects; metric modifications arise from scalar field (dilaton) dynamics rather than fundamental gravitons.
- **Mathematical/Technical Details**: Evades Weinberg-Witten theorem via emergent (not fundamental) metric excitations and scalar mediation.
- **References**: RVG paper Section 8.

### Euler-Heisenberg Effective Action

- **Definition**: The one-loop effective Lagrangian in QED describing nonlinear photon-photon interactions in strong electromagnetic fields, arising from virtual electron-positron pair creation.
- **Project Context**: Basis for vacuum polarization effects; predicts refractive index changes in strong fields, enhanced by dilaton coupling in the RVG framework from Δn ~ 10⁻²² (standard QED) to macroscopic values.
- **Mathematical/Technical Details**: `ℒ_EH = −(1/4)F_μνF^μν + (α²/90m_e⁴)[(F_μνF^μν)² + (7/4)(F_μνF̃^μν)²]`.
- **References**: RVG paper Section 3.1; PVLAS experiment.

---

## F

### Finemet Nanocrystalline Iron

- **Definition**: A soft magnetic alloy composed of iron-based nanocrystals in an amorphous matrix, offering high saturation and low losses.
- **Project Context**: Top-ranked material (96/100) for MADA circuits, ideal for high-frequency pulsing (up to 1 kHz) with minimal eddy currents.
- **Mathematical/Technical Details**: $B_s \approx 1.9$ T; core loss <0.5 W/kg at 50 Hz.
- **References**: Materials Ranking table.

### Flux Frustration

- **Definition**: The condition in opposing-pole magnet configurations where like poles face each other, forcing magnetic flux lines to compress laterally rather than bridging the gap.
- **Project Context**: Key mechanism in MADA/Bushman arrays creating regions of extreme magnetic pressure and steep field gradients for vacuum engineering.
- **Mathematical/Technical Details**: Creates quasi-singularities in ∇B² approaching 10¹⁰–10¹² T²/m in nested configurations.
- **References**: RVG paper Section 6; MADA section.

### Flux Mapping

- **Definition**: Real-time visualization and analysis of magnetic flux density distributions in 3D space.
- **Project Context**: AI input for 6DOF navigation, ensuring optimal field gradients for thrust vectoring in drones.
- **Mathematical/Technical Details**: Computed via $\mathbf{B} = \nabla \times \mathbf{A}$; integrated with Matplotlib/SciPy.
- **References**: Key Features; `cad/flux_visualizer.py`.

---

## G

### Gordon Optical Metric

- **Definition**: The effective metric tensor describing photon propagation in a medium with refractive index $n$, where light follows geodesics of this metric rather than the background spacetime metric.
- **Project Context**: Mathematical framework unifying electromagnetism and gravity in RVG; variations in vacuum refractive index $K$ translate directly to effective metric curvature, equivalent to gravitational effects.
- **Mathematical/Technical Details**: $\gamma_{\mu\nu} = g_{\mu\nu} + (1 - n^2)u_\mu u_\nu$; gradients in $n$ create forces analogous to gravity (cf. Shapiro delay).
- **References**: RVG paper Section 3.2; Gordon (1923).

---

## H

### Heisenberg-Euler-Schwinger (HES) Effective Action

- **Definition**: Alternative name for the Euler-Heisenberg effective action, sometimes including Schwinger's contributions on pair creation in constant fields.
- **Project Context**: See [Euler-Heisenberg Effective Action](#euler-heisenberg-effective-action).
- **References**: Theory Overview; `simulations/equations.py`.

### Hiperco-50

- **Definition**: A high-saturation cobalt-iron alloy (50% Co, 50% Fe) with vanadium additions for soft magnetic properties.
- **Project Context**: Mentioned for magnetic circuit optimization; traded off for cobalt-free alternatives like Minnealloy due to cost/scalability concerns.
- **Mathematical/Technical Details**: $B_s \approx 2.4$ T; used in early prototypes.
- **References**: README.md intro.

### h_μν (Metric Perturbation)

- **Definition**: Small deviation from flat Minkowski metric in linearized gravity, $g_{\mu\nu} = \eta_{\mu\nu} + h_{\mu\nu}$.
- **Project Context**: Historical notation in earlier EGDPP formulations; current RVG framework emphasizes Gordon optical metric and refractive index gradients rather than direct metric perturbations.
- **Mathematical/Technical Details**: Relates to effective metric via $\gamma_{\mu\nu}$ in Gordon formalism.
- **References**: Legacy equations; see Gordon Optical Metric.

---

## I

### Inverse Cube Law (Magnetic Field Decay)

- **Definition**: Approximation for dipole magnetic field falloff, $B \propto 1/r^3$.
- **Project Context**: Explains MADA amplification requirements; 6x distance requires ~216x field strength for equivalent effect, motivating the Bushman focusing geometry.
- **Mathematical/Technical Details**: $B(r) = \frac{\mu_0}{4\pi} \frac{2 m}{r^3}$ for axial dipole; force decay follows $1/r^7$.
- **References**: MADA section; RVG paper Section 6.

---

## K

### K (Vacuum Refractive Index)

- **Definition**: The effective refractive index of the vacuum in the presence of strong electromagnetic fields, governing the local speed of light and effective metric properties.
- **Project Context**: Central quantity in metric engineering; gradients in $K$ produce gravitational-equivalent forces. Modified from unity by dilaton-enhanced vacuum polarization.
- **Mathematical/Technical Details**: $K(\mathbf{r}) = 1 + \chi_{\text{vac}}(B) \approx 1 + \Theta_{95} \frac{B^2}{B_{\text{crit}}^2}$; $\nabla K \propto \Theta_{\text{dilaton}}(B) \nabla B^2$.
- **References**: RVG paper Sections 3–4; Useful Equations.

---

## L

### Lagrangian (ℒ_disrupt)

- **Definition**: Historical disruption term in earlier EGDPP formulations coupling electromagnetic fields to metric perturbations.
- **Project Context**: Superseded by dilaton interaction Lagrangian in current RVG framework.
- **Mathematical/Technical Details**: Legacy form: `ℒ_disrupt = −(1/2)χB²h_μν h^μν`.
- **References**: Historical; see Trace Anomaly Coupling.

---

## M

### MADA (Magnetic Amplification and Direction Assembly)

- **Definition**: Patented device (U.S. Patent 5,929,732, Lockheed Martin Corporation) for focusing and amplifying magnetic beams using opposing-pole geometries, overcoming inverse power laws for extended-range field effects.
- **Project Context**: Core hardware for generating B_opposing fields and steep ∇B² gradients; simplifies EMF propulsion requirements by 200–500x through flux frustration and beam focusing.
- **Mathematical/Technical Details**: Amplification factor k = 200–529; nested/stacked configurations can achieve >10¹² T²/m gradients in frustration zones.
- **References**: U.S. Patent #5,929,732 (Bushman); Dedicated MADA section; RVG paper Section 6.

### Mach 26

- **Definition**: Velocity equivalent to 26 times the speed of sound (~8,900 m/s at sea level), indicating hypersonic regime.
- **Project Context**: Target performance metric for drone thrust under optimized vacuum polarization and MADA configurations.
- **Mathematical/Technical Details**: Derived from range and thrust equations with high-efficiency propulsion.
- **References**: README.md intro.

### Master Equation of Levitation

- **Definition**: The fundamental equation quantifying propulsive force from engineered vacuum refractive index gradients in the RVG framework.
- **Project Context**: Central design equation for all propulsion calculations; integrates dilaton enhancement and magnetic energy density gradients over the active volume.
- **Mathematical/Technical Details**: `F_lift = ∫ (1/2μ₀) Θ_dilaton(B) · ∇(B·B) dV`. Force scales as T²/m; direction opposite highest B² concentration.
- **References**: RVG paper Section 4; Useful Equations; `simulations/equations.py`.

### Metglas Amorphous Iron

- **Definition**: Rapidly quenched iron-based metallic glass with amorphous structure, providing high permeability and low losses.
- **Project Context**: Ranked 95/100 for pulsing circuits; alternative to nanocrystalline for cost-sensitive builds.
- **Mathematical/Technical Details**: $\mu_r \approx 1,000,000$; thickness ~20–25 μm.
- **References**: Materials Ranking.

### Metric Engineering

- **Definition**: The concept that the spacetime metric tensor is not a fixed background but a dynamic variable determined by local vacuum properties (permittivity, permeability, refractive index), and can therefore be manipulated via electromagnetic means.
- **Project Context**: Core philosophy of the RVG framework; gravity is isomorphic to refractive index gradients, so engineering $\nabla K$ engineers gravity.
- **Mathematical/Technical Details**: Based on Polarizable Vacuum representation where $g_{\mu\nu} \leftrightarrow K(\mathbf{r})$.
- **References**: RVG paper Section 1; Puthoff PV theory.

### MIMO (Multiple Input Multiple Output)

- **Definition**: Control system paradigm handling multiple sensors/actuators for robust multivariable dynamics.
- **Project Context**: Backbone of AI navigation for flux-based 6DOF control in noisy, high-field environments.
- **Mathematical/Technical Details**: Transfer matrix $\mathbf{G}(s)$; optimized via neural nets.
- **References**: Key Features; TensorFlow.

### Minnealloy

- **Definition**: Family of cobalt-free, high-performance soft magnetic alloys based on iron nitrides/carbides, developed at University of Minnesota, optimized for extreme permeability and high saturation.
- **Project Context**: Best overall material (95/100) for scalable MADA magnetic circuits; enables supra-saturation fields with lower overdrive requirements due to high $B_s$ (~2.8–2.9 T).
- **Mathematical/Technical Details**: Variants α′-Fe₈(NC) for circuits, α″-Fe₁₆N₂ for permanent magnets; both metastable phases requiring careful synthesis.
- **References**: Materials Ranking; RVG paper Section 5; README.md.

### Modifier Equation

- **Definition**: Empirically derived function adjusting theoretical predictions (e.g., for Θ_dilaton) to match experimental data, enabling simulation fidelity independent of specific theoretical hypotheses.
- **Project Context**: Essential for practical propulsion calculations; the system is neutral—any validated modifier equation (RVG-derived, legacy EGDPP, or purely experimental) can be used. Public experiments needed for calibration.
- **Mathematical/Technical Details**: Functional form of Θ_dilaton(B) to be determined; current framework provides theoretical guidance, experiment provides validation.
- **References**: Theory Overview; RVG paper conclusion.

### μ_0 (Vacuum Permeability)

- **Definition**: Magnetic constant $4\pi \times 10^{-7}$ H/m, relating B and H fields in vacuum.
- **Project Context**: Fundamental constant in all field and force calculations, including Master Equation.
- **Mathematical/Technical Details**: SI base unit; appears in $\mathbf{f}_{\text{vac}} \approx -\frac{B^2}{2\mu_0} \nabla K$.
- **References**: Useful Equations.

---

## N

### N52 Magnets

- **Definition**: Neodymium-iron-boron (NdFeB) permanent magnets with grade 52, offering high remanence (~1.4–1.6 T).
- **Project Context**: Low-cost source for MADA stacks (6x stacks ~3 T base); amplified to 600+ T effective via MADA geometry.
- **Mathematical/Technical Details**: $B_r \approx 1.45$ T; affordable ($25/stack of 6).
- **References**: MADA Implementation section.

### Nested MADA

- **Definition**: Recursive MADA configuration where each magnet position in a base unit is replaced by a complete subscale MADA assembly, creating multi-stage hierarchical flux compression.
- **Project Context**: Advanced implementation for achieving extreme localized B_opposing and ∇B² (potentially >10¹² T²/m) through compounded frustration effects.
- **Mathematical/Technical Details**: Each nesting level multiplies effective amplification; practical limits from demagnetization and material saturation.
- **References**: MADA section; RVG paper Section 6.2.

---

## P

### PCM (Phase Change Material)

- **Definition**: Substances absorbing/releasing latent heat during phase transitions (e.g., solid-liquid) for thermal buffering.
- **Project Context**: Channels in drone design for managing 10–40 kW from pulsing, preventing overheating of coils and electronics.
- **Mathematical/Technical Details**: Heat capacity $Q = m \cdot L_f$, where $L_f$ is fusion latent heat.
- **References**: Key Features.

### Polarizable Vacuum (PV)

- **Definition**: Theoretical representation of General Relativity where gravity manifests as spatial variations in the vacuum's dielectric properties (permittivity ε, permeability μ), with the metric encoded in the refractive index $K = \sqrt{\epsilon_r \mu_r}$.
- **Project Context**: Foundational concept for metric engineering; establishes that gravitational potentials are isomorphic to refractive index gradients, enabling electromagnetic manipulation of effective gravity.
- **Mathematical/Technical Details**: In PV representation: $\epsilon = K\epsilon_0$, $\mu = K\mu_0$; speed of light $c_{\text{local}} = c_0/K$; gravitational time dilation ↔ $K > 1$.
- **References**: RVG paper Section 1; Puthoff (2002); Dicke's variable-c theories.

### Pulsed Enhancement (ΔB)

- **Definition**: Incremental magnetic field increase from rapid current pulses in solenoids or coils.
- **Project Context**: Boosts B_opposing efficiency at 50–100 Hz default, enabling bursts up to 1 kHz for high-agility maneuvers; asymmetric waveforms can produce net momentum transfer.
- **Mathematical/Technical Details**: $\frac{dB}{dt} = \mu_0 n \frac{dI}{dt}$; $\Delta B \approx \mu_0 n \Delta I$, where $n$ is turns density, $I$ is current.
- **References**: Useful Equations; Pulsing strategy.

---

## Q

### QED (Quantum Electrodynamics)

- **Definition**: Relativistic quantum field theory describing electromagnetic interactions via photon exchange and charged particle dynamics.
- **Project Context**: Foundation for vacuum polarization effects; nonlinear extensions via Euler-Heisenberg action describe strong-field behavior enabling propulsion.
- **Mathematical/Technical Details**: Virtual pair loops modify vacuum properties; effective action encodes nonlinear corrections.
- **References**: Project name; Theory Overview; RVG paper.

---

## R

### Radion

- **Definition**: A scalar field arising in extra-dimensional theories (e.g., Randall-Sundrum models) that stabilizes the size of compact dimensions; couples to the trace of the energy-momentum tensor.
- **Project Context**: Alternative identification for the 95 GeV resonance; radion and dilaton are often used interchangeably in the RVG framework as both couple to $T^\mu_\mu$.
- **Mathematical/Technical Details**: Mixing with Higgs allows shared decay channels; distinct from Higgs via direct $T^\mu_\mu$ coupling.
- **References**: RVG paper Section 2.2; see also [95 GeV Resonance](#95-gev-resonance-dilatonradion).

### Range (R)

- **Definition**: Maximum operational distance under given power and velocity constraints.
- **Project Context**: Extended via high efficiency η and low-detection pulsing for stealth missions.
- **Mathematical/Technical Details**: $R \approx v \cdot t_{\text{op}} = v \cdot \frac{E_{\text{stored}}}{P}$.
- **References**: Useful Equations.

### Refractive Vacuum Gravity (RVG) Unified Field

- **Definition**: The theoretical framework synthesizing Disformal QED, the 95 GeV dilaton/radion resonance, and the Gordon Optical Metric to enable macroscopic engineering of spacetime via electromagnetic configurations.
- **Project Context**: Current theoretical foundation for all propulsion calculations and simulations; posits that the 95 GeV scalar mediates vacuum refractive index changes, allowing metric engineering at Tesla (not Planck) scales.
- **Mathematical/Technical Details**: Core elements: dilaton enhancement Θ_dilaton(B), Gordon metric $\gamma_{\mu\nu}$, Master Equation of Levitation, disformal coupling for directional thrust.
- **References**: RVG paper (Hofseth, 2025) https://dx.doi.org/10.2139/ssrn.5381654; README.md Theory Overview.

### Renormalization Group Flow (RG Flow)

- **Definition**: Framework tracking how coupling constants and parameters evolve with energy scale in quantum field theories.
- **Project Context**: Historical approach in EGDPP for χ evolution; current RVG framework focuses on phenomenological Θ_dilaton(B) with experimental calibration.
- **Mathematical/Technical Details**: β-functions describe scale dependence; asymptotic safety ensures UV finiteness.
- **References**: Historical; RVG paper.

---

## S

### Shielding

- **Definition**: Protective measures (e.g., Faraday cages, mu-metal enclosures) against electromagnetic interference or high-voltage field exposure.
- **Project Context**: Critical for protecting AI control electronics in QED propulsion systems; failure risks hardware damage (documented power supply failures).
- **Mathematical/Technical Details**: Attenuation $A = 20 \log_{10} (E_i / E_t)$ dB; requires multi-layer approach for broadband protection.
- **References**: `docs/shielding.pdf`; Safety note in README.md.

### SLSB (Spontaneous Lorentz Symmetry Breaking)

- **Definition**: A mechanism where Lorentz invariance is spontaneously broken by a background field configuration, establishing a preferred frame locally.
- **Project Context**: Enables evasion of Weinberg-Witten theorem; the MADA magnetic beam creates a birefringent, anisotropic vacuum region where strict Lorentz covariance assumptions fail.
- **Mathematical/Technical Details**: Background B-field defines preferred direction; WW theorem assumptions violated locally.
- **References**: RVG paper Section 8.

### Stealth Operations

- **Definition**: Tactics minimizing detectability across electromagnetic spectra (radar, IR, acoustic).
- **Project Context**: Achieved via pulsed EMF (low average signature), variable duty cycles, and material choices for thermal/radar absorption.
- **Mathematical/Technical Details**: RCS reduction via geometry; IR via PCM thermal management.
- **References**: About The Project.

### Supra-Saturation

- **Definition**: Operating regime where the opposing gap magnetic field substantially exceeds the ferromagnetic material's saturation magnetization B_s, driving effective permeability toward unity (μ_eff ≈ 1) in the high-stress zone.
- **Project Context**: Universal critical requirement for macroscopic vacuum effects; achievable with any ferromagnetic material given sufficient opposing field drive. Higher-B_s materials (Minnealloy ~2.9 T) require less overdrive than lower-B_s materials (iron ~2.1 T).
- **Mathematical/Technical Details**: Requires B_opposing ≫ B_s; enables intense localized B and steep ∇B² for strong Θ_dilaton pumping.
- **References**: RVG paper Sections 5–7; Useful Equations; Materials discussion.

### Surface Field (B)

- **Definition**: Magnetic field at the surface of a magnet or coil assembly.
- **Project Context**: Base input for MADA amplification calculations; scaled via opposing geometry for propulsion circuits.
- **Mathematical/Technical Details**: Axial field: $B(z) = \frac{B_r}{2} \left[ \frac{L + z}{\sqrt{R^2 + (L + z)^2}} - \frac{z}{\sqrt{R^2 + z^2}} \right]$.
- **References**: Useful Equations.

---

## T

### Thermal Management

- **Definition**: Engineering strategies for heat dissipation, distribution, and recovery in high-power systems.
- **Project Context**: Handles 10–40 kW from high-field pulsing; integrates PCM channels and optional TEG for efficiency and component protection.
- **Mathematical/Technical Details**: Eddy loss $P_{\text{eddy}} \propto f^2 B^2 t^2$; total power $P = I^2 R_{\text{coil}} + P_{\text{eddy}} + P_{\text{switching}}$.
- **References**: Key Features.

### Thrust (T)

- **Definition**: Propulsive force generated by the system, in newtons (N).
- **Project Context**: Vectorized for 6DOF control; derived from Master Equation integration over active volume.
- **Mathematical/Technical Details**: `F_net = |F_lift| · η_align · cosθ`. Direction opposite B² maximum.
- **References**: Useful Equations; `simulations/thrust_model.py`.

### Trace Anomaly

- **Definition**: The quantum correction that breaks classical conformal invariance in QED, producing a non-zero trace of the energy-momentum tensor even for massless fields.
- **Project Context**: The mechanism enabling dilaton coupling to electromagnetic fields; without the trace anomaly, scalars would not interact with light. Generates the dilaton interaction Lagrangian.
- **Mathematical/Technical Details**: `T^μ_μ = (β(g)/2g)F_μνF^μν + m_f ψ̄ψ`. β-function encodes running coupling.
- **References**: RVG paper Section 2.2.1; Huang (2018).

### Trace Anomaly Coupling

- **Definition**: The direct interaction between the dilaton scalar field and electromagnetic energy density arising from the trace anomaly.
- **Project Context**: Theoretical cornerstone of RVG; dictates that magnetic energy density (B² > E²) acts as a source term for the dilaton field, enabling "pumping" of the 95 GeV resonance via intense magnetic fields.
- **Mathematical/Technical Details**: `ℒ_int ∝ (φ/f_φ)(B² − E²)`. Magnetic dominance required for positive coupling.
- **References**: RVG paper Section 2.2.1.

---

## V

### Vacuum Force Density

- **Definition**: The local force per unit volume exerted by a graded vacuum (varying refractive index) on matter or fields within it.
- **Project Context**: Intermediate quantity in deriving Master Equation; describes how refractive index gradients create mechanical forces.
- **Mathematical/Technical Details**: $\mathbf{f}_{\text{vac}} \approx -\frac{B^2}{2\mu_0} \nabla K$; integrates to total lift force.
- **References**: RVG paper Section 4.1; Useful Equations.

### Vacuum Polarization

- **Definition**: QED effect where virtual particle-antiparticle pairs transiently appear in the vacuum, screening charges and modifying field propagation in strong electromagnetic backgrounds.
- **Project Context**: Fundamental mechanism for vacuum refractive index modification; enhanced by dilaton coupling from negligible ($\Delta n \sim 10^{-22}$) to macroscopic levels at high $B$.
- **Mathematical/Technical Details**: Encoded in Euler-Heisenberg effective action; polarization tensor $\Pi^{\mu\nu}(q)$ modifies photon propagator.
- **References**: Theory Overview; RVG paper Section 3.

### Vacuum Stiffness (Vacuum Tension)

- **Definition**: The resistance of the vacuum to refractive index modification; in standard QED, extremely high (Planck-scale energy density required), but reduced by dilaton coupling in the RVG framework.
- **Project Context**: The dilaton acts as a "softening agent," lowering the threshold for metric modification from Planck to Tesla scales; also connects laboratory effects to cosmological dark matter phenomenology.
- **Mathematical/Technical Details**: Standard QED: $\Delta n \sim 10^{-22}$ at 1 T; RVG with dilaton: macroscopic $\Delta K$ achievable.
- **References**: RVG paper Sections 1, 4.3, 9.

### Virtual Electron-Positron Pairs (e⁺e⁻)

- **Definition**: Transient particle-antiparticle pairs arising from vacuum fluctuations consistent with Heisenberg uncertainty, existing briefly before annihilation.
- **Project Context**: Mediators of vacuum polarization; their creation/annihilation in strong B-fields modifies vacuum refractive properties.
- **Mathematical/Technical Details**: Loop contributions to Euler-Heisenberg action; threshold for real pair creation at Schwinger field ~10¹⁸ V/m.
- **References**: Theory Overview.

---

## W

### Weinberg-Witten Theorem

- **Definition**: A no-go theorem stating that massless spin-2 particles (gravitons) cannot carry a Lorentz-covariant stress-energy tensor, constraining emergent gravity theories.
- **Project Context**: The RVG framework evades this theorem via: (1) emergent rather than fundamental gravitons, (2) scalar (spin-0) dilaton mediation (explicitly allowed by WW), and (3) Spontaneous Lorentz Symmetry Breaking in the magnetic beam region.
- **Mathematical/Technical Details**: WW forbids massless $j > 1$ particles with non-zero charge coupling to conserved $T^{\mu\nu}$; spin-0 explicitly exempt.
- **References**: RVG paper Section 8; Weinberg & Witten (1980).

---

## Other Symbols and Parameters

### δT_μν (Stress-Energy Perturbation)

- **Definition**: Historical notation for the sourced modification to the energy-momentum tensor from field disruptions in EGDPP formulations.
- **Project Context**: Superseded by dilaton source term in current RVG framework.
- **Mathematical/Technical Details**: Legacy: $\delta T_{\mu\nu} \approx \chi B^2 h_{\mu\nu}$.
- **References**: Historical; see Trace Anomaly Coupling.

### g (Coupling Constant)

- **Definition**: Generic coupling parameter in QED-gravity interactions, related to fine structure constant.
- **Project Context**: Appears in historical β_χ RG flows; current framework uses phenomenological Θ_dilaton.
- **Mathematical/Technical Details**: $\alpha = g^2 / 4\pi \approx 1/137$.
- **References**: Historical equations.

### λ (Lambda, RG Parameter)

- **Definition**: Fixed-point regulator parameter in β-function formulations.
- **Project Context**: Historical parameter in EGDPP RG flows.
- **Mathematical/Technical Details**: Appears in denominator $(1 - 2\lambda)$.
- **References**: Historical; legacy equations.

### χ (Magnetic Susceptibility)

- **Definition**: A dimensionless measure of a material's or vacuum's magnetization response to an applied magnetic field, $\chi = M/H$.
- **Project Context**: Historical parameter in earlier EGDPP thrust equations; current RVG framework uses vacuum refractive index $K$ and dilaton enhancement Θ_dilaton(B) as primary quantities.
- **Mathematical/Technical Details**: Vacuum susceptibility $\chi_{\text{vac}}$ appears in $K = 1 + \chi_{\text{vac}}(B)$.
- **References**: Useful Equations; see [K (Vacuum Refractive Index)](#k-vacuum-refractive-index).

---

This glossary is designed to evolve with the project; contributions via pull requests are encouraged (see `CONTRIBUTING.md`). For API-specific terms, consult Sphinx docs in `/docs/api`. 

**Total entries**: 70+; a comprehensive reference for RVG-based QED-EMF propulsion development.
