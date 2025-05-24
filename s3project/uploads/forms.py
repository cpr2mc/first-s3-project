from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Invitation, UploadedFile, Project, ProjectMembership


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if a user with this email already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
class AcceptInvitationForm(UserCreationForm):
    invitation_token = forms.UUIDField(widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        self.invitation = kwargs.pop('invitation', None)
        super().__init__(*args, **kwargs)
        if self.invitation:
            self.fields['email'].initial = self.invitation.email
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['invitation_token'].initial = self.invitation.token

    def clean_email(self):
        # Ensure the email matches the invitation
        email = self.cleaned_data.get('email')
        if self.invitation and email != self.invitation.email:
            raise forms.ValidationError("This email does not match the invitation.")
        return email
    
    def clean_invitation_token(self):
        token = self.cleaned_data.get('invitation_token')
        try:
            invitation = Invitation.objects.get(token=token)
            if invitation.is_accepted:
                raise forms.ValidationError("This invitation has already been used.")
            if invitation.is_expired:
                raise forms.ValidationError("This invitation has expired.")
        except Invitation.DoesNotExist:
            raise forms.ValidationError("Invalid invitation token.")
        return token
    
    def clean(self):
        cleaned_data = super().clean()
        # Ensure the invitation token hasn't been tampered with
        token = cleaned_data.get('invitation_token')
        if token and self.invitation and str(token) != str(self.invitation.token):
            raise forms.ValidationError("Invalid invitation token.")
        return cleaned_data

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ProjectMembershipForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select users to add to this project"
    )

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        if project:
            # Exclude users already in the project
            existing_members = project.projectmembership_set.values_list('user_id', flat=True)
            self.fields['users'].queryset = User.objects.filter(
                is_active = True
            ).exclude(
                id__in=existing_members
            ).order_by('username')

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance