from django.urls import path
from . import views

urlpatterns = [
    path('', views.file_list, name='file_list'),
    path('upload/', views.upload_file, name='upload_file'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),

    # Invitation management
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('invitations/create/', views.create_invitation, name='create_invitation'),
    path('invitations/resend/<int:invitation_id>/', views.resend_invitation, name='resend_invitation'),
    path('invitations/cancel/<int:invitation_id>/', views.cancel_invitation, name='cancel_invitation'),
    path('accept-invitation/<uuid:token>/', views.accept_invitation, name='accept_invitation'),
]
