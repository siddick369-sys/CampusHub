"""
CV Generator Pro — Views
========================
Full-page builder, live preview, PDF generation (WeasyPrint),
auto-save, AI enhance, scoring, duplication, versioning.
"""
import json
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.decorators import student_required
from accounts.models import Profile
from accounts.services import UsageManager
from orientation.models import OrientationResult
from stages.models import Application

from .cv_models import (
    CVProfile, CVVersion, CVTemplate, CVExperience, CVEducation,
    CVSkill, CVLanguage, CVProject, CVCertification, CVInterest,
    CVScoreResult,
)
from .cv_forms import (
    CVProfileForm, CVExperienceFormSet, CVEducationFormSet,
    CVSkillFormSet, CVLanguageFormSet, CVProjectFormSet,
    CVCertificationFormSet, CVInterestFormSet,
)
from .cv_score_engine import score_cv, score_cv_for_offer


def _prefill_cv(cv, user, profile):
    """Pré-rempli un CVProfile depuis le Profile utilisateur et les stages."""
    if not cv.first_name:
        names = (profile.full_name or user.get_full_name() or user.username).split(' ', 1)
        cv.first_name = names[0]
        cv.last_name = names[1] if len(names) > 1 else ''
    if not cv.email:
        cv.email = user.email
    if not cv.phone:
        cv.phone = profile.phone or ''
    if not cv.city:
        cv.city = profile.city or ''
    if not cv.country:
        cv.country = profile.country or ''
    if not cv.summary:
        cv.summary = profile.bio or ''
    if not cv.professional_title and profile.student_field:
        cv.professional_title = f"Étudiant en {profile.student_field}"
    if profile.avatar and not cv.photo:
        cv.photo = profile.avatar
    cv.save()

    # Pre-fill experiences from accepted stage applications
    if not cv.experiences.exists():
        apps = (
            Application.objects
            .select_related('offer', 'offer__company')
            .filter(student=user, status__in=['accepted', 'completed'])
            .order_by('-created_at')[:5]
        )
        for i, app in enumerate(apps):
            CVExperience.objects.create(
                cv_profile=cv,
                job_title=app.offer.title,
                company_name=getattr(app.offer.company, 'username', 'Entreprise'),
                location=f"{getattr(app.offer, 'city', '')} {getattr(app.offer, 'country', '')}".strip(),
                start_date=app.created_at.strftime('%m/%Y') if app.created_at else '',
                description="Stage effectué via CampusHub.",
                from_application=app,
                order=i,
            )

    # Pre-fill education from profile
    if not cv.educations.exists() and profile.student_school:
        CVEducation.objects.create(
            cv_profile=cv,
            diploma=profile.get_student_level_display() if hasattr(profile, 'get_student_level_display') else 'DUT',
            institution=profile.student_school,
            description=profile.student_field or '',
            order=0,
        )

    # Pre-fill skills from orientation results
    if not cv.skills.exists():
        last_orientation = (
            OrientationResult.objects
            .filter(user=user)
            .order_by('-created_at')
            .first()
        )
        if last_orientation:
            i = 0
            for track in last_orientation.suggested_tracks.all()[:5]:
                if track.main_skills:
                    for skill_name in track.main_skills.split(',')[:3]:
                        CVSkill.objects.create(
                            cv_profile=cv,
                            name=skill_name.strip(),
                            level=3,
                            category='technical',
                            order=i,
                        )
                        i += 1


def _get_cv_context(cv):
    """Build the template context for a CVProfile."""
    return {
        'cv': cv,
        'experiences': cv.experiences.all(),
        'educations': cv.educations.all(),
        'skills': cv.skills.all(),
        'languages': cv.languages.all(),
        'projects': cv.projects.all(),
        'certifications': cv.certifications.all(),
        'interests': cv.interests.all(),
        'section_order': cv.get_section_order(),
    }


def _save_version_snapshot(cv):
    """Save a version snapshot before any major change."""
    data = {
        'personal': {
            'first_name': cv.first_name, 'last_name': cv.last_name,
            'professional_title': cv.professional_title, 'email': cv.email,
            'phone': cv.phone, 'city': cv.city, 'country': cv.country,
            'summary': cv.summary,
        },
        'design': {
            'primary_color': cv.primary_color, 'font_family': cv.font_family,
            'photo_frame': cv.photo_frame, 'skill_display': cv.skill_display,
        },
        'experiences': list(cv.experiences.values('job_title', 'company_name', 'location', 'start_date', 'end_date', 'is_current', 'description')),
        'educations': list(cv.educations.values('diploma', 'institution', 'location', 'start_date', 'end_date', 'description')),
        'skills': list(cv.skills.values('name', 'level', 'category')),
        'languages': list(cv.languages.values('language', 'level')),
        'projects': list(cv.projects.values('title', 'description', 'url', 'technologies')),
        'certifications': list(cv.certifications.values('name', 'issuer', 'date', 'url')),
        'interests': list(cv.interests.values('name')),
    }
    CVVersion.objects.create(
        cv_profile=cv,
        version_number=cv.version,
        snapshot_data=data,
    )
    cv.version += 1
    cv.save(update_fields=['version'])


# -------------------------------------------------------------------
# MAIN BUILDER VIEW
# -------------------------------------------------------------------
@login_required
@student_required
def cv_builder_view(request):
    """Page principale du générateur de CV / éditeur."""
    profile = request.user.profile

    # Get or create the primary CV
    cv = CVProfile.objects.filter(user=request.user, is_primary=True).first()
    if not cv:
        cv = CVProfile.objects.filter(user=request.user).first()
    if not cv:
        default_template = CVTemplate.objects.filter(is_active=True, slug='modern').first()
        cv = CVProfile.objects.create(
            user=request.user,
            title="Mon CV CampusHub",
            template=default_template,
            is_primary=True,
        )
        _prefill_cv(cv, request.user, profile)

    if request.method == 'POST':
        form = CVProfileForm(request.POST, request.FILES, instance=cv)
        exp_formset = CVExperienceFormSet(request.POST, instance=cv, prefix='exp')
        edu_formset = CVEducationFormSet(request.POST, instance=cv, prefix='edu')
        skill_formset = CVSkillFormSet(request.POST, instance=cv, prefix='skill')
        lang_formset = CVLanguageFormSet(request.POST, instance=cv, prefix='lang')
        proj_formset = CVProjectFormSet(request.POST, instance=cv, prefix='proj')
        cert_formset = CVCertificationFormSet(request.POST, instance=cv, prefix='cert')
        interest_formset = CVInterestFormSet(request.POST, instance=cv, prefix='interest')

        all_valid = (
            form.is_valid() and exp_formset.is_valid() and edu_formset.is_valid() and
            skill_formset.is_valid() and lang_formset.is_valid() and proj_formset.is_valid() and
            cert_formset.is_valid() and interest_formset.is_valid()
        )

        if all_valid:
            _save_version_snapshot(cv)
            form.save()
            exp_formset.save()
            edu_formset.save()
            skill_formset.save()
            lang_formset.save()
            proj_formset.save()
            cert_formset.save()
            interest_formset.save()

            # Handle template selection
            template_slug = request.POST.get('template_slug')
            if template_slug:
                tpl = CVTemplate.objects.filter(slug=template_slug, is_active=True).first()
                if tpl:
                    cv.template = tpl
                    cv.save(update_fields=['template'])

            cv.is_draft = False
            cv.save(update_fields=['is_draft'])
            messages.success(request, "CV sauvegardé avec succès !")
            return redirect('cv_builder')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = CVProfileForm(instance=cv)
        exp_formset = CVExperienceFormSet(instance=cv, prefix='exp')
        edu_formset = CVEducationFormSet(instance=cv, prefix='edu')
        skill_formset = CVSkillFormSet(instance=cv, prefix='skill')
        lang_formset = CVLanguageFormSet(instance=cv, prefix='lang')
        proj_formset = CVProjectFormSet(instance=cv, prefix='proj')
        cert_formset = CVCertificationFormSet(instance=cv, prefix='cert')
        interest_formset = CVInterestFormSet(instance=cv, prefix='interest')

    templates = CVTemplate.objects.filter(is_active=True)
    all_cvs = CVProfile.objects.filter(user=request.user).order_by('-updated_at')

    context = {
        'cv': cv,
        'form': form,
        'exp_formset': exp_formset,
        'edu_formset': edu_formset,
        'skill_formset': skill_formset,
        'lang_formset': lang_formset,
        'proj_formset': proj_formset,
        'cert_formset': cert_formset,
        'interest_formset': interest_formset,
        'templates': templates,
        'all_cvs': all_cvs,
    }
    return render(request, 'stages/cv_builder.html', context)


# -------------------------------------------------------------------
# LIVE PREVIEW (iframe endpoint)
# -------------------------------------------------------------------
@login_required
def cv_preview_view(request):
    """Rend la preview HTML du CV dans une iframe."""
    cv_id = request.GET.get('cv_id')
    if cv_id:
        cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    else:
        cv = CVProfile.objects.filter(user=request.user, is_primary=True).first()
    if not cv:
        return HttpResponse("<p style='padding:20px;color:#999;'>Aucun CV trouvé.</p>")

    template_path = cv.get_template_path()
    context = _get_cv_context(cv)
    html = render_to_string(template_path, context)
    return HttpResponse(html)


# -------------------------------------------------------------------
# PDF DOWNLOAD (WeasyPrint)
# -------------------------------------------------------------------
@login_required
@student_required
def cv_download_pdf_view(request):
    """Génère et télécharge le PDF via WeasyPrint."""
    cv_id = request.GET.get('cv_id')
    if cv_id:
        cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    else:
        cv = CVProfile.objects.filter(user=request.user, is_primary=True).first()
    if not cv:
        messages.error(request, "Aucun CV trouvé.")
        return redirect('cv_builder')

    # Quota check
    if not UsageManager.is_action_allowed(request.user, 'cv_ia'):
        messages.warning(request, "Quota de téléchargement CV atteint.")
        return redirect('cv_builder')

    try:
        from weasyprint import HTML

        template_path = cv.get_template_path()
        context = _get_cv_context(cv)
        html_string = render_to_string(template_path, context, request=request)

        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        cv.increment_download()
        UsageManager.increment_usage(request.user, 'cv_ia')

        filename = f"CV_{cv.first_name}_{cv.last_name}.pdf".replace(' ', '_')
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        # Fallback to xhtml2pdf if WeasyPrint fails
        from .utils_pdf import render_html_to_pdf_bytes
        template_path = cv.get_template_path()
        context = _get_cv_context(cv)
        pdf_bytes = render_html_to_pdf_bytes(template_path, context)
        if pdf_bytes:
            cv.increment_download()
            filename = f"CV_{cv.first_name}_{cv.last_name}.pdf".replace(' ', '_')
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        messages.error(request, f"Erreur de génération PDF: {str(e)}")
        return redirect('cv_builder')


# -------------------------------------------------------------------
# AUTO-SAVE (AJAX)
# -------------------------------------------------------------------
@login_required
@require_POST
def cv_save_draft_api(request):
    """Endpoint AJAX pour sauvegarde automatique."""
    try:
        data = json.loads(request.body)
        cv_id = data.get('cv_id')
        cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)

        # Update only the fields that are sent
        fields_to_update = []
        for field in ['first_name', 'last_name', 'professional_title', 'email', 'phone',
                      'city', 'country', 'summary', 'primary_color', 'secondary_color',
                      'font_family', 'photo_frame', 'skill_display']:
            if field in data:
                setattr(cv, field, data[field])
                fields_to_update.append(field)

        if 'section_order' in data:
            cv.section_order = data['section_order']
            fields_to_update.append('section_order')

        if 'template_slug' in data:
            tpl = CVTemplate.objects.filter(slug=data['template_slug']).first()
            if tpl:
                cv.template = tpl
                fields_to_update.append('template')

        if fields_to_update:
            cv.save(update_fields=fields_to_update + ['updated_at'])

        return JsonResponse({'status': 'ok', 'saved_at': timezone.now().isoformat()})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# -------------------------------------------------------------------
# AI ENHANCE (AJAX)
# -------------------------------------------------------------------
@login_required
@require_POST
def cv_ai_enhance_api(request):
    """Utilise l'IA pour améliorer un texte (résumé, description, etc.)."""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        field_type = data.get('type', 'summary')

        if not text:
            return JsonResponse({'status': 'error', 'message': 'Texte vide'}, status=400)

        # Use the existing AI infrastructure
        from ai_assistant.models import AICachedResponse
        import hashlib

        prompt_map = {
            'summary': f"Réécris ce résumé professionnel de manière concise et impactante pour un CV. Garde le même sens, utilise un ton professionnel. Maximum 4 phrases:\n\n{text}",
            'description': f"Réécris cette description d'expérience professionnelle de manière concise et impactante pour un CV. Utilise des verbes d'action. Maximum 3 phrases:\n\n{text}",
            'ats_keywords': f"Analyse ce texte de CV et suggère 10 mots-clés ATS importants qui manquent:\n\n{text}",
        }
        prompt = prompt_map.get(field_type, prompt_map['summary'])

        # Check cache
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        cached = AICachedResponse.objects.filter(prompt_hash=cache_key).first()
        if cached:
            return JsonResponse({'status': 'ok', 'enhanced_text': cached.response_text})

        # Call AI (using settings-based API)
        try:
            from django.conf import settings
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            enhanced = response.text

            # Cache the response
            AICachedResponse.objects.create(
                prompt_hash=cache_key,
                prompt_text=prompt[:500],
                response_text=enhanced,
            )

            return JsonResponse({'status': 'ok', 'enhanced_text': enhanced})
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Service IA temporairement indisponible'}, status=503)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# -------------------------------------------------------------------
# CV SCORE (AJAX)
# -------------------------------------------------------------------
@login_required
def cv_score_api(request):
    """Retourne le score ATS du CV."""
    cv_id = request.GET.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)

    offer_title = request.GET.get('offer_title', '')
    offer_desc = request.GET.get('offer_desc', '')

    if offer_title:
        scores = score_cv_for_offer(cv, offer_title, offer_desc)
    else:
        scores = score_cv(cv)

    # Save score result
    CVScoreResult.objects.create(
        cv_profile=cv,
        overall_score=scores['overall_score'],
        keyword_score=scores['keyword_score'],
        action_verbs_score=scores['action_verbs_score'],
        completeness_score=scores['completeness_score'],
        formatting_score=scores['formatting_score'],
        missing_keywords=scores.get('missing_keywords', []),
        suggestions=scores.get('suggestions', []),
        weak_descriptions=scores.get('weak_descriptions', []),
        target_offer_title=offer_title,
    )

    cv.last_ats_score = scores['overall_score']
    cv.save(update_fields=['last_ats_score'])

    return JsonResponse(scores)


# -------------------------------------------------------------------
# DUPLICATE CV
# -------------------------------------------------------------------
@login_required
@require_POST
def cv_duplicate_view(request):
    """Duplique un CV."""
    cv_id = request.POST.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    new_cv = cv.duplicate()
    messages.success(request, f"CV dupliqué : {new_cv.title}")
    return redirect('cv_builder')


# -------------------------------------------------------------------
# SWITCH CV
# -------------------------------------------------------------------
@login_required
def cv_switch_view(request, cv_id):
    """Change le CV actif."""
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    CVProfile.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    cv.is_primary = True
    cv.save(update_fields=['is_primary'])
    return redirect('cv_builder')


# -------------------------------------------------------------------
# NEW CV
# -------------------------------------------------------------------
@login_required
@require_POST
def cv_new_view(request):
    """Crée un nouveau CV vierge."""
    default_tpl = CVTemplate.objects.filter(is_active=True, slug='modern').first()
    cv = CVProfile.objects.create(
        user=request.user,
        title=f"CV #{CVProfile.objects.filter(user=request.user).count() + 1}",
        template=default_tpl,
    )
    CVProfile.objects.filter(user=request.user, is_primary=True).exclude(pk=cv.pk).update(is_primary=False)
    cv.is_primary = True
    cv.save(update_fields=['is_primary'])
    _prefill_cv(cv, request.user, request.user.profile)
    messages.success(request, "Nouveau CV créé !")
    return redirect('cv_builder')


# -------------------------------------------------------------------
# DELETE CV
# -------------------------------------------------------------------
@login_required
@require_POST
def cv_delete_view(request):
    """Supprime un CV."""
    cv_id = request.POST.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    cv.delete()
    messages.success(request, "CV supprimé.")
    return redirect('cv_builder')


# -------------------------------------------------------------------
# VERSION HISTORY
# -------------------------------------------------------------------
@login_required
def cv_version_history_view(request):
    """Liste l'historique des versions d'un CV."""
    cv_id = request.GET.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    versions = cv.versions.all()[:20]
    return JsonResponse({
        'versions': [
            {
                'version': v.version_number,
                'date': v.created_at.strftime('%d/%m/%Y %H:%M'),
                'snapshot': v.snapshot_data,
            }
            for v in versions
        ]
    })
