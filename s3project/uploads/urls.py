from django.urls import path
from . import views

urlpatterns = [
    # path('', views.file_list, name='file_list'),
    path('', views.dashboard, name='dashboard'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('projects/<int:project_id>/members/', views.manage_project_members, name='manage_project_members'),
    path('projects/<int:project_id>/members/remove/<int:user_id>/', views.remove_project_member, name='remove_project_member'),
    path('projects/<int:project_id>/upload/', views.upload_to_project, name='upload_to_project'),
    path('my-projects/', views.user_projects, name='user_projects'),

    # Files
    # path('upload/', views.upload_file, name='upload_file'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),

    # Invitation management
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('invitations/create/', views.create_invitation, name='create_invitation'),
    path('invitations/resend/<int:invitation_id>/', views.resend_invitation, name='resend_invitation'),
    path('invitations/cancel/<int:invitation_id>/', views.cancel_invitation, name='cancel_invitation'),
    path('accept-invitation/<uuid:token>/', views.accept_invitation, name='accept_invitation'),
]
