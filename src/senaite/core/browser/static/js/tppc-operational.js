/* Presentation only. Native listing and result handlers own all data/actions. */
(function(){
 'use strict';
 function addTopScroll(listing, fa) {
  var current;
  var observer = new ResizeObserver(sync);
  var control = document.createElement('input');
  control.type = 'range';
  control.min = 0;
  control.step = 1;
  control.dir = 'ltr';
  control.setAttribute('aria-label', fa ? 'پیمایش افقی جدول نمونه‌ها' : 'Scroll samples table horizontally');
  control.style.cssText = 'display:block;width:100%;height:22px;margin:4px 0;accent-color:#217d68';

  function sync() {
   if (!current) return;
   var width = Math.max(0, current.scrollWidth - current.clientWidth);
   var rtl = getComputedStyle(current).direction === 'rtl';
   control.style.display = width ? 'block' : 'none';
   control.max = width;
   control.value = rtl ? width + current.scrollLeft : current.scrollLeft;
  }

  control.addEventListener('input', function () {
   var rtl = getComputedStyle(current).direction === 'rtl';
   current.scrollLeft = Number(control.value) - (rtl ? Number(control.max) : 0);
  });

  function attach() {
   var table = listing.querySelector('.table-responsive table.contentstable');
   var wrapper = table && table.closest('.table-responsive');
   if (wrapper !== current) {
    if (current) current.removeEventListener('scroll', sync);
    observer.disconnect();
    current = wrapper;
    control.remove();
    if (current) {
     current.before(control);
     current.addEventListener('scroll', sync, {passive:true});
     observer.observe(current);
    }
   }
   if (table) observer.observe(table);
   sync();
  }

  new MutationObserver(attach).observe(listing, {childList:true, subtree:true});
  attach();
 }

 function start(){
  var listing=document.querySelector('.ajax-contents-table[data-form_id="samples"]');
  var results=document.querySelector('#sample-sections .analysis-listing-table');
  if(!listing&&!results){
   var internal = document.querySelector('#portal-column-content');
   var section = document.body.matches(
    '.portaltype-methods,.portaltype-method,.portaltype-batchfolder,.portaltype-batch,' +
    '.portaltype-instruments,.portaltype-instrument,.portaltype-customercare'
   ) || /\/(?:@@)?customer-care-status\/?$/.test(location.pathname)
     || /\/(?:bika_methods|bika_instruments|customercare)(?:\/|$)/.test(location.pathname);
   if (!section || !internal) return;
   internal.classList.add('tppc-operational', 'op-internal');
   var title = internal.querySelector('#viewlet-listing-table-title, h1');
   if (title) title.classList.add('op-title');
   return;
  }
  var root=document.querySelector('#portal-column-content');
  if(!root||root.classList.contains('tppc-operational'))return;
  root.classList.add('tppc-operational',listing?'op-samples':'op-results');
  var fa=(document.documentElement.lang||'fa').toLowerCase().indexOf('fa')===0;
  root.setAttribute('data-op-language',fa?'fa':'en');
  if (listing) addTopScroll(listing, fa);
  var title=root.querySelector('#viewlet-listing-table-title')||root.querySelector('h1');
  if(title){title.classList.add('op-title');}
  var help=document.createElement('section');help.className='op-guide';
  var lead=document.createElement('p');
  lead.textContent=listing?(fa?'نمونهٔ مورد نظر را با جست‌وجو یا فیلتر وضعیت پیدا کنید. برای دیدن آزمون‌ها و نتایج، شناسهٔ نمونه را باز کنید.':'Find a sample using search or a status filter. Open its sample ID to view analyses and results.'):(fa?'نتایج آزمون‌های این نمونه در جدول‌های زیر قرار دارند. فیلدهای قابل ویرایش بر اساس وضعیت نمونه و دسترسی شما نمایش داده می‌شوند.':'Results for this sample appear in the tables below. Editable fields depend on the sample status and your permissions.');
  help.appendChild(lead);
  var details=document.createElement('details'),summary=document.createElement('summary');
  summary.textContent=fa?'راهنمای این صفحه':'Page guide';details.appendChild(summary);
  var lines=listing?(fa?['فیلتر وضعیت، فهرست را محدود می‌کند؛ تعداد روی فیلتر با تعداد ردیف‌های انتخاب‌شده فرق دارد.','مربع کنار هر ردیف برای انتخاب آن است. عملیات گروهی را پس از بررسی نمونه‌های انتخاب‌شده انجام دهید.','از تنظیم ستون‌ها برای انتخاب اطلاعات مورد نیاز استفاده کنید. روی نمایشگر کوچک، جدول به‌صورت افقی پیمایش می‌شود.']:['Status filters narrow the list. Filter counts are different from the number of selected rows.','Use the checkbox beside a row to select it. Review selected samples before applying a bulk action.','Use column settings to choose the information you need. On small screens, scroll the table horizontally.']):(fa?['نتیجه را در ستون «نتیجه» و با توجه به واحد همان ردیف وارد کنید.','برای نتیجهٔ تشخیص‌داده‌نشده، گزینهٔ تعریف‌شدهٔ همان آزمون را انتخاب کنید؛ آن را با صفر جایگزین نکنید.','پس از ویرایش، از فرمان ذخیره یا ارسال موجود در جدول استفاده کنید و پیام موفقیت یا خطا را بررسی کنید.']:['Enter the result in its result column and check the unit on the same row.','For a non-detected result, use the option defined for that test; do not substitute zero.','After editing, use the table’s save or submit action and check its success or error message.']);
  var ul=document.createElement('ul');lines.forEach(function(line){var li=document.createElement('li');li.textContent=line;ul.appendChild(li);});details.appendChild(ul);help.appendChild(details);
  var target=listing?root.querySelector('#viewlet-listing-table-description'):root.querySelector('#sample-sections');
  if(target){target.parentNode.insertBefore(help,target);}else root.prepend(help);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
