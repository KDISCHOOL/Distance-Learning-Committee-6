from django.contrib import admin
from .models import Faculty, CourseModality

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('korean_name', 'english_name', 'category', 'email')

@admin.register(CourseModality)
class CourseModalityAdmin(admin.ModelAdmin):
    list_display = ('id', 'korean_name', 'english_name', 'year', 'semester', 'apply_this_semester', 'modified_date')
