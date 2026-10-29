from django.urls import path
from . import views
from tickets import admin_views

urlpatterns = [
    path("admin/", admin_views.admin_dashboard, name="admin_dashboard"),
    path("", views.employee_dashboard, name="dashboard"),
    path( "technician/",views.technician_dashboard, name="technician_dashboard",
    ),
]