from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
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

from .admin_views import staff_required, technician_only, is_admin, is_technician  # noqa: E402

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


def _notify_staff_of_new_ticket(ticket, creator):
    """Tell every active technician and admin about a new ticket, assigned or not.

    This is what makes the live bell/sound fire for staff whenever a ticket is
    created. The auto-assigned technician already got a dedicated "You were
    assigned" notification, and the creator is never notified about their own
    ticket here.
    """
    skip = {creator.pk}
    if ticket.assigned_to_id:
        skip.add(ticket.assigned_to_id)

    message = f"New ticket #{ticket.id}: {ticket.title}"

    for tech in User.objects.filter(role="TECHNICIAN", is_active=True).exclude(pk__in=skip):
        create_notification(tech, message, ticket=ticket, audience="technician")

    # Admins read the "employee" bucket (see _audience_for / the context processor).
    for admin in User.objects.filter(Q(role="ADMIN") | Q(is_superuser=True), is_active=True).exclude(pk__in=skip):
        create_notification(admin, message, ticket=ticket, audience="employee")


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

            _notify_staff_of_new_ticket(ticket, request.user)

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

    # Technicians/admins following a link to a ticket they didn't file get the
    # staff view of it rather than a 404.
    if (is_technician(request.user) or is_admin(request.user)) and not Ticket.objects.filter(
        pk=pk, created_by=request.user
    ).exists():
        return redirect("technician_ticket_detail", pk=pk)

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


@staff_required
def all_tickets(request):
    from .admin_views import is_admin, admin_all_tickets_context
    if is_admin(request.user):
        return render(request, "tickets/admin_all_tickets.html", admin_all_tickets_context(request))
    tickets = Ticket.objects.all().order_by("-created_at")

    q = request.GET.get("q")

    if q:
        tickets = tickets.filter(
            title__icontains=q
        )

    return render(request, "tickets/all_tickets.html", {
        "tickets": tickets,
    })


@technician_only("all_tickets")
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
    }

    return render(
        request,
        "tickets/my_queue.html",
        context,
    )


@staff_required
def unassigned_queue(request):
    from .admin_views import is_admin, admin_unassigned_context
    if is_admin(request.user):
        return render(request, "tickets/admin_unassigned_queue.html", admin_unassigned_context(request))

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


@staff_required
def ticket_search(request):
    query = request.GET.get("q", "").strip()
    tickets = Ticket.objects.none()

    if query:
        number = query.lstrip("#")
        match = (
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(created_by__username__icontains=query)
            | Q(created_by__first_name__icontains=query)
            | Q(created_by__last_name__icontains=query)
        )
        if number.isdigit():
            match |= Q(pk=int(number))
        tickets = (
            Ticket.objects.filter(match)
            .select_related("created_by", "assigned_to")
            .order_by("-created_at")[:100]
        )

    return render(request, "tickets/search_results.html", {
        "tickets": tickets,
        "query": query,
    })


@technician_only("admin_dashboard")
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
    from .admin_views import is_technician

    ticket = get_object_or_404(Ticket, pk=pk)

    if not is_technician(request.user):
        messages.error(request, "Only technicians can claim tickets.")
        return redirect("technician_ticket_detail", pk=ticket.pk) if request.user.is_staff or str(getattr(request.user, "role", "")).upper() == "ADMIN" else redirect("dashboard")

    if request.method != "POST":
        return redirect("technician_ticket_detail", pk=ticket.pk)

    # One atomic UPDATE: if two technicians click at once, only one row changes.
    finished = [TicketStatus.RESOLVED, TicketStatus.CLOSED]
    claimed = Ticket.objects.filter(pk=ticket.pk, assigned_to__isnull=True).update(
        assigned_to=request.user,
        updated_at=timezone.now(),
    )

    if claimed:
        ticket.refresh_from_db()
        if ticket.status not in finished and ticket.status != TicketStatus.IN_PROGRESS:
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.save()

        who = request.user.get_full_name() or request.user.username
        messages.success(request, f"You claimed Ticket #{ticket.id}. It is now in your queue.")

        create_notification(
            request.user,
            f"You claimed Ticket #{ticket.id}.",
            ticket=ticket,
            audience="technician",
        )
        create_notification(
            ticket.created_by,
            f"Ticket #{ticket.id} was claimed by {who}.",
            ticket=ticket,
            audience="employee",
        )
    else:
        ticket.refresh_from_db()
        owner = ticket.assigned_to
        name = (owner.get_full_name() or owner.username) if owner else "someone else"
        messages.warning(request, f"Ticket #{ticket.id} was already claimed by {name}.")

    return redirect("technician_ticket_detail", pk=ticket.pk)


@login_required
def update_ticket_status(request, pk):
    from .admin_views import is_admin, is_technician

    if not (is_admin(request.user) or is_technician(request.user)):
        messages.error(request, "You don't have permission to update tickets.")
        return redirect("dashboard")

    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method != "POST":
        return redirect("technician_ticket_detail", pk=ticket.pk)

    new_status = request.POST.get("status")
    resolution = (request.POST.get("resolution") or "").strip()

    if new_status not in TicketStatus.values:
        messages.error(request, "Please choose a valid status.")
        return redirect("technician_ticket_detail", pk=ticket.pk)

    if new_status == TicketStatus.RESOLVED and not (resolution or ticket.resolution):
        messages.error(request, "Please describe how the issue was resolved.")
        return redirect("technician_ticket_detail", pk=ticket.pk)

    old_status = ticket.status
    changed = new_status != old_status
    new_resolution = bool(resolution) and resolution != ticket.resolution

    if not changed and not new_resolution:
        messages.info(request, "Nothing to update.")
        return redirect("technician_ticket_detail", pk=ticket.pk)

    # Updating an unclaimed ticket claims it for the technician doing the work
    claimed = False
    if ticket.assigned_to is None and is_technician(request.user):
        ticket.assigned_to = request.user
        claimed = True

    if resolution:
        ticket.resolution = resolution

    if changed:
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = timezone.now()
            ticket.closed_at = None
        elif new_status == TicketStatus.CLOSED:
            ticket.closed_at = timezone.now()
            if ticket.resolved_at is None:
                ticket.resolved_at = ticket.closed_at
        else:
            # Re-opened or still being worked: it is no longer finished
            ticket.resolved_at = None
            ticket.closed_at = None
        ticket.status = new_status

    ticket.save()

    messages.success(request, f"Ticket updated to {ticket.status}." if changed else "Resolution notes saved.")

    who = request.user.get_full_name() or request.user.username
    if changed:
        create_notification(
            request.user,
            f"You updated Ticket #{ticket.id} to {new_status}.",
            ticket=ticket,
            audience="technician",
        )
        if new_status == TicketStatus.RESOLVED:
            text = f"Ticket #{ticket.id} was resolved. Let us know how we did!"
        elif new_status == TicketStatus.CLOSED:
            text = f"Ticket #{ticket.id} has been closed."
        else:
            text = f"Ticket #{ticket.id} status changed to {new_status}."
        create_notification(ticket.created_by, text, ticket=ticket, audience="employee")
    if claimed:
        create_notification(
            ticket.created_by,
            f"Ticket #{ticket.id} was claimed by {who}.",
            ticket=ticket,
            audience="employee",
        )

    return redirect("technician_ticket_detail", pk=ticket.pk)


@staff_required
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
            "status_choices": TicketStatus.choices,
        },
    )


@staff_required
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


@staff_required
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


@staff_required
def delete_article(request, pk):

    if request.method != "POST":
        return redirect("manage_articles")

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


@staff_required
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


@staff_required
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


@login_required
def ticket_search_api(request):
    """JSON for the top-bar live search dropdown.

    Technicians and admins search every ticket; employees only ever see their own.
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    staff = is_technician(request.user) or is_admin(request.user)

    match = (
        Q(title__icontains=query)
        | Q(created_by__first_name__icontains=query)
        | Q(created_by__last_name__icontains=query)
        | Q(created_by__username__icontains=query)
    )
    number = query.lstrip("#")
    if number.isdigit():
        match |= Q(pk=int(number))

    tickets = Ticket.objects.filter(match).select_related("created_by")
    if not staff:
        tickets = tickets.filter(created_by=request.user)
    tickets = tickets.order_by("-created_at")[:8]

    detail_route = "technician_ticket_detail" if staff else "ticket_detail"
    return JsonResponse({
        "results": [
            {
                "id": t.pk,
                "title": t.title,
                "requester": (t.created_by.get_full_name() or t.created_by.username) if t.created_by else "",
                "status": t.get_status_display(),
                "priority": t.priority,
                "url": reverse(detail_route, kwargs={"pk": t.pk}),
            }
            for t in tickets
        ]
    })
