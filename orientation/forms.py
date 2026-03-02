from django import forms
from .models import Question


class OrientationTestForm(forms.Form):
    """
    Formulaire dynamique : une question active = un champ radio.
    """

    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', None)
        super().__init__(*args, **kwargs)

        if questions is None:
            questions = Question.objects.filter(is_active=True)

        for question in questions:
            choices_qs = question.choices.all()
            self.fields[f"question_{question.id}"] = forms.ModelChoiceField(
                queryset=choices_qs,
                widget=forms.RadioSelect,
                required=True,
                label=question.text
            )