# orientation/management/commands/populate_youtube_playlists.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from orientation.models import YouTubePlaylist, Track


class Command(BaseCommand):
    help = "Ajoute automatiquement des ressources vidéo YouTube (3 par filière)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Supprime toutes les entrées existantes avant de recréer les vidéos.",
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Début de l'alimentation des vidéos YouTube…")

        # --- Récupération des filières (adapté à tes noms) ---
        try:
            informatique = Track.objects.get(name__icontains="informatique")
            sociales = Track.objects.get(name__icontains="Sciences sociales")
            sante = Track.objects.get(name__icontains="Sciences de la santé")
            gestion = Track.objects.get(name__icontains="Gestion / Management")
            arts_design = Track.objects.get(name__icontains="Arts / Design")
        except Track.DoesNotExist as e:
            self.stderr.write(f"❌ Erreur : {e}")
            self.stderr.write(
                "❌ Certaines filières n'existent pas. Vérifie les noms dans l'admin Django."
            )
            return

        overwrite = options.get("overwrite", False)
        today = timezone.now().date()

        if overwrite:
            count = YouTubePlaylist.objects.count()
            YouTubePlaylist.objects.all().delete()
            self.stdout.write(f"🗑️ Anciennes entrées supprimées : {count}")

        # -----------------------------------------------------------
        # TES 15 LIENS, RÉPARTIS PAR FILIÈRE (3 chacun)
        # -----------------------------------------------------------
        videos_data = [

            # ==============================
            # INFORMATIQUE (1–3)
            # ==============================
            {
                "title": "Informatique - Ressource 1",
                "youtube_url": "https://www.youtube.com/watch?v=t8b9f5M9yoY&list=PLMS9Cy4Enq5InyTit-FRwCcqRSAtSc54s",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo d'introduction en informatique / programmation.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [informatique],
            },
            {
                "title": "Informatique - Ressource 2",
                "youtube_url": "https://www.youtube.com/watch?v=Y80juYcu3ZI&list=PLwLsbqvBlImHG5yeUCXJ1aqNMgUKi1NK3",
                "channel_name": "Ressource YouTube",
                "description": "Tutoriel HTML / CSS pour débutants et confirmés.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [informatique],
            },
            {
                "title": "Informatique - Ressource 3",
                "youtube_url": "https://www.youtube.com/watch?v=G3e-cpL7ofc",
                "channel_name": "Ressource YouTube",
                "description": "Cours complet HTML / CSS (structure, mise en page, etc.).",
                "difficulty": "intermediate",
                "language": "en",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [informatique],
            },

            # ==============================
            # SCIENCES SOCIALES (4–6)
            # ==============================
            {
                "title": "Sciences sociales - Ressource 1",
                "youtube_url": "https://www.youtube.com/watch?v=Uy_ApDmnR-8",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo d'introduction à des notions de sciences sociales.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [sociales],
            },
            {
                "title": "Sciences sociales - Ressource 2",
                "youtube_url": "https://www.youtube.com/watch?v=zgKU5PluVKM&list=PLABRzgxxbXhh0c4NYcTcYLOrt3MzfDIhM",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo sur la stratification, la société, les inégalités, etc.",
                "difficulty": "intermediate",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [sociales],
            },
            {
                "title": "Sciences sociales - Ressource 3",
                "youtube_url": "https://www.youtube.com/watch?v=Q70O580wvyw&list=PLJo4b5dXvi0KW9heNHB1fFsNGIso-2BtE",
                "channel_name": "Ressource YouTube",
                "description": "Introduction / cours de sociologie.",
                "difficulty": "intermediate",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [sociales],
            },

            # ==============================
            # SCIENCES DE LA SANTÉ (7–9)
            # ==============================
            {
                "title": "Sciences de la santé - Ressource 1",
                "youtube_url": "https://www.youtube.com/watch?v=o7vlSWf00M8",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo autour de la santé mentale / psychologie clinique.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [sante],
            },
            {
                "title": "Sciences de la santé - Ressource 2",
                "youtube_url": "https://www.youtube.com/watch?v=y9MMiw2p8Mk",
                "channel_name": "Ressource YouTube",
                "description": "Documentaire ou émission liée à la santé / alimentation, etc.",
                "difficulty": "intermediate",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [sante],
            },
            {
                "title": "Sciences de la santé - Ressource 3",
                "youtube_url": "https://www.youtube.com/watch?v=NY_egkXbg3g",
                "channel_name": "Ressource YouTube",
                "description": "Ressource vidéo liée aux sciences de la santé.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [sante],
            },

            # ==============================
            # GESTION / MANAGEMENT (10–12)
            # ==============================
            {
                "title": "Gestion / Management - Ressource 1",
                "youtube_url": "https://www.youtube.com/playlist?list=PL6ITMYvPOJHRpZb4OGMjNjIloT-0fdKeH",
                "channel_name": "Ressource YouTube",
                "description": "Playlist / série de vidéos liée à la gestion / management.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 2,
                "video_count": 1,
                "tracks": [gestion],
            },
            {
                "title": "Gestion / Management - Ressource 2",
                "youtube_url": "https://www.youtube.com/watch?v=b1Gc_XucDv8&list=PL4EgFiuFC3KSD4TTkECN_OATAw5vPBFOk",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo en lien avec la gestion / management.",
                "difficulty": "intermediate",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [gestion],
            },
            {
                "title": "Gestion / Management - Ressource 3",
                "youtube_url": "https://www.youtube.com/watch?v=jVgYgN0zcWs",
                "channel_name": "Ressource YouTube",
                "description": "Ressource complémentaire en gestion / management.",
                "difficulty": "beginner",
                "language": "fr",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [gestion],
            },

            # ==============================
            # ARTS / DESIGN (13–15)
            # ==============================
            {
                "title": "Arts / Design - Ressource 1",
                "youtube_url": "https://www.youtube.com/watch?v=zzhSFobLkYw&list=PLXDU_eVOJTx5IuSrbtanZHnDuPB3Hx0hq",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo / série autour du design / multimédia.",
                "difficulty": "beginner",
                "language": "en",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [arts_design],
            },
            {
                "title": "Arts / Design - Ressource 2",
                "youtube_url": "https://www.youtube.com/watch?v=1SNZRCVNizg",
                "channel_name": "Ressource YouTube",
                "description": "Vidéo en lien avec l’animation, le design ou les arts.",
                "difficulty": "beginner",
                "language": "en",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [arts_design],
            },
            {
                "title": "Arts / Design - Ressource 3",
                "youtube_url": "https://www.youtube.com/watch?v=zl3EOqCYpWs&list=PLusGTl1J6aRWREOphHfdU6VZSeFoI6upf",
                "channel_name": "Ressource YouTube",
                "description": "Ressource avancée en design / UX / multimédia.",
                "difficulty": "intermediate",
                "language": "en",
                "estimated_hours": 1,
                "video_count": 1,
                "tracks": [arts_design],
            },
        ]

        created = 0
        updated = 0

        for data in videos_data:
            tracks = data.pop("tracks")

            playlist, is_created = YouTubePlaylist.objects.get_or_create(
                title=data["title"],
                youtube_url=data["youtube_url"],
                defaults={
                    **data,
                    "last_verified": today,
                    "is_active": True,
                    "is_free": True,
                },
            )

            if is_created:
                playlist.tracks.set(tracks)
                created += 1
                self.stdout.write(f"✅ Ajouté : {playlist.title}")
            else:
                # Mise à jour légère
                for field, value in data.items():
                    setattr(playlist, field, value)
                playlist.last_verified = today
                playlist.tracks.set(tracks)
                playlist.is_active = True
                playlist.save()
                updated += 1
                self.stdout.write(f"♻️ Mis à jour : {playlist.title}")

        self.stdout.write("")
        self.stdout.write("🎉 Import terminé !")
        self.stdout.write(f"➕ Créées : {created}")
        self.stdout.write(f"🔁 MAJ     : {updated}")