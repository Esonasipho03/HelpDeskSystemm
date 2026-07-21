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
            "title": "Title",
            "category": "Problem Category",
            "department": "Department",
            "priority": "Priority",
            "description": "Problem Description",
            "attachment": "Attachment",
        }

        widgets = {

            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Tittle"
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