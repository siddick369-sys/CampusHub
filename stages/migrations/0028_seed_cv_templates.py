"""
Data migration: seed the 5 default CV templates.
"""
from django.db import migrations


def seed_templates(apps, schema_editor):
    CVTemplate = apps.get_model('stages', 'CVTemplate')

    templates = [
        {
            'name': 'Modern',
            'slug': 'modern',
            'description': '2 colonnes, sidebar sombre, barres de compétences',
            'template_file': 'stages/cv_templates/modern.html',
            'css_class': 'cv-modern',
            'is_premium': False,
            'sort_order': 1,
        },
        {
            'name': 'Classic',
            'slug': 'classic',
            'description': 'En-tête centré, sections traditionnelles, ATS-optimisé',
            'template_file': 'stages/cv_templates/classic.html',
            'css_class': 'cv-classic',
            'is_premium': False,
            'sort_order': 2,
        },
        {
            'name': 'Minimal',
            'slug': 'minimal',
            'description': 'Ultra-épuré, une seule colonne, maximum d\'espace',
            'template_file': 'stages/cv_templates/minimal.html',
            'css_class': 'cv-minimal',
            'is_premium': False,
            'sort_order': 3,
        },
        {
            'name': 'Creative',
            'slug': 'creative',
            'description': 'Sidebar gradient, barres segmentées, badges colorés',
            'template_file': 'stages/cv_templates/creative.html',
            'css_class': 'cv-creative',
            'is_premium': True,
            'sort_order': 4,
        },
        {
            'name': 'Executive',
            'slug': 'executive',
            'description': 'Bande sombre, accents dorés, typographie élégante',
            'template_file': 'stages/cv_templates/executive.html',
            'css_class': 'cv-executive',
            'is_premium': True,
            'sort_order': 5,
        },
    ]

    for tpl_data in templates:
        CVTemplate.objects.get_or_create(
            slug=tpl_data['slug'],
            defaults=tpl_data,
        )


def reverse_seed(apps, schema_editor):
    CVTemplate = apps.get_model('stages', 'CVTemplate')
    CVTemplate.objects.filter(slug__in=['modern', 'classic', 'minimal', 'creative', 'executive']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stages', '0027_cvtemplate_alter_message_attachment_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_seed),
    ]
