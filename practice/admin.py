from django.contrib import admin

from .models import Activity, QuestionType, Topic


@admin.register(QuestionType)
class QuestionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "bloom_level", "stance", "display_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "question_type", "bloom_level", "estimated_minutes")
    list_filter = ("topic", "question_type", "bloom_level")
