# -*- coding: utf-8 -*-
from plone.app.contenttypes.behaviors.leadimage import ILeadImage
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class LeadImageViewlet(ViewletBase):
    """ A simple viewlet which renders leadimage """

    index = ViewPageTemplateFile('document_leadimage.pt')

    def update(self):
        self.context = ILeadImage(self.context)
        self.available = True if self.context.image else False
