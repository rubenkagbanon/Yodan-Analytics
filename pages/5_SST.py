# =============================================================================
# 3_SST.py — SST - Santé & Sécurité au Travail
# Page d'analyse avec upload de fichier et KPIs généraux
# Style KPI uniforme et flexible (template yodan_view_mode.py)
# =============================================================================

from pathlib import Path
import sys
import io
import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Import du module partagé ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from yodan_view_mode import (
        render_mode_switcher, inject_shared_css, render_mode_banner,
        get_mode, init_mode, MODE_RH, MODE_MEDECIN, MODE_COLORS, MODE_ICONS,
        is_rh, is_medecin, show_if, SHOW_ALL, SHOW_RH, SHOW_MEDECIN, SHOW_RH_MEDECIN,
    )
    _VIEW_MODE_AVAILABLE = True
except ImportError:
    _VIEW_MODE_AVAILABLE = False
    MODE_RH = "RH/DG"
    MODE_MEDECIN = "Médecin"
    MODE_COLORS = {
        MODE_RH:      {"accent": "#2f66b3", "accent_soft": "#e7eefb", "accent_2": "#4f8be4", "badge_bg": "#EFF6FF", "badge_text": "#1d4ed8"},
        MODE_MEDECIN: {"accent": "#0f766e", "accent_soft": "#f0fdfa", "accent_2": "#2dd4bf", "badge_bg": "#F0FDF4", "badge_text": "#15803d"},
    }
    MODE_ICONS = {
        MODE_RH:      "fas fa-user-tie",
        MODE_MEDECIN: "fas fa-stethoscope",
    }
    def get_mode(key="view_mode"): return st.session_state.get(key, MODE_RH)
    def init_mode(key="view_mode"):
        if key not in st.session_state: st.session_state[key] = MODE_RH
    def inject_shared_css(mode=None): pass
    def render_mode_switcher(**kwargs): return get_mode()
    def render_mode_banner(mode): pass
    def is_rh(m): return m == MODE_RH
    def is_medecin(m): return m == MODE_MEDECIN
    def show_if(m, allowed): return m in allowed
    SHOW_ALL = [MODE_RH, MODE_MEDECIN]
    SHOW_RH = [MODE_RH]
    SHOW_MEDECIN = [MODE_MEDECIN]
    SHOW_RH_MEDECIN = [MODE_RH, MODE_MEDECIN]


# =============================================================================
# CONFIGURATION DE LA PAGE SST
# =============================================================================
PAGE_TITLE = "SST — Santé & Sécurité au Travail"
PAGE_ICON = "🛡️"
PAGE_KEY = "sst_view_mode"

# ══════════════════════════════════════════════════════════
# TEXTE COMPLET DES QUESTIONS PAR PRINCIPE
# ══════════════════════════════════════════════════════════
TEXTE_QUESTIONS = {
    "AT_MP": [
        "Les AT sont déclarées",
        "Les AT sont analysés pour identifier la cause",
        "Les AT sont enregistrés et présentés en Comité SST",
        "Les enquêtes se limitent à la recherche de causes immédiates",
        "Il y a un suivi de la réalisation des actions",
        "Des indicateurs de sinistralité sont affichés",
        "Les Maladies professionnelles et les incidents sont pris en compte",
        "Les AT/MP des CDD et intérimaires sont enregistrés",
        "Les AT/MP sont analysés selon une méthode définie",
        "Le CSST ou management participe aux analyses",
        "Les mesures sont intégrées dans un plan d'action",
        "Le Document Unique est mis à jour",
        "Les analyses sont diffusées au personnel",
        "Un comité fait des propositions après un AT/MP",
        "Les tendances AT/MP alimentent la stratégie",
        "Les salariés sont encouragés à signaler les risques",
        "Une veille exploite les AT/MP graves d'activités similaires"
    ],
    "Maintenance": [
        "Les équipements sont réparés en cas de panne",
        "L'entreprise ne connaît pas la liste des équipements à vérifier",
        "Certains équipements sont vérifiés sans suivi des remarques",
        "Les équipements soumis à vérification sont identifiés",
        "Les vérifications sont effectuées",
        "Les travaux sont réalisés au coup par coup",
        "La maintenance est principalement curative",
        "Les responsables maintenance sont identifiés",
        "Un responsable suit le matériel sur site extérieur",
        "Les vérifications couvrent tous les matériaux",
        "Les vérifications suivent un planning",
        "La prise en compte des anomalies est formalisée",
        "La maintenance préventive est planifiée",
        "La maintenance est pilotée par indicateurs",
        "La coordination entre services est recherchée",
        "Les besoins utilisateurs sont pris en compte",
        "Recherche de nouvelles technologies",
        "La liste des équipements est mise à jour par veille",
        "L'analyse des vérifications fait évoluer les cahiers des charges"
    ],
    "Sous_traitants": [
        "Évaluation des risques a priori pour entreprises extérieures",
        "Situations dangereuses gérées au coup par coup",
        "Évaluation des risques rédigée dans un plan de prévention",
        "Sous forme de check-list",
        "Objectif principal : répondre à une obligation",
        "Généralement inconnu des intervenants",
        "Une personne désignée pour signer",
        "Le CSST est informé",
        "Évaluation des risques avant travaux par les 2 entreprises",
        "L'utilisatrice commente le plan aux salariés",
        "Les entreprises veillent au respect",
        "Modifications prises en compte, CSST participe aux visites",
        "Débriefing en fin de travaux",
        "Choix des sous-traitants basé sur leurs performances SST",
        "Accompagnement des sous-traitants dans leur gestion SST"
    ],
    "Interimaires": [
        "Appel à intérimaires dans l'urgence sans accueil",
        "Contenu des missions non défini",
        "Analyse du besoin avec l'ETT",
        "Fourniture des EPI définie",
        "Accueil minimal assuré",
        "Connaissance des travaux interdits",
        "Liste des postes à risques communiquée",
        "Échange préalable formalisé avec l'ETT",
        "L'ETT connaît les postes",
        "Anticipation des besoins",
        "Liste des postes accessibles",
        "Accueil adapté à chaque poste",
        "Parcours d'intégration incluant la SST",
        "Nouvelle analyse si changement de poste",
        "L'agence est prévenue",
        "Bilan en fin de mission",
        "Partenariat effectif avec les agences",
        "Intérimaires associés aux échanges SST"
    ],
    "Preparation": [
        "SST prise en compte à l'achat",
        "Limité à une phrase de conformité",
        "Postes et allées encombrés",
        "Outils pas toujours adaptés",
        "Critères sécurité intégrés à la commande",
        "Conception basée sur réglementation et ergonomie",
        "Protections collectives installées",
        "EPI appropriés fournis",
        "Responsable désigné pour l'extérieur",
        "Cahiers des charges établis",
        "Rubrique sécurité systématique",
        "Conception basée sur analyse des situations",
        "Réception par service compétent",
        "Vérification avant mise en service",
        "CSST consulté",
        "Analyse préalable pour les chantiers",
        "Gestion des matériels organisée",
        "Salariés associés au processus d'achat",
        "Environnement analysé avec le personnel",
        "Analyse avant modifications"
    ],
    "Sante": [
        "SST abordée dans l'entreprise",
        "Visites médicales réalisées",
        "Évaluation limitée au chimique et nuisances",
        "Évaluation transcrite dans le DU",
        "CSST informé",
        "Sollicitation du médecin du travail",
        "FDS disponibles et actualisées",
        "Fiches d'exposition CMR existent",
        "Réflexions pour réduire les risques",
        "Risque santé intègre toutes les nuisances et TMS",
        "Actions en amont avec CSST/DP",
        "Travail avec fournisseurs",
        "Modalités définies pour achats",
        "Maintien dans l'emploi recherché",
        "Préoccupation des risques émergents",
        "Santé prise en compte dès la conception",
        "CSST/DP associé"
    ],
    "EvRP": [
        "EvRP peu ou pas réalisée",
        "DU succinct pour obligation",
        "Pas de plan d'action",
        "EvRP réalisée et mise à jour chaque année",
        "Travaux extérieurs pris en compte",
        "Basée sur description des activités",
        "Connaissance basée sur les accidents",
        "Plans d'action sans priorités",
        "Mise à jour par direction sans concertation",
        "Méthodologie basée sur observation",
        "EvRP collective avec managers et équipes",
        "Pilote désigné",
        "Plan d'action général",
        "Pilotes, moyens et délais précisés",
        "Délais globalement tenus",
        "CSST/DP associé",
        "EvRP moteur du système SST",
        "Intègre veilles technologiques",
        "Direction évalue les moyens",
        "Salariés systématiquement associés"
    ],
    "Formation": [
        "Compétences SST faibles",
        "Chacun se fie à son expérience",
        "Formation limitée au réglementaire",
        "SST identifiés/formés",
        "Formations réglementaires identifiées et réalisées",
        "Formation technique limitée aux postes",
        "Outils et formations standards",
        "Équipiers première intervention formés",
        "Formation au poste inclut SST",
        "Membres CSST formés",
        "Accueil minimal des nouveaux",
        "Besoins formation recensés et actualisés",
        "Validité des habilitations suivie",
        "Formations planifiées",
        "CSST consulté",
        "Formation des membres actualisée",
        "Nouvel arrivant évalué",
        "Tutorat organisé",
        "Recours à l'externe si besoin",
        "Indicateurs de suivi",
        "Délégation de pouvoir formée",
        "Programme intègre besoins des entretiens",
        "Tient compte des objectifs SST",
        "Risques transversaux couverts",
        "Tous niveaux hiérarchiques concernés",
        "Évaluation de la qualité des formations",
        "Appropriation des compétences externes",
        "Capitalisation et diffusion des bonnes pratiques"
    ],
    "Responsabilites": [
        "Fonction sécurité non identifiée",
        "Actions au coup par coup",
        "Encadrement ne veille pas",
        "Salariés non impliqués",
        "Peu ou pas de procédures SST",
        "Pas de réunion CSST/DP",
        "Une personne en charge SST",
        "Considérée comme seul responsable",
        "Encadrement s'inquiète de l'application",
        "Écart instructions/pratiques",
        "Salariés sensibilisés",
        "Connaissance de consignes",
        "CSST/DP informé mais peu sollicité",
        "Responsable SST compétent et conseiller",
        "Anime la démarche",
        "Acteurs opérationnels associés",
        "Encadrement exemplaire",
        "Moteur en détection des risques",
        "CSST/DP associé",
        "Président CSST a moyens",
        "Responsabilités définies mais cloisonnées",
        "Communication organisée mais non évaluée",
        "SST composante de tous les managers",
        "Responsabilités réparties avec coordination",
        "Échanges réguliers avec encadrement",
        "Audits SST terrain",
        "Règles de sécurité valorisées",
        "CSST/DP pleinement impliqué",
        "Communication réelle avec direction"
    ],
    "Management": [
        "Pas de démarche structurée",
        "Absence d'accident justifie inutilité",
        "Accidents fatalité ou erreur humaine",
        "Actions SST externalisées",
        "Direction ne définit pas d'objectifs",
        "Budget significatif alloué",
        "Prévention technique essentiellement",
        "Moyens considérés suffisants",
        "Démarche imposée de l'extérieur",
        "Pas de recours à ressources extérieures",
        "Seulement organismes de contrôle",
        "Objectifs de résultats à court terme",
        "Direction prend en compte les risques",
        "Démarche volontaire mais directive",
        "Mission partagée avec réseau interne",
        "Efficacité des EP évaluée",
        "Appel à ressources extérieures",
        "Objectifs variés mais abandonnés",
        "Engagement particulier de la direction",
        "Anticipation des nouveaux risques",
        "Coordination avec qualité et environnement",
        "Démarche participative",
        "Relations basées sur la confiance",
        "Objectifs SST dans stratégie",
        "Ressources SST évaluées",
        "Benchmarking avec partenaires",
        "Démarche SST valorise l'image"
    ]
}

# ══════════════════════════════════════════════════════════
# DÉFINITION DES PALIERS POUR CHAQUE PRINCIPE
# ══════════════════════════════════════════════════════════
PALIERS_LIMITS = {
    "AT_MP": {1: list(range(1, 3)), 2: list(range(3, 7)), 3: list(range(7, 14)), 4: list(range(14, 18))},
    "Maintenance": {1: list(range(1, 4)), 2: list(range(4, 10)), 3: list(range(10, 16)), 4: list(range(16, 20))},
    "Sous_traitants": {1: list(range(1, 3)), 2: list(range(3, 9)), 3: list(range(9, 13)), 4: list(range(13, 16))},
    "Interimaires": {1: list(range(1, 3)), 2: list(range(3, 8)), 3: list(range(8, 17)), 4: list(range(17, 19))},
    "Preparation": {1: list(range(1, 5)), 2: list(range(5, 10)), 3: list(range(10, 18)), 4: list(range(18, 21))},
    "Sante": {1: list(range(1, 3)), 2: list(range(3, 10)), 3: list(range(10, 15)), 4: list(range(15, 18))},
    "EvRP": {1: list(range(1, 4)), 2: list(range(4, 10)), 3: list(range(10, 17)), 4: list(range(17, 21))},
    "Formation": {1: list(range(1, 5)), 2: list(range(5, 12)), 3: list(range(12, 22)), 4: list(range(22, 29))},
    "Responsabilites": {1: list(range(1, 7)), 2: list(range(7, 14)), 3: list(range(14, 23)), 4: list(range(23, 30))},
    "Management": {1: list(range(1, 6)), 2: list(range(6, 13)), 3: list(range(13, 19)), 4: list(range(19, 28))}
}

# ══════════════════════════════════════════════════════════
# NOMS DES PRINCIPES
# ══════════════════════════════════════════════════════════
NOMS_PRINCIPES = {
    "AT_MP": "Analyse des AT-MP",
    "Maintenance": "Vérifications périodiques et maintenance",
    "Sous_traitants": "Attitude vis-à-vis des sous-traitants",
    "Interimaires": "Attitude vis-à-vis des intérimaires",
    "Preparation": "Préparation et organisation du travail",
    "Sante": "Santé au travail",
    "EvRP": "Évaluation des risques",
    "Formation": "Formation et compétences SST",
    "Responsabilites": "Responsabilités et communication",
    "Management": "Pratiques managériales"
}

CATEGORIES_RADAR = [
    "Sous-traitants", "Maintenance", "AT/MP",
    "Intérimaires", "Préparation", "Santé",
    "EvRP", "Formation", "Responsabilités", 
    "Management"
]

# =============================================================================
# CSS INLINE DE LA PAGE
# =============================================================================
def get_page_css() -> str:
    return """
    <style>
        .non-questions-box {
            background-color: #f8d7da;
            border-left: 4px solid #e74c3c;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        .non-questions-box h5 {
            margin-top: 0;
            margin-bottom: 8px;
            color: #721c24;
            font-size: 1rem;
        }
        .non-questions-box ul {
            margin: 0;
            padding-left: 20px;
        }
        .non-questions-box li {
            margin-bottom: 8px;
            line-height: 1.4;
        }
        .no-non-message {
            font-style: italic;
            color: #27ae60;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            background-color: #d4edda;
            border-radius: 5px;
        }
        .principles-list {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            font-size: 1rem;
        }
        .principles-list ol {
            column-count: 2;
            column-gap: 40px;
        }
        .principles-list li {
            margin-bottom: 8px;
            break-inside: avoid;
        }
        .radar-container {
            background-color: white;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            margin-bottom: 15px;
            display: flex;
            justify-content: center;
        }
    </style>
    """

# =============================================================================
# FONCTIONS DE CALCUL SST
# =============================================================================

def clean_data(data_raw):
    if data_raw is None:
        return None
    for col in data_raw.columns:
        data_raw[col] = data_raw[col].astype(str).fillna("NA")
    return data_raw


def calculate_palier_hierarchique(row_data, principe, questions_par_principe):
    cols = questions_par_principe[principe]
    valid_cols = [c for c in cols if c < len(row_data)]
    if not valid_cols:
        return 0
    
    responses = [row_data.iloc[c] for c in valid_cols]
    current_palier = 0
    
    for palier_num in range(1, 5):
        if palier_num not in PALIERS_LIMITS[principe]:
            continue
        palier_indices = PALIERS_LIMITS[principe][palier_num]
        if max(palier_indices) > len(responses):
            break
        palier_responses = [responses[i-1] for i in palier_indices]
        all_valid = all(
            not pd.isna(r) and str(r) != "NA" and str(r) != "" and str(r) == "Oui"
            for r in palier_responses
        )
        if all_valid:
            current_palier = palier_num
        else:
            break
    return current_palier


def get_non_questions(row_data, principe, questions_par_principe):
    cols = questions_par_principe[principe]
    textes = TEXTE_QUESTIONS[principe]
    valid_cols = [c for c in cols if c < len(row_data)]
    if not valid_cols:
        return None
    responses = [row_data.iloc[c] for c in valid_cols]
    non_indices = [i for i, r in enumerate(responses) if str(r) == "Non"]
    if not non_indices:
        return None
    return [textes[i] for i in non_indices]


# =============================================================================
# FONCTIONS DE RENDU PAR ONGLET
# =============================================================================

def render_tab_overview(df, paliers_df, questions_par_principe):
    """Onglet Vue d'ensemble - Radar SST + Points d'amélioration."""
    idx = 0  # Première ligne
    
    # ── Radar chart ──────────────────────────────────────────
    st.markdown('<div class="section-title">Niveau de maturité SST</div>', unsafe_allow_html=True)
    # ── Liste des 10 principes ─────────────────────────────────
    with st.expander("📋 Voir la liste des 10 principes évalués"):
        st.markdown("""
        <div class="principles-list">
            <ol>
                <li><strong>AT/MP</strong> - Analyse des accidents du travail et des maladies professionnelles</li>
                <li><strong>Maintenance</strong> - Vérifications périodiques et maintenance des équipements</li>
                <li><strong>Sous-traitants</strong> - Attitude de l'entreprise vis-à-vis des sous-traitants</li>
                <li><strong>Intérimaires</strong> - Attitude de l'entreprise vis-à-vis des intérimaires</li>
                <li><strong>Préparation</strong> - Préparation et organisation du travail</li>
                <li><strong>Santé</strong> - Santé au travail</li>
                <li><strong>EvRP</strong> - Réalisation et mise à jour de l'évaluation des risques et du plan d'actions</li>
                <li><strong>Formation</strong> - Programme de formation et compétence SST</li>
                <li><strong>Responsabilités</strong> - Responsabilités, communication et implication des salariés</li>
                <li><strong>Management</strong> - Pratiques managériales de prévention</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    paliers_values = [paliers_df.loc[idx, principe] for principe in questions_par_principe.keys()]
    
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=paliers_values + [paliers_values[0]],
        theta=CATEGORIES_RADAR + [CATEGORIES_RADAR[0]],
        fill='toself',
        name="Niveau de maturité",
        line_color='#e74c3c',
        fillcolor='rgba(231, 76, 60, 0.3)'
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 4], tickvals=[0, 1, 2, 3, 4], tickfont=dict(size=12)),
            angularaxis=dict(tickfont=dict(size=14, color='black'), rotation=90, tickangle=0)
        ),
        showlegend=False,
        height=600,
        margin=dict(l=100, r=100, t=40, b=80),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    st.markdown('<div class="radar-container">', unsafe_allow_html=True)
    st.plotly_chart(fig_radar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">Points d\'amélioration</div>', unsafe_allow_html=True)
    
    raw_row = df.iloc[idx]
    has_any_non = False
    
    col_left, col_right = st.columns(2)
    principe_list = list(questions_par_principe.keys())
    mid_point = len(principe_list) // 2
    
    with col_left:
        for principe in principe_list[:mid_point]:
            non_qs = get_non_questions(raw_row, principe, questions_par_principe)
            if non_qs:
                has_any_non = True
                questions_html = "".join([f"<li>{q}</li>" for q in non_qs])
                st.markdown(f"""
                <div class="non-questions-box">
                    <h5>{NOMS_PRINCIPES[principe]}</h5>
                    <ul>{questions_html}</ul>
                </div>
                """, unsafe_allow_html=True)
    
    with col_right:
        for principe in principe_list[mid_point:]:
            non_qs = get_non_questions(raw_row, principe, questions_par_principe)
            if non_qs:
                has_any_non = True
                questions_html = "".join([f"<li>{q}</li>" for q in non_qs])
                st.markdown(f"""
                <div class="non-questions-box">
                    <h5>{NOMS_PRINCIPES[principe]}</h5>
                    <ul>{questions_html}</ul>
                </div>
                """, unsafe_allow_html=True)
    
    if not has_any_non:
        st.markdown('<div class="no-non-message">✅ Toutes les réponses sont \'Oui\'</div>', unsafe_allow_html=True)

# =============================================================================
# COMPOSANTS KPI STANDARDS
# =============================================================================

def kpi_card(icon_class: str, icon_color: str, icon_bg: str, accent_color: str,
            value, suffix: str, subtitle: str, label: str) -> str:
    return f"""<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;padding:20px 16px 16px;text-align:center;box-shadow:0 2px 12px rgba(15,23,42,0.06);border-top:3px solid {accent_color};transition:transform 0.2s ease,box-shadow 0.2s ease;min-height:160px;display:flex;flex-direction:column;justify-content:space-between;" onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 24px {accent_color}30';" onmouseout="this.style.transform='none';this.style.boxShadow='0 2px 12px rgba(15,23,42,0.06)';"><div><div style="width:40px;height:40px;background:{icon_bg};border-radius:10px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;"><i class="{icon_class}" style="color:{icon_color};font-size:16px;"></i></div><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;margin:0 0 6px 0;">{label}</p></div><div><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:28px;font-weight:800;color:#0F172A;margin:0;line-height:1;letter-spacing:-0.03em;">{value}<span style="font-size:13px;font-weight:500;color:#94A3B8;">{suffix}</span></p><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:11px;color:#94A3B8;margin:4px 0 0 0;">{subtitle}</p></div></div>"""


# =============================================================================
# CHARGEMENT DES DONNÉES
# =============================================================================

@st.cache_data(show_spinner=False)
def load_data_from_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    buf = io.BytesIO(file_bytes)
    if file_name.lower().endswith(".csv"):
        df = pd.read_csv(buf, sep=None, engine="python")
    else:
        df = pd.read_excel(buf)
    return df


# =============================================================================
# POINT D'ENTRÉE STREAMLIT
# =============================================================================

def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")
    init_mode(PAGE_KEY)
    current_mode = get_mode(PAGE_KEY)
    inject_shared_css(current_mode)

    st.markdown(get_page_css(), unsafe_allow_html=True)
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # TOPBAR DYNAMIQUE
    # ════════════════════════════════════════════════════════════
    col_top, col_switch, col_back = st.columns([5, 3, 1])

    with col_top:
        mode_colors = MODE_COLORS.get(current_mode, MODE_COLORS[MODE_RH])
        accent = mode_colors["accent"]
        accent2 = mode_colors["accent_2"]

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;background:white;border-radius:12px;'
            f'padding:14px 24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06),'
            f'0 4px 12px rgba(30,64,175,0.08);border:1px solid #e8edf5;">'
            f'<div style="width:38px;height:38px;background:linear-gradient(135deg,{accent},{accent2});'
            f'border-radius:10px;display:flex;align-items:center;justify-content:center;">'
            f'<i class="fas fa-hard-hat" style="color:white;font-size:15px;"></i></div>'
            f'<div><div style="font-size:16px;font-weight:700;color:#1e293b;'
            f'font-family:\'Plus Jakarta Sans\',sans-serif;">{PAGE_TITLE}</div>'
            f'<div style="font-size:11px;color:#64748b;margin-top:1px;'
            f'font-family:\'Plus Jakarta Sans\',sans-serif;">Analyse des niveaux de maturité SST</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    with col_switch:
        st.markdown('<div style="margin-top:4px;">', unsafe_allow_html=True)
        current_mode = render_mode_switcher(key=PAGE_KEY, position="topbar")
        st.markdown('</div>', unsafe_allow_html=True)
        inject_shared_css(current_mode)

    with col_back:
        if st.button("← Accueil", key=f"back_home_{PAGE_KEY}", use_container_width=True):
            st.switch_page("app.py")

    # ════════════════════════════════════════════════════════════
    # UPLOAD
    # ════════════════════════════════════════════════════════════
    uploaded_file = st.file_uploader("Charger un fichier Excel ou CSV", type=["xlsx", "xls", "csv"], key=f"uploader_{PAGE_KEY}")
    if uploaded_file is not None:
        st.session_state[f"_file_bytes_{PAGE_KEY}"] = uploaded_file.read()
        st.session_state[f"_file_name_{PAGE_KEY}"] = uploaded_file.name
    if f"_file_bytes_{PAGE_KEY}" not in st.session_state:
        st.info("Veuillez charger un fichier de données pour démarrer l'analyse.")
        st.stop()

    file_bytes = st.session_state[f"_file_bytes_{PAGE_KEY}"]
    file_name = st.session_state[f"_file_name_{PAGE_KEY}"]

    with st.spinner("Chargement et traitement des données…"):
        df_raw = load_data_from_bytes(file_bytes, file_name)
        df_clean = clean_data(df_raw)

    if df_clean.empty:
        st.error("Aucune donnée exploitable.")
        st.stop()

    # ════════════════════════════════════════════════════════════
    # CALCULS SST
    # ════════════════════════════════════════════════════════════
    total_questions = df_clean.shape[1]
    
    questions_per_principe = {
        "AT_MP": 17, "Maintenance": 19, "Sous_traitants": 15,
        "Interimaires": 18, "Preparation": 20, "Sante": 17,
        "EvRP": 20, "Formation": 28, "Responsabilites": 29, "Management": 27
    }
    
    total_calcule = sum(questions_per_principe.values())
    if total_calcule != total_questions:
        facteur = total_questions / total_calcule
        for key in questions_per_principe:
            questions_per_principe[key] = round(questions_per_principe[key] * facteur)
        diff = total_questions - sum(questions_per_principe.values())
        last_key = list(questions_per_principe.keys())[-1]
        questions_per_principe[last_key] += diff
    
    debut = 0
    questions_par_principe = {}
    for principe, nb_questions in questions_per_principe.items():
        fin = debut + nb_questions - 1
        questions_par_principe[principe] = list(range(debut, fin + 1))
        debut = fin + 1
    
    paliers_data = {}
    for principe in questions_par_principe.keys():
        paliers_data[principe] = []
    
    for i in range(len(df_clean)):
        row_data = df_clean.iloc[i]
        for principe in questions_par_principe.keys():
            palier = calculate_palier_hierarchique(row_data, principe, questions_par_principe)
            paliers_data[principe].append(palier)
    
    paliers_df = pd.DataFrame(paliers_data)

    # ════════════════════════════════════════════════════════════
    # ONGLETS
    # ════════════════════════════════════════════════════════════
    if is_medecin(current_mode):
        tabs = st.tabs(["Vue d'ensemble"])
    else:
        tabs = st.tabs(["Vue d'ensemble"])

    with tabs[0]:
        render_tab_overview(df_clean, paliers_df, questions_par_principe)
    # ════════════════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(f'<p style="text-align:center;color:#9CA3AF;font-size:0.8rem;font-family:\'Plus Jakarta Sans\',sans-serif;">{PAGE_TITLE} — YODAN Analytics © 2026</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()