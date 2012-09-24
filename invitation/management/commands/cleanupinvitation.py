"""
A management command which deletes expired invitations (e.g.,
invitations which were never activated) from the database.

Calls ``Invitation.objects.delete_expired_invitations()``, which
contains the actual logic for determining which invitations are deleted.

"""

from django.core.management.base import NoArgsCommand

from invitation.models import Invitation


class Command(NoArgsCommand):
    help = "Delete expired invitations from the database"

    def handle_noargs(self, **options):
        Invitation.objects.delete_expired_invitations()
