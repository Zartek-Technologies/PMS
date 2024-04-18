# Projects,milestones and module are configured here

# Python imports
from uuid import uuid4

# imports for performing signals
from django.db.models.signals import post_save
from django.dispatch import receiver


# Django imports
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# Modeule imports
from plane.db.mixins import AuditModel

# Module imports
from . import BaseModel

ROLE_CHOICES = (
    (20, "Admin"),
    (15, "Member"),
    (10, "Viewer"),
    (5, "Guest"),
)


def get_default_props():
    return {
        "filters": {
            "priority": None,
            "state": None,
            "state_group": None,
            "assignees": None,
            "created_by": None,
            "labels": None,
            "start_date": None,
            "target_date": None,
            "subscriber": None,
        },
        "display_filters": {
            "group_by": None,
            "order_by": "-created_at",
            "type": None,
            "sub_issue": True,
            "show_empty_groups": True,
            "layout": "list",
            "calendar_date_range": "",
        },
    }


def get_default_preferences():
    return {"pages": {"block_display": True}}


class Project(BaseModel):
    NETWORK_CHOICES = ((0, "Secret"), (2, "Public"))
    name = models.CharField(max_length=255, verbose_name="Project Name")
    # start_date = models.DateField()
    # end_date = models.DateField()
    description = models.TextField(
        verbose_name="Project Description", blank=True
    )
    description_text = models.JSONField(
        verbose_name="Project Description RT", blank=True, null=True
    )
    description_html = models.JSONField(
        verbose_name="Project Description HTML", blank=True, null=True
    )
    network = models.PositiveSmallIntegerField(
        default=2, choices=NETWORK_CHOICES
    )
    workspace = models.ForeignKey(
        "db.WorkSpace",
        on_delete=models.CASCADE,
        related_name="workspace_project",
    )
    identifier = models.CharField(
        max_length=12,
        verbose_name="Project Identifier",
    )
    default_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="default_assignee",
        null=True,
        blank=True,
    )
    project_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_lead",
        null=True,
        blank=True,
    )
    emoji = models.CharField(max_length=255, null=True, blank=True)
    icon_prop = models.JSONField(null=True)
    module_view = models.BooleanField(default=True)
    cycle_view = models.BooleanField(default=True)
    issue_views_view = models.BooleanField(default=True)
    page_view = models.BooleanField(default=True)
    inbox_view = models.BooleanField(default=False)
    cover_image = models.URLField(blank=True, null=True, max_length=800)
    estimate = models.ForeignKey(
        "db.Estimate",
        on_delete=models.SET_NULL,
        related_name="projects",
        null=True,
    )
    archive_in = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(12)]
    )
    close_in = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(12)]
    )
    logo_props = models.JSONField(default=dict)
    default_state = models.ForeignKey(
        "db.State",
        on_delete=models.SET_NULL,
        null=True,
        related_name="default_state",
    )
    archived_at = models.DateTimeField(null=True)

    def __str__(self):
        """Return name of the project"""
        return f"{self.name} <{self.workspace.name}>"

    class Meta:
        unique_together = [["identifier", "workspace"], ["name", "workspace"]]
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        db_table = "projects"
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        self.identifier = self.identifier.strip().upper()
        return super().save(*args, **kwargs)


@receiver(post_save, sender=Project)
def create_initial_milestones(sender, instance, created, **kwargs):
    if created:  # Only execute when a new project is created
        # Create six initial milestones
        for i in range(1, 7):
            milestone_name = f"Milestone {i}"
            Milestone.objects.create(
                name=milestone_name,
                project=instance,
                created_at=timezone.now(),  # Set the creation time
                modified_at=timezone.now(),  # Set the modification time
            )


# the model which fully depends on the project
class Milestone(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Milestone Name")
    project = models.ForeignKey(
        "db.Project",
        on_delete=models.CASCADE,
        related_name="project_name",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"
        db_table = "milestones"
        ordering = ("-created_at",)


class Module(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Module Name")
    milestone = models.ForeignKey(
        "db.Milestone",
        on_delete=models.CASCADE,
        related_name="project_name",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        db_table = "modules"
        ordering = ("-created_at",)


class ProjectBaseModel(BaseModel):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="project_%(class)s"
    )
    workspace = models.ForeignKey(
        "db.Workspace", models.CASCADE, related_name="workspace_%(class)s"
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.workspace = self.project.workspace
        super(ProjectBaseModel, self).save(*args, **kwargs)


class ProjectMemberInvite(ProjectBaseModel):
    email = models.CharField(max_length=255)
    accepted = models.BooleanField(default=False)
    token = models.CharField(max_length=255)
    message = models.TextField(null=True)
    responded_at = models.DateTimeField(null=True)
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=10)

    class Meta:
        verbose_name = "Project Member Invite"
        verbose_name_plural = "Project Member Invites"
        db_table = "project_member_invites"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.project.name} {self.email} {self.accepted}"


class ProjectMember(ProjectBaseModel):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="member_project",
    )
    comment = models.TextField(blank=True, null=True)
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=10)
    view_props = models.JSONField(default=get_default_props)
    default_props = models.JSONField(default=get_default_props)
    preferences = models.JSONField(default=get_default_preferences)
    sort_order = models.FloatField(default=65535)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self._state.adding:
            smallest_sort_order = ProjectMember.objects.filter(
                workspace_id=self.project.workspace_id, member=self.member
            ).aggregate(smallest=models.Min("sort_order"))["smallest"]

            # Project ordering
            if smallest_sort_order is not None:
                self.sort_order = smallest_sort_order - 10000

        super(ProjectMember, self).save(*args, **kwargs)

    class Meta:
        unique_together = ["project", "member"]
        verbose_name = "Project Member"
        verbose_name_plural = "Project Members"
        db_table = "project_members"
        ordering = ("-created_at",)

    def __str__(self):
        """Return members of the project"""
        return f"{self.member.email} <{self.project.name}>"


# TODO: Remove workspace relation later
class ProjectIdentifier(AuditModel):
    workspace = models.ForeignKey(
        "db.Workspace",
        models.CASCADE,
        related_name="project_identifiers",
        null=True,
    )
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="project_identifier"
    )
    name = models.CharField(max_length=12)

    class Meta:
        unique_together = ["name", "workspace"]
        verbose_name = "Project Identifier"
        verbose_name_plural = "Project Identifiers"
        db_table = "project_identifiers"
        ordering = ("-created_at",)


class ProjectFavorite(ProjectBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_favorites",
    )

    class Meta:
        unique_together = ["project", "user"]
        verbose_name = "Project Favorite"
        verbose_name_plural = "Project Favorites"
        db_table = "project_favorites"
        ordering = ("-created_at",)

    def __str__(self):
        """Return user of the project"""
        return f"{self.user.email} <{self.project.name}>"


def get_anchor():
    return uuid4().hex


def get_default_views():
    return {
        "list": True,
        "kanban": True,
        "calendar": True,
        "gantt": True,
        "spreadsheet": True,
    }


class ProjectDeployBoard(ProjectBaseModel):
    anchor = models.CharField(
        max_length=255, default=get_anchor, unique=True, db_index=True
    )
    comments = models.BooleanField(default=False)
    reactions = models.BooleanField(default=False)
    inbox = models.ForeignKey(
        "db.Inbox",
        related_name="bord_inbox",
        on_delete=models.SET_NULL,
        null=True,
    )
    votes = models.BooleanField(default=False)
    views = models.JSONField(default=get_default_views)

    class Meta:
        unique_together = ["project", "anchor"]
        verbose_name = "Project Deploy Board"
        verbose_name_plural = "Project Deploy Boards"
        db_table = "project_deploy_boards"
        ordering = ("-created_at",)

    def __str__(self):
        """Return project and anchor"""
        return f"{self.anchor} <{self.project.name}>"


class ProjectPublicMember(ProjectBaseModel):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="public_project_members",
    )

    class Meta:
        unique_together = ["project", "member"]
        verbose_name = "Project Public Member"
        verbose_name_plural = "Project Public Members"
        db_table = "project_public_members"
        ordering = ("-created_at",)
