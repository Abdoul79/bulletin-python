# translations.py — charge les traductions depuis JSON
import json
import os

# Charger les traductions depuis le fichier JSON
TRANSLATIONS_FILE = 'translations_auto.json'

if not os.path.exists(TRANSLATIONS_FILE):
    raise FileNotFoundError(f"Le fichier {TRANSLATIONS_FILE} est manquant. Exécutez auto_translate.py d'abord.")

with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
    TRANSLATIONS = json.load(f)

def t(key, lang='fr'):
    """Fonction de traduction"""
    return TRANSLATIONS.get(key, {}).get(lang, key)

def get_translation(key, lang='fr'):
    return t(key, lang)