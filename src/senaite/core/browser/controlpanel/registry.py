# -*- coding: utf-8 -*-
"""Translate registry metadata without modifying fields, records or handlers."""
import io
import json
import os
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.registry.browser.records import RecordsControlPanel
from zope.i18n import translate

_DATA = os.path.join(os.path.dirname(__file__), 'settings-fa.json')
with io.open(_DATA, encoding='utf-8') as stream:
    _FA = json.load(stream)


class LocalizedRegistry(RecordsControlPanel):
    template = ViewPageTemplateFile('templates/registry_records.pt')

    def metadata_text(self, text):
        if not text:
            return u''
        language = getToolByName(self.context, 'portal_languages').getPreferredLanguage()
        if (language or 'en').split('-')[0] != 'fa':
            return translate(text, context=self.request, target_language=language or 'en')
        for value in (unicode(text or ''), getattr(text, 'default', None)):
            if value:
                key = u' '.join(value.split())
                if key in _FA:
                    return _FA[key]
        return translate(text, domain='plone', context=self.request, target_language='fa')

    def updateActions(self):
        super(LocalizedRegistry, self).updateActions()
        for action in self.actions.values():
            action.title = self.metadata_text(action.title)