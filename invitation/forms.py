from django import forms
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _

from invitation.models import Invitation

class InvitationForm(forms.Form):
    """ A simple form for validating that the supplied email
    address is not already in use by an existing user and has
    not already been sent an invitation. This prevents users
    from 'wasting' an invite. This also prevents users from inviting
    themselves multiple times by using the same email address
    but different usernames to create user accounts.
    """
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Invitation.objects.filter(email__iexact=email).count():
            raise forms.ValidationError(_("An invitation has already been sent to that address."))
        elif User.objects.filter(email__iexact=email).count():
            raise forms.ValidationError(_("A user with that email address has already registered."))
        return email
