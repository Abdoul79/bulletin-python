# auto_translate.py — Traduction automatique avec DeepL
import deepl
import json
import os

# 🔑 Remplace par ta clé API DeepL (gratuit jusqu'à 500k caractères/mois)
DEEPL_API_KEY = "ta_clé_api_ici"  # ← https://www.deepl.com/pro#developer

# Charger les traductions existantes (optionnel, si tu veux compléter)
from translations_manual import TRANSLATIONS  # ton ancien fichier

# Initialiser le traducteur DeepL
translator = deepl.Translator(DEEPL_API_KEY)

# Langues cibles (DeepL utilise des codes comme "AR", "EN-US", etc.)
TARGET_LANGS = {
    'ar': 'AR',   # Arabe
   
}

def translate_missing_with_deepl():
    updated = False
    for key, translations in TRANSLATIONS.items():
        fr_text = translations.get('fr', key)
        if not fr_text or fr_text == key:
            print(f"⚠️ Pas de texte source en français pour '{key}'")
            continue

        for lang_code, deepl_code in TARGET_LANGS.items():
            # Si déjà traduit, on saute
            if lang_code in translations and translations[lang_code].strip():
                continue

            try:
                result = translator.translate_text(fr_text, target_lang=deepl_code)
                translated = result.text
                TRANSLATIONS[key][lang_code] = translated
                print(f"✅ '{fr_text}' → '{translated}' ({lang_code})")
                updated = True
            except Exception as e:
                print(f"❌ Erreur DeepL pour '{key}' en {lang_code}: {e}")

    if updated:
        output_file = 'translations_auto.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(TRANSLATIONS, f, ensure_ascii=False, indent=4)
        print(f"💾 Traductions sauvegardées dans {output_file}")

if __name__ == '__main__':
    translate_missing_with_deepl()