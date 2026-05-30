from plone.memoize import ram
from Products.Five.browser import BrowserView
from zope.component import queryUtility
from zope.i18n.interfaces import ITranslationDomain

import json


def _cache_key(method, self, domain, language):
    return (
        domain,
        language,
    )


class i18njs(BrowserView):
    @ram.cache(_cache_key)
    def _gettext_catalog(self, domain, language):
        td = queryUtility(ITranslationDomain, domain)
        if td is None:
            return
        if language not in td._catalogs:
            baselanguage = language.split("-")[0]
            if baselanguage not in td._catalogs:
                return
            else:
                language = baselanguage
        _catalog = {}
        for mo_path in reversed(td._catalogs[language]):
            catalog = td._data[mo_path]._catalog
            if catalog is None:
                td._data[mo_path].reload()
                catalog = td._data[mo_path]._catalog
            _catalog.update(catalog._catalog)
        return _catalog

    def __call__(self, domain=None, language=None):
        if domain is None:
            catalog = {}
        else:
            if language is None:
                language = self.request["LANGUAGE"]
            catalog = self._gettext_catalog(domain, language)

        response = self.request.response
        response.setHeader("Content-Type", "application/json; charset=utf-8")
        response.setBody(json.dumps(catalog))
        return response
