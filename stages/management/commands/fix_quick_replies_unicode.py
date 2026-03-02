import codecs

from django.core.management.base import BaseCommand
from django.db import transaction

from stages.models import QuickReply


class Command(BaseCommand):
    help = (
        "Nettoie les QuickReply existants en décodant les séquences "
        "Unicode échappées (\\u000A, \\u002D, etc.)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        qs = QuickReply.objects.all()
        total = qs.count()
        fixed = 0
        skipped = 0

        self.stdout.write(f"Analyse de {total} QuickReply...")

        for qr in qs:
            old_text = qr.text or ""

            # On ne touche que ceux qui ont des séquences échappées typiques
            if "\\u" in old_text or "\\n" in old_text or "\\r" in old_text:
                try:
                    # decode \uXXXX, \n, etc.
                    new_text = codecs.decode(old_text, "unicode_escape")
                except Exception as e:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"⏩ Impossible de décoder QuickReply id={qr.id} ({qr.label}): {e}"
                        )
                    )
                    continue

                if new_text != old_text:
                    qr.text = new_text
                    qr.save(update_fields=["text"])
                    fixed += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Fixé QuickReply id={qr.id} ({qr.label})"
                        )
                    )
                else:
                    skipped += 1
            else:
                skipped += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Terminé. {fixed} QuickReply corrigés, {skipped} ignorés."
        ))