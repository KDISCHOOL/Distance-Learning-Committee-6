from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('faculty/upload/', views.faculty_upload, name='faculty_upload'),
    path('faculty/enrich/', views.faculty_enrich_upload, name='faculty_enrich'),
    path('faculty/search/', views.faculty_search, name='faculty_search'),
    path('course/upload/', views.course_upload, name='course_upload'),
    path('course/search/', views.course_search, name='course_search'),
    path('course/apply/<int:pk>/', views.course_apply, name='course_apply'),
    path('course/lookup/<int:pk>/', views.course_lookup, name='course_lookup'),
    path('course/admin_export/', views.course_admin_export, name='course_admin_export'),
]
