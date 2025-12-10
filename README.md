# QED-Vacuum-Thrust-Control

Open-source control system for QED vacuum polarization-based EMF propulsion in combat drones.  Optimizes magnetic circuits with materials like Minnealloy & Hiperco-50 for high-thrust (e.g., Mach 26), stealthy ops in asymmetric warfare.  Features AI navigation, MADA pulsing, thermal management, and simulation tools for defense applications.


![Alt text](assets/IMG_1846.jpeg)
[Very Brief Sample QED Vacuum Thrust Control Video - Click this text.](https://drive.google.com/file/d/1_4zi3hHS7li0avwlS-Sk1KF_Y8pp4-vq/view?usp=drivesdk)

**[Please note: One of the most important tasks is properly shielding your QED vacuum polarization-based EMF propulsion AI control electronics.  I had two high-voltage laboratory power supplies that had to be thrown away.  They weren’t damaged due to the aforementioned AFAIK, but that will be many times your difficulty without proper shielding.  *See  [docs/shielding.pdf](docs/shielding.pdf)*]**

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

Inspired by U.S. Patent #5,929,732 (MADA) and EGDPP model (Hofseth, 2025), which is a scalar-tensor theory (spin-0 emergent gravity) with asymptotic safety.  The EGDPP model predicts a 95 GeV spin-0 resonance and integrates nonlinear QED with functional RG flows.  A public experiment is needed to confirm the RG modifier equation for χ (i.e., or any modifier equation), as simulations require it for proper EMF propulsion functionality.  Options include the current spin-0 emergent version, the old spin-2 emergent version, or an alternative modifier equation derived from experimental data; the system is neutral and adaptable.  I really don't care about my paper's hypothesis (i.e., EDGPP), because EMF propulsion *demonstrably* occurs and it 100% *requires* some modifier equation.  All I care about is truth, and QED vacuum polarization-based EMF propulsion is 100% truth that doesn't depend upon EGDPP—only upon a modifier equation.

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

*See full table in [docs/materials_ranking.pdf](docs/materials_ranking.pdf)*

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

**RG for χ** (EGDPP spin-0 emergent, present version; note: alternatives exist, e.g., spin-2 emergent: β_χ = (4 + η_χ) χ + c g χ, *or data-derived; experiment needed*):

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

## Magnetic Amplification and Direction Apparatus (MADA)

![Alt text](assets/IMG_0220.jpeg)
![Alt text](assets/IMG_2317.jpeg)

Good news: Lockheed Martin's patented MADA makes EMF propulsion **~200-500x easier!**

Based on the physical laws governing magnetic fields and the specific text from Lockheed Martin Corporation's [U.S. Patent 5,929,732](https://patents.google.com/patent/US5929732A/en) regarding an "Apparatus and Method for Amplifying a Magnetic Beam", here is the breakdown of the amplification implied.

To achieve the effect described—lifting an object at 6 inches that a standard magnet can only lift at 1 inch—the magnetic assembly would effectively require an amplification of the source **B value** (magnetic field strength) of approximately **216 to 529 times**, depending on the magnetic saturation of the object.

### Why the Amplification is So High

To understand why the number is so high, we have to look at how rapidly magnetic force drops off over distance. It is not linear.

#### The Inverse Cube Law (Field Strength)

The magnetic field (B) of a standard dipole magnet drops off roughly with the cube of the distance (1/r³).

- If you move from 1 inch to 6 inches (6x distance), the field strength drops by a factor of 6³ (6 cubed)
- **6³ = 216**
- **Result:** To deliver the same field strength at 6 inches as you did at 1 inch, your source magnet would need to be **~216 times stronger**

#### The Force Law (Lifting Power)

Lifting a ferric object (like a paperclip or steel weight) depends on both the field strength and the field gradient (how fast the field changes). For a small object, the force (F) typically drops off at the 7th power of the distance (1/r⁷).

- To get the same force at 6x the distance: Amplification = √(6⁷) ≈ **529**
- **Result:** To lift the same weight at 6 inches, the effective magnetic power at the source must be **~529 times greater**

### Implications

In standard physics, achieving a 6x increase in lifting distance is extraordinary. It means the device is projecting magnetic energy with the efficiency of a laser compared to a lightbulb.

| Metric | Value |
|--------|-------|
| Distance Increase | 1 inch → 6 inches |
| Field Decay (1/r³) | 1/216 |
| Force Decay (1/r⁷) | 1/279,936 |
| **Implied Amplification** | **~200x - 500x** |

It is not merely "6 times" stronger. It is demonstrating an **effective B-value amplification of over 200 times** compared to the single magnet, because it is overcoming the massive drop-off in force that usually occurs over that extra 5 inches.

### Practical Application

This means that a MADA can take 5 stacks of 6 cheap N52 magnets with spacers removed ($25 total from Amazon; each stack of 6 is ~3T) to **~600+T B_opposing**. Put that inside a magnetic circuit in opposition to other identical adjacent MADA, and the B_opposing would be massive. That's before even factoring in additional B_opposing from the partially hybridized MADA pole positions.

### Implementation in Code

`simulations/equations.py` was updated to reflect:
```python
def opposing_field(m1: float, m2: float, d: float, k: float = 200.0) -> float:
    """
    Calculate opposing magnetic field with MADA amplification.
    
    Args:
        m1: Magnetic moment of first magnet
        m2: Magnetic moment of second magnet
        d: Distance between magnets
        k: Scaling factor for MADA amplification (default 200.0 for ~200x vs. single magnet)
    
    Note:
        k may need to be set up to 529 depending on specific configuration
    """
    # Implementation details...
```

**Key parameter:**
- `k`: Scaling factor for MADA amplification (default `200.0` for ~200x vs. single magnet; may need to be set up to `529`)

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

**Run simulations:**

```bash
python simulations/thrust_model.py --b_opposing 50 --frequency 100
```

**AI navigation demo:**

```bash
python ai/navigation.py
```

**Advanced options:**

```bash
# Custom parameters
python simulations/thrust_model.py --b_opposing 75 --frequency 200 --mass 15000 --n_units 32

# Verbose output
python simulations/thrust_model.py --verbose
```

See `examples/` for more usage patterns and tutorials.

<p align="right">(<a href="#top">back to top</a>)</p>

## API Documentation

Comprehensive API documentation generated via Sphinx: [View API Docs](docs/api/)

**Key Modules:**
- `simulations/equations.py` - Core physics equations and calculations
- `ai/navigation.py` - MIMO neural network for 6DOF control
- `hardware/interfaces.py` - Hardware interfacing (coming soon)

Generate docs locally:
```bash
cd docs/
make html
```

<p align="right">(<a href="#top">back to top</a>)</p>

## Tutorials

- **[Hardware Setup Guide](docs/tutorials/hardware_setup.md)**: Transitioning from simulations to prototypes
- **[Flight Control Tutorial](docs/tutorials/flight_control.md)**: Real-time systems, PID/MPC, and safety protocols
- **Interactive Notebooks:**
  - [Sensor Fusion Demo](examples/sensor_fusion.ipynb)
  - [ML Optimization](examples/ml_optimization.ipynb)
  - [Swarm Simulation](examples/swarm_simulation.ipynb)
- **Video Tutorials**: Coming soon ([YouTube Playlist](https://youtube.com/playlist?list=PLACEHOLDER))

<p align="right">(<a href="#top">back to top</a>)</p>

## Glossary

- **Heisenberg-Euler-Schwinger (HES) Action**: Effective field theory describing nonlinear QED effects in strong electromagnetic fields
- **MADA**: Magnetic Amplification and Direction Assembly – Patent-inspired setup for magnetic beam focusing
- **QED Vacuum Polarization**: Quantum effect where virtual particle-antiparticle pairs modify electromagnetic field properties
- **RG Flow**: Renormalization Group – Describes how physical parameters change with energy scale
- **Spin-0 Emergent Gravity**: Scalar field theory where gravitational effects arise from QED disruptions
- **Spin-2 Emergent Gravity**: The old version of EGDPP; the relevant modifier equation is also provided for testing, but neither old nor new modifiers are necessary if an experimentally derived modifier is desired/provided
- **EGDPP**: Emergent Gravity from Disrupted Photon Pairs – Theoretical framework for gravity, but not necessary for QED vacuum polarization-based EMF propulsion (i.e., only a *modifier* equation is necessary)

Full glossary available in [docs/glossary.md](docs/glossary.md).

<p align="right">(<a href="#top">back to top</a>)</p>

## Roadmap

- [x] Add `experiments/` directory for bench-top test protocols
- [x] Add `cad/` for drone models and 3D visualizations
- [x] Add `testing/` for data logging and test protocols
- [ ] Add full drone CAD models (STEP/STL formats)
- [ ] Integrate ML for gradient optimization
- [x] Support for hardware interfacing (progress: `interfaces.py` but schematics not yet added)
- [ ] Develop firmware for embedded controllers
- [ ] Create simulation-to-hardware pipeline

See [open issues](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/issues) for detailed status and discussions.

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
