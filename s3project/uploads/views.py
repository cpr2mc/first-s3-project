from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseForbidden
from .models import UploadedFile, Invitation
from .forms import FileUploadForm, InvitationForm, AcceptInvitationForm

# Helper function to check if a user is a superuser
def is_superuser(user):
    return user.is_superuser

@login_required
def file_list(request):
    files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'uploads/file_list.html', {'files': files})

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_instance = form.save(commit=False)
            file_instance.user = request.user
            file_instance.save()
            return redirect('file_list')
    else:
        form = FileUploadForm()
    
    return render(request, 'uploads/upload_file.html', {'form': form})

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

@login_required
def delete_file(request, file_id):
    file = get_object_or_404(UploadedFile, id=file_id)

    # Ensure users can only delete their own files
    if file.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to delete this file.")
    
    if request.method == 'POST':
        file.file.delete(save=False) # Delete the file from S3
        file.delete() # Delete the database entry
        messages.success(request, "File deleted successfully.")
        return redirect('file_list')
    
    return render(request, 'uploads/confirm_delete.html')
