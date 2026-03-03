"""
CV Generator Pro — Views (Upgraded)
===================================
Full-page builder, live preview, PDF generation (WeasyPrint ONLY),
auto-save, Groq AI enhance, intelligent scoring.
"""
import json
import io
import hashlib
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
from .cv_score_engine import score_cv, score_cv_for_offer, _collect_all_text


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


@login_required
@student_required
def cv_builder_view(request):
    """Page principale du générateur de CV / éditeur."""
    profile = request.user.profile

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


@login_required
def cv_preview_view(request):
    """Rend la preview HTML du CV dans une iframe."""
    cv_id = request.GET.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user) if cv_id else CVProfile.objects.filter(user=request.user, is_primary=True).first()
    if not cv: return HttpResponse("<p>Aucun CV trouvé.</p>")
    template_path = cv.get_template_path()
    context = _get_cv_context(cv)
    return HttpResponse(render_to_string(template_path, context))


@login_required
@student_required
def cv_download_pdf_view(request):
    """Génère le PDF via WeasyPrint EXCLUSIVEMENT pour une qualité premium."""
    cv_id = request.GET.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user) if cv_id else CVProfile.objects.filter(user=request.user, is_primary=True).first()
    if not cv:
        messages.error(request, "Aucun CV trouvé.")
        return redirect('cv_builder')

    if not UsageManager.is_action_allowed(request.user, 'cv_ia'):
        messages.warning(request, "Quota de téléchargement CV atteint.")
        return redirect('cv_builder')

    try:
        from weasyprint import HTML
        html_string = render_to_string(cv.get_template_path(), _get_cv_context(cv), request=request)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(presentational_hints=True)
        cv.increment_download()
        UsageManager.increment_usage(request.user, 'cv_ia')
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="CV_Premium_{cv.last_name}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur PDF Premium (WeasyPrint requis): {str(e)}")
        return redirect('cv_builder')


@login_required
@require_POST
def cv_save_draft_api(request):
    """Endpoint AJAX pour sauvegarde automatique."""
    try:
        data = json.loads(request.body)
        cv = get_object_or_404(CVProfile, pk=data.get('cv_id'), user=request.user)
        fields = ['first_name', 'last_name', 'professional_title', 'email', 'phone', 'city', 'country', 'summary', 'primary_color', 'secondary_color', 'font_family', 'photo_frame', 'skill_display', 'job_category', 'job_description']
        updated = []
        for f in fields:
            if f in data:
                setattr(cv, f, data[f])
                updated.append(f)
        if updated: cv.save(update_fields=updated + ['updated_at'])
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def cv_ai_enhance_api(request):
    """Utilise Groq pour améliorer un texte."""
    try:
        data = json.loads(request.body)
        text, ftype = data.get('text', ''), data.get('type', 'summary')
        if not text: return JsonResponse({'status': 'error', 'message': 'Texte vide'}, status=400)
        
        from .groq_client import GroqCVClient
        groq = GroqCVClient()
        enhanced = groq.enhance_text(text, ftype)
        if enhanced: return JsonResponse({'status': 'ok', 'enhanced_text': enhanced})
        return JsonResponse({'status': 'error', 'message': 'Erreur Groq'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def cv_score_api(request):
    """Analyse ATS via Groq."""
    cv_id = request.GET.get('cv_id')
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    
    from .groq_client import GroqCVClient
    cv_text = _collect_all_text(cv)
    groq = GroqCVClient()
    scores = groq.analyze_cv(cv_text, cv.job_category, cv.job_description)
    
    if scores:
        CVScoreResult.objects.create(cv_profile=cv, **scores)
        cv.last_ats_score = scores['overall_score']
        cv.save(update_fields=['last_ats_score'])
        return JsonResponse(scores)
    return JsonResponse({'status': 'error', 'message': 'Analyse échouée'}, status=500)


@login_required
@require_POST
def cv_duplicate_view(request):
    cv = get_object_or_404(CVProfile, pk=request.POST.get('cv_id'), user=request.user)
    new_cv = cv.duplicate()
    messages.success(request, f"CV dupliqué : {new_cv.title}")
    return redirect('cv_builder')

@login_required
def cv_switch_view(request, cv_id):
    cv = get_object_or_404(CVProfile, pk=cv_id, user=request.user)
    CVProfile.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    cv.is_primary = True
    cv.save(update_fields=['is_primary'])
    return redirect('cv_builder')

@login_required
@require_POST
def cv_new_view(request):
    default_tpl = CVTemplate.objects.filter(is_active=True, slug='modern').first()
    cv = CVProfile.objects.create(user=request.user, title=f"Nouveau CV", template=default_tpl, is_primary=True)
    CVProfile.objects.filter(user=request.user, is_primary=True).exclude(pk=cv.pk).update(is_primary=False)
    _prefill_cv(cv, request.user, request.user.profile)
    return redirect('cv_builder')

@login_required
@require_POST
def cv_delete_view(request):
    get_object_or_404(CVProfile, pk=request.POST.get('cv_id'), user=request.user).delete()
    return redirect('cv_builder')

@login_required
def cv_version_history_view(request):
    cv = get_object_or_404(CVProfile, pk=request.GET.get('cv_id'), user=request.user)
    return JsonResponse({'versions': [{'version': v.version_number, 'date': v.created_at.isoformat()} for v in cv.versions.all()]})
