from django.db import models

class Faculty(models.Model):
    korean_name = models.CharField(max_length=200, unique=True)
    english_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.korean_name

class CourseModality(models.Model):
    korean_name = models.CharField(max_length=200)
    name = models.CharField(max_length=200, blank=True)
    english_name = models.CharField(max_length=200, blank=True)
    year = models.CharField(max_length=20, blank=True)
    semester = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=50, blank=True)
    course_title = models.CharField(max_length=500, blank=True)
    time_slot = models.CharField(max_length=200, blank=True)
    day = models.CharField(max_length=50, blank=True)
    time = models.CharField(max_length=100, blank=True)
    frequency_week = models.CharField(max_length=50, blank=True)
    course_format = models.CharField(max_length=200, blank=True)
    apply_this_semester = models.BooleanField(default=False)
    reason_for_applying = models.TextField(blank=True)
    modified_date = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=10, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['korean_name']),
            models.Index(fields=['english_name']),
        ]

    def __str__(self):
        return f"{self.korean_name} ({self.id})"
