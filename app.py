# CoC Hero Upgrade Calculator — Streamlit (Two Tools in One)
# Save as app.py, then run:  streamlit run app.py

import math
import datetime as dt
import streamlit as st

st.set_page_config(page_title="CoC Upgrade Toolkit", page_icon="🛠️", layout="centered")

# ===================== Shared helpers & data =====================

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

# ===================== Sidebar: Global Event Settings (Presets) =====================
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
        st.session_state.preset = preset
        st.rerun()

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
        help="Enter how much Gold Pass boost you've unlocked (0–20%). Applies on top of the event reduction.",
    )

    potion_hours = st.number_input(
        "Builder Potion effective hours per potion",
        min_value=1.0, max_value=24.0, value=st.session_state.potion_hours, step=0.5,
        key="potion_hours",
        help="Your model: 9 h progress per potion (10× speed for 1 h).",
    )

    st.divider()
    st.write("Apprentice model: ~1 use/day saving 'level' hours of progress per day.")

# ===================== Page Title =====================
st.title("Clash of Clans — Upgrade Toolkit 🛠️")
st.caption("Two tools: (1) Hero Upgrade & Potion Planner  (2) Builder Potion Finish-Time Calculator")

# =====================================================
# TOOL 1: Hero Upgrade & Potion Planner
# =====================================================
with st.expander("Hero Upgrade & Potion Planner", expanded=False):
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

    # Gold Pass toggle in the MAIN window
    gp_choice = st.radio(
        "Use Gold Pass boost?",
        ["No", "Yes"],
        index=(1 if st.session_state.get("gp_enabled", False) else 0),
        help="If you have Gold Pass boost active, choose 'Yes'. The percent you entered in the sidebar (0–20) will be applied.",
    )
    st.session_state.gp_enabled = (gp_choice == "Yes")

    # Core computation
    upgrades_needed = h['max_lv'] - int(current_lv)
    start_idx = int(current_lv) - h['min_lv']
    start_idx = max(0, min(start_idx, len(h['times_str']) - 1))
    levels_slice = h['times_str'][start_idx : start_idx + upgrades_needed]

    total_normal_h = sum(parse_time(t) for t in levels_slice)

    def effective_hours_needed(total_hours: float) -> float:
        mult = (1 - st.session_state.hammer_jam_percent / 100)
        if st.session_state.get("gp_enabled", False) and st.session_state.gold_pass_percent > 0:
            mult *= (1 - st.session_state.gold_pass_percent / 100)
        return total_hours * mult

    save_h_per_day = apprentice_lv if apprentice_lv > 0 else 0
    speed_mult = 1 + save_h_per_day / 24.0

    avail_h = event_days * 24

    P = effective_hours_needed(total_normal_h)
    base_time_h = P / speed_mult
    max_prog_no_p = avail_h * speed_mult

    if max_prog_no_p >= P:
        potions = 0
        shortfall = 0
    else:
        shortfall = P - max_prog_no_p
        potions = math.ceil(shortfall / st.session_state.potion_hours)

    st.subheader(f"Plan for {hero_name}: lv{current_lv} → lv{h['max_lv']} ({upgrades_needed} upgrades)")

    st.metric("Total normal time", f"{total_normal_h/24:.1f} d ({total_normal_h:.0f} h)")
    st.metric("Boosted progress needed", f"{P:.1f} h ({P/24:.1f} d)")
    st.metric("Real time with apprentice", f"{base_time_h:.1f} h ({base_time_h/24:.1f} d)")
    st.metric("Available during event", f"{avail_h:.0f} h ({avail_h/24:.1f} d)")

    if potions == 0:
        st.success("No potions needed! 🧪")
    else:
        st.warning(f"{potions} potions needed (shortfall {shortfall:.1f} h)")

    with st.expander("Per-level times used in this calc"):
        st.write(levels_slice if levels_slice else "No upgrades needed.")

# =====================================================
# TOOL 2: Builder Potion Finish-Time Calculator
# =====================================================
with st.expander("Builder Potion Finish-Time Calculator", expanded=False):
    st.markdown("Estimate when each builder's upgrade will actually finish, given a live 10× potion window.")

    # Inputs
    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        boost_h = st.number_input("Boost hours left (10×)", min_value=0, value=0, step=1, help="How many hours of 10× boost remain.")
    with col2:
        boost_m = st.number_input("Boost minutes left", min_value=0, max_value=59, value=0, step=1)
    with col3:
        # Date + time inputs (no st.datetime_input in Streamlit)
        today = dt.date.today()
        col_date, col_time = st.columns(2)
        with col_date:
            date_val = st.date_input("Select date", value=today)
        with col_time:
            time_val = st.time_input("Select time", value=dt.datetime.now().time())
        now_dt = dt.datetime.combine(date_val, time_val)

    st.markdown("Enter remaining in-game time for each active builder. Set idle ones to 0h 0m.")
    n_builders = st.slider("How many builders to track?", 1, 7, 5)

    builders_minutes = []
    for i in range(1, n_builders + 1):
        c1, c2 = st.columns(2)
        with c1:
            rh = st.number_input(f"Builder {i} — remaining hours", min_value=0, value=0, step=1, key=f"b{i}_h")
        with c2:
            rm = st.number_input(f"Builder {i} — remaining minutes", min_value=0, max_value=59, value=0, step=1, key=f"b{i}_m")
        builders_minutes.append(rh * 60 + rm)

    # Logic port
    def compute_real_time_to_finish(remaining_minutes: int, boost_left_minutes: int, x_multiplier: int = 10) -> int:
        boosted_work_capacity = x_multiplier * boost_left_minutes
        if remaining_minutes <= boosted_work_capacity:
            # ceiling division to align with in-game stepping
            return (remaining_minutes + x_multiplier - 1) // x_multiplier
        else:
            leftover = remaining_minutes - boosted_work_capacity
            return boost_left_minutes + leftover

    boost_left_minutes = boost_h * 60 + boost_m

    # Compute & display
    any_active = any(m > 0 for m in builders_minutes)

    if any_active:
        st.divider()
        for idx, remaining in enumerate(builders_minutes, start=1):
            if remaining <= 0:
                st.write(f"Builder {idx}: idle (no upgrade).")
                continue
            real_minutes = compute_real_time_to_finish(remaining, boost_left_minutes, x_multiplier=10)
            finish_time = now_dt + dt.timedelta(minutes=real_minutes)
            real_h, real_m = divmod(max(real_minutes, 0), 60)

            # Also show time-to-finish from actual current system time
            from_now_minutes = max(0, int((finish_time - dt.datetime.now()).total_seconds() // 60))
            from_now_h, from_now_m = divmod(from_now_minutes, 60)

            st.write(
                f"**Builder {idx}:** shown {remaining//60}h {remaining%60}m → real {real_h}h {real_m}m "
                f"→ finishes at {finish_time.strftime('%Y-%m-%d %H:%M')} (≈ in {from_now_h}h {from_now_m}m)"
            )
    else:
        st.info("All builders idle. Nothing to compute.")

# ===================== Developer Card =====================
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

# ===================== Footer Notes =====================
st.caption("Reductions stack multiplicatively (Event then optional Gold Pass 0–20%). Apprentice increases speed by (1 + level/24). Potion hours default to 9h. Two tools are available via expanders.")
