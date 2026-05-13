# =============================================================================
# 6_WHO_PSS10.py — WHO-5 · PSS-10 — Bien-être & Stress Perçu
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
# CONFIGURATION DE LA PAGE
# =============================================================================
PAGE_TITLE = "WHO-5 · PSS-10 — Bien-être & Stress Perçu"
PAGE_ICON = "🧘"
PAGE_KEY = "who5_pss10_view_mode"

# ══════════════════════════════════════════════════════════
# QUESTIONS PSS-10 (détectées via fuzzy matching)
# ══════════════════════════════════════════════════════════
PSS_ITEMS = {
    "Q1": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_ete_contrarie_par_un_evenement_inattendu",
    "Q2": "au_cours_du_dernier_mois_a_quelle_frequence_vous_etes_vous_senti_incable_de_controler_les_choses_importantes_dans_votre_vie",
    "Q3": "au_cours_du_dernier_mois_a_quelle_frequence_vous_etes_vous_senti_nerveux_ou_stresse",
    "Q4": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_eu_le_sentiment_de_bien_maitriser_les_choses",
    "Q5": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_senti_que_les_difficultes_s_accumulaient_au_point_de_ne_plus_pouvoir_les_surmonter",
    "Q6": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_eu_confiance_en_votre_capacite_a_resoudre_vos_problemes_personnels",
    "Q7": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_estime_que_les_choses_allaient_comme_vous_le_vouliez",
    "Q8": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_eu_le_sentiment_que_vous_ne_pouviez_pas_maitriser_toutes_les_choses_que_vous_aviez_a_faire",
    "Q9": "au_cours_du_dernier_mois_a_quelle_frequence_avez_vous_pu_controler_vos_difficultes",
    "Q10": "au_cours_du_dernier_mois_a_quelle_frequence_vous_etes_vous_senti_depasse_par_les_evenements",
}

# Items inversés (Q4, Q5, Q7, Q8)
PSS_INVERTED = ["Q4", "Q5", "Q7", "Q8"]

# ══════════════════════════════════════════════════════════
# VARIABLES UNIFORMES POUR LES ANALYSES UNIVARIÉES
# ══════════════════════════════════════════════════════════
VARIABLES_UNIVARIEES = [
    ("Genre", "genre"),
    ("Situation matrimoniale", "situation_matrimoniale"),
    ("Tranche d'âge", "Tranche_dage"),
    ("Tranche ancienneté", "Tranche_anciennete"),
    ("Catégorie IMC", "Categorie_IMC"),
    ("IMC (normal/surpoids)", "IMC_binaire"),
    ("Direction", "direction"),
    ("Fonction", "fonction"),
    ("Service", "service"),
    ("Département", "departement"),
    ("Tabagisme", "tabagisme"),
    ("Consommation d'alcool", "consommation_alcool"),
    ("Maladie chronique", "maladie_chronique"),
    ("Handicap physique", "handicap_physique"),
    ("Suivi psychologique", "suivi_psychologique"),
    ("Pratique sportive", "pratique_sport"),
]

VARIABLES_SPECIFIQUES = [
    ("Niveau de stress (PSS-10)", "niveau_stress"),
]

# =============================================================================
# CSS INLINE DE LA PAGE
# =============================================================================
def get_page_css() -> str:
    return """
    <style>
        .stress-box {
            background: #FFFFFF;
            border: 1px solid #E3EAF4;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
    </style>
    """

# =============================================================================
# FONCTIONS UTILITAIRES DE NETTOYAGE (STANDARDISÉES)
# =============================================================================

def _pp_normalize_text(text: str) -> str:
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _find_by_patterns(columns: list, patterns: list) -> str | None:
    for col in columns:
        normalized_col = _pp_normalize_text(col)
        for pattern in patterns:
            if re.search(pattern, normalized_col):
                return col
    return None


def _find_age_numeric_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        col_norm = _pp_normalize_text(col)
        if "tranche" in col_norm:
            continue
        if re.search(r"\bage\b", col_norm):
            series = df[col]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            vals = pd.to_numeric(series, errors="coerce")
            if not vals.dropna().empty:
                return col
    return None


def clean_common_variables(df: pd.DataFrame, missing_threshold: float = 0.55) -> tuple:
    """Nettoyage standardisé pour toutes les pages."""
    cleaned_df = df.copy()
    ops = []

    _PII_PATTERNS = [
        r"\bnom\b", r"\bprenom", r"\be[- ]?mail\b", r"\bmail\b", r"\bcourriel\b",
        r"\btelephone\b", r"\btel\b", r"\bphone\b", r"\bcommentaire",
        r"\bobservation", r"\bremarque", r"\bnumero\b", r"\bidentifiant\b", r"\bid\b",
    ]
    _pii_dropped = []
    for col in list(cleaned_df.columns):
        col_norm = _pp_normalize_text(col)
        if any(re.search(pat, col_norm) for pat in _PII_PATTERNS):
            cleaned_df = cleaned_df.drop(columns=[col])
            _pii_dropped.append(str(col))
    if _pii_dropped:
        ops.append(f"Colonnes PII supprimées ({len(_pii_dropped)})")

    missing_ratio = cleaned_df.isna().mean()
    cols_to_drop = missing_ratio[missing_ratio > missing_threshold].index.tolist()
    if cols_to_drop:
        for c in cols_to_drop:
            ops.append(f"Colonne '{c}' supprimée ({missing_ratio[c]*100:.1f}% NA)")
        cleaned_df = cleaned_df.drop(columns=cols_to_drop)

    # ÂGE
    age_col = _find_age_numeric_col(cleaned_df)
    if age_col is not None:
        cleaned_df['age'] = pd.to_numeric(cleaned_df[age_col], errors="coerce")
        ops.append(f"Colonne 'age' créée depuis: {age_col}")
        age_vals = pd.to_numeric(cleaned_df['age'], errors="coerce")
        cleaned_df['Tranche_dage'] = pd.cut(
            age_vals, bins=[0, 30, 40, 50, float("inf")],
            labels=["20-30 ans", "31-40 ans", "41-50 ans", "51 ans et plus"], right=True
        )
        ops.append("Colonne 'Tranche_dage' créée")
    else:
        tranche_age_col = _find_by_patterns(list(cleaned_df.columns), [r"tranche.*age", r"tranche.*âge", r"classe.*age"])
        if tranche_age_col is not None:
            if tranche_age_col != 'Tranche_dage':
                cleaned_df['Tranche_dage'] = cleaned_df[tranche_age_col].astype(str)
                cleaned_df = cleaned_df.drop(columns=[tranche_age_col])
                ops.append(f"Colonne '{tranche_age_col}' renommée en 'Tranche_dage'")
        else:
            ops.append("Âge: aucune colonne trouvée")

    # ANCIENNETÉ
    anciennete_num_col = _find_by_patterns(list(cleaned_df.columns), [r"anciennete", r"anciennet"])
    if anciennete_num_col is not None:
        if pd.api.types.is_numeric_dtype(cleaned_df[anciennete_num_col]):
            cleaned_df['anciennete'] = pd.to_numeric(cleaned_df[anciennete_num_col], errors="coerce")
            ops.append("Colonne 'anciennete' créée")
        else:
            cleaned_df['Tranche_anciennete'] = cleaned_df[anciennete_num_col].astype(str)
            ops.append("Colonne 'Tranche_anciennete' créée")
    else:
        tranche_anc_col = _find_by_patterns(list(cleaned_df.columns), [r"tranche.*anciennete", r"tranche.*ancienneté"])
        if tranche_anc_col is not None:
            cleaned_df['Tranche_anciennete'] = cleaned_df[tranche_anc_col].astype(str)
            ops.append("Colonne 'Tranche_anciennete' conservée")
        else:
            ops.append("Ancienneté: aucune colonne trouvée")

    if 'anciennete' in cleaned_df.columns and 'Tranche_anciennete' not in cleaned_df.columns:
        anc_num = pd.to_numeric(cleaned_df['anciennete'], errors="coerce")
        cleaned_df['Tranche_anciennete'] = pd.cut(
            anc_num, bins=[-1, 2, 5, 10, 20, np.inf],
            labels=["0-2 ans", "3-5 ans", "6-10 ans", "11-20 ans", "21 ans et +"]
        )
        ops.append("Colonne 'Tranche_anciennete' créée")

    # GENRE
    genre_col = _find_by_patterns(list(cleaned_df.columns), [r"\bgenre\b", r"\bsexe\b"])
    if genre_col is not None:
        def std_genre(v):
            if pd.isna(v): return np.nan
            vl = str(v).strip().lower()
            if vl in ['homme', 'h', 'male', 'masculin', 'm', 'hommes']: return 'homme'
            elif vl in ['femme', 'f', 'female', 'féminin', 'feminin', 'femmes']: return 'femme'
            return vl
        cleaned_df['genre'] = cleaned_df[genre_col].apply(std_genre)
        ops.append(f"Colonne 'genre' standardisée depuis: {genre_col}")

    # IMC
    poids_col = _find_by_patterns(list(cleaned_df.columns), [r"\bpoids\b"])
    taille_col = _find_by_patterns(list(cleaned_df.columns), [r"\btaille\b"])
    if poids_col is not None and taille_col is not None:
        poids_vals = pd.to_numeric(cleaned_df[poids_col], errors="coerce")
        taille_vals = pd.to_numeric(cleaned_df[taille_col], errors="coerce")
        taille_positive = taille_vals[taille_vals > 0]
        taille_m = taille_vals / 100.0 if (not taille_positive.empty and float(taille_positive.median()) > 3) else taille_vals
        imc_vals = (poids_vals / taille_m ** 2).replace([np.inf, -np.inf], np.nan)
        cleaned_df['imc'] = imc_vals
        cleaned_df['Categorie_IMC'] = pd.cut(
            imc_vals, bins=[0, 18.5, 25, 30, 200],
            labels=["Insuffisance pondérale", "Corpulence normale", "Surpoids", "Obésité"], include_lowest=True
        )
        cleaned_df['IMC_binaire'] = np.where(
            cleaned_df['Categorie_IMC'].isin(["Insuffisance pondérale", "Corpulence normale"]),
            "Normal", np.where(cleaned_df['Categorie_IMC'].isna(), None, "Surpoids/Obésité")
        )
        ops.append("Colonne 'imc', 'Categorie_IMC' et 'IMC_binaire' calculées")

    # COLONNES ORGANISATIONNELLES
    for std_name, patterns in [
        ('direction', [r"direction"]), ('fonction', [r"fonction"]),
        ('service', [r"service"]), ('departement', [r"departement", r"département", r"dept"]),
    ]:
        if std_name not in cleaned_df.columns:
            found = _find_by_patterns(list(cleaned_df.columns), patterns)
            if found is not None:
                cleaned_df[std_name] = cleaned_df[found].astype(str)
                ops.append(f"Colonne '{std_name}' détectée: {found}")

    # FACTEURS DE RISQUE
    for std_name, patterns in [
        ('tabagisme', [r"tabag", r"tabac", r"fumeur"]),
        ('consommation_alcool', [r"alcool", r"consommation.*alcool"]),
        ('maladie_chronique', [r"maladie.*chron", r"chron.*maladie", r"hta", r"diabet"]),
        ('pratique_sport', [r"sport", r"activite.*physique", r"pratique.*sport"]),
        ('situation_matrimoniale', [r"situation.*matrimon", r"matrimon", r"etat.*civil"]),
        ('handicap_physique', [r"handicap.*physique", r"handicap"]),
        ('suivi_psychologique', [r"suivi.*psycho", r"probleme.*psycho", r"psy"]),
    ]:
        if std_name not in cleaned_df.columns:
            found = _find_by_patterns(list(cleaned_df.columns), patterns)
            if found is not None:
                cleaned_df[std_name] = cleaned_df[found]
                ops.append(f"Colonne '{std_name}' détectée: {found}")

    n_before_drop = len(cleaned_df)
    cleaned_df = cleaned_df.dropna()
    n_after_drop = len(cleaned_df)
    n_dropped = n_before_drop - n_after_drop
    if n_dropped > 0:
        ops.append(f"{n_dropped} observation(s) supprimée(s) — {n_after_drop} restantes")
    else:
        ops.append(f"✅ Aucune observation avec valeurs manquantes — {n_after_drop} observations conservées")

    cleaning_log = "Nettoyage appliqué:\n- " + "\n- ".join(ops) if ops else "Aucune opération appliquée."
    return cleaned_df, cleaning_log


# =============================================================================
# FONCTIONS DE DÉTECTION PSS-10
# =============================================================================

def trouver_colonne_pss(df: pd.DataFrame, item_key: str) -> str | None:
    """Trouve la colonne correspondant à un item PSS-10."""
    question_text = PSS_ITEMS.get(item_key)
    if question_text is None:
        return None
    
    # Chercher d'abord par nom exact
    if question_text in df.columns:
        return question_text
    
    # Chercher par pattern Q1..Q10
    for col in df.columns:
        col_norm = _pp_normalize_text(col)
        if item_key.lower() in col_norm:
            return col
    
    # Fuzzy matching
    target = _pp_normalize_text(question_text)
    best_col = None
    best_score = -1.0
    for col in df.columns:
        col_norm = _pp_normalize_text(col)
        score = SequenceMatcher(None, target, col_norm).ratio()
        if score > best_score:
            best_score = score
            best_col = col
    return best_col if (best_col is not None and best_score >= 0.4) else None


def compute_pss_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le score PSS-10 avec inversion des items positifs."""
    out = df.copy()
    
    # Résoudre les colonnes
    pss_cols = {}
    for key in PSS_ITEMS:
        col = trouver_colonne_pss(out, key)
        if col:
            pss_cols[key] = col
            out[f"pss_{key}"] = pd.to_numeric(out[col], errors="coerce")
    
    if not pss_cols:
        return out
    
    # Inverser les items positifs (Q4, Q5, Q7, Q8)
    for inv_key in PSS_INVERTED:
        if inv_key in pss_cols:
            out[f"pss_{inv_key}"] = 4 - out[f"pss_{inv_key}"]
    
    # Calculer le score total
    score_cols = [f"pss_{k}" for k in pss_cols]
    out["score_stress"] = out[score_cols].sum(axis=1)
    
    # Catégoriser le niveau de stress
    def cat_stress(s):
        if pd.isna(s):
            return "Non défini"
        if s >= 27:
            return "Stress sévère"
        elif s >= 20:
            return "Stress modéré"
        else:
            return "Stress faible"
    
    out["niveau_stress"] = out["score_stress"].apply(cat_stress)
    
    return out


# =============================================================================
# COMPOSANTS KPI STANDARDS
# =============================================================================

def kpi_card(icon_class: str, icon_color: str, icon_bg: str, accent_color: str,
            value, suffix: str, subtitle: str, label: str) -> str:
    return f"""<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;padding:20px 16px 16px;text-align:center;box-shadow:0 2px 12px rgba(15,23,42,0.06);border-top:3px solid {accent_color};transition:transform 0.2s ease,box-shadow 0.2s ease;min-height:160px;display:flex;flex-direction:column;justify-content:space-between;" onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 24px {accent_color}30';" onmouseout="this.style.transform='none';this.style.boxShadow='0 2px 12px rgba(15,23,42,0.06)';"><div><div style="width:40px;height:40px;background:{icon_bg};border-radius:10px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;"><i class="{icon_class}" style="color:{icon_color};font-size:16px;"></i></div><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;margin:0 0 6px 0;">{label}</p></div><div><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:28px;font-weight:800;color:#0F172A;margin:0;line-height:1;letter-spacing:-0.03em;">{value}<span style="font-size:13px;font-weight:500;color:#94A3B8;">{suffix}</span></p><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:11px;color:#94A3B8;margin:4px 0 0 0;">{subtitle}</p></div></div>"""


def _compute_cardio_risk(df: pd.DataFrame) -> tuple:
    n = max(len(df), 1)
    score = 0.0
    if 'imc' in df.columns:
        imc = pd.to_numeric(df['imc'], errors='coerce')
        score += float((imc >= 25).sum() / n) * 1.0 + float((imc >= 30).sum() / n) * 2.0
    for col, val, w in [('tabagisme', 'oui', 2.0), ('consommation_alcool', 'oui', 1.0),
                        ('maladie_chronique', 'oui', 2.0), ('pratique_sport', 'non', 1.0)]:
        if col in df.columns:
            s = df[col].astype(str).str.lower().str.strip()
            score += float((s.isin(['oui', 'yes', '1', 'vrai', 'true'])).sum() / n) * w
    score = round(score, 2)
    if score <= 1.5: return score, "Faible", "#16A37F"
    elif score <= 3.0: return score, "Modéré", "#F5A623"
    else: return score, "Élevé", "#E8504A"


def render_kpi_row(df: pd.DataFrame, n_before_cleaning: int = None) -> None:
    n = len(df)
    if n_before_cleaning is None:
        n_before_cleaning = n

    # ÂGE
    if 'age' in df.columns:
        age_num = pd.to_numeric(df['age'], errors='coerce').dropna()
        if not age_num.empty:
            age_display = f"{int(round(age_num.median()))} ans"
            age_subtitle = "Âge médian"
        else:
            age_display, age_subtitle = "—", "non disponible"
    elif 'Tranche_dage' in df.columns:
        age_str = df['Tranche_dage'].astype(str).str.strip()
        age_clean = age_str[~age_str.str.lower().isin(['non renseigné','nan','','none'])]
        if not age_clean.empty:
            vc = age_clean.value_counts()
            age_display = vc.index[0]
            age_subtitle = f"Classe dominante ({(vc.iloc[0]/len(age_clean))*100:.0f}%)"
        else:
            age_display, age_subtitle = "—", "non disponible"
    else:
        age_display, age_subtitle = "—", "non disponible"

    if 'Tranche_anciennete' in df.columns:
        anc_str = df['Tranche_anciennete'].astype(str).str.strip()
        anc_clean = anc_str[~anc_str.str.lower().isin(['non renseigné', 'nan', '', 'none'])]
        if not anc_clean.empty:
            vc = anc_clean.value_counts()
            anc_display, anc_subtitle = vc.index[0], f"Classe dominante ({(vc.iloc[0]/len(anc_clean))*100:.0f}%)"
        else:
            anc_display, anc_subtitle = "—", "non disponible"
    elif 'anciennete' in df.columns:
        anc_num = pd.to_numeric(df['anciennete'], errors='coerce').dropna()
        anc_display = f"{round(anc_num.median())} ans" if not anc_num.empty else "—"
        anc_subtitle = "médiane" if not anc_num.empty else "non disponible"
    else:
        anc_display, anc_subtitle = "—", "non disponible"

    if 'genre' in df.columns:
        genre_clean = df['genre'].dropna()
        if not genre_clean.empty:
            nb_h = int((genre_clean == 'homme').sum())
            nb_f = int((genre_clean == 'femme').sum())
            if nb_h >= nb_f:
                genre_display, genre_subtitle = f"{(nb_h/n)*100:.0f}%", f"Hommes ({nb_h})"
                genre_icon, genre_color, genre_bg = "fas fa-male", "#1D78F5", "#EBF3FF"
            else:
                genre_display, genre_subtitle = f"{(nb_f/n)*100:.0f}%", f"Femmes ({nb_f})"
                genre_icon, genre_color, genre_bg = "fas fa-female", "#EC4899", "#FCE7F3"
        else:
            genre_display, genre_subtitle, genre_icon, genre_color, genre_bg = "—", "non disponible", "fas fa-venus-mars", "#94A3B8", "#F1F5F9"
    else:
        genre_display, genre_subtitle, genre_icon, genre_color, genre_bg = "—", "non disponible", "fas fa-venus-mars", "#94A3B8", "#F1F5F9"

    cardio_score, cardio_label, cardio_color = _compute_cardio_risk(df)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi_card("fas fa-users", "#1D78F5", "#EBF3FF", "#1D78F5", n, "", f"sur {n_before_cleaning} observations", "Répondants analysés"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(genre_icon, genre_color, genre_bg, genre_color, genre_display, "", genre_subtitle, "Genre dominant"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("fas fa-calendar-alt", "#16A37F", "#E8F8EF", "#16A37F", age_display, "", age_subtitle, "Âge"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("fas fa-clock", "#F5A623", "#FEF5E7", "#F5A623", anc_display, "", anc_subtitle, "Ancienneté"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("fas fa-heart", cardio_color, "#FEF0EF", cardio_color, cardio_label, "", f"Score {cardio_score:.1f}/5", "Risque cardio-vasc."), unsafe_allow_html=True)


# =============================================================================
# FONCTIONS INDICATEURS
# =============================================================================

def get_priority_info(priorite_type: str) -> tuple:
    if priorite_type == "risque": return "#EF4444", "Risque prioritaire", "#EF4444"
    elif priorite_type == "levier": return "#22C55E", "Levier performance", "#22C55E"
    elif priorite_type == "vigilance": return "#F59E0B", "Vigilance", "#F59E0B"
    elif priorite_type == "strategique": return "#3B82F6", "Stratégique", "#3B82F6"
    elif priorite_type == "protecteur": return "#22C55E", "Levier protecteur", "#22C55E"
    return "#6B7280", "", "#6B7280"


def render_indicator_card(nom: str, valeur, seuil, operateur: str, priorite_type: str) -> str:
    if valeur is None:
        return '<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:12px;padding:16px;text-align:center;min-height:170px;display:flex;align-items:center;justify-content:center;"><p style="color:#94A3B8;font-size:0.85rem;">Données<br>insuffisantes</p></div>'
    bordure_color, priorite_texte, priorite_color = get_priority_info(priorite_type)
    valeur_color = bordure_color
    priorite_bg = bordure_color + "18"
    seuil_str = f"Seuil {operateur} {seuil}" if seuil is not None else ""
    valeur_str = str(valeur)
    taille_police = "36px" if len(valeur_str) <= 10 else "22px"
    return f'<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;padding:20px 14px 16px;text-align:center;box-shadow:0 2px 10px rgba(15,23,42,0.06);border-top:4px solid {bordure_color};min-height:190px;display:flex;flex-direction:column;justify-content:space-between;"><div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:14px;font-weight:700;color:#1E293B;margin:0;line-height:1.3;">{nom}</p></div><div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:{taille_police};font-weight:800;color:{valeur_color};margin:8px 0;line-height:1;">{valeur}</p><span style="display:inline-block;padding:4px 14px;border-radius:999px;font-size:10px;font-weight:600;color:{priorite_color};background:{priorite_bg};margin:8px 0 4px;">{priorite_texte}</span><p style="font-size:9px;color:#94A3B8;margin:0 0 6px;">{seuil_str}</p></div></div>'


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
    df.columns = [str(col).strip() for col in df.columns]
    return df


# =============================================================================
# FONCTIONS DE RENDU PAR ONGLET
# =============================================================================

def render_tab_overview(df, mode, n_before):
    """Onglet Vue d'ensemble - KPIs et indicateurs WHO-5 · PSS-10."""
    st.markdown('<div class="section-title">Données Générales de la Population</div>', unsafe_allow_html=True)
    render_kpi_row(df, n_before_cleaning=n_before)

    n = len(df)
    
    # Calculs PSS-10
    score_moyen = df["score_stress"].mean() if "score_stress" in df.columns else None
    pct_severe = (df["niveau_stress"] == "Stress sévère").sum() / n * 100 if "niveau_stress" in df.columns else None
    
    # Sentiment de contrôle (moyenne des items inversés normalisée)
    controle_cols = [c for c in df.columns if c.startswith("pss_Q") and c[-1] in ["4", "5", "7", "8"]]
    controle_moyen = df[controle_cols].mean().mean() if controle_cols else None
    controle_pct = (1 - controle_moyen / 4) * 100 if controle_moyen is not None else None

    # ══════════════════════════════════════════════════════════
    # INDICATEURS RH/DG
    # ══════════════════════════════════════════════════════════
    if is_rh(mode):
        st.markdown('<div class="section-title">Indicateurs RH/DG</div>', unsafe_allow_html=True)

        indicateurs_rh = [
            {"nom": "Score stress perçu moyen (PSS-10)", "valeur": f"{score_moyen:.1f}/40" if score_moyen is not None else "N/A", "seuil": "> 20/40", "priorite_type": "risque"},
            {"nom": "% stress sévère (PSS ≥ 27)", "valeur": f"{pct_severe:.1f}%" if pct_severe is not None else "N/A", "seuil": "> 10% OMS", "priorite_type": "risque"},
            {"nom": "Sentiment de contrôle perçu", "valeur": f"{controle_pct:.1f}%" if controle_pct is not None else "N/A", "seuil": "< 50%", "priorite_type": "vigilance"},
            {"nom": "WHO-5 bien-être moyen", "valeur": "N/A", "seuil": "< 50/100", "priorite_type": "vigilance"},
            {"nom": "Évolution entre vagues (Δ T1→T2)", "valeur": "N/A", "seuil": "Δ > 5 = signal", "priorite_type": "strategique"},
        ]
        cols = st.columns(5)
        for i, indic in enumerate(indicateurs_rh):
            with cols[i]:
                st.markdown(render_indicator_card(indic["nom"], indic["valeur"], indic["seuil"], "", indic["priorite_type"]), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # INDICATEURS MÉDECIN
    # ══════════════════════════════════════════════════════════
    if is_medecin(mode):
        st.markdown('<div class="section-title">Indicateurs Médecin du Travail</div>', unsafe_allow_html=True)

        # WHO-5 < 28 prévalence détresse
        who5_detresse = "N/A"  # À calculer si colonnes WHO-5 disponibles
        
        # PSS ≥ 27 stress sévère clinique
        pss_severe_clinique = f"{pct_severe:.1f}%" if pct_severe is not None else "N/A"
        
        # Item Q5 PSS (accumulation difficultés) ≥ 3
        q5_col = trouver_colonne_pss(df, "Q5")
        if q5_col:
            q5_vals = pd.to_numeric(df[q5_col], errors="coerce")
            pct_q5_eleve = (q5_vals >= 3).sum() / max(q5_vals.notna().sum(), 1) * 100
            q5_display = f"{pct_q5_eleve:.1f}%"
        else:
            q5_display = "N/A"
        
        # Stress × comportements à risque
        if "score_stress" in df.columns and "tabagisme" in df.columns:
            tabac_oui = df["tabagisme"].astype(str).str.lower().isin(['oui', 'yes', '1', 'vrai', 'true'])
            stress_tabac = ((df["score_stress"] >= 20) & tabac_oui).sum() / max(n, 1) * 100
            stress_tabac_display = f"{stress_tabac:.1f}%"
        else:
            stress_tabac_display = "N/A"

        indicateurs_med = [
            {"nom": "WHO-5 < 28 — prévalence détresse", "valeur": who5_detresse, "seuil": "Tout cas < 28", "priorite_type": "risque"},
            {"nom": "PSS ≥ 27 — stress sévère clinique", "valeur": pss_severe_clinique, "seuil": "Tout cas ≥ 27", "priorite_type": "risque"},
            {"nom": "Item Q5 PSS (accumulation difficultés)", "valeur": q5_display, "seuil": "> 30%", "priorite_type": "risque"},
            {"nom": "Stress × comportements à risque", "valeur": stress_tabac_display, "seuil": "> 15%", "priorite_type": "vigilance"},
            {"nom": "Suivi longitudinal PSS (Δ T1→T2)", "valeur": "N/A", "seuil": "Δ > 3 = signal", "priorite_type": "vigilance"},
        ]
        cols = st.columns(5)
        for i, indic in enumerate(indicateurs_med):
            with cols[i]:
                st.markdown(render_indicator_card(indic["nom"], indic["valeur"], indic["seuil"], "", indic["priorite_type"]), unsafe_allow_html=True)


def render_tab_analyse(df, mode):
    """Onglet Analyse univariée."""
    st.markdown('<div class="section-title">Analyse univariée</div>', unsafe_allow_html=True)

    VAR_OPTIONS = {}
    for label, col in VARIABLES_SPECIFIQUES + VARIABLES_UNIVARIEES:
        if col in df.columns:
            VAR_OPTIONS[label] = col

    if not VAR_OPTIONS:
        st.info("Aucune variable disponible.")
        return

    c_sel, _ = st.columns([1, 2])
    with c_sel:
        sel_label = st.selectbox("Variable à visualiser", list(VAR_OPTIONS.keys()), key="uni_who5")
    sel_col = VAR_OPTIONS.get(sel_label)

    if sel_col and sel_col in df.columns:
        counts_u = df[sel_col].value_counts()
        total_u = counts_u.sum()
        pcts_u = (counts_u / total_u * 100).round(1)
        n_bars = len(counts_u)

        stats_data = [{"Modalité": str(cat), "Effectif": int(eff), "Fréquence": f"{pct:.1f}%"} for cat, eff, pct in zip(counts_u.index, counts_u.values, pcts_u.values)]
        stats_data.append({"Modalité": "TOTAL", "Effectif": int(total_u), "Fréquence": "100%"})

        c_chart, c_table = st.columns([7, 3])
        with c_chart:
            pal = ["#38A3E8", "#F97316", "#22C55E", "#EF4444", "#A78BFA", "#06B6D4", "#FB923C", "#84CC16", "#EC4899", "#8B5CF6"]
            stress_colors = {"Stress faible": "#22C55E", "Stress modéré": "#F59E0B", "Stress sévère": "#EF4444"}

            fig = go.Figure()
            for i, (cat, pct, eff) in enumerate(zip(counts_u.index, pcts_u.values, counts_u.values)):
                bar_color = stress_colors.get(str(cat), pal[i % len(pal)]) if sel_col == "niveau_stress" else pal[i % len(pal)]
                fig.add_trace(go.Bar(y=[str(cat)], x=[pct], orientation='h', marker_color=bar_color, marker=dict(opacity=0.9, line=dict(width=0)), text=f"{pct:.1f}%  ({int(eff)})", textposition="outside", textfont=dict(color="#6B88A8", size=12, family="Plus Jakarta Sans"), showlegend=False))

            fig.update_layout(plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans, sans-serif", color="#0F2340", size=12), xaxis=dict(range=[0, max(pcts_u.values)*1.5], title_text="Pourcentage (%)", showgrid=True, gridcolor="#EDF5FD", gridwidth=1, showline=True, linecolor="#D6E8F7", zeroline=False, tickfont=dict(color="#6B88A8", size=11)), yaxis=dict(showgrid=False, showline=False, zeroline=False, tickfont=dict(color="#0F2340", size=11)), height=max(300, n_bars*55+120), margin=dict(l=20, r=80, t=60, b=40), title=dict(text=f"Répartition selon : {sel_label}", font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"), x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True, key="uni_who5_plotly")

        with c_table:
            st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Statistiques</p>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True, height=min(400, 35*(len(stats_data)+1)))

            st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">💡 Interprétation</p>', unsafe_allow_html=True)
            modalites = list(counts_u.index)
            if len(modalites) >= 2:
                m1, m2 = modalites[0], modalites[1]
                st.markdown(f'<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;font-family:\'Plus Jakarta Sans\',sans-serif;"><p style="margin:0 0 8px;">Ce graphique montre la répartition de <b>{sel_label}</b> parmi les {int(total_u)} répondants.</p><p style="margin:0 0 8px;">La modalité dominante est <b>« {m1} »</b> avec <b>{pcts_u.iloc[0]:.1f}%</b> des répondants ({int(counts_u.iloc[0])} personne(s)).</p><p style="margin:0;">Elle est suivie par <b>« {m2} »</b> avec <b>{pcts_u.iloc[1]:.1f}%</b> ({int(counts_u.iloc[1])} personne(s)). Au total, <b>{n_bars}</b> modalités.</p></div>', unsafe_allow_html=True)
            else:
                st.caption("Données insuffisantes.")


def render_tab_croisement(df, mode):
    """Onglet Analyse bivariée."""
    st.markdown('<div class="section-title">Analyse bivariée</div>', unsafe_allow_html=True)

    VAR_CROISE = {label: col for label, col in VARIABLES_UNIVARIEES if col in df.columns}
    
    OUTCOME_MAP = {}
    if "niveau_stress" in df.columns:
        OUTCOME_MAP["Niveau de stress"] = "niveau_stress"
    if "score_stress" in df.columns:
        df["score_stress_cat"] = pd.cut(df["score_stress"], bins=[-1, 13, 26, 40], labels=["Faible (0-13)", "Modéré (14-26)", "Sévère (27-40)"])
        OUTCOME_MAP["Score PSS-10 (catégoriel)"] = "score_stress_cat"
    
    OUTCOME_OPTIONS = {k: v for k, v in OUTCOME_MAP.items() if v in df.columns}

    if not VAR_CROISE or not OUTCOME_OPTIONS:
        st.info("Variables insuffisantes pour l'analyse bivariée.")
        return

    cx1, cx2 = st.columns(2)
    with cx1:
        sel_var = st.selectbox("Variable démographique", list(VAR_CROISE.keys()), key="bivar_var")
    with cx2:
        sel_outcome = st.selectbox("Variable de résultat", list(OUTCOME_OPTIONS.keys()), key="bivar_outcome")

    var_col, out_col = VAR_CROISE.get(sel_var), OUTCOME_OPTIONS.get(sel_outcome)
    if var_col and out_col and var_col in df.columns and out_col in df.columns:
        tmp = df[[var_col, out_col]].dropna()
        if not tmp.empty:
            ct = pd.crosstab(tmp[var_col].astype(str), tmp[out_col].astype(str))
            pct = ct.div(ct.sum(axis=1), axis=0) * 100

            c_chart, c_table = st.columns([7, 3])
            with c_chart:
                colors_map = {"Stress faible": "#22C55E", "Stress modéré": "#F59E0B", "Stress sévère": "#EF4444",
                             "Faible (0-13)": "#22C55E", "Modéré (14-26)": "#F59E0B", "Sévère (27-40)": "#EF4444"}
                gen_pal = ["#38A3E8", "#F97316", "#22C55E", "#EF4444", "#A78BFA", "#06B6D4", "#FB923C", "#84CC16"]

                fig = go.Figure()
                for i, cat in enumerate(pct.columns):
                    vals, ns = pct[cat].values, ct[cat].values
                    txts = [f"{v:.1f}%  ({n})" if v >= 5 else "" for v, n in zip(vals, ns)]
                    color = colors_map.get(str(cat), gen_pal[i % len(gen_pal)])
                    fig.add_trace(go.Bar(name=str(cat), y=list(pct.index), x=vals, orientation='h', marker_color=color, marker=dict(opacity=0.9, line=dict(width=0)), text=txts, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", size=11, family="Plus Jakarta Sans")))

                fig.update_layout(barmode="stack", plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans, sans-serif", color="#0F2340", size=12), xaxis=dict(range=[0, 100], title_text="Pourcentage (%)", showgrid=True, gridcolor="#EDF5FD", gridwidth=1, showline=True, linecolor="#D6E8F7", zeroline=False, tickfont=dict(color="#6B88A8", size=11)), yaxis=dict(showgrid=False, showline=False, zeroline=False, tickfont=dict(color="#0F2340", size=11)), height=max(300, len(pct.index)*55+120), margin=dict(l=20, r=20, t=50, b=40), title=dict(text=f"{sel_var} selon {sel_outcome}", font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"), x=0.5, xanchor="center"), legend=dict(bgcolor="rgba(255,255,255,0.95)", bordercolor="#D6E8F7", borderwidth=1, font=dict(color="#0F2340", size=10), orientation="h", y=-0.30, x=0.5, xanchor="center"))
                st.plotly_chart(fig, use_container_width=True, key="bivar_plotly")

            with c_table:
                st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Tableau de distribution (%)</p>', unsafe_allow_html=True)
                st.dataframe(pct.round(1).style.format("{:.1f}%"), use_container_width=True)

                st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">💡 Interprétation</p>', unsafe_allow_html=True)
                lignes, colonnes = list(pct.index), list(pct.columns)
                if len(lignes) >= 2 and len(colonnes) >= 1:
                    l1, l2 = lignes[0], lignes[1]
                    st.markdown(f'<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;font-family:\'Plus Jakarta Sans\',sans-serif;"><p style="margin:0 0 8px;">Ce graphique montre la répartition de <b>{sel_outcome}</b> selon <b>{sel_var}</b>.</p><p style="margin:0 0 8px;">Par exemple, parmi les <b>« {l1} »</b> : {", ".join([f'<b>{pct.loc[l1, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l1, c] > 0])}.</p><p style="margin:0;">Tandis que parmi les <b>« {l2} »</b> : {", ".join([f'<b>{pct.loc[l2, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l2, c] > 0])}.</p></div>', unsafe_allow_html=True)
                else:
                    st.caption("Données insuffisantes.")


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
            f'<i class="fas fa-brain" style="color:white;font-size:15px;"></i></div>'
            f'<div><div style="font-size:16px;font-weight:700;color:#1e293b;'
            f'font-family:\'Plus Jakarta Sans\',sans-serif;">{PAGE_TITLE}</div>'
            f'<div style="font-size:11px;color:#64748b;margin-top:1px;'
            f'font-family:\'Plus Jakarta Sans\',sans-serif;">Évaluation du bien-être et du stress perçu</div>'
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
        n_before = len(df_raw)
        df_clean, cleaning_log = clean_common_variables(df_raw)

    with st.expander("📋 Journal de nettoyage", expanded=False):
        st.text(cleaning_log)
        st.write(f"Avant: **{n_before}** — Après: **{len(df_clean)}**")

    if df_clean.empty:
        st.error("Aucune donnée exploitable.")
        st.stop()

    # ════════════════════════════════════════════════════════════
    # VÉRIFICATION PSS-10
    # ════════════════════════════════════════════════════════════
    pss_trouvees = sum(1 for k in PSS_ITEMS if trouver_colonne_pss(df_clean, k) is not None)
    if pss_trouvees < 5:
        st.error(f"❌ **Fichier non reconnu** — Seulement {pss_trouvees}/10 items PSS-10 détectés.")
        st.stop()

    with st.sidebar:
        st.markdown(f"**🔍 Items PSS-10 :** {pss_trouvees}/10")

    # ════════════════════════════════════════════════════════════
    # CALCULS PSS-10
    # ════════════════════════════════════════════════════════════
    df_clean = compute_pss_scores(df_clean)

    # ════════════════════════════════════════════════════════════
    # ONGLETS
    # ════════════════════════════════════════════════════════════
    if is_medecin(current_mode):
        tabs = st.tabs(["Vue d'ensemble", "Analyse univariée", "Analyse bivariée"])
    else:
        tabs = st.tabs(["Vue d'ensemble", "Analyse univariée"])

    with tabs[0]:
        # ════════════════════════════════════════════════════════════
        # FILTRES (spécifiques à l'onglet 1)
        # ════════════════════════════════════════════════════════════
        FILTER_VARS = [
            ("Genre", "genre"),
            ("Situation matrimoniale", "situation_matrimoniale"),
            ("Tranche d'âge", "Tranche_dage"),
            ("Tranche ancienneté", "Tranche_anciennete"),
            ("Catégorie IMC", "Categorie_IMC"),
            ("IMC (normal/surpoids)", "IMC_binaire"),
            ("Direction", "direction"),
            ("Fonction", "fonction"),
            ("Service", "service"),
            ("Département", "departement"),
            ("Tabagisme", "tabagisme"),
            ("Consommation d'alcool", "consommation_alcool"),
            ("Maladie chronique", "maladie_chronique"),
            ("Handicap physique", "handicap_physique"),
            ("Suivi psychologique", "suivi_psychologique"),
            ("Pratique sportive", "pratique_sport"),
        ]
        
        cat_vars = [(l, c) for l, c in FILTER_VARS if c in df_clean.columns and not pd.api.types.is_numeric_dtype(df_clean[c])]
        num_vars = [(l, c) for l, c in FILTER_VARS if c in df_clean.columns and pd.api.types.is_numeric_dtype(df_clean[c])]
        
        # Ajouter l'âge numérique s'il existe
        if 'age' in df_clean.columns and pd.api.types.is_numeric_dtype(df_clean['age']):
            num_vars.append(("Âge", "age"))
        
        with st.expander("Filtres", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns([3, 3, 3, 1.5])
            
            with fc1:
                cat_labels = ["— Aucun —"] + [l for l, _ in cat_vars]
                sel_cat_label = st.selectbox("Variable (catégorielle)", cat_labels, key="who5_filtre_cat")
            
            with fc2:
                if sel_cat_label != "— Aucun —":
                    cat_col = dict(cat_vars)[sel_cat_label]
                    modalites = sorted(df_clean[cat_col].dropna().astype(str).unique().tolist())
                    sel_modalite = st.selectbox("Modalité", ["Toutes"] + modalites, key="who5_filtre_mod")
                else:
                    sel_modalite = "Toutes"
                    st.selectbox("Modalité", ["Toutes"], disabled=True)
            
            with fc3:
                num_labels = ["— Aucun —"] + [l for l, _ in num_vars]
                sel_num_label = st.selectbox("Variable (numérique)", num_labels, key="who5_filtre_num")
                
                if sel_num_label != "— Aucun —":
                    num_col = dict(num_vars)[sel_num_label]
                    vals = pd.to_numeric(df_clean[num_col], errors="coerce").dropna()
                    if not vals.empty:
                        vmin, vmax = int(vals.min()), int(vals.max())
                        if vmin == vmax:
                            vmax = vmin + 1
                        sel_range = st.slider(f"Plage — {sel_num_label}", vmin, vmax, (vmin, vmax), key="who5_filtre_range")
                    else:
                        sel_range = None
                        st.slider(f"Plage — {sel_num_label}", 0, 100, (0, 100), disabled=True)
                else:
                    sel_range = None
            
            with fc4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Réinitialiser", key="who5_reset_filtres", use_container_width=True):
                    for k in ["who5_filtre_cat", "who5_filtre_mod", "who5_filtre_num", "who5_filtre_range"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()
        
        # Appliquer les filtres UNIQUEMENT pour l'onglet 1
        mask = pd.Series(True, index=df_clean.index)
        
        if sel_cat_label != "— Aucun —" and sel_modalite != "Toutes":
            cat_col = dict(cat_vars)[sel_cat_label]
            mask &= df_clean[cat_col].astype(str) == sel_modalite
        
        if sel_num_label != "— Aucun —" and sel_range is not None:
            num_col = dict(num_vars)[sel_num_label]
            vals = pd.to_numeric(df_clean[num_col], errors="coerce")
            mask &= vals.between(sel_range[0], sel_range[1])
        
        df_filtered = df_clean[mask].copy()
        
        if len(df_filtered) == 0:
            st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
            st.stop()
        
        # ════════════════════════════════════════════════════════════
        # CONTENU DE L'ONGLET 1 (utilise df_filtered)
        # ════════════════════════════════════════════════════════════
        render_tab_overview(df_filtered, current_mode, n_before)
    with tabs[1]:
        render_tab_analyse(df_clean, current_mode)

    if len(tabs) > 2:
        with tabs[2]:
            render_tab_croisement(df_clean, current_mode)

    # ════════════════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(f'<p style="text-align:center;color:#9CA3AF;font-size:0.8rem;font-family:\'Plus Jakarta Sans\',sans-serif;">{PAGE_TITLE} — YODAN Analytics © 2026</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()