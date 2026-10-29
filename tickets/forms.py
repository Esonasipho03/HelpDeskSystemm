from django import forms
from .models import Ticket, TicketComment,KnowledgeBaseArticle


class TicketCreateForm(forms.ModelForm):

    class Meta:
        model = Ticket

        fields = [
            "title",
            "category",
            "department",
            "priority",
            "description",
            "attachment",
        ]

        labels = {
            "title": "Issue Summary",
            "category": "Problem Category",
            "department": "Department",
            "priority": "Priority",
            "description": "Problem Description",
            "attachment": "Attachment",
        }

        widgets = {

            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Brief summary of the issue"
            }),

            "category": forms.Select(attrs={
                "class": "form-select"
            }),

            "department": forms.Select(attrs={
                "class": "form-select"
            }),

            "location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Production Floor"
            }),

            "computer_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: FIN-PC-021"
            }),

            "asset_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: AST-1045"
            }),

            "priority": forms.Select(attrs={
                "class": "form-select"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Describe the problem in detail..."
            }),

            "attachment": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),

        }

    def clean_title(self):
        title = self.cleaned_data["title"]

        if len(title) < 5:
            raise forms.ValidationError(
                "Please enter a more descriptive title."
            )

        return title


class TicketCommentForm(forms.ModelForm):

    class Meta:
        model = TicketComment

        fields = [
            "comment"
        ]

        widgets = {
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Write your reply..."
            })
        }


class SatisfactionRatingForm(forms.ModelForm):

    class Meta:
        model = Ticket

        fields = [
            "satisfaction_rating"
        ]

        widgets = {
            "satisfaction_rating": forms.RadioSelect(
                choices=[
                    (1, "⭐"),
                    (2, "⭐⭐"),
                    (3, "⭐⭐⭐"),
                    (4, "⭐⭐⭐⭐"),
                    (5, "⭐⭐⭐⭐⭐"),
                ]
            )
        }
class KnowledgeBaseArticleForm(forms.ModelForm):

    class Meta:

        model = KnowledgeBaseArticle

        fields = [
            "title",
            "category",
            "content",
            
        ]

        widgets = {

            "title": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "category": forms.Select(attrs={
                "class": "form-select"
            }),

            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 15,
            }),

            "is_published": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

        }

class ITTaskForm(forms.ModelForm):
    """Admin form for handing an IT task to a technician."""

    class Meta:
        from .models import ITTask as _ITTask
        model = _ITTask
        fields = ["title", "assigned_to", "priority", "due_date", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "What needs doing?"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5,
                                                 "placeholder": "Add any details the technician needs"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        self.fields["assigned_to"].queryset = get_user_model().objects.filter(
            role="TECHNICIAN", is_active=True
        ).order_by("first_name", "username")
        self.fields["assigned_to"].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields["assigned_to"].empty_label = "Choose a technician"
