from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Invitation, UploadedFile


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

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['title', 'file']