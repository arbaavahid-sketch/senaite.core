/* Presentation only: do not alter settings values, names, actions or permissions. */
(function(){
 "use strict";
 var script=document.currentScript,base=script.src.split('/++plone++senaite.core.static/')[0];
 function init(){
  var forced=document.body.getAttribute('data-cp-preview-route');
  var path=forced||decodeURIComponent(location.pathname),key=path.replace(/\/$/,'').split('/').pop().replace(/^@@/,'');
  if(path.indexOf('/portal_registry')!==-1)key='portal_registry';
  if(/\/bika_setup\/(?:@@)?edit\/?$/.test(path))key='legacy-lims-settings';
  var pages={
   'legacy-lims-settings':['تنظیمات تکمیلی لیمز','Additional LIMS settings'],
   'actions-controlpanel':['منوها و عملیات','Portal actions'],
   'prefs_install_products_form':['افزونه‌ها','Add-ons'],
   'dateandtime-controlpanel':['تاریخ و زمان','Date and time'],
   'language-controlpanel':['زبان‌های سامانه','Languages'],
   'mail-controlpanel':['تنظیمات ایمیل','Mail settings'],
   'rules-controlpanel':['قوانین محتوا','Content rules'],
   'markup-controlpanel':['قالب‌های متن','Text formats'],
   'usergroup-userprefs':['کاربران و گروه‌ها','Users and groups'],
   'usergroup-groupprefs':['کاربران و گروه‌ها','Users and groups'],
   'prefs_error_log_form':['خطاهای سامانه','Application errors'],
   'filter-controlpanel':['تنظیمات محتوای HTML','Allowed HTML content'],
   'security-controlpanel':['تنظیمات امنیت','Security settings'],
   'portal_registry':['رجیستری تنظیمات','Configuration registry'],
   'maintenance-controlpanel':['نگهداری سامانه','Maintenance'],
   'impress-controlpanel':['تنظیمات گزارش','Report settings'],
   'senaite-controlpanel':['رجیستری لیمز','LIMS configuration'],
   'spotlight-controlpanel':['جست‌وجوی سامانه','Spotlight search']
  };
  if(!pages[key])return;
  var root=document.querySelector('#portal-column-content')||document.querySelector('#content');
  if(!root||root.classList.contains('cp-detail-page'))return;
  var heading=root.querySelector('h1');if(!heading)return;
  var fa=/^fa(?:-|$)/i.test(document.documentElement.lang||'');
  root.classList.add('cp-detail-page');root.setAttribute('data-cp-panel',key);root.dir=fa?'rtl':'ltr';
  if(!(key==='portal_registry' && /\/(?:edit|@@delete-record)(?:\/|$)/.test(path)))heading.textContent=pages[key][fa?0:1];
  var nav=document.createElement('nav');nav.className='cp-detail-breadcrumb';nav.setAttribute('aria-label',fa?'مسیر تنظیمات':'Settings navigation');
  var back=document.createElement('a');back.href=base+(key==='legacy-lims-settings'?'/@@lims-setup':'/@@overview-controlpanel');back.textContent=fa?(key==='legacy-lims-settings'?'تنظیمات لیمز':'تنظیمات سایت'):(key==='legacy-lims-settings'?'LIMS settings':'Site settings');nav.appendChild(back);
  var separator=document.createElement('span');separator.textContent='/';separator.setAttribute('aria-hidden','true');nav.appendChild(separator);
  var current=document.createElement('span');current.textContent=heading.textContent;nav.appendChild(current);
  heading.parentNode.insertBefore(nav,heading);
  if(fa){
   var localization=document.createElement('script');localization.src=base+'/++plone++senaite.core.static/js/tppc-settings-i18n.js?v=20261029-fa2';document.head.appendChild(localization);
   if(key==='legacy-lims-settings'){
    var help={
     EmailBodySampleRejection:'اگر اعلان ایمیلی رد نمونه فعال باشد، این متن برای مخاطب مشتری ارسال می‌شود. متغیرهای قابل استفاده: <code>$sample_id</code>، <code>$sample_link</code>، <code>$reasons</code> و <code>$lab_address</code>.',
     AutoPrintStickers:'زمان چاپ خودکار برچسب را انتخاب کنید:<ul><li>ثبت: هنگام ایجاد نمونهٔ جدید.</li><li>دریافت: هنگام دریافت نمونه در آزمایشگاه.</li><li>هیچ‌کدام: چاپ خودکار غیرفعال است.</li></ul>',
     IDFormatting:'<p>این بخش برای هر نوع محتوا، مانند نمونه و کاربرگ، شناسهٔ ترتیبی یکتا می‌سازد. قالب از متغیرهای همان نوع محتوا و شمارندهٔ <code>seq</code> تشکیل می‌شود. قالب <code>03d</code> شمارنده را با سه رقم، مانند 001 تا 999، نمایش می‌دهد.</p><p>پیشوند ثابت بدون تغییر می‌ماند: <code>WS-{seq:03d}</code> شناسه‌هایی مانند <code>WS-001</code> می‌سازد. برای ترکیب حروف و اعداد از <code>{alpha}</code> استفاده می‌شود؛ مثلاً <code>WS-{alpha:2a3d}</code> می‌تواند <code>WS-AA001</code>، <code>WS-AA002</code> و <code>WS-AB034</code> بسازد.</p><p>متغیرها: شناسهٔ مشتری <code>{clientId}</code>، سال <code>{year}</code>، شناسهٔ نمونه <code>{sampleId}</code>، نوع نمونه <code>{sampleType}</code>، تاریخ نمونه‌برداری <code>{samplingDate}</code> و تاریخ نمونه‌گیری <code>{dateSampled}</code>.</p><ul><li>قالب: رشته‌ای با متغیرهای ازپیش‌تعریف‌شده. متغیر <code>seq</code> باید در انتهای قالب قرار بگیرد.</li><li>نوع توالی: <code>generated</code> یا <code>counter</code>.</li><li>زمینه: در نوع <code>counter</code>، زمینهٔ تابع شمارش را مشخص می‌کند.</li><li>نوع شمارنده: <code>backreference</code> یا <code>contained</code>.</li><li>مرجع شمارنده: پارامتر تابع شمارش.</li><li>پیشوند: مقدار پیش‌فرض، در صورت نبود پیشوند در قالب.</li><li>تعداد بخش‌ها: تعداد بخش‌هایی که در پیشوند قرار می‌گیرند.</li></ul>'
    };
    Object.keys(help).forEach(function(id){var box=root.querySelector('#archetypes-fieldname-'+id+' .formHelp');if(box)box.innerHTML=help[id];});
   }
   var labels={
    "Security":"امنیت","Accounting":"حسابداری","Results reports":"گزارش‌های نتایج","Analyses":"آنالیزها","Appearance":"ظاهر","Sampling":"نمونه‌گیری","Notifications":"اعلان‌ها","Sticker":"برچسب","Id server":"شماره‌گذاری شناسه‌ها",
    "Site 'From' name":"نام فرستندهٔ ایمیل",
    "Site 'From' address":"آدرس ایمیل فرستنده",
    "E-mail characterset":"کدگذاری متن ایمیل",
    "Default":"عمومی",
    "The address of your local SMTP (outgoing e-mail) server. Usually 'localhost', unless you use an external server to send e-mail.":"نشانی سرور ارسال ایمیل؛ برای سرویس خارجی، نشانی اعلام‌شدهٔ ارائه‌دهنده را وارد کنید.",
    "The port of your local SMTP (outgoing e-mail) server. Usually '25'.":"پورت اتصال به سرور ایمیل را مطابق تنظیمات ارائه‌دهنده وارد کنید.",
    "Plone generates e-mail using this name as the e-mail sender.":"این نام به‌عنوان فرستندهٔ ایمیل‌های سامانه نمایش داده می‌شود.",
    "Plone generates e-mail using this address as the e-mail return address. It is also used as the destination address for the site-wide contact form and the 'Send test e-mail' feature.":"آدرس فرستنده و دریافت‌کنندهٔ پاسخ ایمیل‌های سامانه. پیام فرم تماس و ایمیل آزمایشی نیز به این نشانی فرستاده می‌شود.",
    "Characterset to use when sending e-mails.":"کدگذاری متن ایمیل؛ UTF-8 از متن فارسی پشتیبانی می‌کند.",
    "Warning: disabling this can be dangerous. Only disable if you know what you are doing.":"هشدار: غیرفعال‌کردن این گزینه می‌تواند خطرناک باشد. فقط در صورت آگاهی از پیامدها آن را غیرفعال کنید.",
    "A list of valid tags which will be not filtered out.":"فهرست تگ‌های HTML مجاز که از متن حذف نمی‌شوند.",
    "These attributes are additionally allowed.":"ویژگی‌های HTML دیگری که استفاده از آن‌ها مجاز است.",
    "These tags and their content are completely blocked when a page is saved or rendered. They are only deleted if they are not marked as valid_tags":"این تگ‌ها همراه محتوایشان هنگام ذخیره یا نمایش مسدود می‌شوند؛ مگر اینکه در فهرست تگ‌های مجاز قرار گرفته باشند."
   };
   root.querySelectorAll('[for],legend,h2,h3,.formHelp,.documentDescription,.formTab a,.nav-tabs a,[role="tab"]').forEach(function(element){
    var walker=document.createTreeWalker(element,NodeFilter.SHOW_TEXT),node;
    while((node=walker.nextNode())){var key=node.nodeValue.replace(/\s+/g,' ').trim();if(Object.prototype.hasOwnProperty.call(labels,key))node.nodeValue=labels[key];}
   });
  }
  root.querySelectorAll('[for]').forEach(function(label){
   if(label.tagName==='LABEL')return;
   var control=document.getElementById(label.getAttribute('for'));
   if(!control||!control.matches('input,select,textarea')||control.hasAttribute('aria-label')||control.hasAttribute('aria-labelledby'))return;
   if(!label.id)label.id='cp-label-'+control.id;
   control.setAttribute('aria-labelledby',label.id);
  });
  root.querySelectorAll('table.ordered-selection-field').forEach(function(table){
   if(table.rows.length)table.setAttribute('data-cp-columns',String(table.rows[0].cells.length));
  });
  root.querySelectorAll('.option').forEach(function(option){
   var parent=option.parentElement;
   if(parent.querySelectorAll(':scope > .option').length>3)parent.classList.add('cp-choice-list');
  });
  root.querySelectorAll('input[type=submit],button[type=submit]').forEach(function(button){
   var label=(button.name+' '+button.id+' '+button.textContent+' '+button.value).toLowerCase();
   if(/delete|remove|uninstall|حذف/.test(label))button.classList.add('cp-action-danger');
   else if(/cancel|back|انصراف|بازگشت/.test(label))button.classList.add('cp-action-secondary');
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
}());
