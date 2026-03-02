from django.core.management.base import BaseCommand
from orientation.models import YouTubePlaylist, UserPlaylistProgress


class Command(BaseCommand):
    help = "Supprime toutes les playlists YouTube et les progressions associées."

    def handle(self, *args, **options):
        # D'abord les progressions (car elles pointent vers les playlists)
        progress_count = UserPlaylistProgress.objects.count()
        UserPlaylistProgress.objects.all().delete()

        # Puis les playlists
        playlist_count = YouTubePlaylist.objects.count()
        YouTubePlaylist.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"Supprimé {progress_count} progressions et {playlist_count} playlists."
        ))