import os
from groq import Groq
from django.conf import settings

class GroqCVClient:
    def __init__(self):
        # We use the key from environment variables
        self.api_key = os.getenv("GROQ_API_KEY_CV")
        if not self.api_key:
            # Fallback to general key if specific one is missing
            self.api_key = os.getenv("GROQ_API_KEY")

        self.client = Groq(api_key=self.api_key)

    def enhance_text(self, text, field_type="summary"):
        prompts = {
            'summary': f"Agis en tant qu'expert en recrutement. Réécris ce résumé de CV pour qu'il soit percutant, professionnel et optimisé ATS. Maximum 300 caractères :\n\n{text}",
            'experience': f"Agis en tant qu'expert en recrutement. Réécris cette description d'expérience en utilisant des verbes d'action et en mettant en avant les résultats. Maximum 3 puces :\n\n{text}",
            'project': f"Agis en tant qu'expert en recrutement. Améliore cette description de projet technique pour un CV :\n\n{text}"
        }
        prompt = prompts.get(field_type, prompts['summary'])
        
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq Error: {e}")
            return None

    def analyze_cv(self, cv_data, job_title="", job_desc=""):
        prompt = f"""
        Analyse ce CV par rapport aux standards de recrutement modernes (ATS).
        CV DATA: {cv_data}
        POSTE VISÉ: {job_title}
        DESCRIPTION POSTE: {job_desc}

        Réponds UNIQUEMENT au format JSON strict suivant :
        {{
            "overall_score": 85,
            "keyword_score": 20,
            "action_verbs_score": 22,
            "completeness_score": 25,
            "formatting_score": 18,
            "suggestions": ["suggestion 1", "suggestion 2"],
            "missing_keywords": ["keyword 1", "keyword 2"],
            "feedback_general": "Ton CV est solide mais manque de données chiffrées."
        }}
        """
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            import json
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"Groq Analyze Error: {e}")
            return None
