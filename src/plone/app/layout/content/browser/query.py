from plone.app.querystring.interfaces import IQuerystringRegistryReader
from plone.registry.interfaces import IRegistry
from Products.Five import BrowserView
from zope.component import getUtility

import json


class QueryStringIndexOptions(BrowserView):
    def __call__(self):
        registry = getUtility(IRegistry)
        config = IQuerystringRegistryReader(registry)()
        self.request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )
        return json.dumps(config)
