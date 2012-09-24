"""
Unit tests for django-invitation.

These tests assume that you've completed all the prerequisites for
getting django-invitation running in the default setup, to wit:

1. You have ``invitation`` in your ``INSTALLED_APPS`` setting.

2. You have created all of the templates mentioned in this
   application's documentation.

3. You have added the setting ``ACCOUNT_INVITATION_DAYS`` to your
   settings file.

4. You have URL patterns pointing to the invitation views.

"""

import datetime
import sha

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core import management
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from invitation import forms
from invitation.models import Invitation

class InvitationTestCase(TestCase):
    """
    Base class for the test cases; this sets up one user and two invitations -- one
    expired, one not -- which are used to exercise various parts of
    the application.
    
    """
    def setUp(self):
        self.sample_user = User.objects.create_user(username='alice',
                                                    password='secret',
                                                    email='alice@example.com')
        self.sample_invite = Invitation.objects.create_invitation(user=self.sample_user, email='fred@example.com')
        self.expired_invite = Invitation.objects.create_invitation(user=self.sample_user, email='bob@example.com')
        self.expired_invite.expiration_date = datetime.datetime.now() - datetime.timedelta(1)
        self.expired_invite.save()


class InvitationModelTests(InvitationTestCase):
    """
    Tests for the model-oriented functionality of django-registration,
    including ``RegistrationProfile`` and its custom manager.
    
    """
    def test_registration_profile_created(self):
        """
        Test that an ``Invitation`` is created for a new code.
        
        """
        self.assertEqual(Invitation.objects.count(), 2)

    def test_activation_email(self):
        """
        Test that user signup sends an activation email.
        
        """
        self.sample_invite.send()
        self.assertEqual(len(mail.outbox), 1)

    def test_expired_user_deletion(self):
        """
        Test that
        ``RegistrationProfile.objects.delete_expired_users()`` deletes
        only inactive users whose activation window has expired.
        
        """
        Invitation.objects.delete_expired_invitations()
        self.assertEqual(Invitation.objects.count(), 1)

    def test_management_command(self):
        """
        Test that ``manage.py cleanupinvitation`` functions
        correctly.
        
        """
        management.call_command('cleanupinvitation')
        self.assertEqual(Invitation.objects.count(), 1)


class InvitationFormTests(InvitationTestCase):
    """
    Tests for the forms and custom validation logic included in
    django-invitation.
    
    """
    def test_invitation_form(self):
        """
        Test that ``InvitationForm`` enforces email constraints.
        
        """
        self.client.login(username='alice', password='secret')

        invalid_data_dicts = [
            {
            'data': {'email': 'fred@example.com'},
            'error': ('email', [_("An invitation has already been sent to that address.")])
            },
            {
             'data': {'email': 'alice@example.com'},
             'error': ('email', [_("A user with that email address has already registered.")])
            }
            ]

        for invalid_dict in invalid_data_dicts:
            response = self.client.post(reverse('invitation_invite'), data=invalid_dict['data'])
            field, error_msg = invalid_dict['error']
            self.assertFormError(response, 'form', field, error_msg)


class InvitationViewTests(InvitationTestCase):
    """
    Tests for the views included in django-invitation.
    
    """
    def test_invitation_view(self):
        """
        Test that the invitation view rejects invalid submissions,
        and creates a new invitation and redirects after a valid submission.
        
        """
        # You need to be logged in to send an invite.
        response = self.client.login(username='alice', password='secret')

        # Invalid email data fails.
        response = self.client.post(reverse('invitation_invite'),
                                    data={ 'email': 'example.com' })
        self.assertEqual(response.status_code, 200)
        self.failUnless(response.context['form'])
        self.failUnless(response.context['form'].errors)

        response = self.client.post(reverse('invitation_invite'),
                                    data={ 'email': 'foo@example.com' })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver%s' % reverse('invitation_complete'))
        self.assertEqual(Invitation.objects.count(), 3)

    def test_activated_view(self):
        """
        Test that the invited view invite the user from a valid
        code and fails if the invitation is invalid or has expired.
       
        """
        # Valid code puts use the invited template.
        response = self.client.get(reverse('invitation_accepted',
                                           kwargs={ 'invitation_code': self.sample_invite.code }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'invitation/accepted.html')

        # Expired code use the wrong code template.
        response = self.client.get(reverse('invitation_accepted',
                                           kwargs={'invitation_code': self.expired_invite.code}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'invitation/invalid.html')

        # Invalid code use the wrong code template.
        response = self.client.get(reverse('invitation_accepted',
                                           kwargs={'invitation_code': 'foo'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'invitation/invalid.html')

        # Nonexistent code use the wrong code template.
        response = self.client.get(reverse('invitation_accepted',
                                           kwargs={ 'invitation_code': sha.new('foo').hexdigest() }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'invitation/invalid.html')

class InvitationLimitTests(InvitationTestCase):
    def setUp(self):
        super(InvitationLimitTests, self).setUp()
        settings.INVITATIONS_PER_USER = 2

    def tearDown(self):
        # Have to manually delete the setting so that
        # tests assuming unlimited invitations pass
        del settings._wrapped.INVITATIONS_PER_USER

    def test_invitations_limit(self):
        self.client.login(username='alice', password='secret')
        response = self.client.post(reverse('invitation_invite'),
                                    data={'email': 'tim@example.com'})
        self.assertTemplateUsed(response, 'invitation/invalid.html')
        assert response.context["error_msg"]

    def test_remaining_invitations(self):
        settings.INVITATIONS_PER_USER = 5
        self.client.login(username='alice', password='secret')
        response = self.client.get(reverse('invitation_invite'))
        self.assertEqual(response.context["remaining_invitations"], 3)
