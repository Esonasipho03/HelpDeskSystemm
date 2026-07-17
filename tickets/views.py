from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    Announcement,
    Asset,
    KnowledgeBaseArticle,
    Notification,
    Ticket,
    TicketStatus,
    TicketPriority,
    Department,
)
from .forms import (
    SatisfactionRatingForm,
    TicketCommentForm,
    TicketCreateForm,
    KnowledgeBaseArticleForm,
)

User = get_user_model()

AUTO_ASSIGN = {
    Department.SALES: "Phila",
    Department.DEBT: "bafana",
}


def create_notification(user, message, ticket=None, audience="employee"):
    Notification.objects.create(
        user=user,
        message=message,
        ticket=ticket,
        audience=audience,
    )


def _audience_for(user):
    """Which notification bucket a logged-in user should see, based on role."""
    role = str(getattr(user, "role", "")).upper()
    return "technician" if role == "TECHNICIAN" else "employee"


@login_required
def create_ticket(request):
    initial = {}

    category = request.GET.get("category")
    if category:
        initial["category"] = category

    if request.method == "POST":
        form = TicketCreateForm(request.POST, request.FILES)

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user

            # Automatic assignment
            username = AUTO_ASSIGN.get(ticket.department)
            if username:
                try:
                    ticket.assigned_to = User.objects.get(username=username)
                except User.DoesNotExist:
                    ticket.assigned_to = None

            ticket.save()

            if ticket.assigned_to:
                create_notification(
                    request.user,
                    f"Ticket #{ticket.id} was assigned to {ticket.assigned_to.get_full_name()}.",
                    ticket=ticket,
                    audience="employee",
                )

                create_notification(
                    ticket.assigned_to,
                    f"You were assigned Ticket #{ticket.id}.",
                    ticket=ticket,
                    audience="technician",
                )

            else:
                create_notification(
                    request.user,
                    f"Ticket #{ticket.id} created and is waiting to be claimed.",
                    ticket=ticket,
                    audience="employee",
                )

            return redirect("ticket_detail", pk=ticket.pk)

    else:
        form = TicketCreateForm(initial=initial)

    return render(
        request,
        "tickets/create_ticket.html",
        {
            "form": form,
        },
    )


@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        audience = _audience_for(request.user)
        Notification.objects.filter(
            user=request.user,
            audience=audience,
            is_read=False,
        ).update(is_read=True)
    return JsonResponse({"status": "ok"})


@login_required
def ticket_history(request):

    tickets = Ticket.objects.filter(
        created_by=request.user
    )

    status = request.GET.get("status")

    if status:
        tickets = tickets.filter(
            status=status
        )

    return render(
        request,
        "tickets/ticket_history.html",
        {
            "tickets": tickets,
            "status_choices": TicketStatus.choices,
            "status_filter": status,
        },
    )


@login_required
def ticket_detail(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
        created_by=request.user,
    )

    if request.method == "POST":

        comment_form = TicketCommentForm(
            request.POST
        )

        if comment_form.is_valid():

            comment = comment_form.save(
                commit=False
            )

            comment.ticket = ticket
            comment.author = request.user

            comment.save()

            messages.success(
                request,
                "Comment added successfully."
            )

            create_notification(
                request.user,
                f"Your comment on Ticket #{ticket.id} was added successfully.",
                ticket=ticket,
                audience="employee",
            )

            if ticket.assigned_to:
                create_notification(
                    ticket.assigned_to,
                    f"{request.user.get_full_name() or request.user.username} replied on Ticket #{ticket.id}.",
                    ticket=ticket,
                    audience="technician",
                )

            return redirect(
                "ticket_detail",
                pk=ticket.pk,
            )

    else:

        comment_form = TicketCommentForm()

    comments = ticket.comments.filter(
        is_internal=False
    )

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "comments": comments,
            "comment_form": comment_form,
        },
    )


@login_required
def rate_ticket(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
        created_by=request.user,
    )

    if ticket.status != TicketStatus.RESOLVED:
        messages.error(
            request,
            "Only resolved tickets can be rated."
        )
        return redirect(
            "ticket_detail",
            pk=ticket.pk,
        )

    if request.method == "POST":

        form = SatisfactionRatingForm(
            request.POST,
            instance=ticket,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Thank you for your feedback."
            )

            create_notification(
                request.user,
                f"Thanks for rating Ticket #{ticket.id}.",
                ticket=ticket,
                audience="employee",
            )

            if ticket.assigned_to:
                create_notification(
                    ticket.assigned_to,
                    f"Ticket #{ticket.id} was rated {ticket.satisfaction_rating}/5.",
                    ticket=ticket,
                    audience="technician",
                )

            return redirect(
                "ticket_detail",
                pk=ticket.pk,
            )

    else:

        form = SatisfactionRatingForm(
            instance=ticket
        )

    return render(
        request,
        "tickets/rate_ticket.html",
        {
            "ticket": ticket,
            "form": form,
        },
    )


@login_required
def knowledge_base(request):

    query = request.GET.get("q", "")

    category = request.GET.get("category", "")

    articles = KnowledgeBaseArticle.objects.all()

    if query:
        articles = articles.filter(
            Q(title__icontains=query) |
            Q(summary__icontains=query) |
            Q(content__icontains=query) |
            Q(keywords__icontains=query)
        )

    if category:
        articles = articles.filter(category=category)

    featured = KnowledgeBaseArticle.objects.filter(
        is_featured=True
    )[:6]

    categories = KnowledgeBaseArticle.objects.values_list(
        "category",
        flat=True
    ).distinct()

    latest_articles = KnowledgeBaseArticle.objects.order_by(
        "-created_at"
    )[:5]

    popular_articles = KnowledgeBaseArticle.objects.order_by(
        "-views"
    )[:5]

    return render(
        request,
        "tickets/knowledge_base.html",
        {
            "articles": articles,
            "featured": featured,
            "categories": categories,
            "latest_articles": latest_articles,
            "popular_articles": popular_articles,
            "query": query,
            "selected_category": category,
        },
    )


@login_required
def article_detail(request, pk):

    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk
    )

    article.views += 1
    article.save(update_fields=["views"])

    return render(
        request,
        "tickets/article_detail.html",
        {
            "article": article,
        }
    )


@login_required
def all_tickets(request):
    tickets = Ticket.objects.all().order_by("-created_at")

    q = request.GET.get("q")

    if q:
        tickets = tickets.filter(
            title__icontains=q
        )

    return render(request, "tickets/all_tickets.html", {
        "tickets": tickets,
    })


@login_required
def my_queue(request):

    tickets = Ticket.objects.filter(
        assigned_to=request.user
    )

    status = request.GET.get("status")
    search = request.GET.get("q")

    if status:
        tickets = tickets.filter(status=status)

    if search:
        tickets = tickets.filter(title__icontains=search)

    context = {
        "tickets": tickets,
        "status_filter": status,
        "status_choices": TicketStatus.choices,
    }

    return render(
        request,
        "tickets/my_queue.html",
        context,
    )


@login_required
def unassigned_queue(request):

    tickets = Ticket.objects.filter(
        assigned_to__isnull=True
    )

    return render(
        request,
        "tickets/unassigned_queue.html",
        {
            "tickets": tickets,
        }
    )


@login_required
def ticket_search(request):
    query = request.GET.get("q", "")

    tickets = Ticket.objects.filter(
        title__icontains=query
    ).order_by("-created_at")

    return render(request, "tickets/technician/search_results.html", {
        "tickets": tickets,
        "query": query,
    })


@login_required
def technician_profile(request):

    context = {

        "assigned":
        Ticket.objects.filter(
            assigned_to=request.user
        ).count(),

        "resolved":
        Ticket.objects.filter(
            assigned_to=request.user,
            status=TicketStatus.RESOLVED
        ).count(),

        "closed":
        Ticket.objects.filter(
            assigned_to=request.user,
            status=TicketStatus.CLOSED
        ).count(),

    }

    return render(
        request,
        "tickets/profile.html",
        context,
    )


@login_required
def claim_ticket(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if ticket.assigned_to is None:

        ticket.assigned_to = request.user
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.save()

        messages.success(
            request,
            "Ticket claimed successfully."
        )

        create_notification(
            request.user,
            f"You claimed Ticket #{ticket.id}.",
            ticket=ticket,
            audience="technician",
        )

        create_notification(
            ticket.created_by,
            f"Ticket #{ticket.id} was claimed by {request.user.get_full_name() or request.user.username}.",
            ticket=ticket,
            audience="employee",
        )

    else:

        messages.warning(
            request,
            "Ticket has already been assigned."
        )

    return redirect(
        "technician_ticket_detail",
        pk=ticket.pk,
    )


@login_required
def update_ticket_status(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk
    )

    if request.method == "POST":

        new_status = request.POST.get("status")
        resolution = request.POST.get("resolution")

        if new_status == TicketStatus.RESOLVED:

            if not resolution:
                messages.error(
                    request,
                    "Please enter a resolution."
                )
                return redirect(
                    "technician_ticket_detail",
                    pk=ticket.pk
                )

            ticket.resolution = resolution
            ticket.resolved_at = timezone.now()

        elif new_status == TicketStatus.CLOSED:
            ticket.closed_at = timezone.now()

        ticket.status = new_status
        ticket.save()

        messages.success(
            request,
            "Ticket updated."
        )

        # Let the technician who made the change see it in their own bell
        create_notification(
            request.user,
            f"You updated Ticket #{ticket.id} to {new_status}.",
            ticket=ticket,
            audience="technician",
        )

        # Notify the employee who filed it, worded to match the actual new status
        if new_status == TicketStatus.RESOLVED:
            create_notification(
                ticket.created_by,
                f"Ticket #{ticket.id} was resolved. Let us know how we did!",
                ticket=ticket,
                audience="employee",
            )
        elif new_status == TicketStatus.CLOSED:
            create_notification(
                ticket.created_by,
                f"Ticket #{ticket.id} has been closed.",
                ticket=ticket,
                audience="employee",
            )
        else:
            create_notification(
                ticket.created_by,
                f"Ticket #{ticket.id} status changed to {new_status}.",
                ticket=ticket,
                audience="employee",
            )

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)

    return redirect(
        "technician_ticket_detail",
        pk=ticket.pk
    )


@login_required
def technician_ticket_detail(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if request.method == "POST":

        comment_form = TicketCommentForm(request.POST)

        if comment_form.is_valid():

            comment = comment_form.save(commit=False)

            comment.ticket = ticket
            comment.author = request.user

            # Internal note if hidden field exists
            comment.is_internal = "internal_note" in request.POST

            comment.save()

            if not comment.is_internal:
                create_notification(
                    ticket.created_by,
                    f"{request.user.get_full_name() or request.user.username} replied on Ticket #{ticket.id}.",
                    ticket=ticket,
                    audience="employee",
                )

            return redirect(
                "technician_ticket_detail",
                pk=ticket.pk,
            )

    else:

        comment_form = TicketCommentForm()

    # Comments visible to employees
    public_comments = ticket.comments.filter(
        is_internal=False
    )

    # Technician-only notes
    internal_comments = ticket.comments.filter(
        is_internal=True
    )

    return render(
        request,
        "tickets/technician_ticket_detail.html",
        {
            "ticket": ticket,
            "comments": public_comments,
            "internal_comments": internal_comments,
            "comment_form": comment_form,
        },
    )


@login_required
def manage_articles(request):

    articles = KnowledgeBaseArticle.objects.all()

    search = request.GET.get("q")

    if search:
        articles = articles.filter(
            title__icontains=search
        )

    return render(
        request,
        "tickets/manage_articles.html",
        {
            "articles": articles,
        }
    )


@login_required
def create_article(request):

    if request.method == "POST":

        form = KnowledgeBaseArticleForm(
            request.POST
        )

        if form.is_valid():

            article = form.save(commit=False)
            article.author = request.user
            article.save()

            messages.success(
                request,
                "Knowledge Base article created."
            )

            return redirect(
                "manage_articles"
            )

    else:

        form = KnowledgeBaseArticleForm()

    return render(
        request,
        "tickets/article_form.html",
        {
            "form": form,
            "title": "Create Article",
        }
    )


@login_required
def delete_article(request, pk):

    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk,
    )

    article.delete()

    messages.success(
        request,
        "Article deleted."
    )

    return redirect(
        "manage_articles"
    )


@login_required
def edit_article(request, pk):
    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk
    )

    if request.method == "POST":
        form = KnowledgeBaseArticleForm(
            request.POST,
            instance=article
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Article updated successfully."
            )

            return redirect(
                "knowledge_base"
            )

    else:
        form = KnowledgeBaseArticleForm(
            instance=article
        )

    return render(
        request,
        "tickets/edit_article.html",
        {
            "form": form,
            "article": article,
        },
    )


@login_required
def preview_article(request, pk):
    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk
    )

    return render(
        request,
        "tickets/preview_article.html",
        {
            "article": article,
        },
    )
def _is_admin(user):
    role = str(getattr(user, "role", "")).upper()
    return role == "ADMIN" or user.is_superuser

@login_required
def admin_assign_ticket(request, pk):

    if not _is_admin(request.user):
        messages.error(
            request,
            "You don't have permission to do that."
        )
        return redirect("unassigned_queue")

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if request.method == "POST":

        technician_username = request.POST.get("technician")

        if ticket.assigned_to is not None:
            messages.warning(
                request,
                "Ticket has already been assigned."
            )
            return redirect("unassigned_queue")

        technician = get_object_or_404(
            User,
            username=technician_username,
        )

        ticket.assigned_to = technician
        ticket.status = TicketStatus.ASSIGNED
        ticket.save()

        messages.success(
            request,
            f"Ticket #{ticket.id} assigned to {technician.get_full_name() or technician.username}."
        )

        create_notification(
            technician,
            f"You were assigned Ticket #{ticket.id} by {request.user.get_full_name() or request.user.username}.",
            ticket=ticket,
            audience="technician",
        )

        create_notification(
            ticket.created_by,
            f"Ticket #{ticket.id} was assigned to {technician.get_full_name() or technician.username}.",
            ticket=ticket,
            audience="employee",
        )

    return redirect("unassigned_queue")

 