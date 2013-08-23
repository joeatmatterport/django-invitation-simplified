from django.conf.urls.defaults import *
from django.views.generic import ListView, TemplateView

from invitation.views import invite, invitation_accepted

urlpatterns = patterns('',
    url(r'^invite/complete/$',
        TemplateView.as_view(
            template_name='invitation/invitation_complete.html'),
            name='invitation_complete'),
    url(r'^invite/$',
        invite,
        name='invitation_invite'),
    url(r'^invite/(?P<invitation_code>\w+)/$',
        invitation_accepted,
        name='invitation_accepted'),
)
