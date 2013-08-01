import datetime

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django.shortcuts import render

from invitation.models import Invitation
from invitation.forms import InvitationForm

@login_required
def invite(request, success_url=None, form_class=InvitationForm,
           template_name='invitation/invitation_form.html',):
    context = {}
    if request.user.is_staff:
        context['remaining_invitations'] = 10
    elif hasattr(settings, 'INVITATIONS_PER_USER'):
        remaining_invitations = Invitation.objects.remaining_invitations_for_user(request.user)
        if not remaining_invitations:
            error_msg = _("You do not have any remaining invitations.")
            return render(request, 'invitation/invalid.html', {'error_msg': error_msg})
        else:
            context['remaining_invitations'] = remaining_invitations

    if request.method == 'POST':
        form = form_class(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            invitation = Invitation.objects.create_invitation(request.user, email)
            invitation.send()
            # success_url needs to be dynamically generated here; setting a
            # a default value using reverse() will cause circular-import
            # problems with the default URLConf for this application, which
            # imports this file.
            return HttpResponseRedirect(success_url or reverse('invitation_complete'))
    else:
        form = form_class()
    context['form'] = form
    return render(request, template_name, context)

@transaction.commit_on_success
def invitation_accepted(request, invitation_code, success_url=settings.LOGIN_REDIRECT_URL,
                      form_class=UserCreationForm, template_name='invitation/accepted.html'):
    error_msg = None
    try:
        invitation = Invitation.objects.get(code=invitation_code)
        if invitation.expired():
            error_msg = _("This invitation has expired.")
    except Invitation.DoesNotExist:
        error_msg = _("The invitation code is not valid. Please check the link provided and try again.")

    if error_msg is not None:
        return render(request, 'invitation/invalid.html', {'error_msg': error_msg})

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = invitation.email
            user.save()
            invitation.used = True
            invitation.to_user = user
            invitation.save()
            user = authenticate(username=user.username, password=form.cleaned_data["password1"])
            login(request, user)
            return HttpResponseRedirect(success_url)
    else:
        form = form_class()
    return render(request, template_name,
                              {'form': form,
                               'invitation': invitation})
