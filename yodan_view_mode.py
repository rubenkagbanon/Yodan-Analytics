# =============================================================================
# yodan_view_mode.py — Module partagé : switcher de mode de vue
# Modes : RH/DG · Médecin
# À importer dans chaque page de test pour un rendu uniforme.
# =============================================================================

import streamlit as st

# ── Constantes de mode ────────────────────────────────────────────────────────
MODE_RH      = "RH/DG"
MODE_MEDECIN = "Médecin"
ALL_MODES    = [MODE_RH, MODE_MEDECIN]

# Couleur d'accent par mode
MODE_COLORS = {
    MODE_RH:      {"accent": "#2f66b3", "accent_soft": "#e7eefb", "accent_2": "#4f8be4", "badge_bg": "#EFF6FF", "badge_text": "#1d4ed8"},
    MODE_MEDECIN: {"accent": "#0f766e", "accent_soft": "#f0fdfa", "accent_2": "#2dd4bf", "badge_bg": "#F0FDF4", "badge_text": "#15803d"},
}

# Icône FA par mode
MODE_ICONS = {
    MODE_RH:      "fas fa-user-tie",
    MODE_MEDECIN: "fas fa-stethoscope",
}




# =============================================================================
# SESSION STATE — initialisation du mode courant
# =============================================================================
def init_mode(key: str = "yodan_view_mode") -> None:
    """Initialise le mode dans le session_state si absent."""
    if key not in st.session_state:
        st.session_state[key] = MODE_RH


def get_mode(key: str = "yodan_view_mode") -> str:
    """Retourne le mode courant."""
    init_mode(key)
    return st.session_state[key]


def set_mode(mode: str, key: str = "yodan_view_mode") -> None:
    """Change le mode courant et force un rerun."""
    st.session_state[key] = mode
    st.rerun()


# =============================================================================
# RENDU DU SWITCHER — barre de boutons inline
# =============================================================================
def render_mode_switcher(
    key: str = "yodan_view_mode",
    position: str = "topbar",  # "topbar" | "sidebar"
) -> str:
    """
    Affiche le switcher de mode.
    Retourne le mode sélectionné.
    """
    init_mode(key)
    current = st.session_state[key]
    colors = MODE_COLORS[current]
    if position == "sidebar":
        with st.sidebar:
            _render_switcher_buttons(key, current, colors, compact=True, position=position)
    else:
        _render_switcher_buttons(key, current, colors, compact=False, position=position)
    return current


def _render_switcher_buttons(key, current, colors, compact=False, position="topbar"):
    """Rendu HTML + boutons du switcher."""
    # Bande de couleur active en haut
    st.markdown(
        f'<div style="height:3px;border-radius:4px;margin-bottom:{6 if compact else 10}px;'
        f'background:linear-gradient(90deg,{colors["accent"]},{colors["accent_2"]});"></div>',
        unsafe_allow_html=True,
    )
    
    # Label
    if not compact:
        st.markdown(
            f'<div style="font-size:10px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
            f'text-transform:uppercase;margin-bottom:6px;">Vue active</div>',
            unsafe_allow_html=True,
        )

    # Boutons côte à côte
    cols = st.columns(len(ALL_MODES))
    for i, mode in enumerate(ALL_MODES):
        mc = MODE_COLORS[mode]
        is_active = mode == current
        with cols[i]:
            btn_style = (
                f"background:linear-gradient(135deg,{mc['accent']},{mc['accent_2']})!important; "
                f"border:none!important;color:#fff!important;border-radius:10px!important; "
                f"font-weight:700!important;font-size:0.75rem!important; "
                f"box-shadow:0 3px 10px {mc['accent']}40!important;"
            ) if is_active else (
                f"background:{mc['accent_soft']}!important; "
                f"border:1.5px solid {mc['accent']}40!important; "
                f"color:{mc['accent']}!important;border-radius:10px!important; "
                f"font-weight:600!important;font-size:0.75rem!important;"
            )
            icon = MODE_ICONS[mode]
            label = f'<i class="{icon}"></i> {mode}' if not compact else mode
            btn_key = f"__mode_btn_{key}_{mode}_{position}"
            
            if st.button(mode, key=btn_key, use_container_width=True):
                set_mode(mode, key)

# =============================================================================
# CSS PARTAGÉ — base commune à tous les tests
# Applique le thème Yodan (polices, variables, cards, jauges…)
# =============================================================================
def get_shared_css(mode: str = MODE_RH) -> str:
    colors = MODE_COLORS[mode]
    accent  = colors["accent"]
    accent2 = colors["accent_2"]

    return f"""
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap');

/* ── Variables dynamiques selon le mode ─────────────────────────────────── */
:root {{
  --accent:       {accent};
  --accent2:      {accent2};
  --accent-soft:  {colors["accent_soft"]};
  --bg-soft:      #eef2f7;
  --card:         #ffffff;
  --text:         #2f3d55;
  --border:       #dde5f2;
}}

/* ── Base ───────────────────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {{
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  color: var(--text);
}}

.stApp {{
  background: linear-gradient(180deg, #f4f6fb 0%, var(--bg-soft) 100%);
}}

/* ── Section title (Fraunces italic) ────────────────────────────────────── */
.section-title {{
  display: flex; align-items: center; gap: 0.7rem;
  font-family: 'Fraunces', Georgia, serif !important;
  font-size: 1.2rem !important; font-style: italic !important;
  font-weight: 400 !important; color: #0F2340 !important;
  margin: 1.6rem 0 1rem !important; padding-bottom: 0.65rem !important;
  border-bottom: 2px solid var(--border) !important;
}}
.section-title::before {{
  content: ''; display: inline-block; width: 4px; height: 22px;
  background: linear-gradient(180deg, var(--accent), var(--accent2));
  border-radius: 2px; flex-shrink: 0;
}}

/* ── Onglets ─────────────────────────────────────────────────────────────── */
[data-baseweb="tab-list"] {{
  background: #FFFFFF !important; border-radius: 12px !important;
  padding: 4px !important; gap: 3px !important;
  border: 1px solid var(--border) !important;
  box-shadow: 0 2px 8px rgba(47,102,179,0.07) !important;
}}
[data-baseweb="tab"] {{
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important; font-size: 0.88rem !important;
  color: #6B88A8 !important; border-radius: 9px !important;
  padding: 0.5rem 1.4rem !important; transition: all 0.2s !important;
}}
[aria-selected="true"][data-baseweb="tab"] {{
  background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  color: #FFFFFF !important; font-weight: 700 !important;
  box-shadow: 0 3px 12px {accent}50 !important;
}}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display: none !important; }}

/* ── KPI cards (style COPSOQ) ───────────────────────────────────────────── */
.card-container {{
  background: #fff; padding: 20px; border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #f0f2f6;
  box-sizing: border-box; display: flex; flex-direction: column;
  justify-content: space-between; align-items: center; text-align: center;
  transition: transform 0.22s, box-shadow 0.22s;
}}
.card-container:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px {accent}20; }}
.card-title {{ color: #6e7785; font-size: clamp(11px,1.1vw,14px); font-weight: 500; margin: 0; line-height: 1.2; }}
.card-value {{ color: #0f0f11; font-size: 30px !important; font-weight: 800 !important; line-height: 1; letter-spacing: -0.03em; }}
.card-footer {{ font-size: 12px; color: #6e7785; }}

/* ── KPI cards (style Karasek) ──────────────────────────────────────────── */
.kpi-card {{
  background: #FFF; border: 1px solid #D6E8F7; border-radius: 16px;
  padding: 1.3rem 1.2rem 1.1rem; text-align: center;
  transition: transform 0.22s, box-shadow 0.22s, border-color 0.22s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); position: relative; overflow: hidden;
}}
.kpi-card::after {{
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--accent2)); opacity: 0; transition: opacity 0.22s;
}}
.kpi-card:hover {{ transform: translateY(-4px); border-color: var(--accent2); box-shadow: 0 10px 32px {accent}25; }}
.kpi-card:hover::after {{ opacity: 1; }}
.kpi-label {{ font-size: 0.8rem; color: #4E6A88 !important; text-transform: uppercase; letter-spacing: 0.09em; font-weight: 700; margin-bottom: 0.55rem; display: block; }}
.kpi-icon {{ width: 38px; height: 38px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.55rem; }}
.kpi-value {{ font-size: 2.35rem; font-weight: 800; color: #0F2340 !important; line-height: 1; letter-spacing: -0.04em; }}

/* ── Gauge cards ────────────────────────────────────────────────────────── */
.gauge-card {{
  background: #FFF; border: 1px solid #D6E8F7; border-radius: 18px;
  padding: 1.6rem 1.2rem 1.3rem; text-align: center;
  transition: transform 0.22s, box-shadow 0.22s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); height: 100%; position: relative; overflow: hidden;
}}
.gauge-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 36px {accent}25; }}
.gauge-semi-wrap {{ position: relative; width: 180px; height: 90px; margin: 0 auto 0.7rem; overflow: hidden; }}
.gauge-semi-bg   {{ position: absolute; width: 180px; height: 180px; border-radius: 50%; background: var(--accent-soft); top: 0; left: 0; }}
.gauge-semi-fill {{
  position: absolute; width: 180px; height: 180px; border-radius: 50%; top: 0; left: 0;
  background: conic-gradient(from 270deg, var(--gauge-color, var(--accent)) 0deg, var(--gauge-color, var(--accent)) calc(var(--g,0deg)), transparent calc(var(--g,0deg)));
}}
.gauge-semi-inner {{ position: absolute; width: 112px; height: 112px; background: #FFF; border-radius: 50%; top: 34px; left: 34px; box-shadow: inset 0 2px 8px {accent}10; }}
.gauge-value {{ font-size: 1.9rem; font-weight: 800; color: #0F2340; line-height: 1; letter-spacing: -0.04em; }}
.gauge-pct   {{ font-size: 1rem; font-weight: 500; color: #6B88A8; }}
.gauge-label {{ font-size: 0.96rem; font-weight: 700; color: #0F2340; margin-top: 0.55rem; }}
.gauge-sublabel {{ font-size: 0.84rem; color: #4E6A88; margin-top: 0.25rem; line-height: 1.5; }}
.gauge-badge {{ display: inline-block; margin-top: 0.7rem; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 0.22rem 0.85rem; border-radius: 999px; }}
.gauge-badge.good  {{ background: #DCFCE7; color: #15803D; }}
.gauge-badge.alert {{ background: #FEE2E2; color: #B91C1C; }}
.gauge-badge.moderate {{ background: #FEF3C7; color: #92400E; }}

/* ── Progress bars ──────────────────────────────────────────────────────── */
.prog-track {{ background: var(--accent-soft); border-radius: 999px; height: 7px; overflow: hidden; margin-top: 5px; }}
.prog-fill  {{ height: 7px; border-radius: 999px; width: 0%; transition: width 1.1s cubic-bezier(0.4,0,0.2,1); }}

/* ── Plotly chart wrapper ─────────────────────────────────────────────────── */
div[data-testid="stPlotlyChart"] {{
  border: 1px solid var(--border); border-radius: 12px;
  background: var(--card); box-shadow: 0 4px 16px {accent}10; padding: 6px;
}}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {{
  background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  border: none !important; color: #FFFFFF !important; border-radius: 10px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important; font-size: 0.8rem !important; letter-spacing: 0.02em !important;
  box-shadow: 0 3px 10px {accent}40 !important; transition: all 0.18s !important;
}}
.stButton > button:hover {{
  background: linear-gradient(135deg, {accent2}, var(--accent)) !important;
  box-shadow: 0 4px 16px {accent}55 !important; transform: translateY(-1px) !important;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
  background-color: #FFFFFF !important;
  border-right: 1px solid #E4F0FB !important;
}}
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {{
  color: #0F2340 !important;
}}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: #eef2f7; }}
::-webkit-scrollbar-thumb {{ background: var(--accent2); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}

/* ── Animations ─────────────────────────────────────────────────────────── */
@keyframes slideUp {{ from {{ opacity:0; transform:translateY(14px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes shimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}
@keyframes blink {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.3; }} }}
@keyframes rpsGaugeFillReveal {{ from {{ width:0%; }} to {{ width:var(--gauge-score,0%); }} }}
@keyframes rpsScoreAppear {{ from {{ opacity:0; transform:translateY(4px); }} to {{ opacity:1; transform:translateY(0); }} }}
@property --g {{ syntax: '<angle>'; inherits: false; initial-value: 0deg; }}

/* ── Hero band (Karasek style) ──────────────────────────────────────────── */
.hero-band {{
  background: linear-gradient(135deg, #FFFFFF, #F5F9FF);
  border: 1px solid #D0E8F8; border-radius: 20px; padding: 1.4rem 2rem 1.3rem;
  margin-bottom: 0.9rem; position: relative; overflow: hidden;
  box-shadow: 0 4px 24px {accent}14, 0 1px 0 rgba(255,255,255,0.9) inset;
}}
.hero-band::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, {accent}, {accent2}, {accent});
  background-size: 200% 100%; animation: shimmer 4s linear infinite;
}}
.hero-chip {{
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
  color: {accent}; background: {colors["accent_soft"]}; border: 1px solid {accent}40;
  border-radius: 999px; padding: 0.3rem 0.8rem;
}}
.hero-chip::before {{
  content: ''; width: 6px; height: 6px; border-radius: 50%;
  background: {accent}; animation: blink 2s ease-in-out infinite;
}}

/* ── RPS grille et cards ─────────────────────────────────────────────────── */
.rps-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 14px; margin-top: 6px; }}
.rps-card {{ background: #fff; border: 1px solid #f0f2f6; border-radius: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); min-height: 240px; padding: 14px; }}
.rps-line {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eef2f7; font-size: 14px; }}
.rps-line:last-child {{ border-bottom: none; }}
.rps-gauge {{ width: 100%; height: 8px; border-radius: 999px; background: #e9edf5; overflow: hidden; position: relative; }}
.rps-gauge-fill {{
  position: absolute; top: 0; left: 0; height: 100%;
  background: var(--accent); border-radius: 999px;
  animation: rpsGaugeFillReveal 2200ms ease-out forwards;
}}
.rps-interpret-row {{ border-radius: 8px; padding: 8px 10px; margin-bottom: 6px; border: 1px solid transparent; }}
.rps-interpret-row.interpret-green  {{ background: #eaf8ef; border-color: #b8e6c8; }}
.rps-interpret-row.interpret-yellow {{ background: #fff7e8; border-color: #f7d8a4; }}
.rps-interpret-row.interpret-red    {{ background: #fdecec; border-color: #f3bbbb; }}

/* ── Mode banner ─────────────────────────────────────────────────────────── */
.mode-banner {{
  display: flex; align-items: center; gap: 10px;
  background: {colors["badge_bg"]}; border: 1px solid {accent}30;
  border-left: 4px solid {accent}; border-radius: 10px;
  padding: 8px 16px; margin-bottom: 14px;
}}
.mode-banner-icon {{ font-size: 16px; color: {accent}; }}
.mode-banner-text {{ font-size: 12px; font-weight: 600; color: {colors["badge_text"]}; }}

/* ── Workzone / LS cards ─────────────────────────────────────────────────── */
.workzone-card, .ls-card {{
  background: #FFF; border: 1px solid #D6E8F7; border-radius: 14px;
  padding: 1.1rem 1rem; text-align: center; transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 2px 6px {accent}0D;
}}
.workzone-card:hover, .ls-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px {accent}20; }}

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 900px) {{
  .rps-grid {{ grid-template-columns: 1fr; }}
  .kpi-value {{ font-size: 1.8rem !important; }}
}}
"""


def inject_shared_css(mode: str = MODE_RH) -> None:
    """Injecte le CSS partagé adapté au mode courant."""
    st.markdown(f"<style>\n{get_shared_css(mode)}\n</style>", unsafe_allow_html=True)


# =============================================================================
# BANNIÈRE DE MODE (en haut de chaque page/onglet)
# =============================================================================
def render_mode_banner(mode: str) -> None:
    """Affiche une petite bannière colorée indiquant le mode actif."""
    colors  = MODE_COLORS[mode]
    icon    = MODE_ICONS[mode]
    accent  = colors["accent"]
    badge   = colors["badge_bg"]
    text_c  = colors["badge_text"]

    st.markdown(
        f'<div class="mode-banner">'
        f'<i class="{icon} mode-banner-icon" style="color:{accent};font-size:15px;"></i>'
        f'<div><span class="mode-banner-text" style="color:{text_c};">Mode {mode}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# UTILITAIRES D'AFFICHAGE CONDITIONNEL
# =============================================================================
def is_rh(mode: str)      -> bool: return mode == MODE_RH
def is_medecin(mode: str) -> bool: return mode == MODE_MEDECIN


def show_if(mode: str, allowed_modes: list) -> bool:
    """Retourne True si le mode courant est dans la liste autorisée."""
    return mode in allowed_modes


# Aliases pratiques
SHOW_RH_MEDECIN = [MODE_RH, MODE_MEDECIN]
SHOW_ALL        = ALL_MODES
SHOW_MEDECIN    = [MODE_MEDECIN]
SHOW_RH         = [MODE_RH]
