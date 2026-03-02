import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AICachedResponse(models.Model):
    """
    Stocke les réponses de l'IA pour économiser des appels API et réduire la latence.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question_originale = models.TextField(verbose_name="Question originale")
    question_normalisee = models.TextField(verbose_name="Question normalisée", db_index=True)
    # Note: On pourra ajouter un champ VECTOR si on utilise pgvector plus tard
    reponse = models.TextField(verbose_name="Réponse générée")
    compteur_utilisation = models.PositiveIntegerField(default=1, verbose_name="Nombre d'utilisations")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Réponse IA en Cache"
        verbose_name_plural = "Réponses IA en Cache"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cache: {self.question_normalisee[:50]}..."

class AIChatSession(models.Model):
    """
    Stocke l'historique des conversations par utilisateur pour maintenir le contexte.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_sessions", null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True, db_index=True) # Pour les utilisateurs non connectés
    history = models.JSONField(default=list, verbose_name="Historique (JSON)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Session de Chat IA"
        verbose_name_plural = "Sessions de Chat IA"

    def __str__(self):
        return f"Session {self.session_id} - {self.user if self.user else 'Anonyme'}"
