from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.db.models import Q
from .models import UploadedFile, Invitation, Project, ProjectMembership
from .forms import (
    FileUploadForm, InvitationForm, AcceptInvitationForm, ProjectForm, ProjectMembershipForm
)

# Helper function to check if a user is a superuser
def is_superuser(user):
    return user.is_superuser

# Helper function to check if a user is a member of a project
def is_project_member(user, project):
    if user.is_superuser:
        return True
    return ProjectMembership.objects.filter(user=user, project=project).exists()

# Dashboard view - the main landing page
@login_required
def dashboard(request):
    """Dashboard view showing user's projects and recent files"""
    if request.user.is_superuser:
        # Superusers see all projects
        projects = Project.objects.all().order_by('-created_at')
    else:
        # Regular users see only projects they're members of
        projects = Project.objects.filter(
            projectmembership__user=request.user
        ).order_by('-created_at')
    
    # Get recent files from user's projects
    recent_files = UploadedFile.objects.filter(
        Q(project__in=projects) & (Q(user=request.user) | Q(project__created_by=request.user))
    ).order_by('-uploaded_at')[:5]

    context = {
        'projects': projects,
        'recent_files': recent_files,
    }
    return render(request, 'uploads/dashboard.html', context)


# Project Management Views
@login_required
@user_passes_test(is_superuser)
def project_list(request):
    """List all projects (superuser only)"""
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'uploads/project_list.html', {'projects': projects})

@login_required
@user_passes_test(is_superuser)
def create_project(request):
    """Create a new project (superuser only)"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()

            # Automatically add the creator as a member
            ProjectMembership.objects.create(
                project=project,
                user=request.user,
                added_by=request.user
            )

            messages.success(request, f"Project '{project.name}' created successfully.")
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    
    return render(request, 'uploads/project_form.html', {'form': form, 'title': 'Create Project'})

@login_required
def project_detail(request, project_id):
    """View a project's details and files"""
    project = get_object_or_404(Project, id=project_id)

    # Check if user has access to this project
    if not is_project_member(request.user, project):
        return HttpResponseForbidden("You don't have access to this project. All activites are logged and monitored.")
    
    # Get project files
    files = UploadedFile.objects.filter(project=project).order_by('-uploaded_at')

    # Get project members
    members = ProjectMembership.objects.filter(project=project).select_related('user')

    context = {
        'project': project,
        'files': files,
        'members': members,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'uploads/project_detail.html', context)

@login_required
@user_passes_test(is_superuser)
def edit_project(request, project_id):
    """Edit a project (superuser only)"""
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project '{project.name}' updated successfully.")
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'uploads/project_form.html', {
        'form': form,
        'title': 'Edit Project',
        'project': project
    })

@login_required
@user_passes_test(is_superuser)
def delete_project(request, project_id):
    """Delete a project and all its files (superuser only)"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        # Get all files in this project to delete from S3
        files = UploadedFile.objects.filter(project=project)
        for file in files:
            # Delete the actual file from S3
            file.file.delete(save=False)
        
        # Now delete the project (cascade will handle related records)
        project_name = project.name
        project.delete()
        
        messages.success(request, f"Project '{project_name}' and all its files have been deleted.")
        return redirect('project_list')
    
    return render(request, 'uploads/confirm_delete_project.html', {'project': project})

@login_required
@user_passes_test(is_superuser)
def manage_project_members(request, project_id):
    """Add/remove members from a project (superuser only)"""
    project = get_object_or_404(Project, id=project_id)
    current_members = ProjectMembership.objects.filter(project=project).select_related('user')
    
    if request.method == 'POST':
        form = ProjectMembershipForm(request.POST, project=project)
        if form.is_valid():
            users_to_add = form.cleaned_data['users']
            
            # Add new members
            for user in users_to_add:
                ProjectMembership.objects.create(
                    project=project,
                    user=user,
                    added_by=request.user
                )
            
            messages.success(request, f"{len(users_to_add)} users added to the project.")
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectMembershipForm(project=project)
    
    context = {
        'project': project,
        'form': form,
        'current_members': current_members,
    }
    return render(request, 'uploads/manage_project_members.html', context)

@login_required
@user_passes_test(is_superuser)
def remove_project_member(request, project_id, user_id):
    """Remove a member from a project (superuser only)"""
    project = get_object_or_404(Project, id=project_id)
    user = get_object_or_404(User, id=user_id)
    
    # Don't allow removing the project creator
    if project.created_by == user:
        messages.error(request, "Cannot remove the project creator.")
        return redirect('manage_project_members', project_id=project.id)
    
    membership = get_object_or_404(ProjectMembership, project=project, user=user)
    
    if request.method == 'POST':
        membership.delete()
        messages.success(request, f"{user.username} removed from the project.")
        return redirect('manage_project_members', project_id=project.id)
    
    context = {
        'project': project,
        'user_to_remove': user,
    }
    return render(request, 'uploads/confirm_remove_member.html', context)

@login_required
def upload_to_project(request, project_id):
    """Upload a file to a specific project"""
    project = get_object_or_404(Project, id=project_id)
    
    # Check if user has access to this project
    if not is_project_member(request.user, project):
        return HttpResponseForbidden("You don't have access to this project.")
    
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES, user=request.user, project=project)
        if form.is_valid():
            file = form.save()
            messages.success(request, "File uploaded successfully!")
            return redirect('project_detail', project_id=project.id)
    else:
        form = FileUploadForm(user=request.user, project=project)
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'uploads/upload_to_project.html', context)

@login_required
def user_projects(request):
    """View all projects the user is a member of"""
    if request.user.is_superuser:
        # Superusers see all projects
        projects = Project.objects.all().order_by('-created_at')
    else:
        # Regular users see only projects they're members of
        projects = Project.objects.filter(
            projectmembership__user=request.user
        ).order_by('-created_at')
    
    return render(request, 'uploads/user_projects.html', {'projects': projects})

#File Management Views
@login_required
def delete_file(request, file_id):
    file = get_object_or_404(UploadedFile, id=file_id)
    project = file.project  # Get the project object
    
    # Ensure users can only delete their own files
    if file.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to delete this file.")
    
    if request.method == 'POST':
        file.file.delete(save=False)  # Delete the file from S3
        file.delete()  # Delete the database entry
        messages.success(request, "File deleted successfully.")
        return redirect('project_detail', project_id=project.id)  # Also fix this redirect
    
    return render(request, 'uploads/confirm_delete.html', {
        'file': file, 
        'project': project  # Pass the project object, not just the ID
    })


# Invitation Management Views
@login_required
@user_passes_test(is_superuser)
def invitation_list(request):
    invitations = Invitation.objects.all().order_by('-created_at')
    return render(request, 'uploads/invitation_list.html', {'invitations': invitations})

@login_required
@user_passes_test(is_superuser)
def create_invitation(request):
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.invited_by = request.user
            invitation.save()

            # Generate invitation URL
            invitation_url = request.build_absolute_uri(
                reverse('accept_invitation', args=[str(invitation.token)])
            )

            # Return to the template with the invitation link
            return render(request, 'uploads/invitation_created.html', {
                'invitation': invitation,
                'invitation_url': invitation_url,
            })
    else:
        form = InvitationForm()

    return render(request, 'uploads/create_invitation.html', {'form': form})
    
@login_required
@user_passes_test(is_superuser)
def resend_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.is_accepted:
        messages.error(request, "This invitation has already been accepted.")
        return redirect('invitation_list')
    
    if invitation.is_expired:
        # Reset expiration date
        invitation.expires_at = timezone.now() + timezone.timedelta(days=10)
        invitation.save()

    # Generate invitation URL
    invitation_url = request.build_absolute_uri(
        reverse('accept_invitation', args=[str(invitation.token)])
    )

    return render(request, 'uploads/invitation_created.html', {
        'invitation': invitation,
        'invitation_url': invitation_url,
        'is_resend': True,
    })

def accept_invitation(request, token):
    # If user is already logged in, log them out first
    if request.user.is_authenticated:
        from django.contrib.auth import logout
        logout(request)
        # Redirect back to the same invitation URL after logout
        return redirect('accept_invitation', token=token)

    try: 
        invitation = Invitation.objects.get(token=token)
    except Invitation.DoesNotExist:
        messages.error(request, "Invalid invitation token.")
        return redirect('login')
    
    if invitation.is_accepted:
        messages.error(request, "This invitation has already been used.")
        return redirect('login')
    
    if invitation.is_expired:
        messages.error(request, "This invitation has expired.")
        return redirect('login')
    
    if request.method == 'POST':
        form = AcceptInvitationForm(request.POST, invitation=invitation)
        if form.is_valid():
            user = form.save()
            user.email = invitation.email
            user.save()

            # Mark invitation as accepted
            invitation.is_accepted = True
            invitation.accepted_at = timezone.now()
            invitation.save()

            messages.success(request, "Account created successfully! You can now login.")
            return redirect('login')
    else:
        form = AcceptInvitationForm(request.POST or None, invitation=invitation)
        
    return render(request, 'uploads/accept_invitation.html', {'form': form, 'invitation': invitation})

@login_required
@user_passes_test(is_superuser)
def cancel_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.is_accepted:
        messages.error(request, f"Invitation for {invitation.email} cancelled.")
    else:
        invitation.delete()
        messages.success(request, f"Invitation for {invitation.email} cancelled.")

    return redirect('invitation_list')