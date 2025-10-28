# CoC Hero Upgrade Calculator — Streamlit (Hammer Jam ready)
# Save as app.py, then run locally with:  streamlit run app.py
# Deploy free on Streamlit Community Cloud: https://streamlit.io/cloud

import math
import datetime as dt
import streamlit as st

st.set_page_config(page_title="CoC Hero Upgrade Calculator", page_icon="🛠️", layout="centered")

# ===================== Your original model & helpers =====================

def parse_time(time_str: str) -> int:
    time_str = time_str.strip()
    days = 0
    hours = 0
    if 'd' in time_str:
        parts = time_str.split('d')
        days_str = parts[0].strip()
        if days_str:
            days = int(days_str)
        if len(parts) > 1:
            h_str = parts[1].strip().replace('h', '')
            if h_str:
                hours = int(h_str)
    elif 'h' in time_str:
        hours = int(time_str.replace('h', ''))
    return days * 24 + hours

heroes = {
    "Minion Prince": {"min_lv": 70, "max_lv": 90, "times_str": ["7d 12h"] * 10 + ["8d"] * 10},
    "Barbarian King": {"min_lv": 80, "max_lv": 100, "times_str": ["6d"] * 5 + ["7d"] * 5 + ["7d 12h"] * 5 + ["8d"] * 5},
    "Archer Queen": {"min_lv": 80, "max_lv": 100, "times_str": ["6d"] * 5 + ["7d"] * 5 + ["7d 12h"] * 5 + ["8d"] * 5},
    "Grand Warden": {"min_lv": 55, "max_lv": 75, "times_str": ["5d"] * 5 + ["6d"] * 5 + ["7d"] * 4 + ["7d 12h"] + ["8d"] * 5},
    "Royal Champion": {"min_lv": 30, "max_lv": 50, "times_str": ["4d"] * 5 + ["5d"] * 6 + ["6d", "6d 12h", "7d", "7d 12h"] + ["8d"] * 5},
}

# ===================== UI Controls =====================

st.title("Clash of Clans — Hero Upgrade & Potion Planner 🛠️")
st.caption("Hammer Jam + Gold Pass + Builder Apprentice math — made clickable for non-tech friends.")

# --- Presets (one-click) ---
# IMPORTANT: Apply preset BEFORE creating widgets that use those keys.
with st.sidebar:
    st.header("Global Event Settings")

    # Init session_state defaults once
    if "hammer_jam_percent" not in st.session_state:
        st.session_state.hammer_jam_percent = 50
    if "gold_pass_percent" not in st.session_state:
        st.session_state.gold_pass_percent = 20
    if "potion_hours" not in st.session_state:
        st.session_state.potion_hours = 9.0
    if "preset" not in st.session_state:
        st.session_state.preset = "Custom"
    if "gp_enabled" not in st.session_state:
        st.session_state.gp_enabled = False

    preset = st.radio(
        "Presets",
        ["Custom", "Hammer Jam (50% + GP 20%)", "No event (0% + 0%)"],
        index=["Custom", "Hammer Jam (50% + GP 20%)", "No event (0% + 0%)"].index(st.session_state.preset),
        help="Select a preset to auto-fill. You can still tweak after.",
    )

    # If preset changed, update state BEFORE widgets are created
    if preset != st.session_state.preset:
        if preset == "Hammer Jam (50% + GP 20%)":
            st.session_state.hammer_jam_percent = 50
            st.session_state.gold_pass_percent = 20
            st.session_state.gp_enabled = True
        elif preset == "No event (0% + 0%)":
            st.session_state.hammer_jam_percent = 0
            st.session_state.gold_pass_percent = 0
            st.session_state.gp_enabled = False
        # Custom leaves current values as-is
        st.session_state.preset = preset
        st.rerun()

    # Now create widgets bound to those keys
    hammer_jam_percent = st.slider(
        "Event time reduction (%)",
        min_value=0, max_value=90, value=st.session_state.hammer_jam_percent, step=5,
        key="hammer_jam_percent",
        help="Hammer Jam or similar. Applied as time × (1 − %/100). Default 50% during Hammer Jam.",
    )

    gold_pass_percent = st.number_input(
        "Gold Pass time reduction achieved (%)",
        min_value=0, max_value=20, value=int(st.session_state.gold_pass_percent), step=1,
        key="gold_pass_percent",
        help="Enter how much Gold Pass boost you've unlocked (0–20%). This applies on top of the event reduction. Example: 50% event + 20% GP ≈ 60% net.",
    )

    potion_hours = st.number_input(
        "Builder Potion effective hours per potion",
        min_value=1.0, max_value=24.0, value=st.session_state.potion_hours, step=0.5,
        key="potion_hours",
        help="Your model: 9 h progress per potion (10× speed for 1 h).",
    )

    st.divider()
    st.write("Apprentice model: ~1 use/day saving 'level' hours of progress per day.")

# Main inputs
colA, colB = st.columns([1,1])
with colA:
    hero_name = st.selectbox(
        "Select Hero",
        list(heroes.keys()),
        help="Pick the hero you're upgrading.",
    )
    h = heroes[hero_name]
    current_lv = st.number_input(
        f"Current {hero_name} level (min {h['min_lv']})",
        min_value=h['min_lv'], max_value=h['max_lv']-1, value=h['min_lv'], step=1,
        help="Set the level you're starting from (can't be the max).",
    )
with colB:
    apprentice_lv = st.number_input(
        "Builder Apprentice level (0–8)",
        min_value=0, max_value=8, value=0, step=1,
        help="Adds (level) hours of progress per day. Example: level 4 → +4h/day.",
    )
    event_days = st.number_input(
        "Event duration (days)",
        min_value=1, max_value=30, value=14, step=1,
        help="Length of the event window you're planning for.",
    )

# Gold Pass toggle in the MAIN window (requested)
gp_choice = st.radio(
    "Use Gold Pass boost?",
    ["No", "Yes"],
    index=(1 if st.session_state.get("gp_enabled", False) else 0),
    help="If you have Gold Pass boost active, choose 'Yes'. The percent you entered in the sidebar (0–20) will be applied.",
)
st.session_state.gp_enabled = (gp_choice == "Yes")

# ===================== Core computation (matches your CLI logic) =====================

upgrades_needed = h['max_lv'] - int(current_lv)
start_idx = int(current_lv) - h['min_lv']

# Clamp index to avoid user errors
start_idx = max(0, min(start_idx, len(h['times_str']) - 1))
levels_slice = h['times_str'][start_idx : start_idx + upgrades_needed]

total_normal_h = sum(parse_time(t) for t in levels_slice)

def effective_hours_needed(total_hours: float) -> float:
    # Event reduction (e.g., 50%) + optional Gold Pass extra reduction (0–20%)
    mult = (1 - st.session_state.hammer_jam_percent / 100)
    if st.session_state.get("gp_enabled", False) and st.session_state.gold_pass_percent > 0:
        mult *= (1 - st.session_state.gold_pass_percent / 100)
    return total_hours * mult

save_h_per_day = apprentice_lv if apprentice_lv > 0 else 0
speed_mult = 1 + save_h_per_day / 24.0  # your model

avail_h = event_days * 24

# Single-case computation based on radio
P = effective_hours_needed(total_normal_h)   # boosted progress required
base_time_h = P / speed_mult                 # real hours required with apprentice
max_prog_no_p = avail_h * speed_mult         # progress possible with just time + apprentice

if max_prog_no_p >= P:
    potions = 0
    shortfall = 0
else:
    shortfall = P - max_prog_no_p
    potions = math.ceil(shortfall / st.session_state.potion_hours)

# ===================== Output =====================

st.subheader(f"Plan for {hero_name}: lv{current_lv} → lv{h['max_lv']} ({upgrades_needed} upgrades)")

st.metric("Total normal time", f"{total_normal_h/24:.1f} d ({total_normal_h:.0f} h)")

st.metric(
    "Boosted progress needed",
    f"{P:.1f} h ({P/24:.1f} d)")

st.metric(
    "Real time with apprentice",
    f"{base_time_h:.1f} h ({base_time_h/24:.1f} d)")

st.metric(
    "Available during event",
    f"{avail_h:.0f} h ({avail_h/24:.1f} d)")

if potions == 0:
    st.success("No potions needed! 🧪")
else:
    st.warning(f"{potions} potions needed (shortfall {shortfall:.1f} h)")

st.divider()
with st.expander("Per-level times used in this calc"):
    st.write(levels_slice if levels_slice else "No upgrades needed.")

# Developer card (click to open)
with st.expander("Developer’s details"):
    st.markdown(
        """
        <div style="padding:16px;border:1px solid rgba(0,0,0,0.08);border-radius:16px;background:linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0.00));">
          <div style="font-size:1.05rem;margin-bottom:6px;">👤 Crafted by <strong>Roy</strong></div>
          <div style="margin:4px 0;">📸 Instagram: <a href="https://instagram.com/royyy_769" target="_blank" style="text-decoration:none;">@royyy_769</a></div>
          <div style="margin:4px 0;">🎮 Clash Tag: <code>#2GUGJJGYC</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption("Model notes: Reductions stack multiplicatively (Event then optional Gold Pass 0–20%). Builder Apprentice increases effective speed by (1 + level/24). Each potion counts as your chosen hours of progress (default 9h). Use the sidebar presets for one-click setup. The Gold Pass choice is controlled by the radio in the main panel.")
("Model notes: Reductions stack multiplicatively (Event then optional Gold Pass 0–20%). Builder Apprentice increases effective speed by (1 + level/24). Each potion counts as your chosen hours of progress (default 9h). Use the sidebar presets for one-click setup. The Gold Pass choice is controlled by the radio in the main panel.")
