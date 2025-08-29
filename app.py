# app.py
import os
import re
import html
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
# Charger les variables d'environnement
load_dotenv()
# 1. Import de pdfkit
import pdfkit
path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

# === Configuration PDF ===
path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
import pdfkit  # ✅ Import après configuration

# === Initialisation FastAPI ===
app = FastAPI(title="Chatbot Générateur de Fiches de Poste", version="1.2.0")

# ✅ Middleware CORS (une seule fois)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Configuration avec GROQ ===
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",  # ✅ URL corrigée (pas d'espaces)
    api_key=os.getenv("GROQ_API_KEY")
)

if not client.api_key:
    raise RuntimeError("Clé GROQ manquante. Ajoute GROQ_API_KEY dans le fichier .env")

# === Templates personnalisés ===
TEMPLATES = {
    "standard": {
        "description": "Fiche classique, neutre et professionnelle",
        "prompt": """
# Structure
- Mission
- Profil recherché
- Compétences requises
- Conditions (contrat, localisation, salaire, avantages)
- Pour postuler

Ton : neutre, clair, inclusif.
        """
    },
    "startup": {
        "description": "Style dynamique, moderne, pour startup tech",
        "prompt": """
# Structure
- 🚀 À propos du poste
- 💡 Mission impactante
- 🔧 Stack technique & outils
- 🌱 Profil idéal (pas besoin de tout matcher !)
- 🌟 Ce que tu apporteras
- 🏖️ Avantages & culture
- ✨ Pourquoi nous rejoindre ?

Ton : dynamique, enthousiaste, informel mais professionnel.
        """
    },
    "corporate": {
        "description": "Style formel, hiérarchisé, pour grand groupe",
        "prompt": """
# Structure
1. Intitulé du poste
2. Direction / Entité
3. Objectifs principaux
4. Missions détaillées
5. Profil requis (diplômes, expérience)
6. Compétences techniques et comportementales
7. Conditions d’emploi (localisation, contrat, salaire, avantages)
8. Processus de recrutement

Ton : formel, structuré, précis.
        """
    },
    "creative": {
        "description": "Style original, pour métiers créatifs (design, marketing, com)",
        "prompt": """
# Structure
- 🎨 Le poste en 1 phrase
- 🧠 Ce que tu feras au quotidien
- 🎯 Ce qu’on attend de toi
- 🧰 Tes super-pouvoirs (compétences)
- 🌈 Notre univers (culture, équipe)
- 🎁 Ce qu’on t’offre
- 📬 Viens créer avec nous !

Ton : créatif, vivant, inspirant. Utilise des emojis avec parcimonie.
        """
    },
    "tech": {
        "description": "Focus technique, pour développeurs, data, ingénieurs",
        "prompt": """
# Structure
- Poste : Développeur(euse) {title}
- Équipe : {department}
- Stack technique
- Problèmes que tu résoudras
- Impact de ton rôle
- Expérience requise (langages, années, outils)
- Bon à savoir (code review, CI/CD, agile, etc.)
- Conditions (télétravail, horaires, salaire, stock options)

Ton : technique, précis, mais accessible. Évite le jargon excessif.
        """
    }
}

# === Modèle d'entrée ===
class JobInput(BaseModel):
    title: str
    department: str = ""
    seniority: str = "junior"
    location: str = ""
    contract_type: str = "CDI"
    language: str = "fr"
    tone: str = "neutre"
    length: str = "standard"
    key_skills: List[str] = []
    salary_band: str = ""
    benefits: List[str] = []
    company_context: str = ""
    policies: str = ""
    template: str = "standard"

    @field_validator("seniority")
    @classmethod
    def validate_seniority(cls, v):
        allowed = ["junior", "intermédiaire", "senior", "expert"]
        if v not in allowed:
            raise ValueError(f"Niveau invalide. Autorisés : {allowed}")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        if v not in ["fr", "en"]:
            raise ValueError("Langue supportée : 'fr' ou 'en'")
        return v

    @field_validator("template")
    @classmethod
    def validate_template(cls, v):
        if v not in TEMPLATES:
            raise ValueError(f"Template inconnu. Valeurs possibles : {list(TEMPLATES.keys())}")
        return v

# === Routes ===
@app.get("/")
def home():
    return {
        "message": "✅ Chatbot Job Description API is running!",
        "documentation": "/docs pour tester l'API"
    }

@app.get("/templates")
def list_templates():
    return {
        "available_templates": [
            {"name": name, "description": data["description"]}
            for name, data in TEMPLATES.items()
        ],
        "message": "Utilise le champ 'template' dans /generate"
    }

@app.post("/generate")
def generate_description(job: JobInput):
    try:
        template_data = TEMPLATES[job.template]
        instructions = template_data["prompt"]
        instructions = instructions.format(
            title=job.title,
            department=job.department or "non spécifié"
        )

        skills_str = ", ".join(job.key_skills) if job.key_skills else "À définir"
        benefits_str = ", ".join(job.benefits) if job.benefits else "Non spécifiés"
        salary_info = f"Rémunération : {job.salary_band}. " if job.salary_band else ""
        company_info = f"Contexte entreprise : {job.company_context}. " if job.company_context else ""
        policy_info = f"Politiques RH : {job.policies}. " if job.policies else ""

        prompt = f"""
{instructions}

**Informations fournies :**
- Poste : {job.title}
- Département : {job.department}
- Niveau : {job.seniority}
- Localisation : {job.location}
- Contrat : {job.contract_type}
- Compétences clés : {skills_str}
- Avantages : {benefits_str}
{salary_info}{company_info}{policy_info}

**Langue :** {job.language}
**Longueur :** {job.length}
        """

        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Tu es un expert RH. Génère une fiche de poste claire et inclusive."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        markdown = response.choices[0].message.content.strip()

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "title": job.title,
            "template": job.template,
            "language": job.language,
            "markdown": markdown
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")

# === Génération de PDF ===
@app.post("/generate-pdf")
def generate_pdf(job: JobInput):
    try:
        # Réutilise la logique de /generate
        template_data = TEMPLATES[job.template]
        instructions = template_data["prompt"]
        instructions = instructions.format(
            title=job.title,
            department=job.department or "non spécifié"
        )

        skills_str = ", ".join(job.key_skills) if job.key_skills else "À définir"
        benefits_str = ", ".join(job.benefits) if job.benefits else "Non spécifiés"
        salary_info = f"Rémunération : {job.salary_band}. " if job.salary_band else ""
        company_info = f"Contexte entreprise : {job.company_context}. " if job.company_context else ""
        policy_info = f"Politiques RH : {job.policies}. " if job.policies else ""

        prompt = f"""
{instructions}

**Informations fournies :**
- Poste : {job.title}
- Département : {job.department}
- Niveau : {job.seniority}
- Localisation : {job.location}
- Contrat : {job.contract_type}
- Compétences clés : {skills_str}
- Avantages : {benefits_str}
{salary_info}{company_info}{policy_info}

**Langue :** {job.language}
**Longueur :** {job.length}
        """

        # Appel à Groq
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Tu es un expert RH. Génère une fiche de poste claire et inclusive."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        markdown = response.choices[0].message.content.strip()

        # Convertir en HTML
        def markdown_to_html(md: str) -> str:
            md = html.escape(md)
            md = md.replace('\n', '<br>')
            md = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', md)
            md = re.sub(r'\*(.*?)\*', r'<em>\1</em>', md)
            return f"""
            <html>
            <head><meta charset="UTF-8"></head>
            <body style="font-family: Arial; line-height: 1.6; padding: 20px;">
                <h2>Fiche de poste : {job.title}</h2>
                <p>{md}</p>
            </body>
            </html>
            """

        html_content = markdown_to_html(markdown)

        # Options PDF
        options = {
            'page-size': 'A4',
            'margin-top': '15mm',
            'margin-right': '15mm',
            'margin-bottom': '15mm',
            'margin-left': '15mm',
            'encoding': 'UTF-8'
        }

        pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)
        filename = f"fiche_poste_{job.title.replace(' ', '_')}.pdf"

        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur PDF : {str(e)}")
    

# === Démarrage du serveur ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)