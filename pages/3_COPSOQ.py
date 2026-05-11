# 3_COPSOQ.py — COPSOQ - Copenhagen Psychosocial Questionnaire
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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
# CONFIGURATION DE LA PAGE COPSOQ
# =============================================================================
PAGE_TITLE = "COPSOQ — Copenhagen Psychosocial Questionnaire"
PAGE_ICON = "📋"
PAGE_KEY = "copsoq_view_mode"

QUESTION_TEXT_MAP = {
    "Q1": "Prenez-vous du retard dans votre travail ?",
    "Q2": "Disposez-vous d'un temps suffisant pour accomplir vos taches professionnelles ?",
    "Q3": "Travaillez-vous a une cadence elevee tout au long de la journee ?",
    "Q4": "Est-il necessaire de maintenir un rythme soutenu au travail ?",
    "Q5": "Durant votre travail, devez-vous avoir l'oeil sur beaucoup de choses ?",
    "Q6": "Votre travail exige-t-il que vous vous souveniez de beaucoup de choses ?",
    "Q7": "Au travail, etes-vous informe(e) suffisamment a l'avance des decisions importantes, des changements ou de projets futurs ?",
    "Q8": "Recevez-vous toutes les informations dont vous avez besoin pour bien faire votre travail ?",
    "Q9": "Votre travail est-il reconnu et apprecie par le management ?",
    "Q10": "Etes-vous traite(e) equitablement au travail ?",
    "Q11": "Les conflits sont-ils resolus de maniere equitable ?",
    "Q12": "Le travail est-il reparti equitablement ?",
    "Q13": "Votre travail a-t-il des objectifs clairs ?",
    "Q14": "Savez-vous exactement ce que l'on attend de vous au travail ?",
    "Q15": "Au travail, etes-vous soumis(e) a des demandes contradictoires ?",
    "Q16": "Devez-vous parfois faire des choses qui auraient du etre faites autrement ?",
    "Q17": "Dans quelle mesure diriez-vous que votre superieur(e) hierarchique accorde une grande priorite a la satisfaction au travail ?",
    "Q18": "Dans quelle mesure diriez-vous que votre superieur(e) hierarchique est competent(e) dans la planification du travail ?",
    "Q19": "A quelle frequence votre superieur(e) hierarchique est-il (elle) dispose(e) a vous ecouter au sujet de vos problemes au travail ?",
    "Q20": "A quelle frequence recevez-vous de l'aide et du soutien de votre superieur(e) hierarchique ?",
    "Q21": "Le management fait-il confiance aux salaries quant a leur capacite a bien faire leur travail ?",
    "Q22": "Pouvez-vous faire confiance aux informations venant du management ?",
    "Q23": "Y a-t-il une bonne cooperation entre les collegues au travail ?",
    "Q24": "Dans l'ensemble, les salaries se font-ils confiance entre eux ?",
    "Q25": "A quelle frequence recevez-vous de l'aide et du soutien de vos collegues ?",
    "Q26": "A quelle frequence vos collegues se montrent-ils a l'ecoute de vos problemes au travail ?",
    "Q27": "Avez-vous une grande marge de manoeuvre dans votre travail ?",
    "Q28": "Pouvez-vous intervenir sur la quantite de travail qui vous est attribuee ?",
    "Q29": "Votre travail necessite-t-il que vous preniez des initiatives ?",
    "Q30": "Votre travail vous donne-il la possibilite d'apprendre des choses nouvelles ?",
    "Q31": "En general, diriez-vous que votre sante est :",
    "Q32": "A quelle frequence avez-vous ete irritable ?",
    "Q33": "A quelle frequence avez-vous ete stresse(e) ?",
    "Q34": "A quelle frequence vous etes-vous senti(e) a bout de force ?",
    "Q35": "A quelle frequence avez-vous ete emotionnellement epuise(e) ?",
    "Q36": "Votre travail vous place-t-il dans des situations destabilisantes sur le plan emotionnel ?",
    "Q37": "Votre travail est-il eprouvant sur le plan emotionnel ?",
    "Q38": "Sentez-vous que votre travail vous prend tellement d'energie que cela a un impact negatif sur votre vie privee ?",
    "Q39": "Sentez-vous que votre travail vous prend tellement de temps que cela a un impact negatif sur votre vie privee ?",
    "Q40": "Etes-vous inquiet(ete) a l'idee de perdre votre emploi ?",
    "Q41": "Craignez-vous d'etre mute(e) a un autre poste de travail contre votre volonte ?",
    "Q42": "Votre travail a-t-il du sens pour vous ?",
    "Q43": "Avez-vous le sentiment que le travail que vous faites est important ?",
    "Q44": "Recommanderiez-vous a un ami proche de postuler sur un emploi dans votre entreprise ?",
    "Q45": "Pensez-vous que votre entreprise est d'une grande importance pour vous ?",
    "Q46": "A quel point etes-vous satisfait(e) de votre travail dans son ensemble, en prenant en consideration tous les aspects ?",
}

# ══════════════════════════════════════════════════════════════════════════════
# SOUS-DOMAINES ET DOMAINES RPS (issus de 5_COPSOQ)
# ══════════════════════════════════════════════════════════════════════════════

SUBDOMAINS_LABELS = {
    "Charge de travail": ["Q1", "Q2"],
    "Rythme travail": ["Q3", "Q4"],
    "Exigences cognitive": ["Q5", "Q6"],
    "Previsibilite": ["Q7", "Q8"],
    "Reconnaissance": ["Q9", "Q10"],
    "Equite": ["Q11", "Q12"],
    "Clarte des roles": ["Q13", "Q14"],
    "Conflit de roles": ["Q15", "Q16"],
    "Qualite de leadership du superieur hierarchique": ["Q17", "Q18"],
    "Soutien social de la part du superieur hierarchique": ["Q19", "Q20"],
    "Confiance entre les salaries et le management": ["Q21", "Q22"],
    "Confiance entre les collegues": ["Q23", "Q24"],
    "Soutien social entre les collegues": ["Q25", "Q26"],
    "Marge de manoeuvre": ["Q27", "Q28"],
    "Possibilites d'epanouissement": ["Q29", "Q30"],
    "Sante auto evaluee": ["Q31"],
    "Stress": ["Q32", "Q33"],
    "Epuisement": ["Q34", "Q35"],
    "Exigence emotionnelle": ["Q36", "Q37"],
    "Conflit famille-travail": ["Q38", "Q39"],
    "Insecurite Professionnelle": ["Q40", "Q41"],
    "Sens du travail": ["Q42", "Q43"],
    "Engagement dans l'entreprise": ["Q44", "Q45"],
    "Satisfaction au travail": ["Q46"],
}

# Domaines principaux → liste de (label_affichage, clé_sous_domaine)
RPS_DOMAINS_CFG = {
    "Contraintes Quantitatives": [
        ("Charge de travail", "Charge de travail"),
        ("Rythme de travail", "Rythme travail"),
        ("Exigences cognitive", "Exigences cognitive"),
    ],
    "Organisation et Leadership": [
        ("Previsibilite", "Previsibilite"),
        ("Reconnaissance", "Reconnaissance"),
        ("Equite", "Equite"),
        ("Clarte des roles", "Clarte des roles"),
        ("Conflit de roles", "Conflit de roles"),
        ("Qualite de leadership du superieur hierarchique", "Qualite de leadership du superieur hierarchique"),
        ("Soutien social de la part du superieur hierarchique", "Soutien social de la part du superieur hierarchique"),
        ("Confiance entre les salaries et le management", "Confiance entre les salaries et le management"),
    ],
    "Relations Horizontales": [
        ("Confiance entre les collegues", "Confiance entre les collegues"),
        ("Soutien social de la part des collegues", "Soutien social entre les collegues"),
    ],
    "Autonomie": [
        ("Marge de manoeuvre", "Marge de manoeuvre"),
        ("Possibilites d'epanouissement", "Possibilites d'epanouissement"),
    ],
    "Sante et Bien-etre": [
        ("Sante auto evaluee", "Sante auto evaluee"),
        ("Stress", "Stress"),
        ("Epuisement", "Epuisement"),
        ("Exigence emotionnelle", "Exigence emotionnelle"),
        ("Conflit famille-travail", "Conflit famille-travail"),
        ("Insecurite professionnelle", "Insecurite Professionnelle"),
    ],
    "Vecu Professionnel": [
        ("Sens du travail", "Sens du travail"),
        ("Engagement dans l'entreprise", "Engagement dans l'entreprise"),
        ("Satisfaction au travail", "Satisfaction au travail"),
    ],
}

ORDER_LEVELS = ["Tres faible", "Faible", "Fort", "Tres fort"]

LEVEL_COLORS_RISK = {"Tres faible": "#4ADE80", "Faible": "#FACC15", "Fort": "#FB923C", "Tres fort": "#EF4444"}
LEVEL_COLORS_GOOD = {"Tres faible": "#EF4444", "Faible": "#FB923C", "Fort": "#FACC15", "Tres fort": "#4ADE80"}

_SUBDOMAIN_POLARITY: dict = {
    "Charge de travail": "normal", "Rythme de travail": "normal", "Exigences cognitive": "normal",
    "Previsibilite": "inverted", "Reconnaissance": "inverted", "Equite": "inverted",
    "Clarte des roles": "inverted", "Conflit de roles": "normal",
    "Qualite de leadership du superieur hierarchique": "inverted",
    "Soutien social de la part du superieur hierarchique": "inverted",
    "Confiance entre les salaries et le management": "inverted",
    "Confiance entre les collegues": "inverted",
    "Soutien social de la part des collegues": "inverted",
    "Soutien social entre les collegues": "inverted",
    "Marge de manoeuvre": "inverted", "Possibilites d'epanouissement": "inverted",
    "Sante auto evaluee": "inverted", "Stress": "normal", "Epuisement": "normal",
    "Exigence emotionnelle": "normal", "Conflit famille-travail": "normal",
    "Insecurite professionnelle": "normal", "Insecurite Professionnelle": "normal",
    "Sens du travail": "inverted", "Engagement dans l'entreprise": "inverted",
    "Satisfaction au travail": "inverted",
}

# ══════════════════════════════════════════════════════════════════════════════
# VARIABLES UNIFORMES POUR LES ANALYSES UNIVARIÉES
# ══════════════════════════════════════════════════════════════════════════════
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

    # SUPPRESSION OBSERVATIONS AVEC NA
    n_before_drop = len(cleaned_df)
    cleaned_df = cleaned_df.dropna()
    n_after_drop = len(cleaned_df)
    n_dropped = n_before_drop - n_after_drop
    if n_dropped > 0: ops.append(f"{n_dropped} observation(s) supprimée(s) — {n_after_drop} restantes")
    else: ops.append(f"Aucune observation avec valeurs manquantes — {n_after_drop} observations conservées")

    cleaning_log = "Nettoyage appliqué:\n- " + "\n- ".join(ops) if ops else "Aucune opération appliquée."
    return cleaned_df, cleaning_log


# =============================================================================
# FONCTIONS DE DÉTECTION COPSOQ — MAPPING Q → colonnes
# =============================================================================

def trouver_colonne_q(df: pd.DataFrame, qx: str) -> str | None:
    if qx in df.columns: return qx
    question_text = QUESTION_TEXT_MAP.get(qx)
    if question_text is None: return None
    target = _pp_normalize_text(question_text)
    best_col = None; best_score = -1.0
    for col in df.columns:
        col_norm = _pp_normalize_text(col)
        score = SequenceMatcher(None, target, col_norm).ratio()
        if score > best_score: best_score = score; best_col = col
    if best_col is not None and best_score >= 0.4: return best_col
    return None


def calculer_indicateur_par_noms(df: pd.DataFrame, qx_list: list) -> float | None:
    colonnes_trouvees = []
    for qx in qx_list:
        col = trouver_colonne_q(df, qx)
        if col is not None: colonnes_trouvees.append(col)
    if not colonnes_trouvees: return None
    valeurs = pd.DataFrame()
    for col in colonnes_trouvees:
        serie = pd.to_numeric(df[col], errors='coerce')
        if serie.max() <= 5: serie = ((serie - 1) / 4 * 100).clip(0, 100)
        valeurs[col] = serie
    return float(valeurs.mean(axis=1).mean())


# =============================================================================
# CALCUL DES SCORES SOUS-DOMAINES (normalisés 0-100 sur l'ensemble du df)
# =============================================================================

def _to_numeric_safe(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_df_scores_from_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit un DataFrame de scores (0-100) par sous-domaine pour
    chaque répondant, en cherchant les colonnes Q1..Q46 par fuzzy matching.
    """
    # Résoudre les colonnes Q
    q_map = {}
    for qx in QUESTION_TEXT_MAP:
        col = trouver_colonne_q(df, qx)
        if col is not None:
            q_map[qx] = col

    scores = pd.DataFrame(index=df.index)
    for subdomain_name, questions in SUBDOMAINS_LABELS.items():
        available_cols = [q_map[q] for q in questions if q in q_map]
        if not available_cols:
            scores[subdomain_name] = np.nan
            continue
        raw = df[available_cols].apply(_to_numeric_safe)
        # Normaliser 1-5 → 0-100 si nécessaire
        if raw.max().max() <= 5:
            raw = ((raw - 1) / 4 * 100).clip(0, 100)
        scores[subdomain_name] = raw.mean(axis=1)
    return scores


# =============================================================================
# FONCTIONS RPS DOMAINES (portées depuis 5_COPSOQ)
# =============================================================================

def _normalize_to_four_levels(series: pd.Series) -> pd.Series:
    mapping = {
        "Tres faible": "Tres faible", "Très faible": "Tres faible",
        "Faible": "Faible", "Modere": "Faible", "Modéré": "Faible",
        "Fort": "Fort",
        "Tres fort": "Tres fort", "Très fort": "Tres fort",
    }
    return series.astype("object").map(lambda v: mapping.get(str(v).strip(), str(v)))


def _categorize_to_four_levels(series: pd.Series) -> pd.Series:
    num = _to_numeric_safe(series)
    if num.dropna().empty:
        return pd.Series([np.nan] * len(series), index=series.index)
    q25, q50, q75 = num.quantile(0.25), num.quantile(0.50), num.quantile(0.75)
    def _classify(v):
        if pd.isna(v): return np.nan
        if v <= q25: return "Tres faible"
        if v <= q50: return "Faible"
        if v <= q75: return "Fort"
        return "Tres fort"
    return num.apply(_classify)


def _build_rps_domain_categories(score_df: pd.DataFrame) -> tuple:
    """Construit le df catégoriel domaine, domain_map, missing, label_map."""
    out = pd.DataFrame(index=score_df.index)
    domain_map: dict = {}
    missing: list = []
    label_map: dict = {}
    for domain, items in RPS_DOMAINS_CFG.items():
        domain_cols: list = []
        for label, score_col in items:
            if score_col not in score_df.columns:
                missing.append({"Groupe": domain, "Sous-domaine": label, "Colonne attendue": score_col})
                continue
            cat_col = f"{label}__Categorie"
            out[cat_col] = _categorize_to_four_levels(score_df[score_col])
            domain_cols.append(cat_col)
            label_map[cat_col] = label
        domain_map[domain] = domain_cols
    return out, domain_map, missing, label_map


def _colors_for_subdomain(label: str) -> dict:
    polarity = _SUBDOMAIN_POLARITY.get(label, "normal")
    return LEVEL_COLORS_GOOD if polarity == "inverted" else LEVEL_COLORS_RISK


def _pct_text(value: float) -> str:
    rounded = round(float(value), 1)
    return f"{int(rounded)}%" if float(rounded).is_integer() else f"{rounded:.1f}%"


def _fig_to_png_bytes(fig) -> bytes | None:
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.25)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


def _plot_domain_stacked_bar(cat_df: pd.DataFrame, domain_cols: list, title: str, label_map: dict):
    valid_cols = [c for c in domain_cols if c in cat_df.columns]
    if not valid_cols:
        return None
    rows = []
    for col in valid_cols:
        collapsed = _normalize_to_four_levels(cat_df[col]).dropna()
        pct = collapsed.value_counts(normalize=True).mul(100).reindex(ORDER_LEVELS, fill_value=0)
        rows.append(pct)
    stacked = pd.DataFrame(rows, index=valid_cols)
    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.6 * len(valid_cols) + 1.5)))
    y = np.arange(len(stacked))
    row_labels = [label_map.get(col, col) for col in stacked.index]
    row_palettes = [_colors_for_subdomain(lbl) for lbl in row_labels]
    row_polarities = [_SUBDOMAIN_POLARITY.get(lbl, "normal") for lbl in row_labels]
    has_normal   = any(p == "normal"   for p in row_polarities)
    has_inverted = any(p == "inverted" for p in row_polarities)
    mixed = has_normal and has_inverted
    for i, (col, palette) in enumerate(zip(stacked.index, row_palettes)):
        left = 0.0
        for level in ORDER_LEVELS:
            v = float(stacked.loc[col, level])
            ax.barh(i, v, left=left, color=palette[level])
            if v > 0:
                ax.text(left + v / 2, i, _pct_text(v), ha="center", va="center",
                        color="white", fontsize=9, fontweight="bold")
            left += v
    if mixed:
        row_labels_display = [
            f"{lbl}  (1)" if _SUBDOMAIN_POLARITY.get(lbl, "normal") == "normal" else f"{lbl}  (2)"
            for lbl in row_labels
        ]
    else:
        row_labels_display = row_labels
    ax.set_yticks(y, row_labels_display)
    ax.set_xlim(0, 100)
    ax.set_xticks(np.arange(0, 101, 10))
    ax.set_xlabel("Pourcentage (%)")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    patches_risk = [plt.Rectangle((0,0),1,1, color=LEVEL_COLORS_RISK[lvl], label=lvl) for lvl in ORDER_LEVELS]
    patches_good = [plt.Rectangle((0,0),1,1, color=LEVEL_COLORS_GOOD[lvl], label=lvl) for lvl in ORDER_LEVELS]
    if mixed:
        leg_risk = ax.legend(handles=patches_risk, ncol=len(ORDER_LEVELS),
                             bbox_to_anchor=(0.5, -0.14), loc="upper center",
                             frameon=True, title="(1) Items non inversés", title_fontsize=8, fontsize=8)
        ax.add_artist(leg_risk)
        ax.legend(handles=patches_good, ncol=len(ORDER_LEVELS),
                  bbox_to_anchor=(0.5, -0.26), loc="upper center",
                  frameon=True, title="(2) Items inversés", title_fontsize=8, fontsize=8)
        fig.subplots_adjust(bottom=0.28)
    elif has_inverted:
        ax.legend(handles=patches_good, ncol=len(ORDER_LEVELS),
                  bbox_to_anchor=(0.5, -0.14), loc="upper center", frameon=True, fontsize=8)
        fig.subplots_adjust(bottom=0.18)
    else:
        ax.legend(handles=patches_risk, ncol=len(ORDER_LEVELS),
                  bbox_to_anchor=(0.5, -0.14), loc="upper center", frameon=True, fontsize=8)
        fig.subplots_adjust(bottom=0.18)
    fig.tight_layout()
    return fig


def _plot_bivariate_stacked(ct: pd.DataFrame, title: str, subdomain_label: str = ""):
    palette = _colors_for_subdomain(subdomain_label)
    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.6 * len(ct) + 1.5)))
    y = np.arange(len(ct))
    legend_patches = [plt.Rectangle((0,0),1,1, color=palette[lvl], label=lvl) for lvl in ORDER_LEVELS]
    for i in range(len(ct)):
        left = 0.0
        for level in ORDER_LEVELS:
            v = float(ct.iloc[i][level]) if level in ct.columns else 0.0
            ax.barh(i, v, left=left, color=palette[level])
            if v > 0:
                ax.text(left + v / 2, i, _pct_text(v), ha="center", va="center",
                        color="white", fontsize=9, fontweight="bold")
            left += v
    ax.set_yticks(y, ct.index.astype(str))
    ax.set_xlim(0, 100)
    ax.set_xticks(np.arange(0, 101, 10))
    ax.set_xlabel("Pourcentage (%)")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.legend(handles=legend_patches, ncol=len(ORDER_LEVELS),
              bbox_to_anchor=(0.5, -0.14), loc="upper center", frameon=True, fontsize=8)
    fig.subplots_adjust(bottom=0.18)
    fig.tight_layout()
    return fig


def _bivariate_table(socio_series: pd.Series, outcome_series: pd.Series) -> pd.DataFrame | None:
    outcome_collapsed = _normalize_to_four_levels(outcome_series)
    temp = pd.DataFrame({"socio": socio_series, "outcome": outcome_collapsed}).dropna()
    if temp.empty:
        return None
    ct = pd.crosstab(temp["socio"], temp["outcome"], normalize="index").mul(100)
    ct = ct.reindex(columns=ORDER_LEVELS, fill_value=0)
    ct["Total"] = ct.sum(axis=1)
    return ct


def _domain_distribution_table(cat_df: pd.DataFrame, domain_cols: list, label_map: dict) -> pd.DataFrame:
    valid_cols = [c for c in domain_cols if c in cat_df.columns]
    rows = []
    for col in valid_cols:
        collapsed = _normalize_to_four_levels(cat_df[col]).dropna()
        pct = collapsed.value_counts(normalize=True).mul(100).reindex(ORDER_LEVELS, fill_value=0)
        row = {"Sous-domaine": label_map.get(col, col)}
        for level in ORDER_LEVELS:
            row[level] = float(pct[level])
        row["Total"] = sum(row[l] for l in ORDER_LEVELS)
        rows.append(row)
    return pd.DataFrame(rows)


def _style_domain_table(df: pd.DataFrame):
    CELL_RISK = {"Tres faible": "#bbf7d0", "Faible": "#fef08a", "Fort": "#fed7aa", "Tres fort": "#fecaca"}
    CELL_GOOD = {"Tres faible": "#fecaca", "Faible": "#fed7aa", "Fort": "#fef08a", "Tres fort": "#bbf7d0"}
    def _style_row(row):
        subdomain = row.get("Sous-domaine", "")
        palette = CELL_GOOD if _SUBDOMAIN_POLARITY.get(str(subdomain), "normal") == "inverted" else CELL_RISK
        return [f"background-color:{palette[col]};color:#111;" if col in ORDER_LEVELS else "" for col in row.index]
    fmt = {lvl: "{:.1f}%" for lvl in ORDER_LEVELS}
    if "Total" in df.columns: fmt["Total"] = "{:.0f}%"
    return df.round(1).style.apply(_style_row, axis=1).format(fmt)


def _style_bivariate_table(ct: pd.DataFrame, subdomain_label: str = ""):
    CELL_RISK = {"Tres faible": "#bbf7d0", "Faible": "#fef08a", "Fort": "#fed7aa", "Tres fort": "#fecaca"}
    CELL_GOOD = {"Tres faible": "#fecaca", "Faible": "#fed7aa", "Fort": "#fef08a", "Tres fort": "#bbf7d0"}
    palette = CELL_GOOD if _SUBDOMAIN_POLARITY.get(subdomain_label, "normal") == "inverted" else CELL_RISK
    def _style_row(row):
        return [f"background-color:{palette[col]};color:#111;" if col in ORDER_LEVELS else "" for col in row.index]
    level_cols = [c for c in ORDER_LEVELS if c in ct.columns]
    fmt = {lvl: "{:.1f}%" for lvl in level_cols}
    if "Total" in ct.columns: fmt["Total"] = "{:.0f}%"
    return ct.round(1).style.apply(_style_row, axis=1).format(fmt)


# =============================================================================
# RÉSOLUTION DES COLONNES SOCIO-DÉMOGRAPHIQUES (variables croisables)
# =============================================================================

def _resolve_socio_columns_clean(df: pd.DataFrame) -> dict:
    """Retourne un dict {label_affichage: colonne_réelle} sur df_clean."""
    candidates = {
        "Genre": ["genre", "Genre", "Sexe"],
        "Tranche d'âge": ["Tranche_dage", "Tranche d'age", "Tranche age"],
        "Tranche ancienneté": ["Tranche_anciennete", "Tranche anciennete", "Tranche ancienneté"],
        "Direction": ["direction", "Direction"],
        "Fonction": ["fonction", "Fonction"],
        "Service": ["service", "Service"],
        "Département": ["departement", "Département", "Departement"],
        "Situation matrimoniale": ["situation_matrimoniale", "Situation matrimoniale"],
        "Catégorie IMC": ["Categorie_IMC", "Categorie IMC"],
        "Tabagisme": ["tabagisme", "Tabagisme"],
        "Consommation alcool": ["consommation_alcool"],
        "Maladie chronique": ["maladie_chronique"],
        "Pratique sportive": ["pratique_sport"],
    }
    out = {}
    for label, names in candidates.items():
        for name in names:
            if name in df.columns:
                out[label] = name
                break
    return out


# =============================================================================
# GÉNÉRATION DE L'INTERPRÉTATION AUTOMATIQUE (domaine global + bivarié)
# =============================================================================

def _interpret_domain_global(domain_table: pd.DataFrame, domain_name: str) -> str:
    """Génère un texte d'interprétation automatique pour un graphe de domaine (vue globale)."""
    if domain_table.empty:
        return "Données insuffisantes pour l'interprétation."

    lines = []
    lines.append(f"<b>Interprétation — {domain_name}</b>")
    lines.append(f"Ce graphique présente la répartition de <b>{len(domain_table)}</b> sous-domaine(s) "
                 f"pour l'ensemble des répondants.")

    # Sous-domaine le plus à risque (fort + très fort)
    if "Fort" in domain_table.columns and "Tres fort" in domain_table.columns:
        domain_table = domain_table.copy()
        domain_table["_risk"] = domain_table["Fort"] + domain_table["Tres fort"]
        worst = domain_table.sort_values("_risk", ascending=False).iloc[0]
        worst_name = worst["Sous-domaine"] if "Sous-domaine" in domain_table.columns else "—"
        worst_pct = worst["_risk"]
        polarity = _SUBDOMAIN_POLARITY.get(str(worst_name), "normal")

        if polarity == "normal":
            lines.append(f"Le sous-domaine le plus exposé est <b>« {worst_name} »</b> avec "
                         f"<b>{worst_pct:.1f}%</b> des répondants en niveaux Fort ou Très fort (exposition élevée).")
        else:
            # Pour les items inversés, Fort/Très fort = situation favorable
            best = domain_table.sort_values("_risk", ascending=False).iloc[0]
            best_name = best["Sous-domaine"] if "Sous-domaine" in domain_table.columns else "—"
            lines.append(f"Le sous-domaine le plus favorable est <b>« {best_name} »</b> avec "
                         f"<b>{best['_risk']:.1f}%</b> des répondants à des niveaux élevés (indicateur positif).")

    # Sous-domaine le plus faible (très faible + faible)
    if "Tres faible" in domain_table.columns and "Faible" in domain_table.columns:
        domain_table["_low"] = domain_table["Tres faible"] + domain_table["Faible"]
        best_low = domain_table.sort_values("_low", ascending=False).iloc[0]
        best_low_name = best_low["Sous-domaine"] if "Sous-domaine" in domain_table.columns else "—"
        lines.append(f"À l'inverse, <b>« {best_low_name} »</b> présente le plus fort taux de niveaux Très faible/Faible "
                     f"(<b>{best_low['_low']:.1f}%</b>).")

    return "<br>".join(lines)


def _interpret_bivariate(ct: pd.DataFrame, socio_label: str, subdomain_label: str) -> str:
    """Génère un texte d'interprétation automatique pour un graphe bivarié."""
    if ct is None or ct.empty:
        return "Données insuffisantes pour l'interprétation."

    polarity = _SUBDOMAIN_POLARITY.get(subdomain_label, "normal")
    risk_level = "Tres fort" if polarity == "normal" else "Tres faible"
    risk_label_text = "Très fort (exposition maximale)" if polarity == "normal" else "Très faible (déficit maximal)"

    lines = []
    lines.append(f"<b>Interprétation — {subdomain_label}</b>")
    lines.append(f"Ce graphique croise <b>{socio_label}</b> avec le sous-domaine <b>« {subdomain_label} »</b>.")

    if risk_level in ct.columns:
        risk_col = ct[risk_level].dropna()
        if not risk_col.empty:
            max_mod = risk_col.idxmax()
            max_val = risk_col.max()
            min_mod = risk_col.idxmin()
            min_val = risk_col.min()
            lines.append(
                f"La modalité <b>« {max_mod} »</b> affiche le taux le plus élevé de niveau {risk_label_text} "
                f"(<b>{max_val:.1f}%</b>), contre <b>{min_val:.1f}%</b> pour <b>« {min_mod} »</b>."
            )
            diff = max_val - min_val
            if diff >= 20:
                lines.append(f"L'écart de <b>{diff:.1f} points</b> indique une disparité <b>importante</b> entre les groupes.")
            elif diff >= 10:
                lines.append(f"L'écart de <b>{diff:.1f} points</b> indique une disparité <b>modérée</b> entre les groupes.")
            else:
                lines.append(f"L'écart de <b>{diff:.1f} points</b> est <b>faible</b> — les groupes sont relativement homogènes.")

    return "<br>".join(lines)


def _render_interpretation_box(html_text: str) -> None:
    st.markdown(
        f"""<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;
        padding:14px 16px;font-size:12px;color:#475569;line-height:1.8;
        font-family:'Plus Jakarta Sans',sans-serif;">{html_text}</div>""",
        unsafe_allow_html=True
    )


# =============================================================================
# COMPOSANTS KPI STANDARDS
# =============================================================================

def kpi_card(icon_class: str, icon_color: str, icon_bg: str, accent_color: str,
             value, suffix: str, subtitle: str, label: str) -> str:
    return (
        f'<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;'
        f'padding:20px 16px 16px;text-align:center;box-shadow:0 2px 12px rgba(15,23,42,0.06);'
        f'border-top:3px solid {accent_color};transition:transform 0.2s ease,box-shadow 0.2s ease;'
        f'min-height:160px;display:flex;flex-direction:column;justify-content:space-between;" '
        f'onmouseover="this.style.transform=\'translateY(-3px)\';this.style.boxShadow=\'0 8px 24px {accent_color}30\';" '
        f'onmouseout="this.style.transform=\'none\';this.style.boxShadow=\'0 2px 12px rgba(15,23,42,0.06)\';">'
        f'<div><div style="width:40px;height:40px;background:{icon_bg};border-radius:10px;'
        f'display:flex;align-items:center;justify-content:center;margin:0 auto 12px;">'
        f'<i class="{icon_class}" style="color:{icon_color};font-size:16px;"></i></div>'
        f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:10px;color:#94A3B8;'
        f'text-transform:uppercase;letter-spacing:0.06em;font-weight:700;margin:0 0 6px 0;">{label}</p></div>'
        f'<div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:28px;font-weight:800;'
        f'color:#0F172A;margin:0;line-height:1;letter-spacing:-0.03em;">{value}'
        f'<span style="font-size:13px;font-weight:500;color:#94A3B8;">{suffix}</span></p>'
        f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:11px;color:#94A3B8;'
        f'margin:4px 0 0 0;">{subtitle}</p></div></div>'
    )


def _compute_cardio_risk(df: pd.DataFrame) -> tuple:
    n = max(len(df), 1); score = 0.0
    if 'imc' in df.columns:
        imc = pd.to_numeric(df['imc'], errors='coerce')
        score += float((imc >= 25).sum()/n)*1.0 + float((imc >= 30).sum()/n)*2.0
    for col, val, w in [('tabagisme','oui',2.0),('consommation_alcool','oui',1.0),
                        ('maladie_chronique','oui',2.0),('pratique_sport','non',1.0)]:
        if col in df.columns:
            s = df[col].astype(str).str.lower().str.strip()
            score += float((s.isin(['oui','yes','1','vrai','true'])).sum()/n)*w
    score = round(score, 2)
    if score <= 1.5: return score, "Faible", "#16A37F"
    elif score <= 3.0: return score, "Modéré", "#F5A623"
    else: return score, "Élevé", "#E8504A"


def render_kpi_row(df: pd.DataFrame, n_before_cleaning: int = None) -> None:
    n = len(df)
    if n_before_cleaning is None: n_before_cleaning = n

    if 'Tranche_dage' in df.columns:
        age_str = df['Tranche_dage'].astype(str).str.strip()
        age_clean = age_str[~age_str.str.lower().isin(['non renseigné','nan','','none'])]
        if not age_clean.empty:
            vc = age_clean.value_counts()
            age_display = vc.index[0]
            age_subtitle = f"Classe dominante ({(vc.iloc[0]/len(age_clean))*100:.0f}%)"
        else: age_display, age_subtitle = "—", "non disponible"
    elif 'age' in df.columns:
        age_num = pd.to_numeric(df['age'], errors='coerce').dropna()
        if not age_num.empty: age_display = f"{int(round(age_num.median()))} ans"; age_subtitle = "médiane"
        else: age_display, age_subtitle = "—", "non disponible"
    else: age_display, age_subtitle = "—", "non disponible"

    if 'Tranche_anciennete' in df.columns:
        anc_str = df['Tranche_anciennete'].astype(str).str.strip()
        anc_clean = anc_str[~anc_str.str.lower().isin(['non renseigné','nan','','none'])]
        if not anc_clean.empty:
            vc = anc_clean.value_counts()
            anc_display = vc.index[0]
            anc_subtitle = f"Classe dominante ({(vc.iloc[0]/len(anc_clean))*100:.0f}%)"
        else: anc_display, anc_subtitle = "—", "non disponible"
    elif 'anciennete' in df.columns:
        anc_num = pd.to_numeric(df['anciennete'], errors='coerce').dropna()
        if not anc_num.empty: anc_display = f"{round(anc_num.median())} ans"; anc_subtitle = "médiane"
        else: anc_display, anc_subtitle = "—", "non disponible"
    else: anc_display, anc_subtitle = "—", "non disponible"

    if 'genre' in df.columns:
        genre_clean = df['genre'].dropna()
        if not genre_clean.empty:
            nb_h = int((genre_clean=='homme').sum()); nb_f = int((genre_clean=='femme').sum())
            if nb_h >= nb_f:
                genre_display = f"{(nb_h/n)*100:.0f}%"; genre_subtitle = f"Hommes ({nb_h})"
                genre_icon, genre_color, genre_bg = "fas fa-male", "#1D78F5", "#EBF3FF"
            else:
                genre_display = f"{(nb_f/n)*100:.0f}%"; genre_subtitle = f"Femmes ({nb_f})"
                genre_icon, genre_color, genre_bg = "fas fa-female", "#EC4899", "#FCE7F3"
        else:
            genre_display, genre_subtitle = "—", "non disponible"
            genre_icon, genre_color, genre_bg = "fas fa-venus-mars", "#94A3B8", "#F1F5F9"
    else:
        genre_display, genre_subtitle = "—", "non disponible"
        genre_icon, genre_color, genre_bg = "fas fa-venus-mars", "#94A3B8", "#F1F5F9"

    cardio_score, cardio_label, cardio_color = _compute_cardio_risk(df)

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(kpi_card("fas fa-users","#1D78F5","#EBF3FF","#1D78F5",n,"",f"sur {n_before_cleaning} observations","Répondants analysés"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(genre_icon,genre_color,genre_bg,genre_color,genre_display,"",genre_subtitle,"Genre dominant"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("fas fa-calendar-alt","#16A37F","#E8F8EF","#16A37F",age_display,"",age_subtitle,"Âge"), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("fas fa-clock","#F5A623","#FEF5E7","#F5A623",anc_display,"",anc_subtitle,"Ancienneté"), unsafe_allow_html=True)
    with c5: st.markdown(kpi_card("fas fa-heart",cardio_color,"#FEF0EF",cardio_color,cardio_label,"",f"Score {cardio_score:.1f}/5","Risque cardio-vasc."), unsafe_allow_html=True)


# =============================================================================
# COMPOSANTS INDICATEURS KPI SPÉCIALISÉS
# =============================================================================

def get_priority_info(priorite_type: str) -> tuple:
    if priorite_type == "risque": return "#EF4444","Risque prioritaire","#EF4444"
    elif priorite_type == "levier": return "#22C55E","Levier performance","#22C55E"
    elif priorite_type == "vigilance": return "#F59E0B","Vigilance","#F59E0B"
    elif priorite_type == "strategique": return "#3B82F6","Stratégique","#3B82F6"
    elif priorite_type == "protecteur": return "#22C55E","Levier protecteur","#22C55E"
    return "#6B7280","","#6B7280"


def render_indicator_card(nom: str, valeur, seuil, operateur: str, priorite_type: str) -> str:
    if valeur is None:
        return ('<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:12px;padding:16px;'
                'text-align:center;min-height:170px;display:flex;align-items:center;justify-content:center;">'
                '<p style="color:#94A3B8;font-size:0.85rem;">Données<br>insuffisantes</p></div>')
    bordure_color, priorite_texte, priorite_color = get_priority_info(priorite_type)
    priorite_bg = bordure_color + "18"
    seuil_str = f"Seuil {operateur} {seuil}/100" if seuil is not None else ""
    valeur_str = str(valeur); taille_police = "36px" if len(valeur_str) <= 10 else "22px"
    return (
        f'<div style="background:#FFFFFF;border:1px solid #E3EAF4;border-radius:14px;'
        f'padding:20px 14px 16px;text-align:center;box-shadow:0 2px 10px rgba(15,23,42,0.06);'
        f'border-top:4px solid {bordure_color};min-height:190px;display:flex;flex-direction:column;'
        f'justify-content:space-between;">'
        f'<div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:14px;font-weight:700;'
        f'color:#1E293B;margin:0;line-height:1.3;">{nom}</p></div>'
        f'<div><p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:{taille_police};'
        f'font-weight:800;color:{bordure_color};margin:8px 0;line-height:1;">{valeur}</p>'
        f'<span style="display:inline-block;padding:4px 14px;border-radius:999px;font-size:10px;'
        f'font-weight:600;color:{priorite_color};background:{priorite_bg};margin:8px 0 4px;">{priorite_texte}</span>'
        f'<p style="font-size:9px;color:#94A3B8;margin:0 0 6px;">{seuil_str}</p></div></div>'
    )


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
    init_mode(PAGE_KEY)
    current_mode = get_mode(PAGE_KEY)
    inject_shared_css(current_mode)

    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,400;1,9..144,600&display=swap" rel="stylesheet">
    <style>
    .section-title {
        display:flex;align-items:center;gap:0.7rem;
        font-family:'Fraunces',Georgia,serif !important;
        font-size:1.25rem !important;font-style:italic !important;font-weight:400 !important;
        color:#0F2340 !important;margin:1.6rem 0 1rem !important;
        padding-bottom:0.65rem !important;border-bottom:2px solid #dde5f2 !important;
    }
    .section-title::before {
        content:'';display:inline-block;width:4px;height:22px;
        background:linear-gradient(180deg,#2f66b3 0%,#4f8be4 100%);
        border-radius:2px;flex-shrink:0;
    }
    [data-baseweb="tab-list"] {
        background:#FFFFFF !important;border-radius:12px !important;padding:4px !important;
        gap:3px !important;border:1px solid #dde5f2 !important;
        box-shadow:0 2px 8px rgba(47,102,179,0.07) !important;
    }
    [data-baseweb="tab"] {
        font-family:'Plus Jakarta Sans',sans-serif !important;font-weight:600 !important;
        font-size:0.88rem !important;color:#6B88A8 !important;border-radius:9px !important;
        padding:0.5rem 1.4rem !important;transition:all 0.2s !important;
    }
    [aria-selected="true"][data-baseweb="tab"] {
        background:linear-gradient(135deg,#2f66b3,#4f8be4) !important;
        color:#FFFFFF !important;font-weight:700 !important;
        box-shadow:0 3px 12px rgba(47,102,179,0.30) !important;
    }
    [data-baseweb="tab-highlight"],[data-baseweb="tab-border"] { display:none !important; }
    .stButton > button {
        background:linear-gradient(135deg,#2f66b3,#4f8be4) !important;
        border:none !important;color:#FFFFFF !important;border-radius:10px !important;
        font-family:'Plus Jakarta Sans',sans-serif !important;font-weight:700 !important;
    }
    [data-testid="stSidebar"] { background-color:#FFFFFF !important; border-right:1px solid #E4F0FB; }
    </style>
    """, unsafe_allow_html=True)

    # ── TOPBAR ───────────────────────────────────────────────────────────────
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
            f'<i class="fas fa-clipboard-check" style="color:white;font-size:15px;"></i></div>'
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
    # ── UPLOAD ───────────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Charger un fichier Excel ou CSV", type=["xlsx","xls","csv"], key=f"uploader_{PAGE_KEY}"
    )
    if uploaded_file is not None:
        st.session_state[f"_file_bytes_{PAGE_KEY}"] = uploaded_file.read()
        st.session_state[f"_file_name_{PAGE_KEY}"] = uploaded_file.name
    if f"_file_bytes_{PAGE_KEY}" not in st.session_state:
        st.info("Veuillez charger un fichier de données pour démarrer l'analyse.")
        st.stop()

    file_bytes = st.session_state[f"_file_bytes_{PAGE_KEY}"]
    file_name  = st.session_state[f"_file_name_{PAGE_KEY}"]

    with st.spinner("Chargement et traitement des données…"):
        df_raw = load_data_from_bytes(file_bytes, file_name)
        n_before = len(df_raw)
        df_clean, cleaning_log = clean_common_variables(df_raw)

    with st.expander("Journal de nettoyage", expanded=False):
        st.text(cleaning_log)
        st.text(f"Questions COPSOQ : {sum(1 for qx in QUESTION_TEXT_MAP if trouver_colonne_q(df_clean, qx) is not None)}/46")
        st.write(f"Avant: **{n_before}** — Après: **{len(df_clean)}**")

    if df_clean.empty:
        st.error("Aucune donnée exploitable.")
        st.stop()

    # ── VÉRIFICATION COPSOQ ──────────────────────────────────────────────────
    q_trouvees = sum(1 for qx in QUESTION_TEXT_MAP if trouver_colonne_q(df_clean, qx) is not None)
    if q_trouvees < 46:
        st.error(
            f"❌ **Fichier non reconnu comme un questionnaire COPSOQ**\n\n"
            f"Seulement **{q_trouvees}/46** questions détectées.\n\n"
            f"**Solution :** Chargez ce fichier dans le module approprié."
        )
        st.stop()

    # ── CALCUL DES SCORES ───────────────────────────────────────────────────
    with st.spinner("Calcul des scores COPSOQ…"):
        df_scores = build_df_scores_from_clean(df_clean)
        domain_cat_df, domain_map, missing_domains, domain_label_map = _build_rps_domain_categories(df_scores)

    # ── ONGLETS ─────────────────────────────────────────────────────────────
    if is_medecin(current_mode):
        onglet1, onglet2, onglet3 = st.tabs(["Vue d'ensemble", "Analyses univariées", "Analyse bivariée"])
    else:
        onglet1, onglet2 = st.tabs(["Vue d'ensemble", "Analyses univariées"])
        onglet3 = None

    # ╔══════════════════════════════════════════════════════════╗
    # ║  ONGLET 1 : VUE D'ENSEMBLE                              ║
    # ╚══════════════════════════════════════════════════════════╝
    # ╔══════════════════════════════════════════════════════════╗
    # ║  ONGLET 1 : VUE D'ENSEMBLE                              ║
    # ╚══════════════════════════════════════════════════════════╝
    with onglet1:
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
        
        with st.expander("Filtres", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns([3, 3, 3, 1.5])
            
            with fc1:
                cat_labels = ["— Aucun —"] + [l for l, _ in cat_vars]
                sel_cat_label = st.selectbox("Variable (catégorielle)", cat_labels, key="cop_filtre_cat")
            
            with fc2:
                if sel_cat_label != "— Aucun —":
                    cat_col = dict(cat_vars)[sel_cat_label]
                    modalites = sorted(df_clean[cat_col].dropna().astype(str).unique().tolist())
                    sel_modalite = st.selectbox("Modalité", ["Toutes"] + modalites, key="cop_filtre_mod")
                else:
                    sel_modalite = "Toutes"
                    st.selectbox("Modalité", ["Toutes"], disabled=True)
            
            with fc3:
                num_labels = ["— Aucun —"] + [l for l, _ in num_vars]
                sel_num_label = st.selectbox("Variable (numérique)", num_labels, key="cop_filtre_num")
                
                if sel_num_label != "— Aucun —":
                    num_col = dict(num_vars)[sel_num_label]
                    vals = pd.to_numeric(df_clean[num_col], errors="coerce").dropna()
                    if not vals.empty:
                        vmin, vmax = int(vals.min()), int(vals.max())
                        if vmin == vmax:
                            vmax = vmin + 1
                        sel_range = st.slider(f"Plage — {sel_num_label}", vmin, vmax, (vmin, vmax), key="cop_filtre_range")
                    else:
                        sel_range = None
                        st.slider(f"Plage — {sel_num_label}", 0, 100, (0, 100), disabled=True)
                else:
                    sel_range = None
            
            with fc4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Réinitialiser", key="cop_reset_filtres", use_container_width=True):
                    for k in ["cop_filtre_cat", "cop_filtre_mod", "cop_filtre_num", "cop_filtre_range"]:
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
        st.markdown('<div class="section-title">Données Générales de la Population</div>', unsafe_allow_html=True)
        render_kpi_row(df_filtered, n_before_cleaning=n_before)

        if is_rh(current_mode):
            st.markdown('<div class="section-title">Indicateurs RH/DG</div>', unsafe_allow_html=True)
            indicateurs_rh = [
                {"nom": "Score contraintes quantitatives", "questions": ["Q1","Q2","Q3","Q4","Q5","Q6"], "seuil": 55, "operateur": ">", "priorite_type": "risque"},
                {"nom": "Niveau de reconnaissance perçue", "questions": ["Q9","Q10"], "seuil": 50, "operateur": "<", "priorite_type": "levier"},
                {"nom": "Qualité du leadership", "questions": ["Q17","Q18"], "seuil": 50, "operateur": "<", "priorite_type": "vigilance"},
                {"nom": "Sens du travail", "questions": ["Q42","Q43"], "seuil": 50, "operateur": "<", "priorite_type": "strategique"},
                {"nom": "Insécurité professionnelle", "questions": ["Q40","Q41"], "seuil": 50, "operateur": ">", "priorite_type": "risque"},
            ]
            cols = st.columns(5)
            for i, indic in enumerate(indicateurs_rh):
                with cols[i]:
                    val = calculer_indicateur_par_noms(df_filtered, indic["questions"])
                    st.markdown(render_indicator_card(
                        nom=indic["nom"],
                        valeur=f"{val:.1f}" if val is not None else None,
                        seuil=indic["seuil"], operateur=indic["operateur"],
                        priorite_type=indic["priorite_type"]
                    ), unsafe_allow_html=True)

        if is_medecin(current_mode):
            st.markdown('<div class="section-title">Indicateurs Médecin du Travail</div>', unsafe_allow_html=True)
            indicateurs_med = [
                {"nom": "Score d'épuisement professionnel", "questions": ["Q34","Q35"], "seuil": 60, "operateur": ">", "priorite_type": "risque"},
                {"nom": "Exigences émotionnelles", "questions": ["Q36","Q37"], "seuil": 60, "operateur": ">", "priorite_type": "risque"},
                {"nom": "Conflit travail–famille", "questions": ["Q38","Q39"], "seuil": 50, "operateur": ">", "priorite_type": "vigilance"},
                {"nom": "Santé auto-évaluée (SAE)", "questions": ["Q31"], "seuil": 50, "operateur": "<", "priorite_type": "risque"},
                {"nom": "Soutien social du superviseur", "questions": ["Q19","Q20"], "seuil": 40, "operateur": "<", "priorite_type": "protecteur"},
            ]
            cols = st.columns(5)
            for i, indic in enumerate(indicateurs_med):
                with cols[i]:
                    val = calculer_indicateur_par_noms(df_filtered, indic["questions"])
                    st.markdown(render_indicator_card(
                        nom=indic["nom"],
                        valeur=f"{val:.1f}" if val is not None else None,
                        seuil=indic["seuil"], operateur=indic["operateur"],
                        priorite_type=indic["priorite_type"]
                    ), unsafe_allow_html=True)
    # ╔══════════════════════════════════════════════════════════╗
    # ║  ONGLET 2 : ANALYSES UNIVARIÉES                         ║
    # ╚══════════════════════════════════════════════════════════╝
    with onglet2:
        st.markdown('<div class="section-title">Analyses univariées</div>', unsafe_allow_html=True)

        VAR_OPTIONS = {}
        for label, col in VARIABLES_UNIVARIEES:
            if col in df_clean.columns:
                VAR_OPTIONS[label] = col

        if not VAR_OPTIONS:
            st.info("Aucune variable disponible.")
        else:
            c_sel, _ = st.columns([1, 2])
            with c_sel:
                sel_label = st.selectbox("Variable à visualiser", list(VAR_OPTIONS.keys()), key="uni_copsoq")
            sel_col = VAR_OPTIONS.get(sel_label)

            if sel_col and sel_col in df_clean.columns:
                counts_u = df_clean[sel_col].value_counts()
                total_u  = counts_u.sum()
                pcts_u   = (counts_u / total_u * 100).round(1)
                n_bars   = len(counts_u)

                stats_data = []
                for cat, eff, pct in zip(counts_u.index, counts_u.values, pcts_u.values):
                    stats_data.append({"Modalité": str(cat), "Effectif": int(eff), "Fréquence": f"{pct:.1f}%"})
                stats_data.append({"Modalité": "TOTAL", "Effectif": int(total_u), "Fréquence": "100%"})

                c_chart, c_table = st.columns([7, 3])
                with c_chart:
                    pal = ["#38A3E8","#F97316","#22C55E","#EF4444","#A78BFA","#06B6D4","#FB923C","#84CC16","#EC4899","#8B5CF6"]
                    fig = go.Figure()
                    for i, (cat, pct, eff) in enumerate(zip(counts_u.index, pcts_u.values, counts_u.values)):
                        fig.add_trace(go.Bar(
                            y=[str(cat)], x=[pct], orientation='h',
                            marker_color=pal[i % len(pal)],
                            marker=dict(opacity=0.9, line=dict(width=0)),
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
                        title=dict(text=f"Répartition selon : {sel_label}",
                                   font=dict(size=14, color="#0F2340", family="Plus Jakarta Sans"),
                                   x=0.5, xanchor="center")
                    )
                    st.plotly_chart(fig, use_container_width=True, key="uni_copsoq_plotly")

                with c_table:
                    st.markdown(
                        '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                        'text-transform:uppercase;margin-bottom:0.8rem;">Statistiques</p>',
                        unsafe_allow_html=True
                    )
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True, hide_index=True,
                                 height=min(400, 35*(len(stats_data)+1)))

                    st.markdown(
                        '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                        'text-transform:uppercase;margin:1rem 0 0.5rem;">💡 Interprétation</p>',
                        unsafe_allow_html=True
                    )
                    modalites = list(counts_u.index)
                    if len(modalites) >= 2:
                        m1, m2 = modalites[0], modalites[1]
                        p1, p2 = pcts_u.iloc[0], pcts_u.iloc[1]
                        e1, e2 = int(counts_u.iloc[0]), int(counts_u.iloc[1])
                        st.markdown(
                            f'<div style="background:#F8FAFC;border:1px solid #E3EAF4;border-radius:10px;'
                            f'padding:14px 16px;font-size:12px;color:#475569;line-height:1.7;'
                            f'font-family:\'Plus Jakarta Sans\',sans-serif;">'
                            f'<p style="margin:0 0 8px;">Ce graphique montre la répartition de '
                            f'<b>{sel_label}</b> parmi les {int(total_u)} répondants.</p>'
                            f'<p style="margin:0 0 8px;">La modalité dominante est <b>« {m1} »</b> avec '
                            f'<b>{p1:.1f}%</b> des répondants ({e1} personne(s)).</p>'
                            f'<p style="margin:0;">Elle est suivie par <b>« {m2} »</b> avec '
                            f'<b>{p2:.1f}%</b> ({e2} personne(s)). Au total, <b>{n_bars}</b> modalités.</p>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.caption("Données insuffisantes.")

    # ╔══════════════════════════════════════════════════════════════════════╗
    # ║  ONGLET 3 : ANALYSE BIVARIÉE — Domaines × Démographie              ║
    # ╚══════════════════════════════════════════════════════════════════════╝
    if onglet3 is not None:
        with onglet3:
            st.markdown('<div class="section-title">Domaines et sous-domaines RPS</div>', unsafe_allow_html=True)

            # ── Vérification disponibilité domaines ──────────────────────────
            domain_choices = [grp for grp, cols in domain_map.items() if cols]
            socio_columns  = _resolve_socio_columns_clean(df_clean)

            if not domain_choices:
                st.warning("Aucun domaine exploitable détecté avec les colonnes disponibles.")
                st.stop()

            # ── SÉLECTEURS ────────────────────────────────────────────────────
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1px;'
                'text-transform:uppercase;margin-bottom:0.4rem;">Sélection</p>',
                unsafe_allow_html=True
            )
            sel_c1, sel_c2, sel_c3 = st.columns([2, 2, 2])

            with sel_c1:
                # Domaines + sous-domaines dans la liste déroulante
                # On construit une liste hiérarchique :
                # - Les 6 domaines principaux
                # - Séparateur, puis tous les sous-domaines croisables
                domain_options = list(domain_choices)

                # Construire la liste des sous-domaines disponibles (ceux qui ont une colonne __Categorie)
                subdomain_options = []
                for grp, cols in domain_map.items():
                    for cat_col in cols:
                        if cat_col in domain_cat_df.columns:
                            label = domain_label_map.get(cat_col, cat_col)
                            subdomain_options.append(f"↳ {label}")

                all_options = domain_options + (["─── Sous-domaines ───"] + subdomain_options if subdomain_options else [])
                selected_group = st.selectbox("Domaine / Sous-domaine", all_options, key="bivar_domain_sel")

            with sel_c2:
                socio_list = ["Aucun croisement"] + list(socio_columns.keys())
                sel_socio = st.selectbox("Variable démographique", socio_list, key="bivar_socio_sel")

            with sel_c3:
                # Modalité (disponible seulement si variable démographique choisie)
                if sel_socio != "Aucun croisement" and sel_socio in socio_columns:
                    socio_col = socio_columns[sel_socio]
                    modalities = sorted(df_clean[socio_col].dropna().astype(str).unique().tolist())
                    sel_modalite = st.selectbox("Modalité", ["Toutes"] + modalities, key="bivar_modalite_sel")
                else:
                    sel_modalite = "Toutes"
                    st.selectbox("Modalité", ["Toutes"], key="bivar_modalite_sel_disabled", disabled=True)

            st.markdown("<hr style='border-color:#E3EAF4;margin:0.5rem 0 1rem;'>", unsafe_allow_html=True)

            # ── RÉSOLUTION DE LA SÉLECTION ────────────────────────────────────
            is_subdomain = selected_group.startswith("↳ ")
            is_separator = selected_group.startswith("─")

            if is_separator:
                st.info("Sélectionnez un domaine ou un sous-domaine dans la liste.")
                st.stop()

            # Déterminer les colonnes catégorielles à afficher
            if is_subdomain:
                # Sous-domaine unique
                subdomain_label = selected_group[2:].strip()  # enlever "↳ "
                # Retrouver la cat_col correspondante
                target_cat_col = None
                target_domain_name = None
                for grp, cols in domain_map.items():
                    for cat_col in cols:
                        if domain_label_map.get(cat_col, cat_col) == subdomain_label:
                            target_cat_col = cat_col
                            target_domain_name = grp
                            break
                    if target_cat_col:
                        break
                display_cols    = [target_cat_col] if target_cat_col else []
                display_title   = subdomain_label
                is_single_subdomain = True
            else:
                # Domaine complet
                display_cols    = domain_map.get(selected_group, [])
                display_title   = selected_group
                is_single_subdomain = False

            if not display_cols:
                st.warning(f"Aucune donnée disponible pour « {selected_group} ».")
                st.stop()

            # ── VUE GLOBALE (Aucun croisement) ────────────────────────────────
            if sel_socio == "Aucun croisement":
                c_chart_g, c_interp_g = st.columns([7, 3])

                with c_chart_g:
                    fig_global = _plot_domain_stacked_bar(
                        domain_cat_df, display_cols,
                        f"Répartition des employés — {display_title}",
                        domain_label_map
                    )
                    if fig_global is not None:
                        png_bytes = _fig_to_png_bytes(fig_global)
                        if png_bytes:
                            fname = re.sub(r"[^a-zA-Z0-9_-]", "_", display_title)
                            st.download_button(
                                "⬇ Télécharger PNG", data=png_bytes,
                                file_name=f"{fname}.png", mime="image/png",
                                key=f"dl_global_{fname}"
                            )
                        st.pyplot(fig_global, use_container_width=True)
                        plt.close(fig_global)
                    else:
                        st.warning("Impossible de générer le graphique.")

                with c_interp_g:
                    st.markdown(
                        '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                        'text-transform:uppercase;margin-bottom:0.8rem;">💡 Interprétation</p>',
                        unsafe_allow_html=True
                    )
                    domain_tbl = _domain_distribution_table(domain_cat_df, display_cols, domain_label_map)
                    if not domain_tbl.empty:
                        interp_html = _interpret_domain_global(domain_tbl, display_title)
                        _render_interpretation_box(interp_html)
                        st.markdown(
                            '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                            'text-transform:uppercase;margin:1rem 0 0.5rem;">Tableau de distribution</p>',
                            unsafe_allow_html=True
                        )
                        st.dataframe(_style_domain_table(domain_tbl), use_container_width=True)
                    else:
                        st.info("Données insuffisantes pour ce domaine.")

            # ── VUE CROISÉE (variable démographique sélectionnée) ─────────────
            else:
                socio_col = socio_columns[sel_socio]

                if not is_single_subdomain:
                    # ── CAS 1 : Domaine complet + variable démographique
                    # On filtre le df selon la modalité choisie
                    if sel_modalite != "Toutes":
                        mask = df_clean[socio_col].astype(str) == sel_modalite
                        subset_idx = df_clean[mask].index
                    else:
                        subset_idx = df_clean.index

                    cat_subset = domain_cat_df.loc[domain_cat_df.index.intersection(subset_idx)]

                    if cat_subset.empty:
                        st.warning("Aucune donnée disponible pour ce filtre.")
                        st.stop()

                    st.markdown(
                        f'<p style="font-size:13px;font-weight:600;color:#334866;margin-bottom:0.5rem;">'
                        f'{"Vue globale" if sel_modalite == "Toutes" else f"{sel_socio} = {sel_modalite}"}'
                        f' — {len(cat_subset)} répondants</p>',
                        unsafe_allow_html=True
                    )

                    c_chart_d, c_interp_d = st.columns([7, 3])
                    with c_chart_d:
                        fig_dom = _plot_domain_stacked_bar(
                            cat_subset, display_cols,
                            f"Répartition — {display_title} "
                            f"({'Tous' if sel_modalite == 'Toutes' else f'{sel_socio}={sel_modalite}'})",
                            domain_label_map
                        )
                        if fig_dom is not None:
                            png_bytes = _fig_to_png_bytes(fig_dom)
                            if png_bytes:
                                fname = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{display_title}_{sel_modalite}")
                                st.download_button(
                                    "⬇ Télécharger PNG", data=png_bytes,
                                    file_name=f"{fname}.png", mime="image/png",
                                    key=f"dl_cross_dom_{fname}"
                                )
                            st.pyplot(fig_dom, use_container_width=True)
                            plt.close(fig_dom)
                        else:
                            st.warning("Impossible de générer le graphique.")

                    with c_interp_d:
                        st.markdown(
                            '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                            'text-transform:uppercase;margin-bottom:0.8rem;">💡 Interprétation</p>',
                            unsafe_allow_html=True
                        )
                        domain_tbl = _domain_distribution_table(cat_subset, display_cols, domain_label_map)
                        if not domain_tbl.empty:
                            interp_html = _interpret_domain_global(
                                domain_tbl,
                                f"{display_title} — {sel_socio} = {sel_modalite}"
                                if sel_modalite != "Toutes" else display_title
                            )
                            _render_interpretation_box(interp_html)
                            st.markdown(
                                '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                                'text-transform:uppercase;margin:1rem 0 0.5rem;">Tableau de distribution</p>',
                                unsafe_allow_html=True
                            )
                            st.dataframe(_style_domain_table(domain_tbl), use_container_width=True)
                        else:
                            st.info("Données insuffisantes.")

                else:
                    # ── CAS 2 : Sous-domaine unique × variable démographique
                    # Graphique bivarié (barres empilées par modalité socio)
                    outcome_series = domain_cat_df[target_cat_col] if target_cat_col in domain_cat_df.columns else None

                    if outcome_series is None:
                        st.warning(f"Colonne catégorielle introuvable pour « {subdomain_label} ».")
                        st.stop()

                    # Filtrer selon modalité
                    if sel_modalite != "Toutes":
                        mask = df_clean[socio_col].astype(str) == sel_modalite
                        idx  = df_clean[mask].index
                        socio_s   = df_clean.loc[idx, socio_col]
                        outcome_s = outcome_series.loc[outcome_series.index.intersection(idx)]
                    else:
                        socio_s   = df_clean[socio_col]
                        outcome_s = outcome_series

                    ct = _bivariate_table(socio_s, outcome_s)

                    if ct is None:
                        st.warning("Pas de données exploitables pour ce croisement.")
                        st.stop()

                    c_chart_b, c_interp_b = st.columns([7, 3])
                    with c_chart_b:
                        fig_biv = _plot_bivariate_stacked(
                            ct,
                            f"Répartition des employés — {sel_socio} selon {subdomain_label}",
                            subdomain_label=subdomain_label
                        )
                        png_bytes = _fig_to_png_bytes(fig_biv)
                        if png_bytes:
                            fname = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{sel_socio}_x_{subdomain_label}")
                            st.download_button(
                                "⬇ Télécharger PNG", data=png_bytes,
                                file_name=f"{fname}.png", mime="image/png",
                                key=f"dl_biv_{fname}"
                            )
                        st.pyplot(fig_biv, use_container_width=True)
                        plt.close(fig_biv)

                    with c_interp_b:
                        st.markdown(
                            '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                            'text-transform:uppercase;margin-bottom:0.8rem;">💡 Interprétation</p>',
                            unsafe_allow_html=True
                        )
                        interp_html = _interpret_bivariate(ct, sel_socio, subdomain_label)
                        _render_interpretation_box(interp_html)

                        st.markdown(
                            '<p style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;'
                            'text-transform:uppercase;margin:1rem 0 0.5rem;">Tableau de distribution (%)</p>',
                            unsafe_allow_html=True
                        )
                        st.dataframe(
                            _style_bivariate_table(ct, subdomain_label=subdomain_label),
                            use_container_width=True
                        )

    st.markdown("---")
    st.markdown(
        f'<p style="text-align:center;color:#9CA3AF;font-size:0.8rem;">'
        f'{PAGE_TITLE} — YODAN Analytics © 2026</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()