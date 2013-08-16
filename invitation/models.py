import datetime
import random

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

__all__ = ['Invitation']

class InvitationManager(models.Manager):
    def create_invitation(self, user, email, groups):
        """
        Create an ``Invitation`` and returns it.
        
        The code for the ``Invitation`` will be a SHA1 hash, generated
        from a combination of the ``User``'s username and a random salt.
        """

        kwargs = {'from_user': user, 'email': email}
        date_invited = datetime.datetime.now()
        kwargs['date_invited'] = date_invited
        #kwargs['groups':groups]
        kwargs['expiration_date'] = date_invited + datetime.timedelta(settings.ACCOUNT_INVITATION_DAYS)
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        kwargs['code'] = sha_constructor("%s%s%s" % (datetime.datetime.now(), salt, user.username)).hexdigest()
        print kwargs
        invite = self.create(**kwargs)
        for gr in groups:
            invite.groups.add(gr)
        return invite

    def remaining_invitations_for_user(self, user):
        """ Returns the number of remaining invitations for a given ``User``
        if ``INVITATIONS_PER_USER`` has been set.
        """
        if hasattr(settings, 'INVITATIONS_PER_USER'):
            inviteds_count = self.filter(from_user=user).count()
            remaining_invitations = settings.INVITATIONS_PER_USER - inviteds_count
            if remaining_invitations < 0:
                # Possible for admin to change INVITATIONS_PER_USER 
                # to something lower than the initial setting, resulting
                # in a negative value
                return 0
            return remaining_invitations

    def delete_expired_invitations(self):
        """
        Deletes all unused ``Invitation`` objects that are past the expiration date
        """
        self.filter(expiration_date__lt=datetime.datetime.now(), used=False).delete()


class Invitation(models.Model):
    code = models.CharField(_('invitation code'), max_length=40)
    date_invited = models.DateTimeField(_('date invited'))
    expiration_date = models.DateTimeField()
    used = models.BooleanField(default=False)
    from_user = models.ForeignKey(User, related_name='invitations_sent')
    to_user = models.ForeignKey(User, null=True, blank=True, related_name='invitation_received')
    email = models.EmailField(unique=True)
    groups = models.ManyToManyField(Group, related_name='invitations_groups')

    objects = InvitationManager()

    def __unicode__(self):
        return u"Invitation from %s to %s" % (self.from_user.username, self.email)

    def expired(self):
        return timezone.make_aware(self.expiration_date,timezone.get_default_timezone()) < timezone.now()

    def send(self, from_email=settings.DEFAULT_FROM_EMAIL):
        """
        Send an invitation email.
        """
        current_site = Site.objects.get_current()

        subject = render_to_string('invitation/invitation_email_subject.txt',
                                   {'invitation': self,
                                    'site': current_site})
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        message = render_to_string('invitation/invitation_email.txt',
                                   {'invitation': self,
                                    'expiration_days': settings.ACCOUNT_INVITATION_DAYS,
                                    'site': current_site})

        send_mail(subject, message, from_email, [self.email])

