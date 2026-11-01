"""
Monte Carlo simulation of India's speech therapy market.

Instead of three fixed scenarios, every uncertain input is drawn from a
triangular distribution (low, most likely, high), using the same Low / Base / High
values as the Excel model's Inputs sheet. The model is run 100,000 times and the
spread of results shows how uncertain the answer is and which input matters most.
"""
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)  # fixed seed so results are reproducible
N = 100_000

# ---- Inputs: (low, base, high), same as Excel "Inputs" sheet ----
CHILDREN = 350e6                       # children aged 0-14 (Technical Group projection)
THERAPISTS_REGISTERED = 11_031          # RCI, 2023
WORK_DAYS = 250
START_RATE = 0.85        # partner clinic: share of referred children who start therapy
CONSULT_PER_YEAR = 1     # assumption: one assessment/review per child per year

inputs = {
    "Share needing therapy":        (0.02, 0.04, 0.08),
    "Share referred to a clinic":   (0.06, 0.12, 0.24),   # assumption
    "Sessions per child per year":  (48, 96, 104),        # partner clinic: ~8/month
    "Price per session (Rs)":       (1000, 1200, 1500),   # partner clinic: Rs 1,200
    "Share of pros in speech":      (0.40, 0.50, 0.60),   # assumption
    "Sessions per therapist/day":   (4, 5, 6),            # partner clinic
    "Consultation fee (Rs)":        (500, 1250, 2000),    # partner clinic Rs 2,000 = high end
}

def draw(lo, mode, hi):
    return rng.triangular(lo, mode, hi, N)

s = {k: draw(*v) for k, v in inputs.items()}

# ---- Model: identical logic to the Excel "Model" sheet ----
def demand_value(need, referred, sessions, price, fee=inputs["Consultation fee (Rs)"][1]):
    """Market value at full paid demand (therapy + consultations), in Rs crore."""
    children_paid = CHILDREN * need * referred * START_RATE
    return children_paid * (sessions * price + CONSULT_PER_YEAR * fee) / 1e7

paid_sessions = CHILDREN * s["Share needing therapy"] * s["Share referred to a clinic"] * START_RATE * s["Sessions per child per year"]
capacity = THERAPISTS_REGISTERED * s["Share of pros in speech"] * s["Sessions per therapist/day"] * WORK_DAYS
market = demand_value(s["Share needing therapy"], s["Share referred to a clinic"],
                      s["Sessions per child per year"], s["Price per session (Rs)"],
                      s["Consultation fee (Rs)"])
served_share = np.minimum(1, capacity / paid_sessions)
serviceable = np.minimum(paid_sessions, capacity) * s["Price per session (Rs)"] / 1e7
children_served = capacity / s["Sessions per child per year"]

def pct(x, p): return np.percentile(x, p)

print(f"Simulations: {N:,}\n")
print("Market value at full paid demand (Rs crore)")
print(f"  P10 {pct(market,10):,.0f}   P50 {pct(market,50):,.0f}   P90 {pct(market,90):,.0f}")
print("Serviceable market given therapist supply (Rs crore)")
print(f"  P10 {pct(serviceable,10):,.0f}   P50 {pct(serviceable,50):,.0f}   P90 {pct(serviceable,90):,.0f}")
print("Share of paid demand current therapists can serve")
print(f"  P10 {pct(served_share,10):.0%}   P50 {pct(served_share,50):.0%}   P90 {pct(served_share,90):.0%}")
print(f"  Probability supply can meet all paid demand: {np.mean(served_share >= 1):.1%}")
print("Children current therapists can treat at once")
print(f"  P10 {pct(children_served,10):,.0f}   P50 {pct(children_served,50):,.0f}   P90 {pct(children_served,90):,.0f}")

# ---- Tornado: swing in market value when one input moves low -> high, others at base ----
demand_keys = ["Share needing therapy", "Share referred to a clinic",
               "Sessions per child per year", "Price per session (Rs)"]
base = {k: inputs[k][1] for k in demand_keys}
base_value = demand_value(*base.values())
swings = []
for k in demand_keys:
    lo_args = dict(base); lo_args[k] = inputs[k][0]
    hi_args = dict(base); hi_args[k] = inputs[k][2]
    swings.append((k, demand_value(*lo_args.values()), demand_value(*hi_args.values())))
swings.sort(key=lambda t: t[2] - t[1])
print(f"\nBase case market value: Rs {base_value:,.0f} crore")
for k, lo, hi in reversed(swings):
    print(f"  {k:30s} {lo:>8,.0f} to {hi:>8,.0f}  (swing {hi-lo:,.0f})")

# ---- Charts ----
SURFACE, INK, INK2, BLUE, ORANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6", "#eb6834"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#d0cfca",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})

# 1) Distribution of market value
fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
clip = pct(market, 99)
ax.hist(market[market <= clip], bins=60, color=BLUE, edgecolor=SURFACE, linewidth=0.6)
top = ax.get_ylim()[1]; ax.set_ylim(0, top * 1.22)
for p, lab in [(10, "P10"), (50, "Median"), (90, "P90")]:
    v = pct(market, p)
    ax.axvline(v, color=INK2, linewidth=1, linestyle="--", ymax=1 / 1.22)
    ax.text(v, top * 1.04, f"{lab}\nRs {v:,.0f} cr", color=INK, fontsize=9, ha="center", va="bottom")
ax.set_title("India speech therapy market at full paid demand (100,000 simulations)",
             loc="left", color=INK, fontsize=11)
ax.set_xlabel("Market value (Rs crore per year)")
ax.set_ylabel("Number of simulations")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color="#ecebe7", linewidth=0.6); ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
fig.tight_layout(); fig.savefig("market_distribution.png", dpi=200, facecolor=SURFACE)

# 2) Tornado chart
fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
labels = [k for k, _, _ in swings]
for i, (k, lo, hi) in enumerate(swings):
    ax.barh(i, lo - base_value, left=base_value, color=ORANGE, height=0.55,
            label="Input at low value" if i == 0 else None)
    ax.barh(i, hi - base_value, left=base_value, color=BLUE, height=0.55,
            label="Input at high value" if i == 0 else None)
    ax.text(lo, i, f"{lo:,.0f} ", ha="right", va="center", fontsize=8, color=INK)
    ax.text(hi, i, f" {hi:,.0f}", ha="left", va="center", fontsize=8, color=INK)
ax.axvline(base_value, color=INK2, linewidth=1)
ax.set_yticks(range(len(labels)), labels)
ax.set_xlabel("Market value (Rs crore per year)")
ax.set_title(f"What drives the estimate? (base case Rs {base_value:,.0f} cr)",
             loc="left", color=INK, fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, fontsize=8, loc="lower right")
xmax = max(h for _, _, h in swings); ax.set_xlim(0, xmax * 1.15)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
fig.tight_layout(); fig.savefig("tornado.png", dpi=200, facecolor=SURFACE)
print("\nSaved market_distribution.png and tornado.png")