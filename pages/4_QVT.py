# =============================================================================
# 4_QVT.py — QVT - Qualité de Vie au Travail
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
# CONFIGURATION DE LA PAGE QVT
# =============================================================================
PAGE_TITLE = "QVT — Qualité de Vie au Travail"
PAGE_ICON = "❤️"
PAGE_KEY = "qvt_view_mode"

# ══════════════════════════════════════════════════════════
# QUESTIONS & DOMAINES QVT
# ══════════════════════════════════════════════════════════
QUESTIONS = [
    "Je comprends clairement mes missions.",
    "Je dispose des moyens nécessaires pour faire mon travail.",
    "Je peux exprimer mon point de vue au travail.",
    "Je suis reconnu(e) pour le travail bien fait.",
    "Mon travail a du sens pour moi.",
    "Je suis écouté(e) par ma hiérarchie.",
    "J'ai un bon équilibre entre vie privée et professionnelle.",
    "J'ai des relations de qualité avec mes collègues.",
    "Je peux évoluer dans mon poste.",
    "Mon environnement de travail est sain et sécurisé.",
    "J'ai des pauses suffisantes pendant ma journée.",
    "Je reçois des informations utiles pour bien travailler.",
    "Je participe aux décisions qui concernent mon travail.",
    "Mon travail est compatible avec mes valeurs.",
    "Je ressens de la fierté dans ce que je fais.",
    "Mon travail est stimulant.",
    "Les horaires sont compatibles avec ma vie personnelle.",
    "Mon manager me soutient en cas de difficulté.",
    "Je me sens à l'aise dans mon équipe.",
    "Je me sens utile dans mon organisation.",
]

RENOMMED_QUESTIONS = {
    "Je comprends clairement mes missions.": "Clarté des missions",
    "Je dispose des moyens nécessaires pour faire mon travail.": "Disponibilité des moyens nécessaires",
    "Je peux exprimer mon point de vue au travail.": "Liberté d'expression",
    "Je suis reconnu(e) pour le travail bien fait.": "Reconnaissance du travail bienfait",
    "Mon travail a du sens pour moi.": "Sens du travail personnel",
    "Je suis écouté(e) par ma hiérarchie.": "Écoute hiérarchique",
    "J'ai un bon équilibre entre vie privée et professionnelle.": "Équilibre de vie",
    "J'ai des relations de qualité avec mes collègues.": "Bonnes relations entre collègues",
    "Je peux évoluer dans mon poste.": "Évolution professionnelle",
    "Mon environnement de travail est sain et sécurisé.": "Environnement sain et sécurisé",
    "J'ai des pauses suffisantes pendant ma journée.": "Pauses suffisantes",
    "Je reçois des informations utiles pour bien travailler.": "Informations utiles",
    "Je participe aux décisions qui concernent mon travail.": "Participation aux décisions",
    "Mon travail est compatible avec mes valeurs.": "Reflète mes valeurs",
    "Je ressens de la fierté dans ce que je fais.": "Fierté au travail",
    "Mon travail est stimulant.": "Travail stimulant",
    "Les horaires sont compatibles avec ma vie personnelle.": "Horaires compatibles",
    "Mon manager me soutient en cas de difficulté.": "Soutien du manager",
    "Je me sens à l'aise dans mon équipe.": "Intégration dans l'équipe",
    "Je me sens utile dans mon organisation.": "Utilité dans l'organisation",
}

SCORE_GROUPS = {
    "Sens du Travail": [
        "Mon travail a du sens pour moi.",
        "Mon travail est compatible avec mes valeurs.",
        "Je ressens de la fierté dans ce que je fais.",
        "Mon travail est stimulant.",
        "Je me sens utile dans mon organisation.",
    ],
    "Relations Interpersonnelles": [
        "Je peux exprimer mon point de vue au travail.",
        "Je suis écouté(e) par ma hiérarchie.",
        "J'ai des relations de qualité avec mes collègues.",
        "Mon manager me soutient en cas de difficulté.",
        "Je me sens à l'aise dans mon équipe.",
    ],
    "Santé & Environnement": [
        "Je comprends clairement mes missions.",
        "Je dispose des moyens nécessaires pour faire mon travail.",
        "Mon environnement de travail est sain et sécurisé.",
        "Je reçois des informations utiles pour bien travailler.",
    ],
    "Reconnaissance & Évolution": [
        "Je suis reconnu(e) pour le travail bien fait.",
        "Je peux évoluer dans mon poste.",
        "Je participe aux décisions qui concernent mon travail.",
    ],
    "Équilibre de Vie": [
        "J'ai un bon équilibre entre vie privée et professionnelle.",
        "J'ai des pauses suffisantes pendant ma journée.",
        "Les horaires sont compatibles avec ma vie personnelle.",
    ],
}

# ══════════════════════════════════════════════════════════
# VARIABLES UNIFORMES POUR LES ANALYSES UNIVARIEES
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
    ("Niveau de satisfaction", "niveau_satisfaction"),
]

# =============================================================================
# CSS INLINE DE LA PAGE
# =============================================================================
def get_page_css() -> str:
    return """
    <style>
        .qvt-gauge {
            background: #FFFFFF;
            border: 1px solid #E3EAF4;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .qvt-gauge-label {
            font-size: 10px;
            color: #94A3B8;
            text-transform: uppercase;
            font-weight: 700;
            margin: 0 0 8px;
        }
        .qvt-gauge-value {
            font-size: 28px;
            font-weight: 800;
            margin: 0;
        }
        .qvt-gauge-sub {
            font-size: 11px;
            color: #94A3B8;
            margin: 4px 0 0;
        }
    </style>
    """

# =============================================================================
# FONCTIONS UTILITAIRES DE NETTOYAGE (STANDARDISEES)
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

    for std_name, patterns in [
        ('direction', [r"direction"]), ('fonction', [r"fonction"]),
        ('service', [r"service"]), ('departement', [r"departement", r"département", r"dept"]),
    ]:
        if std_name not in cleaned_df.columns:
            found = _find_by_patterns(list(cleaned_df.columns), patterns)
            if found is not None:
                cleaned_df[std_name] = cleaned_df[found].astype(str)
                ops.append(f"Colonne '{std_name}' détectée: {found}")

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
        ops.append(f"Aucune observation avec valeurs manquantes — {n_after_drop} observations conservées")

    cleaning_log = "Nettoyage appliqué:\n- " + "\n- ".join(ops) if ops else "Aucune opération appliquée."
    return cleaned_df, cleaning_log


# =============================================================================
# FONCTIONS DE DETECTION QVT
# =============================================================================

def normaliser_texte(texte: str) -> str:
    t = str(texte).strip().lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", t)


def trouver_colonne_qvt(df: pd.DataFrame, question_text: str) -> str | None:
    if question_text in df.columns:
        return question_text
    target = normaliser_texte(question_text)
    best_col = None
    best_score = -1.0
    for col in df.columns:
        col_norm = normaliser_texte(col)
        score = SequenceMatcher(None, target, col_norm).ratio()
        if score > best_score:
            best_score = score
            best_col = col
    return best_col if (best_col is not None and best_score >= 0.4) else None


def resolve_questions(df: pd.DataFrame) -> dict:
    return {q: trouver_colonne_qvt(df, q) for q in QUESTIONS if trouver_colonne_qvt(df, q)}


def compute_scores(df: pd.DataFrame, question_map: dict) -> pd.DataFrame:
    out = df.copy()
    for score_name, qs in SCORE_GROUPS.items():
        cols = [question_map[q] for q in qs if q in question_map]
        if cols:
            out[score_name] = out[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    q_cols = list(question_map.values())
    if q_cols:
        out["Score_Global"] = out[q_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    return out


def compute_score_normalise(df: pd.DataFrame, cols: list) -> float:
    if not cols:
        return None
    available_cols = [c for c in cols if c in df.columns]
    if not available_cols:
        return None
    valeurs = df[available_cols].apply(pd.to_numeric, errors='coerce')
    moyenne = valeurs.mean(axis=1).mean()
    return round((moyenne - 1) / 3 * 100, 1)


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
    elif score <= 3.0: return score, "Modere", "#F5A623"
    else: return score, "Eleve", "#E8504A"


def render_kpi_row(df: pd.DataFrame, n_before_cleaning: int = None) -> None:
    n = len(df)
    if n_before_cleaning is None:
        n_before_cleaning = n

    if 'age' in df.columns:
        age_num = pd.to_numeric(df['age'], errors='coerce').dropna()
        if not age_num.empty:
            age_display = f"{int(round(age_num.median()))} ans"
            age_subtitle = "Age median"
        else:
            age_display, age_subtitle = "—", "non disponible"
    elif 'Tranche_dage' in df.columns:
        age_str = df['Tranche_dage'].astype(str).str.strip()
        age_clean = age_str[~age_str.str.lower().isin(['non renseigne','nan','','none'])]
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
        anc_clean = anc_str[~anc_str.str.lower().isin(['non renseigne', 'nan', '', 'none'])]
        if not anc_clean.empty:
            vc = anc_clean.value_counts()
            anc_display, anc_subtitle = vc.index[0], f"Classe dominante ({(vc.iloc[0]/len(anc_clean))*100:.0f}%)"
        else:
            anc_display, anc_subtitle = "—", "non disponible"
    elif 'anciennete' in df.columns:
        anc_num = pd.to_numeric(df['anciennete'], errors='coerce').dropna()
        anc_display = f"{round(anc_num.median())} ans" if not anc_num.empty else "—"
        anc_subtitle = "mediane" if not anc_num.empty else "non disponible"
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
        st.markdown(kpi_card("fas fa-users", "#1D78F5", "#EBF3FF", "#1D78F5", n, "", f"sur {n_before_cleaning} observations", "Repondants analyses"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(genre_icon, genre_color, genre_bg, genre_color, genre_display, "", genre_subtitle, "Genre dominant"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("fas fa-calendar-alt", "#16A37F", "#E8F8EF", "#16A37F", age_display, "", age_subtitle, "Age"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("fas fa-clock", "#F5A623", "#FEF5E7", "#F5A623", anc_display, "", anc_subtitle, "Anciennete"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("fas fa-heart", cardio_color, "#FEF0EF", cardio_color, cardio_label, "", f"Score {cardio_score:.1f}/5", "Risque cardio-vasc."), unsafe_allow_html=True)


# =============================================================================
# FONCTIONS INDICATEURS AVEC COMPARAISON AUTOMATIQUE
# =============================================================================

def get_priority_info(priorite_type: str) -> tuple:
    if priorite_type == "risque":
        return "#EF4444", "Risque prioritaire", "#EF4444"
    elif priorite_type == "levier":
        return "#22C55E", "Levier performance", "#22C55E"
    elif priorite_type == "vigilance":
        return "#F59E0B", "Vigilance", "#F59E0B"
    elif priorite_type == "strategique":
        return "#3B82F6", "Suivi strategique", "#3B82F6"
    elif priorite_type == "protecteur":
        return "#22C55E", "Levier protecteur", "#22C55E"
    return "#6B7280", "Information", "#6B7280"


def comparer_valeur_seuil(valeur, seuil, operateur: str) -> bool:
    try:
        if isinstance(valeur, str):
            valeur_clean = valeur.replace('%', '').replace(',', '.').strip()
            val_num = float(valeur_clean)
        else:
            val_num = float(valeur)
        
        if isinstance(seuil, str):
            seuil_clean = seuil.replace('%', '').replace(',', '.').strip()
            seuil_num = float(seuil_clean)
        else:
            seuil_num = float(seuil)
        
        if operateur == ">":
            return val_num > seuil_num
        elif operateur == ">=":
            return val_num >= seuil_num
        elif operateur == "<":
            return val_num < seuil_num
        elif operateur == "<=":
            return val_num <= seuil_num
        elif operateur == "==" or operateur == "=":
            return val_num == seuil_num
        else:
            return val_num > seuil_num
    except (ValueError, TypeError):
        return False


def get_dynamic_priority(valeur, seuil: str, operateur: str, priorite_alerte: str) -> tuple:
    seuil_depasse = comparer_valeur_seuil(valeur, seuil, operateur)
    
    if seuil_depasse:
        return get_priority_info(priorite_alerte)
    else:
        return get_priority_info("levier")


def render_indicator_card(nom: str, valeur, seuil: str = None, operateur: str = "", priorite_type: str = "levier") -> str:
    if valeur is None:
        return '<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:12px;padding:16px;text-align:center;min-height:170px;display:flex;align-items:center;justify-content:center;"><p style="color:#94A3B8;font-size:0.85rem;">Donnees<br>insuffisantes</p></div>'
    
    if seuil is not None and operateur:
        bordure_color, priorite_texte, priorite_color = get_dynamic_priority(
            valeur, seuil, operateur, priorite_type
        )
    else:
        bordure_color, priorite_texte, priorite_color = get_priority_info(priorite_type)
    
    priorite_bg = bordure_color + "18"
    
    seuil_str = ""
    if seuil is not None:
        if operateur:
            seuil_str = f"Seuil {operateur} {seuil}"
        else:
            seuil_str = f"Seuil : {seuil}"
    
    valeur_str = str(valeur)
    taille_police = "36px" if len(valeur_str) <= 10 else "22px"
    
    return f'<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;padding:20px 14px 16px;text-align:center;box-shadow:0 2px 10px rgba(15,23,42,0.06);border-top:4px solid {bordure_color};min-height:190px;display:flex;flex-direction:column;justify-content:space-between;"><div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:14px;font-weight:700;color:#1E293B;margin:0;line-height:1.3;">{nom}</p></div><div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:{taille_police};font-weight:800;color:{bordure_color};margin:8px 0;line-height:1;">{valeur}</p><span style="display:inline-block;padding:4px 14px;border-radius:999px;font-size:10px;font-weight:600;color:{priorite_color};background:{priorite_bg};margin:8px 0 4px;">{priorite_texte}</span><p style="font-size:9px;color:#94A3B8;margin:0 0 6px;">{seuil_str}</p></div></div>'


# =============================================================================
# CHARGEMENT DES DONNEES
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

def render_tab_overview(df, mode, n_before, question_map):
    st.markdown('<div class="section-title">Donnees Generales de la Population</div>', unsafe_allow_html=True)
    render_kpi_row(df, n_before_cleaning=n_before)

    if is_rh(mode):
        st.markdown('<div class="section-title">Indicateurs RH/DG</div>', unsafe_allow_html=True)

        score_cols_global = [d for d in ["Sens du Travail", "Relations Interpersonnelles", "Equilibre de Vie", "Reconnaissance & Evolution", "Sante & Environnement"] if d in df.columns]
        indice_global = compute_score_normalise(df, score_cols_global)

        rel_cols = [trouver_colonne_qvt(df, q) for q in ["Je peux exprimer mon point de vue au travail.", "Je suis ecoute(e) par ma hierarchie.", "J'ai des relations de qualite avec mes collegues."]]
        qualite_rel = compute_score_normalise(df, [c for c in rel_cols if c])

        sens_cols = [trouver_colonne_qvt(df, q) for q in ["Mon travail a du sens pour moi.", "Mon travail est compatible avec mes valeurs.", "Je ressens de la fierte dans ce que je fais.", "Mon travail est stimulant.", "Je me sens utile dans mon organisation."]]
        sens_travail = compute_score_normalise(df, [c for c in sens_cols if c])

        egalite_cols = [trouver_colonne_qvt(df, q) for q in ["Je suis reconnu(e) pour le travail bien fait.", "Je participe aux decisions qui concernent mon travail."]]
        egalite_percue = compute_score_normalise(df, [c for c in egalite_cols if c])

        conditions_cols = [trouver_colonne_qvt(df, q) for q in ["Je comprends clairement mes missions.", "Je dispose des moyens necessaires pour faire mon travail.", "Mon environnement de travail est sain et securise.", "Je recois des informations utiles pour bien travailler."]]
        conditions_travail = compute_score_normalise(df, [c for c in conditions_cols if c])

        indicateurs_rh = [
            {"nom": "Indice global QVT", "valeur": f"{indice_global:.1f}" if indice_global is not None else "N/A", "seuil": "60", "operateur": "<", "priorite_type": "vigilance"},
            {"nom": "Qualite des relations de travail", "valeur": f"{qualite_rel:.1f}" if qualite_rel is not None else "N/A", "seuil": "50", "operateur": "<", "priorite_type": "vigilance"},
            {"nom": "Contenu et sens du travail", "valeur": f"{sens_travail:.1f}" if sens_travail is not None else "N/A", "seuil": "50", "operateur": "<", "priorite_type": "levier"},
            {"nom": "Egalite professionnelle percue", "valeur": f"{egalite_percue:.1f}" if egalite_percue is not None else "N/A", "seuil": "50", "operateur": "<", "priorite_type": "vigilance"},
            {"nom": "Conditions et environnement de travail", "valeur": f"{conditions_travail:.1f}" if conditions_travail is not None else "N/A", "seuil": "50", "operateur": "<", "priorite_type": "risque"},
        ]
        cols = st.columns(5)
        for i, indic in enumerate(indicateurs_rh):
            with cols[i]:
                st.markdown(render_indicator_card(
                    indic["nom"], indic["valeur"], 
                    indic["seuil"], indic.get("operateur", ""), 
                    indic["priorite_type"]
                ), unsafe_allow_html=True)

    if is_medecin(mode):
        st.markdown('<div class="section-title">Indicateurs Medecin du Travail</div>', unsafe_allow_html=True)

        adq_cols = [trouver_colonne_qvt(df, q) for q in ["Je dispose des moyens necessaires pour faire mon travail.", "Je comprends clairement mes missions."]]
        adq_score = compute_score_normalise(df, [c for c in adq_cols if c])

        if 'imc' in df.columns and 'anciennete' in df.columns:
            imc_vals = pd.to_numeric(df['imc'], errors='coerce').dropna()
            anc_vals = pd.to_numeric(df['anciennete'], errors='coerce').dropna()
            
            if not imc_vals.empty and not anc_vals.empty:
                imc_med = imc_vals.median()
                anc_med = anc_vals.median()
                
                imc_score = min(max((imc_med - 18.5) / (30 - 18.5) * 50, 0), 50)
                anc_score = min(anc_med / 20 * 50, 50)
                
                charge_score = round(imc_score + anc_score, 1)
                
                if charge_score <= 35:
                    charge_label = "Faible"
                elif charge_score <= 65:
                    charge_label = "Modere"
                else:
                    charge_label = "Eleve"
                
                charge_display = f"{charge_label}"
            else:
                charge_display = "N/A"
        else:
            charge_display = "N/A"

        conflit_cols = [trouver_colonne_qvt(df, q) for q in ["Je participe aux decisions qui concernent mon travail.", "Je comprends clairement mes missions."]]
        conflit_score = compute_score_normalise(df, [c for c in conflit_cols if c])

        equilibre_cols = [trouver_colonne_qvt(df, q) for q in ["J'ai un bon equilibre entre vie privee et professionnelle.", "J'ai des pauses suffisantes pendant ma journee.", "Les horaires sont compatibles avec ma vie personnelle."]]
        equilibre_score = compute_score_normalise(df, [c for c in equilibre_cols if c])

        equite_cols = [trouver_colonne_qvt(df, q) for q in ["Je suis reconnu(e) pour le travail bien fait.", "Je peux evoluer dans mon poste."]]
        equite_score = compute_score_normalise(df, [c for c in equite_cols if c])

        indicateurs_med = [
            {"nom": "Adequation des ressources aux taches", "valeur": f"{adq_score:.1f}" if adq_score is not None else "N/A", "seuil": "60", "operateur": "<", "priorite_type": "risque"},
            {"nom": "Charge physique du poste", "valeur": charge_display, "seuil": "Modere", "operateur": ">=", "priorite_type": "risque"},
            {"nom": "Conflit de role et ambiguite", "valeur": f"{conflit_score:.1f}" if conflit_score is not None else "N/A", "seuil": "50", "operateur": ">", "priorite_type": "vigilance"},
            {"nom": "Equilibre vie pro / privee", "valeur": f"{equilibre_score:.1f}" if equilibre_score is not None else "N/A", "seuil": "50", "operateur": "<", "priorite_type": "vigilance"},
            {"nom": "Reconnaissance et equite (ERI)", "valeur": f"{equite_score:.1f}" if equite_score is not None else "N/A", "seuil": "66", "operateur": "<", "priorite_type": "risque"},
        ]
        cols = st.columns(5)
        for i, indic in enumerate(indicateurs_med):
            with cols[i]:
                st.markdown(render_indicator_card(
                    indic["nom"], indic["valeur"], 
                    indic["seuil"], indic.get("operateur", ""), 
                    indic["priorite_type"]
                ), unsafe_allow_html=True)


def render_tab_analyse(df, mode):
    st.markdown('<div class="section-title">Analyse univariee</div>', unsafe_allow_html=True)

    VAR_OPTIONS = {}
    
    for label, col in VARIABLES_UNIVARIEES + VARIABLES_SPECIFIQUES:
        if col in df.columns:
            VAR_OPTIONS[label] = col
    
    for domain in SCORE_GROUPS:
        if domain in df.columns:
            col_name = f"__dom_{domain}"
            df[col_name] = df[domain].apply(
                lambda s: "Satisfait" if pd.notna(s) and s >= 2.5 else ("Insatisfait" if pd.notna(s) else "Non defini")
            )
            VAR_OPTIONS[f"Domaine — {domain}"] = col_name
    
    QUESTIONS_CLES = [
        "Mon travail est stimulant.",
        "Je suis ecoute(e) par ma hierarchie.",
        "Je participe aux decisions qui concernent mon travail.",
        "Je dispose des moyens necessaires pour faire mon travail.",
        "Je recois des informations utiles pour bien travailler.",
        "Je me sens a l'aise dans mon equipe.",
        "J'ai des pauses suffisantes pendant ma journee.",
        "Je peux evoluer dans mon poste.",
        "Je comprends clairement mes missions.",
        "Les horaires sont compatibles avec ma vie personnelle.",
    ]
    
    question_map_local = resolve_questions(df)
    for q_text in QUESTIONS_CLES:
        col = question_map_local.get(q_text) or trouver_colonne_qvt(df, q_text)
        if col:
            renamed = RENOMMED_QUESTIONS.get(q_text, q_text)
            col_name = f"__q_{renamed[:20]}"
            df[col_name] = pd.to_numeric(df[col], errors="coerce").apply(
                lambda s: "Satisfait" if pd.notna(s) and s >= 3 else ("Insatisfait" if pd.notna(s) else "Non defini")
            )
            VAR_OPTIONS[f"Question — {renamed}"] = col_name

    if not VAR_OPTIONS:
        st.info("Aucune variable disponible.")
        return

    c_sel, _ = st.columns([1, 2])
    with c_sel:
        sel_label = st.selectbox("Variable a visualiser", list(VAR_OPTIONS.keys()), key="uni_qvt")
    sel_col = VAR_OPTIONS.get(sel_label)

    if sel_col and sel_col in df.columns:
        counts_u = df[sel_col].value_counts()
        total_u = counts_u.sum()
        pcts_u = (counts_u / total_u * 100).round(1)
        n_bars = len(counts_u)

        stats_data = [{"Modalite": str(cat), "Effectif": int(eff), "Frequence": f"{pct:.1f}%"} for cat, eff, pct in zip(counts_u.index, counts_u.values, pcts_u.values)]
        stats_data.append({"Modalite": "TOTAL", "Effectif": int(total_u), "Frequence": "100%"})

        c_chart, c_table = st.columns([7, 3])
        with c_chart:
            pal = ["#38A3E8", "#F97316", "#22C55E", "#EF4444", "#A78BFA", "#06B6D4", "#FB923C", "#84CC16", "#EC4899", "#8B5CF6"]
            satisfaction_colors = {
                "Tres satisfait": "#22C55E", "Satisfait": "#22C55E",
                "Insatisfait": "#EF4444", "Tres insatisfait": "#EF4444",
                "Eleve": "#22C55E", "Moyen": "#F59E0B", "Faible": "#EF4444",
                "Non defini": "#94A3B8",
            }

            fig = go.Figure()
            for i, (cat, pct, eff) in enumerate(zip(counts_u.index, pcts_u.values, counts_u.values)):
                bar_color = satisfaction_colors.get(str(cat), pal[i % len(pal)])
                fig.add_trace(go.Bar(
                    y=[str(cat)], x=[pct], orientation='h',
                    marker_color=bar_color, marker=dict(opacity=0.9, line=dict(width=0)),
                    text=f"{pct:.1f}%  ({int(eff)})",
                    textposition="outside",
                    textfont=dict(color="#6B88A8", size=12, family="Plus Jakarta Sans"),
                    showlegend=False
                ))

            fig.update_layout(
                plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Plus Jakarta Sans, sans-serif", color="#0F2340", size=12),
                xaxis=dict(range=[0, max(pcts_u.values)*1.5], title_text="Pourcentage (%)",
                        showgrid=True, gridcolor="#EDF5FD", gridwidth=1,
                        showline=True, linecolor="#D6E8F7", zeroline=False,
                        tickfont=dict(color="#6B88A8", size=11)),
                yaxis=dict(showgrid=False, showline=False, zeroline=False,
                        tickfont=dict(color="#0F2340", size=11)),
                height=max(300, n_bars*55+120),
                margin=dict(l=20, r=80, t=60, b=40),
                title=dict(text=f"Repartition selon : {sel_label}",
                        font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"),
                        x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True, key="uni_qvt_plotly")

        with c_table:
            st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Statistiques</p>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True, height=min(400, 35*(len(stats_data)+1)))

            st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">Interpretation</p>', unsafe_allow_html=True)
            modalites = list(counts_u.index)
            if len(modalites) >= 2:
                m1, m2 = modalites[0], modalites[1]
                st.markdown(f'<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;font-family:\'Plus Jakarta Sans\',sans-serif;"><p style="margin:0 0 8px;">Ce graphique montre la repartition de <b>{sel_label}</b> parmi les {int(total_u)} repondants.</p><p style="margin:0 0 8px;">La modalite dominante est <b>« {m1} »</b> avec <b>{pcts_u.iloc[0]:.1f}%</b> des repondants ({int(counts_u.iloc[0])} personne(s)).</p><p style="margin:0;">Elle est suivie par <b>« {m2} »</b> avec <b>{pcts_u.iloc[1]:.1f}%</b> ({int(counts_u.iloc[1])} personne(s)). Au total, <b>{n_bars}</b> modalites.</p></div>', unsafe_allow_html=True)
            else:
                st.caption("Donnees insuffisantes.")


def render_tab_croisement(df, mode):
    st.markdown('<div class="section-title">Analyse bivariee</div>', unsafe_allow_html=True)

    VAR_CROISE = {}
    for label, col in VARIABLES_UNIVARIEES:
        if col in df.columns:
            VAR_CROISE[label] = col

    OUTCOME_MAP = {}
    if "niveau_satisfaction" in df.columns:
        OUTCOME_MAP["Niveau de satisfaction"] = "niveau_satisfaction"
    
    for domain in SCORE_GROUPS:
        if domain in df.columns:
            col_name = f"__bivar_dom_{domain}"
            df[col_name] = df[domain].apply(
                lambda s: "Satisfait" if pd.notna(s) and s >= 2.5 else ("Insatisfait" if pd.notna(s) else "Non defini")
            )
            OUTCOME_MAP[f"Domaine — {domain}"] = col_name
    
    QUESTIONS_CLES = [
        "Mon travail est stimulant.",
        "Je suis ecoute(e) par ma hierarchie.",
        "Je participe aux decisions qui concernent mon travail.",
        "Je dispose des moyens necessaires pour faire mon travail.",
        "Je recois des informations utiles pour bien travailler.",
        "Je me sens a l'aise dans mon equipe.",
        "J'ai des pauses suffisantes pendant ma journee.",
        "Je peux evoluer dans mon poste.",
        "Je comprends clairement mes missions.",
        "Les horaires sont compatibles avec ma vie personnelle.",
    ]
    
    question_map_local = resolve_questions(df)
    for q_text in QUESTIONS_CLES:
        col = question_map_local.get(q_text) or trouver_colonne_qvt(df, q_text)
        if col:
            renamed = RENOMMED_QUESTIONS.get(q_text, q_text)
            col_name = f"__bivar_q_{renamed[:20]}"
            df[col_name] = pd.to_numeric(df[col], errors="coerce").apply(
                lambda s: "Satisfait" if pd.notna(s) and s >= 3 else ("Insatisfait" if pd.notna(s) else "Non defini")
            )
            OUTCOME_MAP[f"Question — {renamed}"] = col_name

    OUTCOME_OPTIONS = {k: v for k, v in OUTCOME_MAP.items() if v in df.columns}

    if not VAR_CROISE or not OUTCOME_OPTIONS:
        st.info("Variables insuffisantes pour l'analyse bivariee.")
        return

    cx1, cx2 = st.columns(2)
    with cx1:
        sel_var = st.selectbox("Variable demographique", list(VAR_CROISE.keys()), key="bivar_var")
    with cx2:
        sel_outcome = st.selectbox("Variable de resultat", list(OUTCOME_OPTIONS.keys()), key="bivar_outcome")

    var_col = VAR_CROISE.get(sel_var)
    out_col = OUTCOME_OPTIONS.get(sel_outcome)

    if var_col and out_col and var_col in df.columns and out_col in df.columns:
        tmp = df[[var_col, out_col]].dropna()
        
        if not tmp.empty:
            if out_col == "Score_Global":
                tmp["outcome_name"] = pd.cut(
                    tmp[out_col], bins=[0, 2.5, 3.5, 5],
                    labels=["Faible", "Moyen", "Eleve"]
                )
            elif out_col in [f"__bivar_dom_{d}" for d in SCORE_GROUPS] or out_col.startswith("__bivar_q_"):
                tmp["outcome_name"] = tmp[out_col]
            else:
                tmp["outcome_name"] = tmp[out_col]
            
            ct = pd.crosstab(tmp[var_col].astype(str), tmp["outcome_name"].astype(str))
            pct = ct.div(ct.sum(axis=1), axis=0) * 100

            c_chart, c_right = st.columns([7, 3])

            with c_chart:
                colors_map = {
                    "Satisfait": "#22C55E", "Insatisfait": "#EF4444",
                    "Faible": "#EF4444", "Moyen": "#F59E0B", "Eleve": "#22C55E",
                    "Tres satisfait": "#22C55E", "Tres insatisfait": "#EF4444",
                    "Non defini": "#94A3B8",
                }
                gen_pal = ["#38A3E8", "#F97316", "#22C55E", "#EF4444", "#A78BFA",
                        "#06B6D4", "#FB923C", "#84CC16", "#EC4899", "#8B5CF6"]

                fig = go.Figure()
                for i, cat in enumerate(pct.columns):
                    vals = pct[cat].values
                    ns = ct[cat].values
                    txts = [f"{v:.1f}%  ({n})" if v >= 5 else "" for v, n in zip(vals, ns)]
                    color = colors_map.get(str(cat), gen_pal[i % len(gen_pal)])

                    fig.add_trace(go.Bar(
                        name=str(cat),
                        y=list(pct.index), x=vals,
                        orientation='h',
                        marker_color=color,
                        marker=dict(opacity=0.9, line=dict(width=0)),
                        text=txts,
                        textposition="inside",
                        insidetextanchor="middle",
                        textfont=dict(color="white", size=11, family="Plus Jakarta Sans")
                    ))

                fig.update_layout(
                    barmode="stack",
                    plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Plus Jakarta Sans, sans-serif", color="#0F2340", size=12),
                    xaxis=dict(range=[0, 100], title_text="Pourcentage (%)",
                            showgrid=True, gridcolor="#EDF5FD", gridwidth=1,
                            showline=True, linecolor="#D6E8F7", zeroline=False,
                            tickfont=dict(color="#6B88A8", size=11)),
                    yaxis=dict(showgrid=False, showline=False, zeroline=False,
                            tickfont=dict(color="#0F2340", size=11)),
                    height=max(300, len(pct.index) * 55 + 120),
                    margin=dict(l=20, r=20, t=50, b=40),
                    title=dict(text=f"{sel_var} selon {sel_outcome}",
                            font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"),
                            x=0.5, xanchor="center"),
                    legend=dict(bgcolor="rgba(255,255,255,0.95)", bordercolor="#D6E8F7",
                            borderwidth=1, font=dict(color="#0F2340", size=10),
                            orientation="h", y=-0.30, x=0.5, xanchor="center")
                )
                st.plotly_chart(fig, use_container_width=True, key="bivar_plotly")

            with c_right:
                st.markdown(
                    '<p style="font-size:11px;font-weight:700;color:#64748b;'
                    'letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">'
                    'Tableau de distribution (%)</p>',
                    unsafe_allow_html=True
                )
                st.dataframe(pct.round(1).style.format("{:.1f}%"), use_container_width=True)

                st.markdown(
                    '<p style="font-size:11px;font-weight:700;color:#64748b;'
                    'letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">'
                    'Interpretation</p>',
                    unsafe_allow_html=True
                )
                
                lignes = list(pct.index)
                colonnes = list(pct.columns)
                
                if len(lignes) >= 2 and len(colonnes) >= 1:
                    l1, l2 = lignes[0], lignes[1]
                    
                    if len(colonnes) >= 2:
                        c_principale = colonnes[0]
                        max_pct = pct[c_principale].max()
                        min_pct = pct[c_principale].min()
                        ecart = max_pct - min_pct
                        
                        if ecart > 20:
                            intensite = "forte"
                        elif ecart > 10:
                            intensite = "moderee"
                        else:
                            intensite = "faible"
                        
                        st.markdown(f"""
                        <div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;
                        padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;
                        font-family:'Plus Jakarta Sans',sans-serif;">
                        <p style="margin:0 0 8px;">Ce graphique montre la repartition de <b>{sel_outcome}</b> 
                        selon <b>{sel_var}</b>.</p>
                        <p style="margin:0 0 8px;">
                        <b>« {l1} »</b> : {', '.join([f'<b>{pct.loc[l1, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l1, c] > 0])}.
                        </p>
                        <p style="margin:0 0 8px;">
                        <b>« {l2} »</b> : {', '.join([f'<b>{pct.loc[l2, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l2, c] > 0])}.
                        </p>
                        <p style="margin:0;">
                        L'ecart de <b>{ecart:.1f} points</b> pour <b>« {c_principale} »</b> 
                        indique une disparite <b>{intensite}</b> entre ces groupes.
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;
                        padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;
                        font-family:'Plus Jakarta Sans',sans-serif;">
                        <p style="margin:0 0 8px;">Ce graphique montre la repartition de <b>{sel_outcome}</b> 
                        selon <b>{sel_var}</b>.</p>
                        <p style="margin:0 0 8px;">
                        <b>« {l1} »</b> : {', '.join([f'<b>{pct.loc[l1, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l1, c] > 0])}.
                        </p>
                        <p style="margin:0;">
                        <b>« {l2} »</b> : {', '.join([f'<b>{pct.loc[l2, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l2, c] > 0])}.
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("Donnees insuffisantes pour generer une interpretation automatique.")


# =============================================================================
# POINT D'ENTREE STREAMLIT
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
            f'<i class="fas fa-heart" style="color:white;font-size:15px;"></i></div>'
            f'<div><div style="font-size:16px;font-weight:700;color:#1e293b;'
            f'font-family:\'Plus Jakarta Sans\',sans-serif;">{PAGE_TITLE}</div>'
            f'<div style="font-size:11px;color:#64748b;margin-top:1px;'
            f'font-family:\'Plus Jakarta Sans\',sans-serif;">Analyse de la satisfaction au travail</div>'
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

    uploaded_file = st.file_uploader("Charger un fichier Excel ou CSV", type=["xlsx", "xls", "csv"], key=f"uploader_{PAGE_KEY}")
    if uploaded_file is not None:
        st.session_state[f"_file_bytes_{PAGE_KEY}"] = uploaded_file.read()
        st.session_state[f"_file_name_{PAGE_KEY}"] = uploaded_file.name
    if f"_file_bytes_{PAGE_KEY}" not in st.session_state:
        st.info("Veuillez charger un fichier de donnees pour demarrer l'analyse.")
        st.stop()

    file_bytes = st.session_state[f"_file_bytes_{PAGE_KEY}"]
    file_name = st.session_state[f"_file_name_{PAGE_KEY}"]

    with st.spinner("Chargement et traitement des donnees…"):
        df_raw = load_data_from_bytes(file_bytes, file_name)
        n_before = len(df_raw)
        df_clean, cleaning_log = clean_common_variables(df_raw)

    with st.expander("Journal de nettoyage", expanded=False):
        st.text(cleaning_log)
        st.text(f"Questions QVT :{sum(1 for q in QUESTIONS if trouver_colonne_qvt(df_clean, q) is not None)}/20")
        st.write(f"Avant: **{n_before}** — Apres: **{len(df_clean)}**")

    if df_clean.empty:
        st.error("Aucune donnee exploitable.")
        st.stop()

    q_trouvees = sum(1 for q in QUESTIONS if trouver_colonne_qvt(df_clean, q) is not None)
    if q_trouvees < 20:
        st.error(f"ERREUR - Fichier non reconnu — Seulement {q_trouvees}/20 questions QVT detectees.")
        st.stop()

    question_map = resolve_questions(df_clean)
    df_clean = compute_scores(df_clean, question_map)

    if "Score_Global" in df_clean.columns:
        df_clean["niveau_satisfaction"] = df_clean["Score_Global"].apply(lambda s: "Non defini" if pd.isna(s) else "Tres satisfait" if s >= 3.5 else "Satisfait" if s >= 2.5 else "Insatisfait" if s >= 1.5 else "Tres insatisfait")
        df_clean["score_global_cat"] = df_clean["Score_Global"].apply(lambda s: "Non defini" if pd.isna(s) else "Eleve" if s >= 3 else "Moyen" if s >= 2 else "Faible")

    if is_rh(current_mode):
        tabs = st.tabs(["Vue d'ensemble", "Analyse univariee"])
    else:
        tabs = st.tabs(["Vue d'ensemble", "Analyse univariee", "Analyse bivariee"])

    with tabs[0]:
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
        
        if 'age' in df_clean.columns and pd.api.types.is_numeric_dtype(df_clean['age']):
            num_vars.append(("Age", "age"))
        
        with st.expander("Filtres", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns([3, 3, 3, 1.5])
            
            with fc1:
                cat_labels = ["— Aucun —"] + [l for l, _ in cat_vars]
                sel_cat_label = st.selectbox("Variable (categorielle)", cat_labels, key="qvt_filtre_cat")
            
            with fc2:
                if sel_cat_label != "— Aucun —":
                    cat_col = dict(cat_vars)[sel_cat_label]
                    modalites = sorted(df_clean[cat_col].dropna().astype(str).unique().tolist())
                    sel_modalite = st.selectbox("Modalite", ["Toutes"] + modalites, key="qvt_filtre_mod")
                else:
                    sel_modalite = "Toutes"
                    st.selectbox("Modalite", ["Toutes"], disabled=True)
            
            with fc3:
                num_labels = ["— Aucun —"] + [l for l, _ in num_vars]
                sel_num_label = st.selectbox("Variable (numerique)", num_labels, key="qvt_filtre_num")
                
                if sel_num_label != "— Aucun —":
                    num_col = dict(num_vars)[sel_num_label]
                    vals = pd.to_numeric(df_clean[num_col], errors="coerce").dropna()
                    if not vals.empty:
                        vmin, vmax = int(vals.min()), int(vals.max())
                        if vmin == vmax:
                            vmax = vmin + 1
                        sel_range = st.slider(f"Plage — {sel_num_label}", vmin, vmax, (vmin, vmax), key="qvt_filtre_range")
                    else:
                        sel_range = None
                        st.slider(f"Plage — {sel_num_label}", 0, 100, (0, 100), disabled=True)
                else:
                    sel_range = None
            
            with fc4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Reinitialiser", key="qvt_reset_filtres", use_container_width=True):
                    for k in ["qvt_filtre_cat", "qvt_filtre_mod", "qvt_filtre_num", "qvt_filtre_range"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()
        
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
            st.warning("Aucune donnee ne correspond aux filtres selectionnes.")
            st.stop()
        
        render_tab_overview(df_filtered, current_mode, n_before, question_map)
        
    with tabs[1]:
        render_tab_analyse(df_clean, current_mode)

    if len(tabs) > 2:
        with tabs[2]:
            render_tab_croisement(df_clean, current_mode)

    st.markdown("---")
    st.markdown(f'<p style="text-align:center;color:#9CA3AF;font-size:0.8rem;font-family:\'Plus Jakarta Sans\',sans-serif;">{PAGE_TITLE} — YODAN Analytics © 2026</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()