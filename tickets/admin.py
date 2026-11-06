from django.contrib import admin

from .models import Category, Comment, Ticket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description")
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
