/* Presentation only. Native permissions, values and submission handlers remain authoritative. */
(function(){'use strict';function start(){
 var body=document.body,root=document.querySelector('#portal-column-content');
 var folder=body.classList.contains('portaltype-clientfolder'),client=body.classList.contains('portaltype-client');
 if(!root||(!folder&&!client)||root.classList.contains('cx-page'))return;
 var fa=/^fa(?:-|$)/i.test(document.documentElement.lang||''),editing=client&&body.classList.contains('template-base_edit'),creating=location.pathname.indexOf('/portal_factory/')!==-1;
 root.classList.add('cx-page');if(folder)root.classList.add('tppc-operational');if(editing)root.classList.add('cx-edit');
 var heading=root.querySelector('h1'),crumbs=document.querySelectorAll('#portal-breadcrumbs a,.breadcrumb a');
 if(editing&&heading)heading.textContent=creating?(fa?'افزودن مشتری':'Add client'):(fa?'اطلاعات مشتری':'Client information');
 var guide=document.createElement('section');guide.className='cx-guide';
 var lead=document.createElement('p');lead.textContent=editing?(fa?'اطلاعات مشتری را در بخش‌های زیر بررسی کنید. تغییرات فقط با زدن «ذخیره» ثبت می‌شوند.':'Review the client details below. Changes are recorded only when you save.'):(folder?(fa?'مشتری را بر اساس نام یا شناسه پیدا کنید؛ با بازکردن نام، نمونه‌ها و اطلاعات مرتبط او در دسترس است.':'Find a client by name or ID. Open its name to access samples and related details.'):(fa?'نمونه‌ها و اطلاعات این مشتری را از دسترسی‌های زیر دنبال کنید.':'Use the shortcuts below to access this client’s samples and details.'));
 if(editing||folder||!root.querySelector('.op-guide'))guide.appendChild(lead);
 if(client&&!creating){var nav=document.createElement('nav');nav.className='cx-shortcuts';nav.setAttribute('aria-label',fa?'بخش‌های مشتری':'Client sections');
 var routes={'analysisrequests':[fa?'نمونه‌ها':'Samples','flask'],'contacts':[fa?'مخاطبان':'Contacts','address-book'],'reports_listing':[fa?'گزارش‌ها':'Reports','file-alt'],'edit':[fa?'اطلاعات مشتری':'Client details','pen']},seen={};
 document.querySelectorAll('#senaite-toolbar a[href]').forEach(function(a){if(/[?&]set_language=/.test(a.getAttribute('href')))return;var path=a.getAttribute('href').split('?')[0].replace(/\/$/,'').split('/').pop();if(!routes[path]||seen[path])return;seen[path]=true;var link=document.createElement('a');link.href=a.href;var icon=document.createElement('i');icon.className='fas fa-'+routes[path][1];icon.setAttribute('aria-hidden','true');link.appendChild(icon);link.appendChild(document.createTextNode(routes[path][0]));nav.appendChild(link);});
 if(nav.children.length)guide.appendChild(nav);
 }
 if(heading)heading.insertAdjacentElement('afterend',guide);
 if(!fa)return;
 var labels={'Address':'نشانی‌ها','Bank details':'اطلاعات بانکی','Preferences':'تنظیمات مشتری','Default':'اطلاعات اصلی','پیش‌فرض':'اطلاعات اصلی','PhysicalAddress':'نشانی محل','PostalAddress':'نشانی پستی','BillingAddress':'نشانی صورتحساب','Drag & drop files here, or click to select files':'فایل‌ها را اینجا بکشید یا برای انتخاب کلیک کنید','Maximum file size: 10 MB':'حداکثر اندازهٔ هر فایل: ۱۰ مگابایت'};
 function textLabels(){root.querySelectorAll('[role="tab"],.formTab a,.input-group-text,option,p').forEach(function(e){if(e.tagName==='OPTION'&&!e.hasAttribute('value'))return;var key=e.textContent.replace(/\s+/g,' ').trim();if(labels[key]&&e.textContent!==labels[key])e.textContent=labels[key];});}
 var provinces={'azarbayjan-e sharqi':'آذربایجان شرقی','azarbayjan-e gharbi':'آذربایجان غربی','ardabil':'اردبیل','esfahan':'اصفهان','ilam':'ایلام','bushehr':'بوشهر','tehran':'تهران','chahar mahall va bakhtiari':'چهارمحال و بختیاری','khuzestan':'خوزستان','zanjan':'زنجان','semnan':'سمنان','sistan va baluchestan':'سیستان و بلوچستان','fars':'فارس','kerman':'کرمان','kordestan':'کردستان','kermanshah':'کرمانشاه','kohgiluyeh va buyer ahmad':'کهگیلویه و بویراحمد','gilan':'گیلان','lorestan':'لرستان','mazandaran':'مازندران','markazi':'مرکزی','hormozgan':'هرمزگان','hamadan':'همدان','yazd':'یزد','qom':'قم','golestan':'گلستان','qazvin':'قزوین','khorasan-e janubi':'خراسان جنوبی','khorasan-e razavi':'خراسان رضوی','khorasan-e shemali':'خراسان شمالی'};
 var regions=(typeof Intl!=='undefined'&&Intl.DisplayNames)?new Intl.DisplayNames(['fa'],{type:'region'}):null;
 function addressLabels(){
  textLabels();
  root.querySelectorAll('select[id$=".country"] option[data-country-code]').forEach(function(o){var code=o.getAttribute('data-country-code'),name=regions?regions.of(code):(code==='IR'?'ایران':null);if(name&&o.textContent!==name)o.textContent=name;});
  root.querySelectorAll('select[id$=".state"]').forEach(function(select){var country=document.getElementById(select.id.replace(/\.state$/,'.country'));if(!country||country.value!=='Iran, Islamic Republic of')return;select.querySelectorAll('option[value]').forEach(function(o){var key=o.value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(),name=provinces[key];if(name&&o.textContent!==name)o.textContent=name;});});
  root.querySelectorAll('label[for$=".state"]').forEach(function(e){if(e.textContent.trim()!=='استان')e.textContent='استان';});
 }
 addressLabels();
 root.querySelectorAll('.ArchetypesAddressWidget,.ArchetypesMultiUploadWidget').forEach(function(e){new MutationObserver(addressLabels).observe(e,{childList:true,subtree:true});});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();})();
