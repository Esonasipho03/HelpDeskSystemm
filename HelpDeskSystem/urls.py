"""
URL configuration for HelpDeskSystem project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    # Installable app support (the service worker must live at the site root)
    path("manifest.json", TemplateView.as_view(template_name="pwa/manifest.json",
         content_type="application/manifest+json"), name="pwa_manifest"),
    path("sw.js", TemplateView.as_view(template_name="pwa/sw.js",
         content_type="application/javascript"), name="pwa_sw"),
    path("offline/", TemplateView.as_view(template_name="pwa/offline.html"), name="pwa_offline"),

    path("", RedirectView.as_view(pattern_name="dashboard"), name="home"),

    path("admin/", admin.site.urls),

    path("", include("accounts.urls")),

    path("dashboard/", include("dashboard.urls")),
    path("tickets/", include("tickets.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)