from plone.base import PloneMessageFactory as _
from plone.schema import Email
from zope import schema
from zope.interface import Interface


class IContactForm(Interface):
    """Interface for describing the contact info form"""

    sender_fullname = schema.TextLine(
        title=_("label_sender_fullname", default="Name"),
        description=_("help_sender_fullname", default="Please enter your full name."),
        required=True,
    )

    sender_from_address = Email(
        title=_("label_sender_from_address", default="From"),
        description=_(
            "help_sender_from_address", default="Please enter your e-mail address."
        ),
        required=True,
    )

    subject = schema.TextLine(
        title=_("label_subject", default="Subject"), required=True
    )

    message = schema.Text(
        title=_("label_message", default="Message"),
        description=_(
            "help_message", default="Please enter the message you want to send."
        ),
        required=False,
    )
