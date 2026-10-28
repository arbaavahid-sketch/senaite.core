# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE.
#
# SENAITE.CORE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2018-2025 by it's authors.
# Some rights reserved, see README and LICENSE.

from Products.CMFPlone.controlpanel.browser.overview import \
    OverviewControlPanel as Base
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
import io
import os


class OverviewControlPanel(Base):
    template = ViewPageTemplateFile("templates/overview.pt")

    def is_rtl(self):
        language = getToolByName(self.context, 'portal_languages').getPreferredLanguage()
        return (language or 'en').split('-')[0] in ('fa', 'ar', 'he', 'ur')

    def page_text(self, key):
        values = {
            'title': (u'تنظیمات سایت', u'Site settings'),
            'intro': (u'تنظیمات عمومی، کاربران و ابزارهای مدیریت سامانه', u'General settings, users and site administration'),
            'search': (u'جست‌وجو در تنظیمات', u'Search settings'),
            'search_hint': (u'نام یا کاربرد تنظیمات را بنویسید…', u'Search by name or purpose…'),
            'empty': (u'گزینه‌ای با این عبارت پیدا نشد.', u'No settings match your search.'),
            'technical': (u'اطلاعات فنی سامانه', u'Technical information'),
        }
        return values[key][0 if self.is_rtl() else 1]

    def category_title(self, category):
        title = category.get('title', u'')
        translated = {
            'General': u'تنظیمات عمومی', 'Content': u'محتوا',
            'Users': u'کاربران', 'Security': u'امنیت',
            'Advanced': u'ابزارهای پیشرفته',
            'Add-on Configuration': u'تنظیمات افزونه‌ها',
        }
        return translated.get(title, title) if self.is_rtl() else title

    def panel_meta(self, action):
        # Metadata only: the registered action URL, visibility and permissions stay authoritative.
        entries = {
            'actions-controlpanel': ('list', u'منوها و عملیات', u'پیوندها و گزینه‌های منوی سامانه', u'Site menu links and actions'),
            'senaite-controlpanel': ('sliders', u'رجیستری لیمز', u'تنظیمات ثبت‌شدهٔ سامانهٔ آزمایشگاه', u'Laboratory application configuration'),
            'mail-controlpanel': ('envelope', u'ایمیل', u'فرستنده و اتصال به سرور ایمیل', u'Mail sender and server connection'),
            'language-controlpanel': ('language', u'زبان', u'زبان‌های فعال و زبان پیش‌فرض سامانه', u'Available languages and site default'),
            'dateandtime-controlpanel': ('clock', u'تاریخ و زمان', u'منطقهٔ زمانی و نمایش تاریخ', u'Time zone and date display'),
            'prefs_install_products_form': ('puzzle-piece', u'افزونه‌ها', u'مدیریت افزونه‌های نصب‌شده', u'Manage installed add-ons'),
            'rules-controlpanel': ('sitemap', u'قوانین محتوا', u'قواعد خودکار و رویدادهای محتوا', u'Content rules and automated events'),
            'markup-controlpanel': ('code', u'قالب متن', u'قالب‌های متن و تبدیل محتوا', u'Text formats and content transforms'),
            'usergroup-userprefs': ('users', u'کاربران و گروه‌ها', u'حساب‌های کاربری و عضویت گروه‌ها', u'User accounts and group membership'),
            'security-controlpanel': ('shield-halved', u'امنیت', u'سیاست‌های امنیت و ورود کاربران', u'Security and user access policies'),
            'filter-controlpanel': ('filter', u'پالایش HTML', u'تگ‌ها و ویژگی‌های مجاز محتوای HTML', u'Allowed HTML tags and attributes'),
            'prefs_error_log_form': ('triangle-exclamation', u'خطاهای سامانه', u'مشاهدهٔ خطاهای ثبت‌شده', u'Inspect recorded application errors'),
            'portal_registry': ('database', u'رجیستری تنظیمات', u'مقادیر ثبت‌شدهٔ تنظیمات سامانه', u'Registered site configuration values'),
            'maintenance-controlpanel': ('screwdriver-wrench', u'نگهداری سامانه', u'ابزارهای نگهداری و مدیریت پایگاه داده', u'Maintenance and database tools'),
            'manage_main': ('gears', u'رابط مدیریت فنی', u'دسترسی به ابزارهای مدیریت Zope', u'Open the Zope management tools'),
            'impress-controlpanel': ('file-lines', u'تنظیمات گزارش', u'گزینه‌های تولید گزارش آزمایشگاه', u'Laboratory report generation settings'),
            'spotlight-controlpanel': ('magnifying-glass', u'جست‌وجوی سامانه', u'تنظیمات جست‌وجوی سریع Spotlight', u'Spotlight search configuration'),
        }
        url = action.get('url', u'').rstrip('/')
        key = url.rsplit('/', 1)[-1].lstrip('@')
        item = entries.get(key)
        title = action.get('title', u'')
        if not item:
            return {'title': title, 'description': u'', 'icon': 'fas fa-gear'}
        return {'title': item[1] if self.is_rtl() else title,
                'description': item[2] if self.is_rtl() else item[3],
                'icon': 'fas fa-' + item[0]}

    def settings_styles(self):
        with io.open(os.path.join(os.path.dirname(__file__), 'settings.css'), encoding='utf-8') as source:
            return source.read()
