# =============================================================================
# 2_Karasek.py — Karasek - Demande–Contrôle–Soutien
# Page d'analyse avec upload de fichier et KPIs généraux
# Style KPI uniforme et flexible (template yodan_view_mode.py)
# Formules : karasek_kpi_formulas.py
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
import plotly.express as px

# ── Import du module partagé ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from yodan_view_mode import (
        render_mode_switcher, inject_shared_css, render_mode_banner,
        get_mode, init_mode, MODE_RH, MODE_MEDECIN,
        is_rh, is_medecin, show_if, SHOW_ALL, SHOW_RH, SHOW_MEDECIN, SHOW_RH_MEDECIN,
    )
    _VIEW_MODE_AVAILABLE = True
except ImportError:
    _VIEW_MODE_AVAILABLE = False
    MODE_RH = "RH/DG"; MODE_MEDECIN = "Médecin"
    def get_mode(key="view_mode"): return st.session_state.get(key, MODE_RH)
    def init_mode(key="view_mode"):
        if key not in st.session_state: st.session_state[key] = MODE_RH
    def inject_shared_css(mode=None): pass
    def render_mode_switcher(**kwargs): return get_mode()
    def render_mode_banner(mode): pass
    def is_rh(m): return m == MODE_RH
    def is_medecin(m): return m == MODE_MEDECIN
    def show_if(m, allowed): return m in allowed
    SHOW_ALL = [MODE_RH, MODE_MEDECIN]; SHOW_RH = [MODE_RH]; SHOW_MEDECIN = [MODE_MEDECIN]
    SHOW_RH_MEDECIN = [MODE_RH, MODE_MEDECIN]


# =============================================================================
# CONFIGURATION DE LA PAGE KARASEK
# =============================================================================
PAGE_TITLE = "Karasek — Demande–Contrôle–Soutien"
PAGE_ICON = "🧠"
PAGE_KEY = "karasek_view_mode"

LIKERT_MIN, LIKERT_MAX = 1, 4

# Couleurs des quadrants
KARASEK_COLORS = {
    "Actif":   "#22C55E",
    "Détendu": "#38A3E8",
    "Detendu": "#38A3E8",
    "Tendu":   "#EF4444",
    "Passif":  "#94A3B8",
}

# Seuils théoriques (point médian Likert 1-4)
THRESHOLDS = {
    "Dem_score": 22.5, "Lat_score": 60.0, "SS_score": 20.0,
    "comp_score": 30.0, "auto_score": 30.0, "sup_score": 10.0,
    "col_score": 10.0, "rec_score": 15.0, "equ_score": 2.5,
    "cult_score": 5.0, "sat_score": 2.5, "adq_resources_score": 5.0,
    "adq_role_score": 5.0,
}

INVERT_ITEMS_KARASEK = ["Q2_auto", "Q2_comp", "Q4_dem", "Q1_rec", "Q2_rec"]

SCORE_MULTIPLIERS = {"comp": 2, "auto": 4, "dem": 1, "sup": 1, "col": 1}
RH_SCORE_GROUPS = ["rec", "equ", "cult", "adq_resources", "adq_role", "sat"]

# Dictionnaire des items pour fuzzy matching
KARASEK_ITEMS = {
    'Q1_comp': "je dois apprendre des choses nouvelles",
    'Q2_comp': "j effectue des taches repetitives",
    'Q3_comp': "mon travail me demande d etre creatif",
    'Q4_comp': "mon travail me demande un haut niveau de competence",
    'Q5_comp': "j ai des activites variees",
    'Q6_comp': "j ai l occasion de developper mes competences professionnelles",
    'Q1_auto': "mon travail me permet souvent de prendre des decisions moi meme",
    'Q2_auto': "j ai tres peu de liberte pour decider comment je fais mon travail",
    'Q3_auto': "j ai la possibilite d influencer le deroulement de mon travail",
    'Q1_dem': "mon travail me demande de travailler tres vite",
    'Q2_dem': "mon travail demande de travailler intensement",
    'Q3_dem': "on me demande d effectuer une quantite de travail excessive",
    'Q4_dem': "je dispose du temps necessaire pour effectuer correctement mon travail",
    'Q5_dem': "je recois des ordres contradictoires",
    'Q6_dem': "mon travail necessite de longues periodes de concentration intense",
    'Q7_dem': "mes taches sont souvent interrompues",
    'Q8_dem': "mon travail est tres bouscule",
    'Q9_dem': "attendre le travail de collegues ralentit souvent mon propre travail",
    'Q1_sup': "mon superieur se sent concerne par le bien etre de ses subordonnes",
    'Q2_sup': "mon superieur prete attention a ce que je dis",
    'Q3_sup': "mon superieur m aide a mener ma tache a bien",
    'Q4_sup': "mon superieur reussit facilement a faire collaborer ses subordonnes",
    'Q1_col': "les collegues avec qui je travaille sont des gens professionnellement competents",
    'Q2_col': "les collegues avec qui je travaille me manifestent de l interet",
    'Q3_col': "les collegues avec qui je travaille sont amicaux",
    'Q4_col': "les collegues avec qui je travaille m aident a mener les taches a bien",
    'Q1_rec': "on me traite injustement dans mon travail",
    'Q2_rec': "ma securite d emploi est menacee",
    'Q3_rec': "ma position professionnelle actuelle correspond bien a ma formation",
    'Q4_rec': "je recois le respect et l estime que je merite",
    'Q5_rec': "mes perspectives de promotion sont satisfaisantes",
    'Q6_rec': "mon salaire est satisfaisant",
    'Q1_equ': "la charge de travail est repartie equitablement",
    'Q1_cult': "je m identifie a la culture de l entreprise",
    'Q2_cult': "je recommanderai ma compagnie a mes connaissances",
    'Q1_sat': "je suis satisfait de mon travail",
    'Q1_adq_resources': "je sais ce que je dois faire pour atteindre les objectifs",
    'Q2_adq_resources': "je dispose de toutes les ressources necessaires",
    'Q1_adq_role': "mes besoins de formations sont bien pris en compte",
    'Q2_adq_role': "les formations dispensees sont coherentes avec les taches",
}


# =============================================================================
# FONCTIONS UTILITAIRES DE NETTOYAGE
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
            if re.search(pattern, normalized_col): return col
    return None


def _find_age_numeric_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        col_norm = _pp_normalize_text(col)
        if "tranche" in col_norm: continue
        if re.search(r"\bage\b", col_norm):
            series = df[col]
            if isinstance(series, pd.DataFrame): series = series.iloc[:, 0]
            vals = pd.to_numeric(series, errors="coerce")
            if not vals.dropna().empty: return col
    return None


def _is_likert_col(col: str) -> bool:
    return bool(re.match(r"Q\d+_(comp|auto|dem|sup|col|rec|equ|cult|adq_resources|adq_role|sat)$", col))


def clean_common_variables(df: pd.DataFrame, missing_threshold: float = 0.55) -> tuple:
    cleaned_df = df.copy(); ops = []

    _PII_PATTERNS = [
        r"\bnom\b", r"\bprenom", r"\be[- ]?mail\b", r"\bmail\b", r"\bcourriel\b",
        r"\btelephone\b", r"\btel\b", r"\bphone\b", r"\bcommentaire",
        r"\bobservation", r"\bremarque", r"\bnumero\b", r"\bidentifiant\b", r"\bid\b",
    ]
    _pii_dropped = []
    for col in list(cleaned_df.columns):
        col_norm = _pp_normalize_text(col)
        if any(re.search(pat, col_norm) for pat in _PII_PATTERNS):
            cleaned_df = cleaned_df.drop(columns=[col]); _pii_dropped.append(str(col))
    if _pii_dropped: ops.append(f"Colonnes PII supprimées ({len(_pii_dropped)})")

    missing_ratio = cleaned_df.isna().mean()
    cols_to_drop = missing_ratio[missing_ratio > missing_threshold].index.tolist()
    if cols_to_drop:
        for c in cols_to_drop:
            pct = missing_ratio[c] * 100
            ops.append(f"Colonne '{c}' supprimée ({pct:.1f}% de valeurs manquantes)")
        cleaned_df = cleaned_df.drop(columns=cols_to_drop)

    # ÂGE
    age_col = _find_age_numeric_col(cleaned_df)
    if age_col is not None:
        cleaned_df['age'] = pd.to_numeric(cleaned_df[age_col], errors="coerce")
        ops.append(f"Colonne 'age' créée depuis: {age_col}")
        age_vals = pd.to_numeric(cleaned_df['age'], errors="coerce")
        cleaned_df['Tranche_dage'] = pd.cut(age_vals, bins=[0,30,40,50,float("inf")],
            labels=["20-30 ans","31-40 ans","41-50 ans","51 ans et plus"], right=True)
        ops.append("Colonne 'Tranche_dage' créée")
    else:
        tranche_age_col = _find_by_patterns(list(cleaned_df.columns), [r"tranche.*age",r"tranche.*âge",r"classe.*age"])
        if tranche_age_col is not None:
            if tranche_age_col != 'Tranche_dage':
                cleaned_df['Tranche_dage'] = cleaned_df[tranche_age_col].astype(str)
                cleaned_df = cleaned_df.drop(columns=[tranche_age_col])
                ops.append(f"Colonne '{tranche_age_col}' renommée en 'Tranche_dage'")
            else: ops.append("Colonne 'Tranche_dage' déjà présente")
        else: ops.append("Âge: aucune colonne trouvée")

    # ANCIENNETÉ
    anciennete_num_col = _find_by_patterns(list(cleaned_df.columns), [r"anciennete",r"anciennet"])
    if anciennete_num_col is not None:
        if pd.api.types.is_numeric_dtype(cleaned_df[anciennete_num_col]):
            cleaned_df['anciennete'] = pd.to_numeric(cleaned_df[anciennete_num_col], errors="coerce")
            ops.append(f"Colonne 'anciennete' créée")
        else:
            cleaned_df['Tranche_anciennete'] = cleaned_df[anciennete_num_col].astype(str)
            ops.append(f"Colonne 'Tranche_anciennete' créée")
    else:
        tranche_anc_col = _find_by_patterns(list(cleaned_df.columns), [r"tranche.*anciennete",r"tranche.*ancienneté"])
        if tranche_anc_col is not None:
            cleaned_df['Tranche_anciennete'] = cleaned_df[tranche_anc_col].astype(str)
            ops.append(f"Colonne 'Tranche_anciennete' conservée")
        else: ops.append("Ancienneté: aucune colonne trouvée")

    if 'anciennete' in cleaned_df.columns and 'Tranche_anciennete' not in cleaned_df.columns:
        anc_num = pd.to_numeric(cleaned_df['anciennete'], errors="coerce")
        cleaned_df['Tranche_anciennete'] = pd.cut(anc_num, bins=[-1,2,5,10,20,np.inf],
            labels=["0-2 ans","3-5 ans","6-10 ans","11-20 ans","21 ans et +"])
        ops.append("Colonne 'Tranche_anciennete' créée")

    # GENRE
    genre_col = _find_by_patterns(list(cleaned_df.columns), [r"\bgenre\b",r"\bsexe\b"])
    if genre_col is not None:
        def std_genre(v):
            if pd.isna(v): return np.nan
            vl = str(v).strip().lower()
            if vl in ['homme','h','male','masculin','m','hommes']: return 'homme'
            elif vl in ['femme','f','female','féminin','feminin','femmes']: return 'femme'
            return vl
        cleaned_df['genre'] = cleaned_df[genre_col].apply(std_genre)
        if genre_col != 'genre': ops.append(f"Colonne 'genre' standardisée depuis: {genre_col}")
        else: ops.append("Colonne 'genre' standardisée")

    # IMC
    poids_col = _find_by_patterns(list(cleaned_df.columns), [r"\bpoids\b"])
    taille_col = _find_by_patterns(list(cleaned_df.columns), [r"\btaille\b"])
    if poids_col is not None and taille_col is not None:
        poids_vals = pd.to_numeric(cleaned_df[poids_col], errors="coerce")
        taille_vals = pd.to_numeric(cleaned_df[taille_col], errors="coerce")
        taille_positive = taille_vals[taille_vals > 0]
        if not taille_positive.empty and float(taille_positive.median()) > 3: taille_m = taille_vals/100.0
        else: taille_m = taille_vals
        imc_vals = (poids_vals / taille_m**2).replace([np.inf,-np.inf], np.nan)
        cleaned_df['imc'] = imc_vals
        cleaned_df['Categorie_IMC'] = pd.cut(imc_vals, bins=[0,18.5,25,30,200],
            labels=["Insuffisance pondérale","Corpulence normale","Surpoids","Obésité"], include_lowest=True)
        cleaned_df['IMC_binaire'] = np.where(
            cleaned_df['Categorie_IMC'].isin(["Insuffisance pondérale","Corpulence normale"]),
            "Normal", np.where(cleaned_df['Categorie_IMC'].isna(), None, "Surpoids/Obésité"))
        ops.append("Colonne 'imc', 'Categorie_IMC' et 'IMC_binaire' calculées")

    # COLONNES ORGANISATIONNELLES
    for std_name, patterns in [
        ('direction',[r"direction"]), ('fonction',[r"fonction"]),
        ('service',[r"service"]), ('departement',[r"departement",r"département",r"dept"]),
    ]:
        if std_name not in cleaned_df.columns:
            found = _find_by_patterns(list(cleaned_df.columns), patterns)
            if found is not None:
                cleaned_df[std_name] = cleaned_df[found].astype(str)
                ops.append(f"Colonne '{std_name}' détectée: {found}")

    # FACTEURS DE RISQUE
    for std_name, patterns in [
        ('tabagisme',[r"tabag",r"tabac",r"fumeur"]),
        ('consommation_alcool',[r"alcool",r"consommation.*alcool"]),
        ('maladie_chronique',[r"maladie.*chron",r"chron.*maladie",r"hta",r"diabet"]),
        ('pratique_sport',[r"sport",r"activite.*physique",r"pratique.*sport"]),
        ('situation_matrimoniale',[r"situation.*matrimon",r"matrimon",r"etat.*civil"]),
        ('handicap_physique',[r"handicap.*physique",r"handicap"]),
        ('suivi_psychologique',[r"suivi.*psycho",r"probleme.*psycho",r"psy"]),
    ]:
        if std_name not in cleaned_df.columns:
            found = _find_by_patterns(list(cleaned_df.columns), patterns)
            if found is not None:
                cleaned_df[std_name] = cleaned_df[found]
                ops.append(f"Colonne '{std_name}' détectée: {found}")

    # SUPPRESSION OBSERVATIONS AVEC VALEURS MANQUANTES
    n_before_drop = len(cleaned_df)
    cleaned_df = cleaned_df.dropna()
    n_after_drop = len(cleaned_df)
    n_dropped = n_before_drop - n_after_drop
    if n_dropped > 0: ops.append(f"{n_dropped} observation(s) supprimée(s) — {n_after_drop} restantes")
    else: ops.append(f"Aucune observation avec valeurs manquantes — {n_after_drop} observations conservées")

    cleaning_log = "Nettoyage appliqué:\n- " + "\n- ".join(ops) if ops else "Aucune opération appliquée."
    return cleaned_df, cleaning_log


# =============================================================================
# FONCTIONS DE SCORING KARASEK (formules karasek_kpi_formulas.py)
# =============================================================================

def trouver_colonne_karasek(df: pd.DataFrame, item: str) -> str | None:
    if item in df.columns: return item
    question_text = KARASEK_ITEMS.get(item)
    if question_text is None: return None
    target = _pp_normalize_text(question_text)
    best_col = None; best_score = -1.0
    for col in df.columns:
        col_norm = _pp_normalize_text(col)
        score = SequenceMatcher(None, target, col_norm).ratio()
        if score > best_score: best_score = score; best_col = col
    if best_col is not None and best_score >= 0.4: return best_col
    return None


def _fuzzy_rename_karasek(df: pd.DataFrame) -> pd.DataFrame:
    def _norm_q(text):
        t = unicodedata.normalize("NFKD", str(text))
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        t = t.lower().strip()
        t = re.sub(r"[\u2018\u2019\u201a\u201b\u2032\u0060]", "'", t)
        t = re.sub(r"[\s]+", " ", t)
        return t
    norm_map = {_norm_q(v): k for k, v in KARASEK_ITEMS.items()}
    rename = {}
    for col in df.columns:
        nc = _norm_q(col)
        if nc in norm_map: rename[col] = norm_map[nc]
    return df.rename(columns=rename) if rename else df


def compute_group_score(df: pd.DataFrame, suffix: str, multiplier: int = 1) -> pd.Series:
    """Formule : (somme / n_valides) × n_items × multiplicateur"""
    cols = [c for c in df.columns if c.endswith(f"_{suffix}")]
    if not cols: return pd.Series(np.nan, index=df.index, name=f"{suffix}_score")
    n_items = len(cols)
    row_sum = df[cols].sum(axis=1, skipna=True)
    n_valid = df[cols].notna().sum(axis=1)
    score = (row_sum / n_valid.replace(0, np.nan)) * n_items * multiplier
    return score.where(n_valid > 0, np.nan).rename(f"{suffix}_score")


def compute_all_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline complet : inversion, scores Karasek, scores RH"""
    df_out = df.copy()
    
    # 1. Renommage fuzzy
    df_out = _fuzzy_rename_karasek(df_out)
    
    # 2. Nettoyage Likert
    likert_cols = [c for c in df_out.columns if _is_likert_col(c)]
    for col in likert_cols:
        s = pd.to_numeric(df_out[col], errors="coerce")
        df_out[col] = s.where(s.between(LIKERT_MIN, LIKERT_MAX))
    
    # 3. Inversion des items négatifs
    to_invert = [c for c in INVERT_ITEMS_KARASEK if c in df_out.columns]
    if to_invert: df_out[to_invert] = (LIKERT_MIN + LIKERT_MAX) - df_out[to_invert]
    
    # 4. Sous-scores avec multiplicateurs
    for group, mult in SCORE_MULTIPLIERS.items():
        col_name = f"{group}_score"
        computed = compute_group_score(df_out, group, multiplier=mult)
        if computed.notna().any(): df_out[col_name] = computed
        elif col_name not in df_out.columns: df_out[col_name] = np.nan
    
    # 5. Scores composites Karasek
    if "Lat_score" not in df_out.columns or df_out["Lat_score"].isna().all():
        lat_parts = [c for c in ["comp_score", "auto_score"] if c in df_out.columns]
        df_out["Lat_score"] = sum(df_out[c] for c in lat_parts) if lat_parts else np.nan
    
    if "Dem_score" not in df_out.columns or df_out["Dem_score"].isna().all():
        df_out["Dem_score"] = df_out.get("dem_score", pd.Series(np.nan, index=df_out.index))
    
    if "SS_score" not in df_out.columns or df_out["SS_score"].isna().all():
        ss_parts = [c for c in ["sup_score", "col_score"] if c in df_out.columns]
        df_out["SS_score"] = sum(df_out[c] for c in ss_parts) if ss_parts else np.nan
    
    # 6. Scores RH (mult=1)
    for group in RH_SCORE_GROUPS:
        col_name = f"{group}_score"
        computed = compute_group_score(df_out, group, multiplier=1)
        if computed.notna().any(): df_out[col_name] = computed
        elif col_name not in df_out.columns: df_out[col_name] = np.nan
    
    return df_out


def classify_karasek(df: pd.DataFrame) -> pd.DataFrame:
    """Classification en 4 quadrants + Job Strain + Iso-Strain"""
    df_out = df.copy()
    required = ["Dem_score", "Lat_score", "SS_score"]
    if any(c not in df_out.columns for c in required):
        return df_out
    
    DT = THRESHOLDS["Dem_score"]  # 22.5
    LT = THRESHOLDS["Lat_score"]  # 60.0
    ST = THRESHOLDS["SS_score"]   # 20.0
    
    # Quadrant principal
    df_out["Karasek_quadrant_theoretical"] = np.select(
        [(df_out["Lat_score"] >= LT) & (df_out["Dem_score"] >= DT),
        (df_out["Lat_score"] >= LT) & (df_out["Dem_score"] < DT),
        (df_out["Lat_score"] < LT) & (df_out["Dem_score"] >= DT)],
        ["Actif", "Detendu", "Tendu"], default="Passif"
    )
    
    # Job Strain
    df_out["Job_strain_theoretical"] = np.where(
        (df_out["Dem_score"] >= DT) & (df_out["Lat_score"] < LT), "Présent", "Absent"
    )
    
    # Iso-Strain
    df_out["Iso_strain_theoretical"] = np.where(
        (df_out["Dem_score"] >= DT) & (df_out["SS_score"] < ST), "Présent", "Absent"
    )
    
    # Catégories Faible/Élevé
    for col, thresh in THRESHOLDS.items():
        if col in df_out.columns:
            df_out[f"{col}_theo_cat"] = np.where(
                df_out[col].isna(), "Non renseigné",
                np.where(df_out[col] <= thresh, "Faible", "Élevé")
            )
    
    return df_out


# =============================================================================
# COMPOSANTS KPI STANDARDS
# =============================================================================

def kpi_card(icon_class: str, icon_color: str, icon_bg: str, accent_color: str,
            value, suffix: str, subtitle: str, label: str) -> str:
    return f"""<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;padding:20px 16px 16px;text-align:center;box-shadow:0 2px 12px rgba(15,23,42,0.06);border-top:3px solid {accent_color};transition:transform 0.2s ease,box-shadow 0.2s ease;min-height:160px;display:flex;flex-direction:column;justify-content:space-between;" onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 24px {accent_color}30';" onmouseout="this.style.transform='none';this.style.boxShadow='0 2px 12px rgba(15,23,42,0.06)';"><div><div style="width:40px;height:40px;background:{icon_bg};border-radius:10px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;"><i class="{icon_class}" style="color:{icon_color};font-size:16px;"></i></div><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;margin:0 0 6px 0;">{label}</p></div><div><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:28px;font-weight:800;color:#0F172A;margin:0;line-height:1;letter-spacing:-0.03em;">{value}<span style="font-size:13px;font-weight:500;color:#94A3B8;">{suffix}</span></p><p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:11px;color:#94A3B8;margin:4px 0 0 0;">{subtitle}</p></div></div>"""


def _compute_cardio_risk(df: pd.DataFrame) -> tuple:
    n = max(len(df), 1); score = 0.0
    if 'imc' in df.columns:
        imc = pd.to_numeric(df['imc'], errors='coerce')
        score += float((imc >= 25).sum()/n)*1.0 + float((imc >= 30).sum()/n)*2.0
    for col, val, w in [('tabagisme','oui',2.0),('consommation_alcool','oui',1.0),('maladie_chronique','oui',2.0),('pratique_sport','non',1.0)]:
        if col in df.columns:
            s = df[col].astype(str).str.lower().str.strip()
            score += float((s.isin(['oui','yes','1','vrai','true'])).sum()/n)*w
    score = round(score,2)
    if score <= 1.5: return score,"Faible","#16A37F"
    elif score <= 3.0: return score,"Modéré","#F5A623"
    else: return score,"Élevé","#E8504A"


def render_kpi_row(df: pd.DataFrame, n_before_cleaning: int = None) -> None:
    n = len(df)
    if n_before_cleaning is None: n_before_cleaning = n

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
        age_clean = age_str[~age_str.str.lower().isin(['non renseigné', 'nan', '', 'none'])]
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
        anc_clean = anc_str[~anc_str.str.lower().isin(['non renseigné','nan','','none'])]
        if not anc_clean.empty:
            vc = anc_clean.value_counts(); anc_display = vc.index[0]
            anc_subtitle = f"Classe dominante ({(vc.iloc[0]/len(anc_clean))*100:.0f}%)"
        else: anc_display, anc_subtitle = "—","non disponible"
    elif 'anciennete' in df.columns:
        anc_num = pd.to_numeric(df['anciennete'], errors='coerce').dropna()
        if not anc_num.empty: anc_display = f"{round(anc_num.median())} ans"; anc_subtitle = "médiane"
        else: anc_display, anc_subtitle = "—","non disponible"
    else: anc_display, anc_subtitle = "—","non disponible"

    if 'genre' in df.columns:
        genre_clean = df['genre'].dropna()
        if not genre_clean.empty:
            nb_h = int((genre_clean=='homme').sum()); nb_f = int((genre_clean=='femme').sum())
            if nb_h >= nb_f:
                genre_display = f"{(nb_h/n)*100:.0f}%"; genre_subtitle = f"Hommes ({nb_h})"
                genre_icon="fas fa-male"; genre_color="#1D78F5"; genre_bg="#EBF3FF"
            else:
                genre_display = f"{(nb_f/n)*100:.0f}%"; genre_subtitle = f"Femmes ({nb_f})"
                genre_icon="fas fa-female"; genre_color="#EC4899"; genre_bg="#FCE7F3"
        else: genre_display,genre_subtitle,genre_icon,genre_color,genre_bg = "—","non disponible","fas fa-venus-mars","#94A3B8","#F1F5F9"
    else: genre_display,genre_subtitle,genre_icon,genre_color,genre_bg = "—","non disponible","fas fa-venus-mars","#94A3B8","#F1F5F9"

    cardio_score, cardio_label, cardio_color = _compute_cardio_risk(df)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(kpi_card("fas fa-users","#1D78F5","#EBF3FF","#1D78F5",n,"",f"sur {n_before_cleaning} observations","Répondants analysés"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(genre_icon,genre_color,genre_bg,genre_color,genre_display,"",genre_subtitle,"Genre dominant"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("fas fa-calendar-alt","#16A37F","#E8F8EF","#16A37F",age_display,"",age_subtitle,"Âge"), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("fas fa-clock","#F5A623","#FEF5E7","#F5A623",anc_display,"",anc_subtitle,"Ancienneté"), unsafe_allow_html=True)
    with c5: st.markdown(kpi_card("fas fa-heart",cardio_color,"#FEF0EF",cardio_color,cardio_label,"",f"Score {cardio_score:.1f}/5","Risque cardio-vasc."), unsafe_allow_html=True)


# =============================================================================
# FONCTIONS INDICATEURS AVEC COMPARAISON AUTOMATIQUE
# =============================================================================

def get_priority_info(priorite_type: str) -> tuple:
    """
    Retourne les informations de style selon le type de priorite
    
    Types disponibles:
    - "risque": couleur rouge, alerte prioritaire
    - "vigilance": couleur orange, a surveiller
    - "levier": couleur verte, performance OK
    - "strategique": couleur bleue, suivi strategique
    """
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
    """
    Compare une valeur avec un seuil selon l'operateur
    Retourne True si la condition est vraie (indique un danger/alerte)
    """
    try:
        # Nettoyer la valeur (enlever le % si present)
        if isinstance(valeur, str):
            valeur_clean = valeur.replace('%', '').replace(',', '.').strip()
            val_num = float(valeur_clean)
        else:
            val_num = float(valeur)
        
        # Nettoyer le seuil
        if isinstance(seuil, str):
            seuil_clean = seuil.replace('%', '').replace(',', '.').strip()
            seuil_num = float(seuil_clean)
        else:
            seuil_num = float(seuil)
        
        # Comparaison selon l'operateur
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
            # Par defaut, on considere que depasser le seuil est l'alerte
            return val_num > seuil_num
    except (ValueError, TypeError):
        return False


def get_dynamic_priority(valeur, seuil: str, operateur: str, priorite_alerte: str) -> tuple:
    """
    Determine dynamiquement la priorite a afficher en comparant la valeur avec le seuil
    
    Regles:
    - Si la valeur DEPASSE le seuil (comparaison selon operateur) -> on applique priorite_alerte (risque/vigilance)
    - Sinon -> c'est "levier performance" (vert) car c'est bon
    """
    # Verifier si le seuil est depasse
    seuil_depasse = comparer_valeur_seuil(valeur, seuil, operateur)
    
    if seuil_depasse:
        return get_priority_info(priorite_alerte)
    else:
        return get_priority_info("levier")


def render_indicator_card(nom: str, valeur, seuil: str = None, operateur: str = "", priorite_type: str = "levier") -> str:
    """
    Affiche une carte d'indicateur avec style determine dynamiquement
    
    Parametres:
    - nom: Nom de l'indicateur
    - valeur: Valeur a afficher (sera convertie en str)
    - seuil: Valeur seuil (optionnel)
    - operateur: Operateur de comparaison (">", "<", ">=", "<=")
    - priorite_type: Priorite a afficher SI le seuil est depasse
    """
    if valeur is None:
        return '<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:12px;padding:16px;text-align:center;min-height:170px;display:flex;align-items:center;justify-content:center;"><p style="color:#94A3B8;font-size:0.85rem;">Donnees<br>insuffisantes</p></div>'
    
    # Determiner dynamiquement la priorite a afficher
    if seuil is not None and operateur:
        bordure_color, priorite_texte, priorite_color = get_dynamic_priority(
            valeur, seuil, operateur, priorite_type
        )
    else:
        # Pas de seuil defini -> on affiche la priorite statique
        bordure_color, priorite_texte, priorite_color = get_priority_info(priorite_type)
    
    valeur_color = bordure_color
    priorite_bg = bordure_color + "18"
    
    # Construction du texte du seuil
    seuil_str = ""
    if seuil is not None:
        if operateur:
            seuil_str = f"Seuil {operateur} {seuil}"
        else:
            seuil_str = f"Seuil : {seuil}"
    
    # Taille adaptative
    valeur_str = str(valeur)
    taille_police = "36px" if len(valeur_str) <= 10 else "22px"
    
    return f'<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;padding:20px 14px 16px;text-align:center;box-shadow:0 2px 10px rgba(15,23,42,0.06);border-top:4px solid {bordure_color};min-height:190px;display:flex;flex-direction:column;justify-content:space-between;"><div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:14px;font-weight:700;color:#1E293B;margin:0;line-height:1.3;">{nom}</p></div><div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:{taille_police};font-weight:800;color:{valeur_color};margin:8px 0;line-height:1;">{valeur}</p><span style="display:inline-block;padding:4px 14px;border-radius:999px;font-size:10px;font-weight:600;color:{priorite_color};background:{priorite_bg};margin:8px 0 4px;">{priorite_texte}</span><p style="font-size:9px;color:#94A3B8;margin:0 0 6px;">{seuil_str}</p></div></div>'


# =============================================================================
# CHARGEMENT DES DONNÉES
# =============================================================================

@st.cache_data(show_spinner=False)
def load_data_from_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    buf = io.BytesIO(file_bytes)
    if file_name.lower().endswith(".csv"): df = pd.read_csv(buf, sep=None, engine="python")
    else: df = pd.read_excel(buf)
    df.columns = [str(col).strip() for col in df.columns]
    return df


# =============================================================================
# POINT D'ENTRÉE STREAMLIT
# =============================================================================

def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")
    init_mode(PAGE_KEY); current_mode = get_mode(PAGE_KEY); inject_shared_css(current_mode)
    
    st.markdown("""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap" rel="stylesheet">""", unsafe_allow_html=True)
    
    # TOPBAR
    col_top, col_switch, col_back = st.columns([5,3,1])
    with col_top:
        st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;background:white;border-radius:12px;padding:14px 24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06),0 4px 12px rgba(30,110,79,0.08);border:1px solid #e8edf5;"><div style="width:38px;height:38px;background:linear-gradient(135deg,#1e6e4f,#3aaa7a);border-radius:10px;display:flex;align-items:center;justify-content:center;"><i class="fas fa-brain" style="color:white;font-size:15px;"></i></div><div><div style="font-size:16px;font-weight:700;color:#1e293b;font-family:'Plus Jakarta Sans',sans-serif;">Modele de Karasek — Demande–Controle–Soutien</div><div style="font-size:11px;color:#64748b;margin-top:1px;font-family:'Plus Jakarta Sans',sans-serif;">Analyse des risques psychosociaux au travail (Job Strain et Iso-Strain)</div></div></div>""", unsafe_allow_html=True)
    with col_switch:
        st.markdown('<div style="margin-top:4px;">', unsafe_allow_html=True)
        current_mode = render_mode_switcher(key=PAGE_KEY, position="topbar")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_back:
        if st.button("← Accueil", key=f"back_home_{PAGE_KEY}", use_container_width=True): st.switch_page("app.py")
    
    # UPLOAD
    uploaded_file = st.file_uploader("Charger un fichier Excel ou CSV", type=["xlsx","xls","csv"], key=f"uploader_{PAGE_KEY}")
    if uploaded_file is not None:
        st.session_state[f"_file_bytes_{PAGE_KEY}"] = uploaded_file.read()
        st.session_state[f"_file_name_{PAGE_KEY}"] = uploaded_file.name
    if f"_file_bytes_{PAGE_KEY}" not in st.session_state:
        st.info("Veuillez charger un fichier de donnees pour demarrer l'analyse."); st.stop()
    
    file_bytes = st.session_state[f"_file_bytes_{PAGE_KEY}"]
    file_name = st.session_state[f"_file_name_{PAGE_KEY}"]
    
    with st.spinner("Chargement et traitement des donnees…"):
        df_raw = load_data_from_bytes(file_bytes, file_name)
        n_before = len(df_raw)
        df_clean, cleaning_log = clean_common_variables(df_raw)
        
    with st.expander("Journal de nettoyage", expanded=False):
        st.text(cleaning_log)
        st.text(f"Items Karasek : {sum(1 for item in KARASEK_ITEMS if trouver_colonne_karasek(df_clean, item) is not None)}/{len(KARASEK_ITEMS)}")
        st.write(f"Avant: **{n_before}** — Apres: **{len(df_clean)}**")
    
    if df_clean.empty: st.error("Aucune donnee exploitable."); st.stop()
    
    # VERIFICATION KARASEK
    karasek_trouvees = sum(1 for item in KARASEK_ITEMS if trouver_colonne_karasek(df_clean, item) is not None)
    if karasek_trouvees < 40:
        st.error(f"""ERREUR - Fichier non reconnu comme un questionnaire Karasek
        Seulement **{karasek_trouvees}/{len(KARASEK_ITEMS)}** items detectes.
        Solution : Chargez ce fichier dans le module approprie.""")
        st.stop()
    
    # Scoring Karasek
    df_clean = compute_all_scores(df_clean)
    df_clean = classify_karasek(df_clean)
    
    # ONGLETS
    if is_medecin(current_mode):
        onglet1, onglet2, onglet3 = st.tabs(["Vue d'ensemble", "Analyses univariees", "Analyse bivariee"])
    else:
        onglet1, onglet2 = st.tabs(["Vue d'ensemble", "Analyses univariees"])
        onglet3 = None
    
    # ONGLET 1 : VUE D'ENSEMBLE
    with onglet1:
        FILTER_VARS = [
            ("Genre", "genre"),
            ("Situation matrimoniale", "situation_matrimoniale"),
            ("Tranche d'age", "Tranche_dage"),
            ("Tranche anciennete", "Tranche_anciennete"),
            ("Categorie IMC", "Categorie_IMC"),
            ("IMC (normal/surpoids)", "IMC_binaire"),
            ("Direction", "direction"),
            ("Fonction", "fonction"),
            ("Service", "service"),
            ("Departement", "departement"),
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
                sel_cat_label = st.selectbox("Variable (categorielle)", cat_labels, key="kar_filtre_cat")
            
            with fc2:
                if sel_cat_label != "— Aucun —":
                    cat_col = dict(cat_vars)[sel_cat_label]
                    modalites = sorted(df_clean[cat_col].dropna().astype(str).unique().tolist())
                    sel_modalite = st.selectbox("Modalite", ["Toutes"] + modalites, key="kar_filtre_mod")
                else:
                    sel_modalite = "Toutes"
                    st.selectbox("Modalite", ["Toutes"], disabled=True)
            
            with fc3:
                num_labels = ["— Aucun —"] + [l for l, _ in num_vars]
                sel_num_label = st.selectbox("Variable (numerique)", num_labels, key="kar_filtre_num")
                
                if sel_num_label != "— Aucun —":
                    num_col = dict(num_vars)[sel_num_label]
                    vals = pd.to_numeric(df_clean[num_col], errors="coerce").dropna()
                    if not vals.empty:
                        vmin, vmax = int(vals.min()), int(vals.max())
                        if vmin == vmax:
                            vmax = vmin + 1
                        sel_range = st.slider(f"Plage — {sel_num_label}", vmin, vmax, (vmin, vmax), key="kar_filtre_range")
                    else:
                        sel_range = None
                        st.slider(f"Plage — {sel_num_label}", 0, 100, (0, 100), disabled=True)
                else:
                    sel_range = None
            
            with fc4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Reinitialiser", key="kar_reset_filtres", use_container_width=True):
                    for k in ["kar_filtre_cat", "kar_filtre_mod", "kar_filtre_num", "kar_filtre_range"]:
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
        
        st.markdown('<div class="section-title">Donnees Generales de la Population</div>', unsafe_allow_html=True)
        render_kpi_row(df_filtered, n_before_cleaning=n_before)
        
        n = len(df_filtered)
        quad_col = "Karasek_quadrant_theoretical"
        
        # Indicateurs RH/DG
        if is_rh(current_mode):
            st.markdown('<div class="section-title">Indicateurs RH/DG</div>', unsafe_allow_html=True)
            
            nb_tendu = int((df_filtered.get(quad_col) == 'Tendu').sum()) if quad_col in df_filtered.columns else 0
            pct_job_strain = round((nb_tendu/n)*100, 1) if n > 0 else 0
            
            lat_moyen = round(df_filtered['Lat_score'].mean(), 1) if 'Lat_score' in df_filtered.columns else None
            dem_moyen = round(df_filtered['Dem_score'].mean(), 1) if 'Dem_score' in df_filtered.columns else None
            ss_moyen = round(df_filtered['SS_score'].mean(), 1) if 'SS_score' in df_filtered.columns else None
            
            nb_iso = int((df_filtered.get('Iso_strain_theoretical') == 'Présent').sum()) if 'Iso_strain_theoretical' in df_filtered.columns else 0
            pct_iso = round((nb_iso/n)*100, 1) if n > 0 else 0
            
            indicateurs_rh = [
                {"nom": "Collaborateurs en Job Strain", "valeur": f"{pct_job_strain:.1f}%", "seuil": "25%", "operateur": ">", "priorite_type": "risque"},
                {"nom": "Score latitude decisionnelle", "valeur": f"{lat_moyen:.1f}" if lat_moyen else "N/A", "seuil": "70", "operateur": "<", "priorite_type": "risque"},
                {"nom": "Score demandes psychologiques", "valeur": f"{dem_moyen:.1f}" if dem_moyen else "N/A", "seuil": "40", "operateur": ">", "priorite_type": "vigilance"},
                {"nom": "Score soutien social", "valeur": f"{ss_moyen:.1f}" if ss_moyen else "N/A", "seuil": "20", "operateur": ">", "priorite_type": "vigilance"},
                {"nom": "Iso-Strain", "valeur": f"{pct_iso:.1f}%", "seuil": "10%", "operateur": ">", "priorite_type": "risque"},
            ]
            cols = st.columns(5)
            for i, indic in enumerate(indicateurs_rh):
                with cols[i]: 
                    st.markdown(render_indicator_card(
                        indic["nom"], indic["valeur"], 
                        indic.get("seuil"), indic.get("operateur", ""), 
                        indic["priorite_type"]
                    ), unsafe_allow_html=True)
        
        # Indicateurs Medecin
        if is_medecin(current_mode):
            st.markdown('<div class="section-title">Indicateurs Medecin du Travail</div>', unsafe_allow_html=True)
            
            nb_iso = int((df_filtered.get('Iso_strain_theoretical') == 'Présent').sum()) if 'Iso_strain_theoretical' in df_filtered.columns else 0
            pct_iso = round((nb_iso/n)*100, 1) if n > 0 else 0
            
            sup_moyen = round(df_filtered['sup_score'].mean()/4, 1) if 'sup_score' in df_filtered.columns else None
            dem_moyen = round(df_filtered['Dem_score'].mean(), 1) if 'Dem_score' in df_filtered.columns else None
            lat_moyen = round(df_filtered['Lat_score'].mean(), 1) if 'Lat_score' in df_filtered.columns else None
            
            indicateurs_med = [
                {"nom": "Prevalence Iso-Strain", "valeur": f"{pct_iso:.1f}%", "seuil": "10%", "operateur": ">", "priorite_type": "risque"},
                {"nom": "Soutien social superviseur", "valeur": f"{sup_moyen:.1f}/4" if sup_moyen else "N/A", "seuil": "2.3", "operateur": "<", "priorite_type": "vigilance"},
                {"nom": "Demandes psychologiques", "valeur": f"{dem_moyen:.1f}" if dem_moyen else "N/A", "seuil": "22.5", "operateur": ">", "priorite_type": "risque"},
                {"nom": "Latitude decisionnelle", "valeur": f"{lat_moyen:.1f}" if lat_moyen else "N/A", "seuil": "60", "operateur": "<", "priorite_type": "vigilance"},
                {"nom": "Tendu (Job Strain)", "valeur": f"{round((df_filtered.get(quad_col)=='Tendu').sum()/n*100,1):.1f}%" if quad_col in df_filtered.columns else "N/A", "seuil": "25%", "operateur": ">", "priorite_type": "risque"},
            ]
            cols = st.columns(5)
            for i, indic in enumerate(indicateurs_med):
                with cols[i]: 
                    st.markdown(render_indicator_card(
                        indic["nom"], indic["valeur"], 
                        indic.get("seuil"), indic.get("operateur", ""), 
                        indic["priorite_type"]
                    ), unsafe_allow_html=True)
    
    # ONGLET 2 : ANALYSES UNIVARIEES
    with onglet2:
        st.markdown('<div class="section-title">Analyses univariees</div>', unsafe_allow_html=True)
        VAR_OPTIONS = {}
        for label, col in [
            ("Quadrant Karasek","Karasek_quadrant_theoretical"),("Job Strain","Job_strain_theoretical"),("Iso Strain","Iso_strain_theoretical"),
            ("Genre","genre"),("Situation matrimoniale","situation_matrimoniale"),
            ("Tranche d'age","Tranche_dage"),("Tranche anciennete","Tranche_anciennete"),
            ("Categorie IMC","Categorie_IMC"),("IMC (normal/surpoids)","IMC_binaire"),
            ("Direction","direction"),("Fonction","fonction"),("Service","service"),("Departement","departement"),
            ("Tabagisme","tabagisme"),("Consommation d'alcool","consommation_alcool"),
            ("Maladie chronique","maladie_chronique"),("Handicap physique","handicap_physique"),
            ("Suivi psychologique","suivi_psychologique"),("Pratique sportive","pratique_sport"),
        ]:
            if col in df_clean.columns: VAR_OPTIONS[label] = col
        
        if not VAR_OPTIONS: st.info("Aucune variable disponible.")
        else:
            c_sel, _ = st.columns([1,2])
            with c_sel: sel_label = st.selectbox("Variable a visualiser", list(VAR_OPTIONS.keys()), key="uni_karasek")
            sel_col = VAR_OPTIONS.get(sel_label)
            if sel_col and sel_col in df_clean.columns:
                counts_u = df_clean[sel_col].value_counts(); total_u = counts_u.sum()
                pcts_u = (counts_u/total_u*100).round(1); n_bars = len(counts_u)
                stats_data = []
                for cat,eff,pct in zip(counts_u.index, counts_u.values, pcts_u.values):
                    stats_data.append({"Modalite":str(cat),"Effectif":int(eff),"Frequence":f"{pct:.1f}%"})
                stats_data.append({"Modalite":"TOTAL","Effectif":int(total_u),"Frequence":"100%"})
                
                c_chart, c_table = st.columns([7,3])
                with c_chart:
                    if sel_col == "Karasek_quadrant_theoretical":
                        bar_colors = [KARASEK_COLORS.get(str(cat), "#6B7280") for cat in counts_u.index]
                    else:
                        pal = ["#38A3E8","#F97316","#22C55E","#EF4444","#A78BFA","#06B6D4","#FB923C","#84CC16","#EC4899","#8B5CF6"]
                        bar_colors = [pal[i%len(pal)] for i in range(n_bars)]
                    
                    fig = go.Figure()
                    for i,(cat,pct,eff) in enumerate(zip(counts_u.index, pcts_u.values, counts_u.values)):
                        fig.add_trace(go.Bar(y=[str(cat)],x=[pct],orientation='h',
                            marker_color=bar_colors[i], marker=dict(opacity=0.9, line=dict(width=0)),
                            text=f"{pct:.1f}%  ({int(eff)})", textposition="outside",
                            textfont=dict(color="#6B88A8",size=12,family="Plus Jakarta Sans"), showlegend=False))
                    fig.update_layout(plot_bgcolor="#FAFCFF",paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Plus Jakarta Sans, sans-serif",color="#0F2340",size=12),
                        xaxis=dict(range=[0,max(pcts_u.values)*1.5],title_text="Pourcentage (%)",showgrid=True,gridcolor="#EDF5FD",gridwidth=1,showline=True,linecolor="#D6E8F7",zeroline=False,tickfont=dict(color="#6B88A8",size=11)),
                        yaxis=dict(showgrid=False,showline=False,zeroline=False,tickfont=dict(color="#0F2340",size=11)),
                        height=max(300,n_bars*55+120),margin=dict(l=20,r=80,t=60,b=40),
                        title=dict(text=f"Repartition selon : {sel_label}",font=dict(size=14,color="#0F2340",family="Plus Jakarta Sans"),x=0.5,xanchor="center"))
                    st.plotly_chart(fig, use_container_width=True, key="uni_karasek_plotly")
                
                with c_table:
                    st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Statistiques</p>', unsafe_allow_html=True)
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True, hide_index=True, height=min(400,35*(len(stats_data)+1)))
                    st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">Interpretation</p>', unsafe_allow_html=True)
                    modalites = list(counts_u.index)
                    if len(modalites) >= 2:
                        m1,m2 = modalites[0],modalites[1]; p1,p2 = pcts_u.iloc[0],pcts_u.iloc[1]
                        e1,e2 = int(counts_u.iloc[0]),int(counts_u.iloc[1])
                        st.markdown(f"""<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;font-family:'Plus Jakarta Sans',sans-serif;"><p style="margin:0 0 8px;">Ce graphique montre la repartition de <b>{sel_label}</b> parmi les {int(total_u)} repondants.</p><p style="margin:0 0 8px;">La modalite dominante est <b>« {m1} »</b> avec <b>{p1:.1f}%</b> des repondants ({e1} personne(s)).</p><p style="margin:0;">Elle est suivie par <b>« {m2} »</b> avec <b>{p2:.1f}%</b> ({e2} personne(s)). Au total, <b>{n_bars}</b> modalites.</p></div>""", unsafe_allow_html=True)
                    else: st.caption("Donnees insuffisantes.")
    
    # ONGLET 3 : ANALYSE BIVARIEE (Medecin uniquement)
    if onglet3 is not None:
        with onglet3:
            st.markdown('<div class="section-title">Analyse bivariee</div>', unsafe_allow_html=True)
            
            csp_actual = None
            for c in ("Categorie Socio", "Categorie Socio", "CSP"):
                if c in df_clean.columns: csp_actual = c; break
            
            alc_col2 = next((c for c in df_clean.columns if re.search(r"consommation.*alcool|alcool", _pp_normalize_text(c))), None)
            sport_col2 = _find_by_patterns(list(df_clean.columns), [r"pratique.*sport", r"\bsport\b"])
            tabac_col2 = _find_by_patterns(list(df_clean.columns), [r"tabag"])
            
            quad_col = "Karasek_quadrant_theoretical"
            dir_col_hm = next((c for c in df_clean.columns if _pp_normalize_text(c) == "direction"), None)
            
            VAR_MAP = {
                "Genre":                         "genre",
                "Tranche d'age":                 "Tranche_dage",
                "Anciennete":                    "Tranche_anciennete",
                "Categorie socioprofessionnelle": csp_actual or "",
                "Categorie IMC":                 "Categorie_IMC",
                "IMC (normal / surpoids)":       "IMC_binaire",
                "Direction":                     "direction",
                "Tabagisme":                     tabac_col2 or "",
                "Consommation d'alcool":         alc_col2 or "",
                "Pratique sportive":             sport_col2 or "",
                "Maladie chronique":             next((c for c in df_clean.columns if re.search(r"maladie.*chron", _pp_normalize_text(c))), ""),
            }
            
            CROSS_MAP = {
                "Aucun croisement":                 None,
                "Quadrant Karasek":                 quad_col,
                "Charge mentale (categ.)":          "Dem_score_theo_cat",
                "Autonomie decisionnelle (categ.)": "Lat_score_theo_cat",
                "Soutien social (categ.)":          "SS_score_theo_cat",
                "Reconnaissance (categ.)":          "rec_score_theo_cat",
                "Satisfaction (categ.)":            "sat_score_theo_cat",
                "Culture d'entreprise (categ.)":    "cult_score_theo_cat",
                "Equite de charge (categ.)":        "equ_score_theo_cat",
            }
            
            avail_vars  = [k for k, v in VAR_MAP.items()  if v and v in df_clean.columns]
            avail_cross = [k for k, v in CROSS_MAP.items() if v is None or (v and v in df_clean.columns)]
            
            if not avail_vars:
                st.info("Variables insuffisantes pour l'analyse bivariee.")
            else:
                cx1, cx2 = st.columns(2)
                with cx1:
                    st.markdown('<span style="font-size:0.76rem;font-weight:700;color:#2F577F;letter-spacing:0.1em;text-transform:uppercase;">Variable a visualiser</span>', unsafe_allow_html=True)
                    sel_var = st.selectbox("Variable", avail_vars, key="cr_var", label_visibility="collapsed")
                
                show_heatmap = (sel_var == "Direction" and dir_col_hm and quad_col and quad_col in df_clean.columns)
                
                cross_options = list(avail_cross)
                if show_heatmap:
                    cross_options = ["Heatmap "] + cross_options
                
                with cx2:
                    st.markdown('<span style="font-size:0.76rem;font-weight:700;color:#2F577F;letter-spacing:0.1em;text-transform:uppercase;">Croiser avec (optionnel)</span>', unsafe_allow_html=True)
                    sel_cross = st.selectbox("Croisement", cross_options, key="cr_cross", label_visibility="collapsed")
                
                real_col = VAR_MAP.get(sel_var) if sel_var else None
                
                # HEATMAP
                if sel_cross == "Heatmap ":
                    import matplotlib.pyplot as plt
                    from matplotlib.colors import LinearSegmentedColormap
                    import seaborn as sns
                    
                    ct_hm = pd.crosstab(df_clean[dir_col_hm], df_clean[quad_col], normalize="index") * 100
                    quads_hm = ["Tendu", "Actif", "Passif", "Detendu"]
                    for q in quads_hm:
                        if q not in ct_hm.columns: ct_hm[q] = 0
                    ct_hm = ct_hm.sort_values("Tendu", ascending=True)
                    
                    cmaps = {
                        "Tendu":   ["#ffffff", "#e74c3c"],
                        "Actif":   ["#ffffff", "#2ecc71"],
                        "Passif":  ["#ffffff", "#f39c12"],
                        "Detendu": ["#ffffff", "#3498db"],
                    }
                    
                    fig_hm, axes = plt.subplots(1, 4, figsize=(20, 1 + len(ct_hm) * 0.4), sharey=True)
                    fig_hm.patch.set_facecolor("#f8f9fa")
                    
                    for ax, q in zip(axes, quads_hm):
                        cm = LinearSegmentedColormap.from_list(f"c_{q}", cmaps[q])
                        sns.heatmap(ct_hm[[q]], ax=ax, cmap=cm, vmin=0, vmax=60, annot=True, fmt=".0f",
                                    annot_kws={"size": 8}, linewidths=0.5, linecolor="#eee", cbar=False)
                        ax.set_title(q.upper(), fontsize=11, fontweight="bold", color=cmaps[q][1])
                        ax.set_xlabel("%", fontsize=9)
                        ax.tick_params(axis="y", labelsize=9)
                        for spine in ax.spines.values(): spine.set_visible(False)
                    
                    plt.suptitle("Repartition Karasek par Direction — seuil theorique", fontsize=13, fontweight="bold", y=1.02)
                    plt.tight_layout()
                    st.pyplot(fig_hm, use_container_width=True)
                    
                    buf = io.BytesIO()
                    fig_hm.savefig(buf, format="png", dpi=300, bbox_inches="tight")
                    buf.seek(0)
                    st.download_button("Telecharger PNG", data=buf, file_name="heatmap_direction.png", mime="image/png", key="dl_hm")
                    plt.close(fig_hm)
                
                # CROISEMENT STANDARD
                else:
                    cross_col = CROSS_MAP.get(sel_cross) if sel_cross else None
                    
                    if real_col and real_col in df_clean.columns and cross_col and cross_col in df_clean.columns:
                        tmp = df_clean[[real_col, cross_col]].dropna()
                        if not tmp.empty:
                            ct  = pd.crosstab(tmp[real_col].astype(str), tmp[cross_col].astype(str))
                            pct = ct.div(ct.sum(axis=1), axis=0) * 100
                            
                            bmap = {"Eleve":"#22C55E","Eleve":"#22C55E","Faible":"#EF4444","Present":"#EF4444","Absent":"#22C55E"}
                            gen  = ["#38A3E8","#F97316","#22C55E","#EF4444","#A78BFA","#06B6D4"]
                            
                            def gc(cat, idx):
                                if cat in KARASEK_COLORS: return KARASEK_COLORS[cat]
                                if cat in bmap: return bmap[cat]
                                return gen[idx % len(gen)]
                            
                            c_chart, c_table = st.columns([7, 3])
                            with c_chart:
                                fig = go.Figure()
                                for i, cat in enumerate(pct.columns):
                                    vals, ns = pct[cat].values, ct[cat].values
                                    txts = [f"{v:.1f}%  ({n})" if v >= 6 else "" for v, n in zip(vals, ns)]
                                    fig.add_trace(go.Bar(
                                        name=str(cat), y=list(pct.index), x=vals, orientation="h",
                                        marker_color=gc(str(cat), i), marker=dict(opacity=0.9, line=dict(width=0)),
                                        text=txts, textposition="inside", insidetextanchor="middle",
                                        textfont=dict(color="white", size=11, family="Plus Jakarta Sans")
                                    ))
                                fig.update_layout(
                                    barmode="stack", plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
                                    font=dict(family="Plus Jakarta Sans, sans-serif", color="#0F2340", size=12),
                                    xaxis=dict(range=[0, 100], title_text="Pourcentage (%)", showgrid=True,
                                            gridcolor="#EDF5FD", gridwidth=1, showline=True,
                                            linecolor="#D6E8F7", zeroline=False, tickfont=dict(color="#6B88A8", size=11)),
                                    yaxis=dict(showgrid=False, showline=False, zeroline=False, tickfont=dict(color="#0F2340", size=11)),
                                    height=max(300, len(pct.index) * 55 + 120),
                                    margin=dict(l=20, r=20, t=50, b=40),
                                    title=dict(text=f"{sel_var} selon {sel_cross}", font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"), x=0.5, xanchor="center"),
                                    legend=dict(bgcolor="rgba(255,255,255,0.95)", bordercolor="#D6E8F7", borderwidth=1,
                                                font=dict(color="#0F2340", size=10), orientation="h", y=-0.30, x=0.5, xanchor="center")
                                )
                                st.plotly_chart(fig, use_container_width=True, key="cr_stacked")
                            
                            with c_table:
                                st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Tableau de distribution (%)</p>', unsafe_allow_html=True)
                                pct_tbl = pct.round(1)
                                st.dataframe(pct_tbl.style.format("{:.1f}%"), use_container_width=True)
                                
                                st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">Interpretation</p>', unsafe_allow_html=True)
                                lignes, colonnes = list(pct.index), list(pct.columns)
                                if len(lignes) >= 2 and len(colonnes) >= 1:
                                    l1, l2 = lignes[0], lignes[1]
                                    st.markdown(f"""<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;font-family:'Plus Jakarta Sans',sans-serif;"><p style="margin:0 0 8px;">Ce graphique montre la repartition de <b>{sel_cross}</b> selon <b>{sel_var}</b>.</p><p style="margin:0 0 8px;">Par exemple, parmi les <b>« {l1} »</b> : {', '.join([f'<b>{pct.loc[l1, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l1, c] > 0])}.</p><p style="margin:0;">Tandis que parmi les <b>« {l2} »</b> : {', '.join([f'<b>{pct.loc[l2, c]:.1f}%</b> sont <b>« {c} »</b>' for c in colonnes if pct.loc[l2, c] > 0])}.</p></div>""", unsafe_allow_html=True)
                                else:
                                    st.caption("Donnees insuffisantes.")
                        else:
                            st.warning("Donnees insuffisantes pour ce croisement.")
                    
                    # UNIVARIE
                    elif real_col and real_col in df_clean.columns:
                        counts_u = df_clean[real_col].value_counts()
                        total_u = counts_u.sum()
                        pcts_u = (counts_u / total_u * 100).round(1)
                        n_bars = len(counts_u)
                        
                        stats_data = []
                        for cat, eff, pct in zip(counts_u.index, counts_u.values, pcts_u.values):
                            stats_data.append({"Modalite": str(cat), "Effectif": int(eff), "Frequence": f"{pct:.1f}%"})
                        stats_data.append({"Modalite": "TOTAL", "Effectif": int(total_u), "Frequence": "100%"})
                        
                        c_chart, c_table = st.columns([7, 3])
                        with c_chart:
                            if real_col == "Karasek_quadrant_theoretical":
                                bar_colors = [KARASEK_COLORS.get(str(cat), "#6B7280") for cat in counts_u.index]
                            else:
                                pal = ["#38A3E8","#F97316","#22C55E","#EF4444","#A78BFA","#06B6D4","#FB923C","#84CC16"]
                                bar_colors = [pal[i%len(pal)] for i in range(len(counts_u))]
                            
                            fig = go.Figure()
                            for i, (cat, pct, eff) in enumerate(zip(counts_u.index, pcts_u.values, counts_u.values)):
                                fig.add_trace(go.Bar(
                                    y=[str(cat)], x=[pct], orientation='h',
                                    marker_color=bar_colors[i], marker=dict(opacity=0.9, line=dict(width=0)),
                                    text=f"{pct:.1f}%  ({int(eff)})", textposition="outside",
                                    textfont=dict(color="#6B88A8", size=12, family="Plus Jakarta Sans"), showlegend=False
                                ))
                            fig.update_layout(
                                plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="Plus Jakarta Sans, sans-serif", color="#0F2340", size=12),
                                xaxis=dict(range=[0, max(pcts_u.values)*1.5], title_text="Pourcentage (%)", showgrid=True,
                                        gridcolor="#EDF5FD", gridwidth=1, showline=True, linecolor="#D6E8F7",
                                        zeroline=False, tickfont=dict(color="#6B88A8", size=11)),
                                yaxis=dict(showgrid=False, showline=False, zeroline=False, tickfont=dict(color="#0F2340", size=11)),
                                height=max(300, n_bars*55+120), margin=dict(l=20, r=80, t=60, b=40),
                                title=dict(text=f"Repartition selon : {sel_var}", font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"), x=0.5, xanchor="center")
                            )
                            st.plotly_chart(fig, use_container_width=True, key="cr_bar")
                        
                        with c_table:
                            st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Statistiques</p>', unsafe_allow_html=True)
                            stats_df = pd.DataFrame(stats_data)
                            st.dataframe(stats_df, use_container_width=True, hide_index=True, height=min(400, 35*(len(stats_data)+1)))
                            
                            st.markdown('<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;text-transform:uppercase;margin:1rem 0 0.5rem;">Interpretation</p>', unsafe_allow_html=True)
                            modalites = list(counts_u.index)
                            if len(modalites) >= 2:
                                m1, m2 = modalites[0], modalites[1]
                                p1, p2 = pcts_u.iloc[0], pcts_u.iloc[1]
                                e1, e2 = int(counts_u.iloc[0]), int(counts_u.iloc[1])
                                st.markdown(f"""<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;font-family:'Plus Jakarta Sans',sans-serif;"><p style="margin:0 0 8px;">Ce graphique montre la repartition de <b>{sel_var}</b> parmi les {int(total_u)} repondants.</p><p style="margin:0 0 8px;">La modalite dominante est <b>« {m1} »</b> avec <b>{p1:.1f}%</b> des repondants ({e1} personne(s)).</p><p style="margin:0;">Elle est suivie par <b>« {m2} »</b> avec <b>{p2:.1f}%</b> ({e2} personne(s)). Au total, <b>{n_bars}</b> modalites.</p></div>""", unsafe_allow_html=True)
                            else:
                                st.caption("Donnees insuffisantes.")
                    else:
                        st.info("Selectionnez une variable pour afficher le graphique.")
    
    st.markdown("---")
    st.markdown(f'<p style="text-align:center;color:#9CA3AF;font-size:0.8rem;">{PAGE_TITLE} — YODAN Analytics © 2026</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()