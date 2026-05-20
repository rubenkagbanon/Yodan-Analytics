# =============================================================================
# app.py — Dashboard YODAN Analytics RPS
# Point d'entrée principal avec navigation vers les questionnaires
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

# =============================================================================
# CSS INLINE (intégré directement, pas de dépendance externe)
# =============================================================================

def load_css() -> None:
    """Injecte le CSS global pour le dashboard."""
    st.markdown("""
    <style>
        /* === Google Fonts === */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap');
        
        /* === Reset & Base === */
        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #1e293b;
        }
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }
        .main .block-container {
            padding: 1rem 2rem;
            max-width: 1400px;
        }
        #MainMenu, footer, header {
            visibility: hidden;
        }
        
        /* === Sidebar === */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid #e2e8f0 !important;
        }
        
        /* === Hero Band — Topbar Accueil === */
        .hero-band {
            background: linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%);
            border: 1px solid #bfdbfe;
            border-radius: 20px;
            padding: 1.6rem 2.2rem;
            margin-bottom: 1.2rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 24px rgba(29, 120, 245, 0.08), 0 1px 0 rgba(255, 255, 255, 0.9) inset;
        }
        .hero-band::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #1D78F5, #4f8be4, #1D78F5);
            background-size: 200% 100%;
            animation: shimmer 4s linear infinite;
        }
        .hero-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #1D78F5;
            background: #eff6ff;
            border: 1px solid rgba(29, 120, 245, 0.25);
            border-radius: 999px;
            padding: 0.3rem 0.8rem;
            margin-bottom: 0.6rem;
        }
        .hero-chip::before {
            content: '';
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #1D78F5;
            animation: blink 2s ease-in-out infinite;
        }
        .hero-title {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.8rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
            line-height: 1.2;
        }
        .hero-subtitle {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 0.9rem;
            color: #64748b;
            margin-top: 0.3rem;
        }
        
        /* === Section Title (Fraunces italic) === */
        .section-title {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            font-family: 'Fraunces', Georgia, serif !important;
            font-size: 1.2rem !important;
            font-style: italic !important;
            font-weight: 400 !important;
            color: #0f172a !important;
            margin: 1.6rem 0 1rem !important;
            padding-bottom: 0.65rem !important;
            border-bottom: 2px solid #e2e8f0 !important;
        }
        .section-title::before {
            content: '';
            display: inline-block;
            width: 4px;
            height: 22px;
            background: linear-gradient(180deg, #1D78F5, #4f8be4);
            border-radius: 2px;
            flex-shrink: 0;
        }
        
        /* === KPI Cards === */
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 18px 16px 14px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
            border-top: 3px solid var(--kpi-color, #1D78F5);
            min-height: 130px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            text-align: left;
        }
        .kpi-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(29, 120, 245, 0.12);
        }
        .kpi-icon {
            position: absolute;
            right: 14px;
            top: 14px;
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        .kpi-label {
            font-size: 9.5px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 6px;
            font-weight: 700;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 800;
            color: #0f172a;
            line-height: 1;
            letter-spacing: -0.03em;
        }
        .kpi-value span {
            font-size: 13px;
            font-weight: 500;
            color: #94a3b8;
        }
        .kpi-sub {
            font-size: 11px;
            color: #94a3b8;
            margin-top: 4px;
        }
        
        /* === Menu Buttons === */
        .stButton > button {
            background: linear-gradient(135deg, #1D78F5, #155CC0) !important;
            border: none !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            letter-spacing: 0.02em !important;
            padding: 0.6rem 1.2rem !important;
            box-shadow: 0 3px 10px rgba(29, 120, 245, 0.25) !important;
            transition: all 0.18s !important;
            width: 100%;
            margin-bottom: 0.5rem;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #F97316, #EA6A0A) !important;
            box-shadow: 0 4px 16px rgba(249, 115, 22, 0.35) !important;
            transform: translateY(-1px) !important;
        }
        
        /* === Plotly Chart Wrapper === */
        div[data-testid="stPlotlyChart"] {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
            padding: 8px;
        }
        
        /* === Scrollbar === */
        ::-webkit-scrollbar {
            width: 5px;
            height: 5px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #1D78F5;
        }
        
        /* === Footer === */
        .dashboard-footer {
            text-align: center;
            padding: 1.5rem 0 0.5rem;
            color: #94a3b8;
            font-size: 0.78rem;
            font-family: 'Plus Jakarta Sans', sans-serif;
            border-top: 1px solid #e2e8f0;
            margin-top: 2rem;
        }
        
        /* === Animations === */
        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* === Responsive === */
        @media (max-width: 900px) {
            .main .block-container {
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
            .hero-title {
                font-size: 1.4rem;
            }
        }
        @media (max-width: 700px) {
            .kpi-card {
                min-height: 100px;
            }
            .kpi-value {
                font-size: 22px;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def render_topbar(title: str, subtitle: str, icon_class: str, gradient: str, page_key: str) -> None:
    """Affiche la topbar avec le titre, sous-titre et icône."""
    st.markdown(f"""
        <div class="hero-band">
            <div class="hero-chip">
                <i class="{icon_class}"></i> DASHBOARD
            </div>
            <h1 class="hero-title">{title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)


def section_title(title: str) -> None:
    """Affiche un titre de section stylisé."""
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def render_footer(page_name: str = "") -> None:
    """Affiche le pied de page."""
    st.markdown(f"""
        <div class="dashboard-footer">
            YODAN Analytics — Dashboard RPS &copy; 2026{ ' — ' + page_name if page_name else '' }
        </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

# Configuration de la page (doit être appelée en premier)
st.set_page_config(
    page_title="YODAN Analytics — Dashboard RPS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement des polices Google Fonts et Font Awesome
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# Injection du CSS
load_css()

# ════════════════════════════════════════════════════════════
# TOPBAR
# ════════════════════════════════════════════════════════════
render_topbar(
    title="YODAN Analytics",
    subtitle="Dashboard d'analyse des Risques Psychosociaux (RPS)",
    icon_class="fas fa-chart-line",
    gradient="135deg, #1D78F5, #155CC0",
    page_key="home"
)

# ════════════════════════════════════════════════════════════
# KPIs GLOBAUX
# ════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Vue d\'ensemble</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
        <div class="kpi-card" style="--kpi-color:#1D78F5;">
            <div class="kpi-icon" style="background:#EBF3FF;color:#1D78F5;">
                <i class="fas fa-users"></i>
            </div>
            <div class="kpi-label">Effectif Total</div>
            <div class="kpi-value">1,240<span> salariés</span></div>
            <div class="kpi-sub">base de données active</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
        <div class="kpi-card" style="--kpi-color:#16A37F;">
            <div class="kpi-icon" style="background:#E8F8EF;color:#16A37F;">
                <i class="fas fa-check-double"></i>
            </div>
            <div class="kpi-label">Répondants</div>
            <div class="kpi-value">856<span> réponses</span></div>
            <div class="kpi-sub">taux de participation 69%</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
        <div class="kpi-card" style="--kpi-color:#F5A623;">
            <div class="kpi-icon" style="background:#FEF5E7;color:#F5A623;">
                <i class="fas fa-clipboard-list"></i>
            </div>
            <div class="kpi-label">Questionnaires Actifs</div>
            <div class="kpi-value">6<span> modules</span></div>
            <div class="kpi-sub">analyse multi-dimensionnelle</div>
        </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# JAUGE RPS GLOBAL
# ════════════════════════════════════════════════════════════
section_title("Indicateur de Risque Global (RPS)")

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=42,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={
        'text': "Niveau de Risque Psychosocial",
        'font': {'size': 18, 'family': 'Plus Jakarta Sans'}
    },
    gauge={
        'axis': {
            'range': [None, 100],
            'tickwidth': 1,
            'tickcolor': "#1e293b",
            'tickfont': {'size': 12}
        },
        'bar': {'color': "#1D78F5", 'thickness': 0.15},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "#e2e8f0",
        'steps': [
            {'range': [0, 25], 'color': '#22C55E'},
            {'range': [25, 50], 'color': '#F5A623'},
            {'range': [50, 75], 'color': '#E8504A'},
            {'range': [75, 100], 'color': '#7C3AED'}
        ],
        'threshold': {
            'line': {'color': "#EF4444", 'width': 4},
            'thickness': 0.75,
            'value': 90
        }
    }
))

fig.update_layout(
    height=380,
    margin=dict(l=30, r=30, t=60, b=20),
    font={'family': "Plus Jakarta Sans"}
)

st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════
# ACCÈS AUX QUESTIONNAIRES
# ════════════════════════════════════════════════════════════
section_title("Accès aux Questionnaires")

def menu_button(label: str, icon: str, color: str, page_file: str) -> None:
    """Bouton de navigation vers une page questionnaire."""
    if st.button(
        f"{icon}  {label}",
        key=f"btn_{page_file}",
        use_container_width=True
    ):
        st.switch_page(f"pages/{page_file}")

m1, m2, m3 = st.columns(3)

with m1:
    menu_button("MBI Burnout", "", "#E8504A", "1_MBI_Burnout.py")
    menu_button("KARASEK", "", "#16A37F", "2_KARASEK.py")

with m2:
    menu_button("COPSOQ", "", "#1D78F5", "3_COPSOQ.py")
    menu_button("QVT", "", "#F5A623", "4_QVT.py")

with m3:
    menu_button("WHO-5 · PSS-10", "", "#7C3AED", "6_WHO_PSS.py")
    menu_button("SST", "", "#E67E22", "5_SST.py")

# ════════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════════
render_footer("Accueil")