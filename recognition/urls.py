from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.home,              name='home'),
    path('enroll/',                 views.enroll_face,       name='enroll'),
    path('enroll/ajax/',            views.enroll_face_ajax,  name='enroll_ajax'),
    path('search/',                 views.search_face,       name='search'),
    path('search/ajax/',            views.search_face_ajax,  name='search_ajax'),
    path('enrolled/',               views.enrolled_list,     name='enrolled_list'),
    path('delete/<int:face_id>/',   views.delete_face,       name='delete_face'),
]