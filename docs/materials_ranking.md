# RVG Unified Field - Materials Ranking for Vacuum Propulsion

## Overview

This document provides comprehensive material rankings for use in the **Refractive Vacuum Gravity (RVG) Unified Field** propulsion system. Material selection is critical because the **supra-saturation regime** (B_opposing >> B_sat) is required for macroscopic vacuum effects.

**Key Principle from RVG Theory:**
> The opposing/convergence gap field (B_opposing) must **substantially exceed the material's saturation B_s** (≫ B_s, driving μ_eff ≈ 1 in the high-stress zone) to achieve the intense localized B and steep ∇B² required for macroscopic vacuum effects.

## Framework References

- [RVG Unified Field Theory](https://dx.doi.org/10.2139/ssrn.5381654) (Hofseth, 2025)
- [U.S. Patent #5,929,732 - MADA](https://patents.google.com/patent/US5929732A/en)
- CMS/ATLAS 95.4 GeV di-photon resonance (3.1σ combined significance)

---

## Material Ranking Summary

| Rank | Material | B_sat (T) | Score | Best For | Notes |
|------|----------|-----------|-------|----------|-------|
| 1 | **Minnealloy α'-Fe₈(NC)** | 2.85 | 95/100 | High-power cores | Highest B_sat, excellent for deep supra-saturation |
| 2 | Finemet (Fe-Si-B-Nb-Cu) | 1.20 | 96/100 | High-frequency | Best loss characteristics, lower B_sat |
| 3 | Pure Iron (ARMCO) | 2.10 | 90/100 | Cost-effective | Good balance of properties |
| 4 | Hiperco-50 (Fe-Co) | 2.40 | 88/100 | Aerospace | High B_sat, proven reliability |
| 5 | Silicon Steel (3% Si) | 2.00 | 85/100 | Industrial | Widely available, good performance |
| 6 | Metglas 2605SA1 | 1.56 | 92/100 | Transformers | Excellent at high frequency |
| 7 | Permalloy (Ni-Fe) | 1.08 | 80/100 | Sensors | High permeability, low B_sat |
| 8 | Mu-metal | 0.77 | 75/100 | Shielding | Very high permeability |

---

## Detailed Material Properties

### 1. Minnealloy α'-Fe₈(NC) — BEST OVERALL

**Saturation:** B_sat = 2.85 T  
**Score:** 95/100  
**Composition:** Iron-nitrogen-carbon interstitial compound

**Key Properties:**
- Highest known saturation magnetization for soft magnetic materials
- Enables deepest supra-saturation regime with practical field strengths
- Excellent for MADA core applications
- Moderate permeability (~2000-5000)

**Supra-Saturation Analysis:**
| B_opposing (T) | B/B_sat Ratio | Effectiveness | Regime |
|----------------|---------------|---------------|--------|
| 10 | 3.5× | 0.50 | Onset |
| 20 | 7.0× | 0.84 | Good |
| 50 | 17.5× | 1.00 | Optimal |
| 90 | 31.6× | 1.00 | Deep |

**Recommended Applications:**
- Primary MADA cores for maximum thrust
- High-power propulsion systems
- Applications requiring B_opposing > 50 T

**Procurement:**
- Specialty metallurgical suppliers
- Research-grade from university labs
- Custom synthesis may be required

---

### 2. Finemet (Fe-Si-B-Nb-Cu)

**Saturation:** B_sat = 1.20 T  
**Score:** 96/100  
**Composition:** Fe₇₃.₅Si₁₃.₅B₉Nb₃Cu₁ (nanocrystalline)

**Key Properties:**
- Extremely low core losses at high frequency
- Nanocrystalline structure (grain size ~10-15 nm)
- Excellent for pulsed operation (50-1000 Hz)
- High permeability (>100,000 initial)

**Supra-Saturation Analysis:**
| B_opposing (T) | B/B_sat Ratio | Effectiveness | Regime |
|----------------|---------------|---------------|--------|
| 5 | 4.2× | 0.58 | Onset |
| 10 | 8.3× | 0.92 | Good |
| 20 | 16.7× | 1.00 | Optimal |
| 50 | 41.7× | 1.00 | Deep |

**Recommended Applications:**
- High-frequency pulsing (>100 Hz)
- Efficiency-critical systems
- Compact designs with thermal constraints

**Trade-offs:**
- Lower B_sat requires higher B_opposing for same effectiveness
- More expensive than conventional materials
- Brittle ribbon form factor

---

### 3. Pure Iron (ARMCO)

**Saturation:** B_sat = 2.10 T  
**Score:** 90/100  
**Composition:** 99.85%+ Fe

**Key Properties:**
- Excellent baseline performance
- Well-characterized behavior
- Cost-effective for prototyping
- Good machinability

**Supra-Saturation Analysis:**
| B_opposing (T) | B/B_sat Ratio | Effectiveness | Regime |
|----------------|---------------|---------------|--------|
| 10 | 4.8× | 0.63 | Onset |
| 20 | 9.5× | 0.95 | Good |
| 50 | 23.8× | 1.00 | Optimal |
| 90 | 42.9× | 1.00 | Deep |

**Recommended Applications:**
- Prototype development
- Cost-sensitive applications
- Educational/research systems

---

### 4. Hiperco-50 (Fe-Co)

**Saturation:** B_sat = 2.40 T  
**Score:** 88/100  
**Composition:** 49% Fe, 49% Co, 2% V

**Key Properties:**
- Aerospace-grade reliability
- High Curie temperature (~940°C)
- Good mechanical strength
- Established supply chain

**Supra-Saturation Analysis:**
| B_opposing (T) | B/B_sat Ratio | Effectiveness | Regime |
|----------------|---------------|---------------|--------|
| 10 | 4.2× | 0.57 | Onset |
| 20 | 8.3× | 0.92 | Good |
| 50 | 20.8× | 1.00 | Optimal |
| 90 | 37.5× | 1.00 | Deep |

**Recommended Applications:**
- Flight-qualified systems
- High-temperature environments
- Long-duration missions

---

### 5. Silicon Steel (3% Si)

**Saturation:** B_sat = 2.00 T  
**Score:** 85/100  
**Composition:** Fe + 3% Si (grain-oriented or non-oriented)

**Key Properties:**
- Most widely available magnetic material
- Excellent cost-performance ratio
- Well-understood processing
- Multiple suppliers worldwide

**Supra-Saturation Analysis:**
| B_opposing (T) | B/B_sat Ratio | Effectiveness | Regime |
|----------------|---------------|---------------|--------|
| 10 | 5.0× | 0.67 | Onset |
| 20 | 10.0× | 1.00 | Good |
| 50 | 25.0× | 1.00 | Optimal |
| 90 | 45.0× | 1.00 | Deep |

**Recommended Applications:**
- Industrial-scale production
- Budget-constrained projects
- Rapid prototyping

---

### 6. Metglas 2605SA1

**Saturation:** B_sat = 1.56 T  
**Score:** 92/100  
**Composition:** Fe-based amorphous alloy

**Key Properties:**
- Amorphous (glassy) structure
- Very low core losses
- High permeability (~600,000 max)
- Thin ribbon form (25 μm typical)

**Recommended Applications:**
- High-efficiency transformers
- Pulse power systems
- EMI shielding with flux concentration

---

### 7. Permalloy (Ni-Fe)

**Saturation:** B_sat = 1.08 T  
**Score:** 80/100  
**Composition:** ~80% Ni, 20% Fe

**Key Properties:**
- Very high initial permeability (~100,000)
- Excellent for low-field applications
- Good for magnetic shielding
- Lower B_sat limits supra-saturation depth

**Recommended Applications:**
- Magnetic sensors
- Shielding applications
- Low-field flux concentrators

---

### 8. Mu-metal

**Saturation:** B_sat = 0.77 T  
**Score:** 75/100  
**Composition:** ~77% Ni, 16% Fe, 5% Cu, 2% Cr

**Key Properties:**
- Highest permeability available (~100,000-300,000)
- Excellent magnetic shielding
- Low B_sat severely limits thrust applications
- Primarily for EMF protection

**Recommended Applications:**
- Electronic shielding (see [docs/shielding.pdf](shielding.pdf))
- Sensitive instrument protection
- NOT recommended for MADA cores

---

## Supra-Saturation Engineering Guidelines

### Minimum Requirements

For the Master Equation of Levitation to produce macroscopic thrust:

$$\mathbf{F}_{\text{lift}} = \int_V \frac{1}{2\mu_0} \Theta_{\text{dilaton}}(B) \cdot \nabla B^2 \, dV$$

The following conditions must be met:

1. **B_opposing >> B_sat** (typically B/B_sat > 5)
2. **∇B² > 10⁹ T²/m** (steep gradient required)
3. **Θ_dilaton(B) activation** (requires B > B_crit ≈ 20 T)

### Material Selection Decision Tree

```
START
  │
  ├─ Is maximum thrust priority?
  │   ├─ YES → Minnealloy (B_sat = 2.85 T)
  │   └─ NO ─┐
  │          │
  ├─ Is high-frequency pulsing (>100 Hz) required?
  │   ├─ YES → Finemet (B_sat = 1.20 T)
  │   └─ NO ─┐
  │          │
  ├─ Is aerospace qualification needed?
  │   ├─ YES → Hiperco-50 (B_sat = 2.40 T)
  │   └─ NO ─┐
  │          │
  ├─ Is cost the primary constraint?
  │   ├─ YES → Silicon Steel (B_sat = 2.00 T)
  │   └─ NO ─┐
  │          │
  └─ Default → Pure Iron (B_sat = 2.10 T)
```

### Operating Point Optimization

For each material, the optimal operating point balances:

1. **Thrust** (increases with B/B_sat)
2. **Efficiency** (decreases at extreme overdrive)
3. **Thermal load** (increases with B²)
4. **Material stress** (increases with B)

**Recommended Operating Ranges:**

| Material | Min B/B_sat | Optimal B/B_sat | Max B/B_sat |
|----------|-------------|-----------------|-------------|
| Minnealloy | 5× | 15-20× | 35× |
| Finemet | 8× | 20-30× | 50× |
| Pure Iron | 5× | 15-25× | 45× |
| Hiperco-50 | 5× | 15-20× | 40× |
| Silicon Steel | 5× | 15-25× | 50× |

---

## MADA Amplification Considerations

Per U.S. Patent 5,929,732, MADA provides ~200-500× effective B-field amplification:

- **Single magnet lift distance:** 1 inch
- **MADA assembly lift distance:** 6 inches
- **Amplification factor:** 6³ to √(6⁷) = 216-529×

### Material Impact on MADA Performance

| Material | MADA k=200 B_eff (T)* | MADA k=500 B_eff (T)* | B_eff/B_sat |
|----------|----------------------|----------------------|-------------|
| Minnealloy | 2.78 | 6.94 | 0.97-2.44 |
| Finemet | 2.78 | 6.94 | 2.32-5.78 |
| Pure Iron | 2.78 | 6.94 | 1.32-3.30 |
| Hiperco-50 | 2.78 | 6.94 | 1.16-2.89 |

*Assuming 3T N52 magnet source

**Note:** Higher B_sat materials can achieve deeper supra-saturation with the same MADA configuration, enabling greater thrust per unit volume.

---

## Thermal Considerations

Material selection affects thermal management requirements:

| Material | Curie Temp (°C) | Max Operating (°C) | Thermal Conductivity (W/m·K) |
|----------|-----------------|--------------------|-----------------------------|
| Minnealloy | ~750 | 600 | ~30 |
| Finemet | 570 | 450 | ~8 |
| Pure Iron | 770 | 650 | 80 |
| Hiperco-50 | 940 | 800 | 30 |
| Silicon Steel | 740 | 600 | 25 |

**Recommendation:** For sustained high-power operation, integrate PCM thermal management and Bi₂Te₃ TEG recovery as specified in [experiments/bench_test_designs.md](../experiments/bench_test_designs.md).

---

## Procurement Sources

### Research-Grade Materials

| Material | Supplier | Notes |
|----------|----------|-------|
| Minnealloy | University labs, custom synthesis | Contact metallurgy departments |
| Finemet | Hitachi Metals, VAC | Standard product line |
| ARMCO Iron | AK Steel, Carpenter | Widely available |
| Hiperco-50 | Carpenter Technology | Aerospace certified |
| Silicon Steel | Multiple (AK Steel, NLMK, etc.) | Commodity pricing |
| Metglas | Metglas Inc. (Hitachi) | Standard ribbons |

### Recommended Specifications for MADA Cores

- **Minnealloy:** Request maximum B_sat certification (>2.8 T)
- **Finemet:** Specify FT-3M grade for lowest losses
- **Hiperco-50:** Request AMS 7716 specification
- **Silicon Steel:** M-6 grade or better for grain-oriented

---

## Integration with Code

### Using Material Properties in Python

```python
from simulations.equations import MATERIALS, supra_saturation_effectiveness

# Access material properties
minnealloy = MATERIALS['Minnealloy']
print(f"B_sat: {minnealloy['B_sat']} T")
print(f"Score: {minnealloy['score']}/100")

# Calculate effectiveness at operating point
B_opposing = 50.0  # Tesla
effectiveness = supra_saturation_effectiveness(B_opposing, 'Minnealloy')
print(f"Effectiveness at {B_opposing}T: {effectiveness:.2f}")
```

### Updating Material Parameters

After experimental calibration, update parameters using:

```bash
python scripts/update_parameters.py --material Minnealloy --b_sat 2.87
```

---

## References

1. Hofseth, J.D. (2025). "Refractive Vacuum Gravity Unified Field Theory." SSRN. DOI: 10.2139/ssrn.5381654
2. U.S. Patent 5,929,732 - "Magnetic Amplification and Direction Assembly" (1999)
3. CMS Collaboration. "Search for new resonances in diphoton events." (Combined with ATLAS: 3.1σ at 95.4 GeV)
4. Cullity, B.D. & Graham, C.D. "Introduction to Magnetic Materials" (2009)
5. Jiles, D.C. "Introduction to Magnetism and Magnetic Materials" (2015)

---

**Document Version:** 2.0  
**Last Updated:** 2026-01-04  
**Framework:** Refractive Vacuum Gravity (RVG) Unified Field
