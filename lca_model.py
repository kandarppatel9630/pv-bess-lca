"""
 LIFE CYCLE ASSESSMENT & CARBON PAYBACK ANALYSIS - 
 Industrial Rooftop PV + BESS System — Germany

 QUESTION : Does adding a battery (BESS) improve or worsen the environmental
            profile of an industrial solar system?

BOUNDARY : Cradle-to-gate (manufacturing only; no operation or end-of-life)
Functional Unit : 1 MWh electricity delivered over 25-year system lifetime
"""

import numpy as np                       
import matplotlib.pyplot as plt          
import matplotlib.gridspec as gridspec   

# =============================================================================
# Phase 1 - Goal & Scope
# Define the system, its boundaries, and key parameters.
# =============================================================================

# Study Description
SYSTEM_NAME     = "Industrial Rooftop PV + BESS (Germany)"
SYSTEM_BOUNDARY = "Cradle-to-gate (manufacturing + installation; excl. EOL)"
FUNCTIONAL_UNIT = "1 MWh electricity delivered over 25-year lifetime"

# PV System Parameters
PV_CAPACITY_MWP  = 1.0    # Installed peak capacity [MWp]
                          # Represents a medium-sized industrial rooftop system.
PV_LIFETIME_YR   = 25     # Operational lifetime
PV_YIELD_KWH_KWP = 950    # Annual yield [kWh/kWp/year]
PV_DEGRADATION   = 0.005  # Annual power degradation rate [fraction/year]
                          # i.e. panels lose 0.5% output per year due to aging.

# Battery Energy Storage Parameters
BESS_CAPACITY_MWH = 2.0   # Installed storage capacity [MWh]
BESS_LIFETIME_YR  = 12    # Operational life time [years]
BESS_EFFICIENCY   = 0.93  # Round-Trip Efficiency
BESS_DOD          = 0.90  # Depth of Discharge [-]
                          # Only 90% of capacity used per cycle to
                          # protect battery lifespan. Standard operating practice.
BESS_STORAGE_FRAC = 0.40  # Fraction of annual PV generation routed through BESS
                          # ASSUMPTION: 40% of solar output is stored and later
                          # discharged. Remaining 60% is consumed directly.

# Grid carbon intensity scenarios [kg CO2-eq/kWh]

# They represent the CO2 emitted per kWh drawn from the German national grid.
# As the grid decarbonizes, each kWh of solar displaced saves less CO2,
# which paradoxically extends the carbon payback period.
#
# Unit: kg CO2-eq per kWh of grid electricity consumed
#
GRID_SCENARIOS = {
    "2026 (today)"  : 0.363,     # as per 2024 data
    "2030 (target)" : 0.200,
    "2035 (projection)" : 0.100
}

# =============================================================================
# Phase 2 - Life Cycle Inventory (LCI)
# Emission factors per unit of manufactured component.
# =============================================================================

# Three Impact categories being assessed
CATEGORIES = ["GWP [kg CO2-eq]", "Primary Energy [MJ]", "Water Use [m3]"]

# PV module manufacturing inventory
PV_INVENTORY = {
    "GWP [kg CO2-eq]"   : 400,       
    "Primary Energy [MJ]": 6_500,            
    "Water Use [m3]"     : 15,               
}

# Battery manufacturing inventory
BESS_INVENTORY = {
    "GWP [kg CO2-eq]"   : 180,      
    "Primary Energy [MJ]": 2_500,           
    "Water Use [m3]"     : 4,                
}

# Balance of System (BOS) inventory
BOS_INVENTORY = {
    "GWP [kg CO2-eq]"   : 80,        
    "Primary Energy [MJ]": 1_200,            
    "Water Use [m3]"     : 2,               
}

def compute_lci(include_bess: bool) -> dict:
    """
Phase 2 — Compute the Life Cycle Inventory.

Aggregates all manufacturing impacts for the full system.
Returns absolute total impacts for each impact category.

Parameters
----------
include_bess : bool
    True  → PV + BESS system (Configuration B)
    False → PV only system (Configuration A)

Notes
-----
Battery replacements:
    Battery lifetime = 12 years. PV lifetime = 25 years.
    ceil(25 / 12) = 3 battery installations over system lifetime.
    (Year 0: initial installation, Year 12: 1st replacement,
     Year 24: 2nd replacement — this last one has only 1 year of use,
     which is a conservative assumption that slightly overstates impact.)
"""
    # Convert MWp to kWp (emission factors are defined per kWp)
    pv_kwp = PV_CAPACITY_MWP * 1_000   
 
    lci = {}
 
    for cat in CATEGORIES:
 
        # PV modules — scale emission factor by system size
        pv_total  = PV_INVENTORY[cat]  * pv_kwp
        # Example (GWP): 400 kg CO2/kWp × 1000 kWp = 400,000 kg CO2
 
        # Balance of system — same scaling
        bos_total = BOS_INVENTORY[cat] * pv_kwp
        # Example (GWP):  80 kg CO2/kWp × 1000 kWp =  80,000 kg CO2
 
        if include_bess:
            # Number of battery installations over 25-year lifetime
            # ceil(25/12) = ceil(2.08) = 3
            replacements = int(np.ceil(PV_LIFETIME_YR / BESS_LIFETIME_YR))
 
            # Battery capacity in kWh (2 MWh = 2000 kWh)
            bess_kwh = BESS_CAPACITY_MWH * 1_000
 
            # Total battery impact = impact per kWh × capacity × number of installations
            bess_total = BESS_INVENTORY[cat] * bess_kwh * replacements
            # Example (GWP): 180 × 2000 × 3 = 1,080,000 kg CO2
        else:
            bess_total = 0.0
 
        # Sum all components
        lci[cat] = pv_total + bos_total + bess_total
 
    return lci

# =============================================================================
# Phase 3 - Life Cycle Impact Assessment (LCIA)
# =============================================================================
# Convert absolute LCI results into impact scores per functional unit. 
# This is called "characterization" 

# ║  Characterization step:
# ║    impact score = total_LCI_impact / total_MWh_delivered
# ║
# ║  The denominator (MWh delivered) is calculated accounting for:
# ║    - Panel degradation over 25 years (0.5%/year)
# ║    - Round-trip efficiency losses when electricity passes through BESS

def compute_electricity_delivered(include_bess: bool) -> float:
    """
    Phase 3: Calculate total MWh delivered over 25-year lifetime.
 
    This is the denominator of the functional unit normalization.
 
    The calculation accounts for:
      1. Annual PV yield (950 kWh/kWp/yr for central Germany)
      2. Panel degradation: output reduces by 0.5% each year
      3. BESS round-trip losses: 7% of electricity lost when stored + discharged
 
    Parameters
    ----------
    include_bess : bool
        True  → 40% of generation passes through battery (losing 7%)
        False → all generation delivered directly (no losses)

    """
    
    total_mwh = 0.0
 
    for year in range(1, PV_LIFETIME_YR + 1):
 
        # Annual generation accounting for cumulative degradation
        # Formula: capacity × yield × (1 - degradation_rate)^year
        annual_pv_kwh = (
            PV_CAPACITY_MWP * 1_000   # kWp
            * PV_YIELD_KWH_KWP        # kWh/kWp/yr
            * (1 - PV_DEGRADATION) ** year
        )
 
        if include_bess:
            # Split generation into direct use and battery-routed use
            # Direct (60%): consumed immediately, no losses
            direct_kwh  = annual_pv_kwh * (1 - BESS_STORAGE_FRAC)
 
            # Via BESS (40%): passes through battery, loses 7%
            via_bess_kwh = annual_pv_kwh * BESS_STORAGE_FRAC * BESS_EFFICIENCY
 
            total_mwh += (direct_kwh + via_bess_kwh) / 1_000  # kWh → MWh
 
        else:
            # PV only: all generation delivered directly
            total_mwh += annual_pv_kwh / 1_000  # kWh → MWh
 
    return total_mwh

def compute_lcia(lci: dict, mwh_delivered: float) -> dict:
    """
    Phase 3 — Characterize LCI results per functional unit.
 
    impact per MWh = total manufacturing impact / total MWh delivered
    e.g. GWP: 480,000 kg CO2 / 22,266 MWh = 21.6 kg CO2 per MWh
    
    """
    return {
        cat: lci[cat] / mwh_delivered
        for cat in CATEGORIES
    }

# =============================================================================
# Phase 4 - Interpretation
# =============================================================================
# Carbon payback period + sensitivity analysis.

def compute_carbon_payback(lci: dict, grid_intensity: float) -> float:
    """
    Phase 4 — Calculate carbon payback period.
 
    The carbon payback period is the number of years until the cumulative
    CO2 avoided by displacing grid electricity equals the CO2 emitted
    during system manufacturing.
 
    Logic: every year the system displaces grid electricity, avoiding CO2.
    We count savings year-by-year until they equal the manufacturing debt.
 
    Key insight: cleaner grid → less CO2 saved per kWh → longer payback.
    Returns float('inf') if payback not reached within 25-year lifetime.
    
    """
 
    manufacturing_gwp_tonnes = lci["GWP [kg CO2-eq]"] / 1_000  # kg → tonnes CO2
 
    cumulative_avoided_tonnes = 0.0
 
    for year in range(1, PV_LIFETIME_YR + 1):
 
        # Annual generation with degradation 
        annual_pv_kwh = (
            PV_CAPACITY_MWP * 1_000
            * PV_YIELD_KWH_KWP
            * (1 - PV_DEGRADATION) ** year
        )
 
        # CO2 avoided this year = electricity generated × grid emission factor
        # (assumes 1:1 displacement of grid electricity — valid for industrial
        #  self-consumption where solar directly offsets grid imports)
        avoided_this_year = (annual_pv_kwh * grid_intensity) / 1_000  # → tonnes
 
        cumulative_avoided_tonnes += avoided_this_year
 
        # Check if manufacturing debt is paid off
        if cumulative_avoided_tonnes >= manufacturing_gwp_tonnes:
            return float(year)
 
    # Payback not reached within system lifetime — very long payback on clean grids
    return float("inf")

def compute_sensitivity(include_bess: bool, base_grid: float) -> dict:
    """
    Phase 4 — Sensitivity analysis on grid carbon intensity.
 
    Tests how the carbon payback period changes if the grid intensity
    varies between 50% and 150% of the base case value.
 
    """
 
    lci = compute_lci(include_bess)
 
    # Test 30 evenly spaced values from 50% to 150% of base grid intensity
    grid_values = np.linspace(base_grid * 0.50, base_grid * 1.50, 30)
 
    paybacks = [compute_carbon_payback(lci, g) for g in grid_values]
 
    return {
        "grid_values": grid_values,
        "paybacks"   : paybacks,
    }

# =============================================================================
# RESULTS — COMPUTATION & VISUALIZATION
# =============================================================================

def print_results_table(
    lci_pv, lci_bess,
    mwh_pv, mwh_bess,
    lcia_pv, lcia_bess,
    paybacks
):
    """Print a formatted summary of all LCA results to the console."""
 
    SEP = "=" * 68
 
    print(f"\n{SEP}")
    print(f"  {SYSTEM_NAME}")
    print(f"  Functional unit : {FUNCTIONAL_UNIT}")
    print(f"  System boundary : {SYSTEM_BOUNDARY}")
    print(SEP)
 
    # ── Phase 2 results: absolute LCI totals ──────────────────────────────────
    print("\n  PHASE 2 — Life Cycle Inventory (absolute totals)")
    print(f"  {'':32s} {'PV only':>14} {'PV + BESS':>14}")
    print("  " + "-" * 62)
    for cat in CATEGORIES:
        print(f"  {cat:<32} {lci_pv[cat]:>14,.0f} {lci_bess[cat]:>14,.0f}")
 
    # ── Phase 3 results: LCIA per functional unit ─────────────────────────────
    print(f"\n  PHASE 3 — LCIA per Functional Unit (per MWh delivered)")
    print(f"  {'':32s} {'PV only':>14} {'PV + BESS':>14}")
    print("  " + "-" * 62)
    print(f"  {'MWh delivered (25 yr)':<32} {mwh_pv:>14,.1f} {mwh_bess:>14,.1f}")
    for cat in CATEGORIES:
        print(f"  {cat:<32} {lcia_pv[cat]:>14.3f} {lcia_bess[cat]:>14.3f}")
 
    # ── Phase 4 results: carbon payback ───────────────────────────────────────
    print(f"\n  PHASE 4 — Carbon Payback Period [years]")
    print(f"  {'Grid Scenario':<28} {'PV only':>12} {'PV + BESS':>12}")
    print("  " + "-" * 54)
    for label, pb in paybacks.items():
        pv_val   = f"{pb['PV only']:.1f}" if pb['PV only'] != float("inf") else ">25"
        bess_val = f"{pb['PV + BESS']:.1f}" if pb['PV + BESS'] != float("inf") else ">25"
        print(f"  {label:<28} {pv_val:>12} {bess_val:>12}")
 
    print(f"\n  NOTE: Payback >25 yr means system lifetime expires before break-even.")
    print(f"  This is expected for clean grids — the solar system still reduces")
    print(f"  lifetime emissions, but does not fully offset manufacturing impact.\n")
 
 
def plot_results(lcia_pv, lcia_bess, paybacks, base_grid=0.363):
    """
    Generate all five result charts and save to output file.
 
    Charts produced:
      1. GWP per functional unit
      2. Primary energy per functional unit 
      3. Water use per functional unit
      4. Carbon payback by grid scenario 
      5. Sensitivity: payback vs. grid intensity
    """
 
    # ── Figure setup ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(17, 11))
    fig.suptitle(
        "LCA & Carbon Payback — Industrial PV + BESS System (Germany)\n"
        "Cradle-to-gate | Functional unit: 1 MWh delivered over 25-year lifetime",
        fontsize=13, fontweight="bold", y=0.99
    )
 
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.50, wspace=0.38)
 
    # Color palette
    COLOR_PV   = "#2E86AB"   # blue — PV only
    COLOR_BESS = "#E84855"   # red  — PV + BESS
    colors = {"PV only": COLOR_PV, "PV + BESS": COLOR_BESS}
    configs = ["PV only", "PV + BESS"]
 
    def style_ax(ax, title, ylabel):
        """Apply consistent styling to an axes object."""
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
 
    # ── Chart 1: GWP per functional unit ──────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    gwp_vals = [lcia_pv["GWP [kg CO2-eq]"], lcia_bess["GWP [kg CO2-eq]"]]
    bars1 = ax1.bar(
        configs, gwp_vals,
        color=[COLOR_PV, COLOR_BESS],
        width=0.5, edgecolor="white", linewidth=1.2
    )
    ax1.bar_label(bars1, fmt="%.1f", padding=4, fontsize=9, fontweight="bold")
    ax1.set_ylim(0, max(gwp_vals) * 1.30)
    style_ax(ax1, "GWP per Functional Unit", "kg CO₂-eq / MWh delivered")
    ax1.text(
        0.5, -0.18,
        "Battery manufacturing triples\nthe GWP per MWh",
        transform=ax1.transAxes, ha="center", fontsize=8, color="#666"
    )
 
    # ── Chart 2: Primary energy per functional unit ────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    pe_vals = [lcia_pv["Primary Energy [MJ]"], lcia_bess["Primary Energy [MJ]"]]
    bars2 = ax2.bar(
        configs, pe_vals,
        color=[COLOR_PV, COLOR_BESS],
        width=0.5, edgecolor="white", linewidth=1.2
    )
    ax2.bar_label(bars2, fmt="%.0f", padding=4, fontsize=9, fontweight="bold")
    ax2.set_ylim(0, max(pe_vals) * 1.30)
    style_ax(ax2, "Primary Energy per Functional Unit", "MJ / MWh delivered")
 
    # ── Chart 3: Water use per functional unit ─────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    w_vals = [lcia_pv["Water Use [m3]"], lcia_bess["Water Use [m3]"]]
    bars3 = ax3.bar(
        configs, w_vals,
        color=[COLOR_PV, COLOR_BESS],
        width=0.5, edgecolor="white", linewidth=1.2
    )
    ax3.bar_label(bars3, fmt="%.3f", padding=4, fontsize=9, fontweight="bold")
    ax3.set_ylim(0, max(w_vals) * 1.30)
    style_ax(ax3, "Water Use per Functional Unit", "m³ / MWh delivered")
 
    # ── Chart 4: Carbon payback by grid scenario ───────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0:2])
    scenario_labels = list(paybacks.keys())
    x = np.arange(len(scenario_labels))
    bar_width = 0.32
 
    for i, cfg in enumerate(configs):
        vals = []
        for s in scenario_labels:
            v = paybacks[s][cfg]
            vals.append(min(v, 25.5))   # cap at 25.5 for display (">25" cases)
        rects = ax4.bar(
            x + i * bar_width - bar_width / 2,
            vals, bar_width,
            label=cfg,
            color=[COLOR_PV, COLOR_BESS][i],
            edgecolor="white", linewidth=1.2
        )
        # Custom labels — show ">25" for payback beyond lifetime
        for rect, s in zip(rects, scenario_labels):
            raw = paybacks[s][cfg]
            label = f">25 yr" if raw == float("inf") else f"{raw:.1f} yr"
            ax4.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height() + 0.3,
                label, ha="center", va="bottom", fontsize=8, fontweight="bold"
            )
 
    # System lifetime reference line
    ax4.axhline(
        PV_LIFETIME_YR, color="#888", linestyle="--",
        linewidth=1.2, label=f"System lifetime ({PV_LIFETIME_YR} yr)"
    )
    ax4.set_ylim(0, 30)
    ax4.set_xticks(x)
    ax4.set_xticklabels(scenario_labels, fontsize=9)
    ax4.legend(frameon=False, fontsize=9)
    style_ax(
        ax4,
        "Carbon Payback Period by Grid Scenario",
        "Years to carbon break-even"
    )
    ax4.text(
        0.5, -0.15,
        "As the grid decarbonizes, each kWh displaced saves less CO₂ → payback takes longer",
        transform=ax4.transAxes, ha="center", fontsize=8, color="#666"
    )
 
    # ── Chart 5: Sensitivity — payback vs grid intensity ──────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
 
    for cfg, include in [("PV only", False), ("PV + BESS", True)]:
        sens = compute_sensitivity(include, base_grid=base_grid)
        # Cap infinite values for display
        payback_display = [min(p, 26) for p in sens["paybacks"]]
        ax5.plot(
            sens["grid_values"], payback_display,
            color=colors[cfg], linewidth=2.2, label=cfg
        )
 
    # Mark the three grid scenarios with vertical lines
    scenario_line_colors = {"2026 (today)": "#555", "2030 (target)": "#4C9A52",
                            "2035 (projection)": "#E76F51"}
    for label, intensity in GRID_SCENARIOS.items():
        ax5.axvline(intensity, color=scenario_line_colors[label],
                    linestyle=":", linewidth=1.2, alpha=0.8)
        ax5.text(intensity + 0.003, 23.5, label.split()[0],
                 fontsize=7, color=scenario_line_colors[label])
 
    ax5.axhline(PV_LIFETIME_YR, color="#888", linestyle="--",
                linewidth=1, alpha=0.7, label="System lifetime")
    ax5.set_ylim(0, 27)
    ax5.set_xlabel("Grid carbon intensity [kg CO₂-eq/kWh]", fontsize=9)
    ax5.legend(frameon=False, fontsize=8)
    style_ax(
        ax5,
        "Sensitivity: Payback vs\nGrid Carbon Intensity",
        "Carbon payback [years]"
    )
 
    # ── Save ──────────────────────────────────────────────────────────────────
    output_path = "D:\Projects\LCA & Carbon Payback Analysis\outputs\lca_pv_bess_results.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Charts saved → {output_path}")
    
# =============================================================================
# MAIN — Run full LCA
# =============================================================================

def run_lca():
    """
    Main function — runs the complete LCA model and produces all outputs.
 
    Execution order:
      1. Phase 2: compute LCI for both configurations
      2. Phase 3: normalize to functional unit (LCIA)
      3. Phase 4: carbon payback for all grid scenarios
      4. Print results table
      5. Generate and save charts
    """
 
    print("\n  Running LCA model...")
 
    # ── Phase 2: Life Cycle Inventory ─────────────────────────────────────────
    lci_pv_only = compute_lci(include_bess=False)
    lci_pv_bess = compute_lci(include_bess=True)
 
    # ── Phase 3: Electricity delivered + LCIA normalization ───────────────────
    mwh_pv_only = compute_electricity_delivered(include_bess=False)
    mwh_pv_bess = compute_electricity_delivered(include_bess=True)
 
    lcia_pv_only = compute_lcia(lci_pv_only, mwh_pv_only)
    lcia_pv_bess = compute_lcia(lci_pv_bess, mwh_pv_bess)
 
    # ── Phase 4: Carbon payback for all scenarios ──────────────────────────────
    paybacks = {}
    for label, intensity in GRID_SCENARIOS.items():
        paybacks[label] = {
            "PV only"  : compute_carbon_payback(lci_pv_only, intensity),
            "PV + BESS": compute_carbon_payback(lci_pv_bess, intensity),
        }
 
    # ── Print results ──────────────────────────────────────────────────────────
    print_results_table(
        lci_pv_only, lci_pv_bess,
        mwh_pv_only, mwh_pv_bess,
        lcia_pv_only, lcia_pv_bess,
        paybacks
    )
 
    # ── Generate charts ────────────────────────────────────────────────────────
    plot_results(
        lcia_pv_only, lcia_pv_bess,
        paybacks,
        base_grid=0.363   # 2026 German grid: 363 g CO2/kWh [5][6]
    )
 
 
# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_lca()