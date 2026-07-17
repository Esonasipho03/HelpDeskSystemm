from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "employee_number",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.EMPLOYEE

        if commit:
            user.save()

        return user