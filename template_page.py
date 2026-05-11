# =============================================================================
# template_page.py — Template pour créer une nouvelle page Streamlit
# 
# UTILISATION :
# 1. Copiez ce fichier dans pages/
# 2. Renommez-le (ex: 8_MaNouvellePage.py)
# 3. Remplacez les placeholders (PAGE_TITLE, PAGE_ICON, etc.)
# 4. Implémentez votre contenu dans les onglets
# =============================================================================

from pathlib import Path
import sys
import streamlit as st
import pandas as pd
import plotly.express as px

# ── Import du module partagé ────────────────────────────────────────────────
# Adaptez le chemin selon votre structure
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from yodan_view_mode import (
        render_mode_switcher,
        inject_shared_css,
        render_mode_banner,
        get_mode,
        init_mode,
        MODE_RH,
        MODE_MEDECIN,
        is_rh,
        is_medecin,
        show_if,
        SHOW_ALL,
        SHOW_RH,
        SHOW_MEDECIN,
        SHOW_RH_MEDECIN,
    )
    _VIEW_MODE_AVAILABLE = True
except ImportError:
    _VIEW_MODE_AVAILABLE = False
    MODE_RH = "RH/DG"
    MODE_MEDECIN = "Médecin"
    
    def get_mode(key="view_mode"):
        return st.session_state.get(key, MODE_RH)
    
    def init_mode(key="view_mode"):
        if key not in st.session_state:
            st.session_state[key] = MODE_RH
    
    def inject_shared_css(mode=None):
        pass
    
    def render_mode_switcher(**kwargs):
        return get_mode()
    
    def render_mode_banner(mode):
        pass
    
    def is_rh(m):
        return m == MODE_RH
    
    def is_medecin(m):
        return m == MODE_MEDECIN
    
    def show_if(m, allowed):
        return m in allowed
    
    SHOW_ALL = [MODE_RH, MODE_MEDECIN]
    SHOW_RH = [MODE_RH]
    SHOW_MEDECIN = [MODE_MEDECIN]
    SHOW_RH_MEDECIN = [MODE_RH, MODE_MEDECIN]


# =============================================================================
# CONFIGURATION DE LA PAGE (À CUSTOMISER)
# =============================================================================
PAGE_TITLE = "Titre de ma page"
PAGE_ICON = "📊"
PAGE_KEY = "ma_page_view_mode"  # Clé unique pour le session_state
MENU_LABEL = "👤 Mon Module"

# =============================================================================
# CSS INLINE DE LA PAGE (À CUSTOMISER SI NÉCESSAIRE)
# =============================================================================
def get_page_css() -> str:
    """CSS spécifique à cette page (en plus du CSS partagé)."""
    return """
    <style>
        /* Styles personnalisés pour cette page */
        .my-custom-class {
            /* ... */
        }
    </style>
    """


# =============================================================================
# FONCTIONS DE LA PAGE (À IMPLÉMENTER)
# =============================================================================

@st.cache_data(show_spinner=False)
def load_page_data(uploaded_file):
    """Charge et prépare les données spécifiques à cette page."""
    if uploaded_file is None:
        return None
    
    # Implémentez votre logique de chargement ici
    # Exemple:
    import io
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    return df


def render_tab_general(df, mode):
    """Onglet Général - KPIs et indicateurs globaux."""
    st.markdown('<div class="section-title">Indicateurs Généraux</div>', unsafe_allow_html=True)
    
    # KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="kpi-card" style="--kpi-color:#1D78F5">
            <div class="kpi-label">TOTAL EFFECTIF</div>
            <div class="kpi-value">{len(df)}</div>
            <div class="kpi-sub">répondants</div>
            <div class="kpi-icon">👥</div>
        </div>
        """, unsafe_allow_html=True)
    # ... Ajoutez d'autres KPIs


def render_tab_analyse(df, mode):
    """Onglet Analyse - Statistiques détaillées."""
    st.markdown('<div class="section-title">Analyse Détaillée</div>', unsafe_allow_html=True)
    # Implémentez votre logique d'analyse


def render_tab_croisement(df, mode):
    """Onglet Croisement - Analyses croisées."""
    st.markdown('<div class="section-title">Analyses Croisées</div>', unsafe_allow_html=True)
    # Implémentez vos croisements


# =============================================================================
# POINT D'ENTRÉE STREAMLIT
# =============================================================================

def main():
    # Configuration de la page
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialisation du mode
    init_mode(PAGE_KEY)
    current_mode = get_mode(PAGE_KEY)
    
    # Injection du CSS partagé
    inject_shared_css(current_mode)
    
    # CSS spécifique à la page
    st.markdown(get_page_css(), unsafe_allow_html=True)
    
    # Chargement des polices et icônes
    st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)
    
    # ════════════════════════════════════════════════════════════
    # TOPBAR
    # ════════════════════════════════════════════════════════════
    col_top, col_switch, col_back = st.columns([5, 3, 1])
    
    with col_top:
        st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;background:white;border-radius:12px;
            padding:14px 24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06),
            0 4px 12px rgba(30,64,175,0.08);border:1px solid #e8edf5;">
            <div style="width:38px;height:38px;background:linear-gradient(135deg,#1D78F5,#4f8be4);
            border-radius:10px;display:flex;align-items:center;justify-content:center;">
            <i class="fas fa-chart-bar" style="color:white;font-size:15px;"></i></div>
            <div>
            <div style="font-size:16px;font-weight:700;color:#1e293b;font-family:'Plus Jakarta Sans',sans-serif;">
            {PAGE_TITLE}</div>
            <div style="font-size:11px;color:#64748b;margin-top:1px;font-family:'Plus Jakarta Sans',sans-serif;">
            Sous-titre ou description courte</div>
            </div></div>
        """, unsafe_allow_html=True)
    
    with col_switch:
        st.markdown('<div style="margin-top:4px;">', unsafe_allow_html=True)
        current_mode = render_mode_switcher(key=PAGE_KEY, position="topbar")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_back:
        if st.button("← Accueil", key=f"back_home_{PAGE_KEY}", use_container_width=True):
            st.switch_page("app.py")
    
    # ════════════════════════════════════════════════════════════
    # BANNIÈRE DE MODE
    # ════════════════════════════════════════════════════════════
    if _VIEW_MODE_AVAILABLE:
        render_mode_banner(current_mode)
    
    # ════════════════════════════════════════════════════════════
    # UPLOAD DE FICHIER
    # ════════════════════════════════════════════════════════════
    uploaded_file = st.file_uploader(
        "Charger un fichier Excel ou CSV",
        type=["xlsx", "xls", "csv"],
        help="Glissez-déposez ou cliquez pour sélectionner votre fichier de données.",
        key=f"uploader_{PAGE_KEY}"
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        st.session_state[f"_file_bytes_{PAGE_KEY}"] = file_bytes
        st.session_state[f"_file_name_{PAGE_KEY}"] = uploaded_file.name
    
    if f"_file_bytes_{PAGE_KEY}" not in st.session_state:
        st.info("Veuillez charger un fichier de données pour démarrer l'analyse.")
        
        # Mode Médecin : on peut afficher des informations sur le questionnaire
        if is_medecin(current_mode):
            with st.expander("📋 À propos de ce questionnaire"):
                st.markdown("""
                ### Description du questionnaire
                
                Ce questionnaire permet d'évaluer...
                
                ### Dimensions évaluées
                - Dimension 1
                - Dimension 2
                - Dimension 3
                """)
        
        st.stop()
    
    # Chargement des données
    file_bytes = st.session_state[f"_file_bytes_{PAGE_KEY}"]
    file_name = st.session_state[f"_file_name_{PAGE_KEY}"]
    
    with st.spinner("Chargement et traitement des données…"):
        df = load_page_data(st.session_state[f"_file_bytes_{PAGE_KEY}"])
    
    if df is None or df.empty:
        st.error("Impossible de charger les données. Vérifiez le format du fichier.")
        st.stop()
    
    # ════════════════════════════════════════════════════════════
    # ONGLETS PRINCIPAUX
    # ════════════════════════════════════════════════════════════
    
    # Définir les onglets selon le mode
    if is_rh(current_mode):
        tabs = st.tabs(["📊 Général"])
    else:
        tabs = st.tabs(["📊 Général", "🔍 Analyse", "🔄 Croisement"])
    
    # Onglet Général (visible dans tous les modes)
    with tabs[0]:
        render_tab_general(df, current_mode)
    
    # Onglets supplémentaires (mode Analyse/Médecin uniquement)
    if not is_rh(current_mode) and len(tabs) > 1:
        with tabs[1]:
            render_tab_analyse(df, current_mode)
        
        if len(tabs) > 2:
            with tabs[2]:
                render_tab_croisement(df, current_mode)
    
    # ════════════════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(
        f'<p style="text-align:center;color:#9CA3AF;font-size:0.8rem;font-family:\'Plus Jakarta Sans\',sans-serif;">'
        f'{PAGE_TITLE} — YODAN Analytics © 2026</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()