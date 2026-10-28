# -*- coding: utf-8 -*-
from __future__ import print_function
import os,io,transaction
from collections import Counter
from lxml import html
from Testing.makerequest import makerequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from senaite.core.interfaces import ISenaiteCore
from senaite.core.browser.controlpanel.overview import OverviewControlPanel
assert os.path.isfile('/data/.csrf-stage-only'), 'Disposable stage required'
app=makerequest(app);site=app['senaite'];request=app.REQUEST
setSite(site);setRequest(request);alsoProvides(request,ISenaiteCore);site.setupCurrentSkin(request)
newSecurityManager(request,SimpleUser('settings-stage','',['Manager'],[]).__of__(site.acl_users))
try:
 for language in ('fa','en'):
  view=OverviewControlPanel(site,request);view.is_rtl=lambda:language=='fa'
  expected=[]
  for category in view.categories():
   for action in view.sublists(category['id']):
    if action['visible']:
     expected.append(action['url'])
     assert view.panel_meta(action)['description'], action['id']
  page=view();tree=html.fromstring(page)
  cards=tree.cssselect('.cp-card')
  assert Counter(a.get('href') for a in cards)==Counter(expected)
  assert len(cards)==len(expected) and expected
  assert len(tree.cssselect('.cp-group'))==6
  assert len(tree.cssselect('details.cp-technical'))==1
  assert not tree.cssselect('details.cp-technical')[0].get('open')
  assert not tree.cssselect('.icon-controlpanel-MailHost')
  assert len(tree.cssselect('.cp-card-icon i'))==len(cards)
  assert b'&amp;&amp;' not in page.encode('utf-8') if isinstance(page,unicode) else b'&amp;&amp;' not in page
  root=tree.cssselect('.cp-page')[0]
  assert root.get('dir')==('rtl' if language=='fa' else 'ltr')
  head=''.join(html.tostring(link,encoding='unicode') for link in tree.xpath('//link[@rel="stylesheet"]'))
  preview=u'<!doctype html><html lang="%s" dir="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">%s<title>Site settings preview</title></head><body>%s</body></html>'%(language,root.get('dir'),head,html.tostring(root,encoding='unicode'))
  preview=preview.replace('http://nohost/senaite','https://lims.tppc.ir').replace('http://nohost','https://lims.tppc.ir')
  with io.open('/out/settings-%s.html'%language,'w',encoding='utf-8') as output:output.write(preview)
  print('LINKS_CATEGORIES_ICONS_AND_TECHNICAL_PRESERVED language='+language)
  original=view.sublists
  view.sublists=lambda category: original(category)+[{'id':'hidden-test','url':'/must-not-appear','visible':False,'title':'Hidden test'}]
  assert '/must-not-appear' not in view()
  view.upgrade_warning=lambda:True;view.mailhost_warning=lambda:True;view.timezone_warning=lambda:True;view.pil=lambda:False
  warnings=html.fromstring(view()).cssselect('.portalMessage.warning')
  assert len(warnings)==4,len(warnings)
  print('HIDDEN_ACTIONS_EXCLUDED_AND_ALL_EXISTING_WARNINGS_PRESERVED')
finally:
 transaction.abort();print('TRANSACTION_ABORTED_NO_SETTINGS_CHANGED')