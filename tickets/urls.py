from django.urls import path
from django.http import JsonResponse
from . import views, admin_views

urlpatterns = [
    # live notification poll (all roles)
    path("notifications/latest/", admin_views.notifications_latest, name="notifications_latest"),

    # live search dropdown (all roles)
    path("search/api/", views.ticket_search_api, name="ticket_search_api"),

    # admin console
    path("admin/tasks/", admin_views.admin_task_list, name="admin_task_list"),
    path("admin/tasks/new/", admin_views.admin_task_create, name="admin_task_create"),
    path("admin/tasks/<int:pk>/edit/", admin_views.admin_task_edit, name="admin_task_edit"),
    path("admin/report/", admin_views.technician_report, name="technician_report"),
    path("admin/report/export/", admin_views.technician_report_export, name="technician_report_export"),
    path("admin/tickets/export/", admin_views.all_tickets_export, name="all_tickets_export"),

    # technician IT tasks
    path("technician/tasks/", admin_views.technician_tasks, name="technician_tasks"),
    path("technician/tasks/<int:pk>/", admin_views.technician_task_detail, name="technician_task_detail"),
    path("technician/tasks/<int:pk>/status/", admin_views.update_task_status, name="update_task_status"),

    path("notifications/mark-read/", views.mark_notifications_read, name="mark_notifications_read"),
    path("tickets/<int:pk>/admin-assign/", views.admin_assign_ticket, name="admin_assign_ticket"),
    path("create/", views.create_ticket, name="create_ticket"),
    path("history/", views.ticket_history, name="ticket_history"),
   path( "<int:pk>/",  views.ticket_detail,  name="ticket_detail",
    ),
    path("<int:pk>/rate/", views.rate_ticket, name="rate_ticket"),
    
    path(
    "knowledge-base/",
    views.knowledge_base,
    name="knowledge_base",
),

path(
    "knowledge-base/<int:pk>/",
    views.article_detail,
    name="article_detail",
),

path(
    "all/",
    views.all_tickets,
    name="all_tickets",
),
    path(
    "technician/tickets/<int:pk>/",
    views.technician_ticket_detail,
    name="technician_ticket_detail",
),
    path("technician/queue/", views.my_queue, name="my_queue"),
    path("technician/unassigned/", views.unassigned_queue, name="unassigned_queue"),
    path("technician/tickets/", views.all_tickets, name="all_tickets"),
    path("technician/search/", views.ticket_search, name="ticket_search"),
    path("technician/profile/", views.technician_profile, name="technician_profile"),
    path("technician/tickets/<int:pk>/claim/", views.claim_ticket, name="claim_ticket"),
    path("technician/tickets/<int:pk>/status/", views.update_ticket_status, name="update_ticket_status"),
    
    path(
    "technician/tickets/<int:pk>/claim/",
    views.claim_ticket,
    name="claim_ticket",
),

path(
    "technician/knowledge-base/",
    views.manage_articles,
    name="manage_articles",
),

path(
    "technician/knowledge-base/create/",
    views.create_article,
    name="create_article",
),

path(
    "technician/knowledge-base/<int:pk>/edit/",
    views.edit_article,
    name="edit_article",
),

path(
    "technician/knowledge-base/<int:pk>/delete/",
    views.delete_article,
    name="delete_article",
),

path(
    "technician/knowledge-base/<int:pk>/preview/",
    views.preview_article,
    name="preview_article",
),
]
