from django.urls import path
from . import views

urlpatterns = [
    path("", views.employee_dashboard, name="dashboard"),
    path( "technician/",views.technician_dashboard, name="technician_dashboard",
    ),
]