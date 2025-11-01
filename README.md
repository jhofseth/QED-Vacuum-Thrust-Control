# QED-Vacuum-Thrust-Control

Open-source control system for QED vacuum polarization-based EMF propulsion in combat drones.  Optimizes magnetic circuits with materials like Minnealloy & Hiperco-50 for high-thrust (e.g., Mach 26), stealthy ops in asymmetric warfare.  Features AI navigation, MADA pulsing, thermal management, and simulation tools for defense applications.

[Explore the docs »](docs/)

[Report Bug](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/issues) · [Request Feature](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/issues)

## Table of Contents

- [About The Project](#about-the-project)
  - [Built With](#built-with)
- [Theory Overview](#theory-overview)
- [Key Features](#key-features)
- [Materials Ranking](#materials-ranking)
- [Useful Equations](#useful-equations)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

## About The Project

This repository provides an open-source control system for advanced EMF propulsion systems based on Quantum Electrodynamics (QED) vacuum polarization.  Drawing from emerging theories like Emergent Gravity from Disrupted Photon Pairs (EGDPP), it enables simulation and control of magnetic amplification and direction assemblies (MADA) for EMF propulsion in spherical combat drones.  Optimized for asymmetric warfare, it supports high accelerations (>500g), stealth operations, and integration with materials for efficient magnetic circuits.

Key applications include defense scenarios requiring non-ballistic trajectories, hover capabilities, and precision strikes while evading radar and thermal detection.

<p align="right">(<a href="#top">back to top</a>)</p>

### Built With

- ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
- ![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white)
- ![TensorFlow](https://img.shields.io/badge/TensorFlow-%23FF6F00.svg?style=for-the-badge&logo=TensorFlow&logoColor=white)
- ![Matplotlib](https://img.shields.io/badge/Matplotlib-%23ffffff.svg?style=for-the-badge&logo=Matplotlib&logoColor=black)
- ![SciPy](https://img.shields.io/badge/SciPy-%230C55A5.svg?style=for-the-badge&logo=scipy&logoColor=%white)

<p align="right">(<a href="#top">back to top</a>)</p>

![Alt text](assets/IMG_0848.jpeg)

## Theory Overview

The system leverages QED vacuum polarization, where strong opposing magnetic fields (B_opposing >~20 T; depends upon mass, with some B_opposing >60-90+ T) create virtual electron-positron pairs, inducing diamagnetic repulsion for propulsion.  Based on Heisenberg-Euler-Schwinger (HES) effective action at 0.1-1 MHz frequencies (i.e., pulsed), it achieves thrust via F ∝ χ B² ∇(h²) A ρ.  Pulsing (for spherical EMF propulsion drones): 50 Hz default (20 ms cycles) for balance, dynamically scaling to 100 Hz (agility) or 1 kHz (bursts) with variable duty (20-80%) – boosting efficiency 20-50%, evading detection, and extending range.

Inspired by U.S. Patent #5,929,732 (MADA) and EGDPP model (Hofseth, 2025), which is a scalar-tensor theory (spin-0 emergent gravity) with asymptotic safety.  The EGDPP model predicts a 95 GeV spin-0 resonance and integrates nonlinear QED with functional RG flows.  A public experiment is needed to confirm the RG modifier equation for χ (i.e., or any modifier equation), as simulations require it for proper EMF propulsion functionality.  Options include the current spin-0 emergent version, the old spin-2 emergent version, or *alternatives derived from experimental data*; the system is neutral and adaptable.  I really don't care about my paper's hypothesis (i.e., EDGPP), because *EMF propulsion demonstrably occurs* and it 100% *requires* some modifier equation.  All I care about is truth; QED vacuum polarization-based EMF propulsion is 100% truth, and it doesn't depend upon EGDPP—only upon some modifier equation.

<p align="right">(<a href="#top">back to top</a>)</p>

## Key Features

- **AI Navigation**: MIMO networks for 6DOF control and real-time flux mapping
- **MADA Pulsing**: 50-100 Hz pulsing (up to 1 kHz bursts) for efficiency >95%
- **Thermal Management**: PCM channels and optional Bi₂Te₃ TEG for 10-40 kW dissipation
- **Simulation Tools**: Python scripts for RG flow, thrust calculations, and threat modeling
- **Material Optimization**: Holistic ranking for scalability and cost

<p align="right">(<a href="#top">back to top</a>)</p>

## Materials Ranking

Holistic ranking of magnetic materials for propulsion circuits (as of October 20, 2025):

| Rank | Material | Score |
|------|----------|-------|
| 1 | Finemet Nanocrystalline Iron | 96/100 |
| 2 | Metglas Amorphous Iron | 95/100 |
| 3 | **Minnealloy (α′-Fe₈(NC))** | **95/100** - **BEST OVERALL** |
| 4 | Minnealloy (α″-Fe₁₆(C,N)₂) | 92/100 |
| 5 | Pure Iron (ARMCO) | 90/100 |

*See full table in [docs/materials_ranking.md](docs/materials_ranking.md)*

Prioritizes cobalt-free options for low-cost scalability.

<p align="right">(<a href="#top">back to top</a>)</p>

## Useful Equations

Useful Equations for Propulsion Calculations: Tactical Toolkit derived from *Emergent Gravity from Disrupted Photon Pairs: An Asymptotically Safe Quantum Model of Gravitation, Electromagnetism, and the Standard Model* (i.e., EGDPP Theory).  Grouped for quick reference, with derivations and applications.  These empower simulations – e.g., Python for threat modeling.

### Magnetic Fields

**Surface Field (base for opposition):**

$$B \approx \frac{B_r}{2} \left( \frac{L}{\sqrt{R^2 + L^2}} + \frac{L + d}{\sqrt{R^2 + (L + d)^2}} \right)$$

**Opposing Field (core disruption input):**

$$B_{\text{opposing}} = \frac{\mu_0 m_1 m_2}{2\pi d^2} \cdot k$$

**Pulsed Enhancement (for bursts):**

$$\Delta B = \mu_0 n I$$

### Disruption and Gradient

**Lagrangian:**

$$\mathcal{L}_{\text{disrupt}} = -\frac{1}{2} \chi B^2 h_{\mu\nu} h^{\mu\nu}$$

**RG for χ** (EGDPP spin-0 emergent, present version; note: alternatives exist, e.g., spin-2: β_χ = (4 + η_χ) χ + c g χ, *or data-derived; experiment needed*):

$$\beta_\chi = -4\chi + \frac{g}{2\pi} \frac{\chi}{1 - 2\lambda}$$

*[RG for χ updated to reflect EGDPP switch to spin-0 in QED (updated/expanded article forthcoming).]*

**Source Term:**

$$\delta T_{\mu\nu} \approx \chi B^2 h_{\mu\nu}$$

### Force/Thrust

**Force Vector:**

$$\mathbf{F} = \chi B^2 \nabla (h^2) \cdot A \cdot \rho$$

**Total Thrust:**

$$T = N \cdot F \cdot \eta \cdot \cos\theta$$

**Acceleration:**

$$a = T / m$$

### Power/Efficiency

**Consumption:**

$$P = I^2 R + P_{\text{eddy}}$$

**Efficiency:**

$$\eta = \left( \frac{T \cdot v}{P} \right) \times 100\%$$

**Range:**

$$R = v \cdot \left( \frac{E}{P} \right)$$

*Implementations in `simulations/equations.py`.*

<p align="right">(<a href="#top">back to top</a>)</p>

## Getting Started

### Prerequisites

- Python 3.12+
- pip

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/jhofseth/QED-Vacuum-Thrust-Control.git
   ```

2. Navigate to the directory
   ```sh
   cd QED-Vacuum-Thrust-Control
   ```

3. Install dependencies
   ```sh
   pip install -r requirements.txt
   ```

<p align="right">(<a href="#top">back to top</a>)</p>

## Usage

Run simulations:

```bash
python simulations/thrust_model.py --b_opposing 50 --frequency 100
```

For AI navigation demo:

```bash
python ai/navigation.py
```

See `examples/` for more.

<p align="right">(<a href="#top">back to top</a>)</p>

## Roadmap

- [ ] Add full drone CAD models
- [ ] Integrate ML for gradient optimization
- [ ] Support for hardware interfacing
- [ ] See [open issues](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/issues)

<p align="right">(<a href="#top">back to top</a>)</p>

## Contributing

Contributions welcome!  Fork, create a branch, commit, push, and open a PR.

<p align="right">(<a href="#top">back to top</a>)</p>

## License

Distributed under the MIT License.  See `LICENSE` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>

## Contact

Project Link: [https://github.com/jhofseth/QED-Vacuum-Thrust-Control](https://github.com/jhofseth/QED-Vacuum-Thrust-Control)

<p align="right">(<a href="#top">back to top</a>)</p>

## Acknowledgments

- EGDPP Theory (Jesse D. Hofseth) https://dx.doi.org/10.2139/ssrn.5381654
- U.S. Patent #5,929,732 (Lockheed Martin Corporation) https://patents.google.com/patent/US5929732A/en
- [Best-README-Template](https://github.com/othneildrew/Best-README-Template)

<p align="right">(<a href="#top">back to top</a>)</p>
