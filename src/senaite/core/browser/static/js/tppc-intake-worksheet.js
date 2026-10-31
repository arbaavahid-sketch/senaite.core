/* Page presentation only: preserve native form controls and submission handlers. */
(function(){'use strict';function initialize(){
 var intake=document.querySelector('#analysisrequest_add_form');
 var worksheet=document.querySelector('.manage_results_header');
 if(!intake&&!worksheet)return;
 var root=document.querySelector('#portal-column-content');if(!root||root.classList.contains('iw-page'))return;
 root.classList.add('iw-page',intake?'iw-intake':'iw-worksheet');
 var fa=(document.documentElement.lang||'fa').toLowerCase().indexOf('fa')===0;
 var guide=document.createElement('section');guide.className='iw-guide';
 var title=document.createElement('h2');title.textContent=intake?(fa?'ثبت نمونه در آزمایشگاه':'Register laboratory samples'):(fa?'ثبت و بررسی نتایج کاربرگ':'Enter and review worksheet results');guide.appendChild(title);
 var lead=document.createElement('p');lead.textContent=intake?(fa?'هر ستون مربوط به یک نمونه است. ابتدا مشتری و مشخصات نمونه را کامل کنید، سپس آزمون‌های همان نمونه را انتخاب کنید.':'Each column represents one sample. Complete its customer and sample details, then select its analyses.'):(fa?'پیش از ورود نتیجه، آزمونگر و دستگاه را بررسی کنید. نتایج هر آزمون را با توجه به واحد همان ردیف وارد کنید.':'Check the analyst and instrument before entering results. Use the unit shown on each analysis row.');guide.appendChild(lead);
 var details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=fa?'راهنمای ثبت':'Entry guide';details.appendChild(summary);
 var ul=document.createElement('ul');var lines=intake?(fa?['فیلدهای دارای علامت ضروری را برای هر نمونه تکمیل کنید. انتخاب مشتری و مخاطب باید به همان نمونه مربوط باشد.','دکمهٔ کپی، اطلاعات را بین ستون‌ها منتقل می‌کند؛ پیش از ثبت، مقدارهای هر ستون را دوباره بررسی کنید.','در جدول آزمون‌ها، فقط آزمون‌های مورد نیاز را برای هر نمونه انتخاب کنید. ثبت نهایی با دکمهٔ اصلی پایین فرم انجام می‌شود.']:['Complete required fields for every sample and check its customer and contact.','Copy actions transfer values between columns. Review each column before submitting.','Select the analyses required for each sample. Use the native submission button at the bottom to register them.']):(fa?['تغییر چیدمان با دکمهٔ «اعمال» انجام می‌شود. مقدار نتیجه، واحد و مشخصات نمونه را پیش از ارسال بررسی کنید.','پرکردن گروهی، چند فیلد را با هم تغییر می‌دهد؛ نمونه‌ها و گزینهٔ فیلدهای خالی را پیش از اجرا بررسی کنید.','پس از ویرایش نتیجه از فرمان ذخیره یا ارسال جدول استفاده کنید و پیام موفقیت یا خطا را بخوانید.']:['Apply a layout change with its Apply button. Check result values, units and sample identities before submission.','Bulk fill changes multiple fields. Review the samples and the empty-fields option before applying it.','Use the table’s save or submit action after editing and check its success or error message.']);
 lines.forEach(function(text){var li=document.createElement('li');li.textContent=text;ul.appendChild(li);});details.appendChild(ul);guide.appendChild(details);
 var anchor=intake||worksheet.closest('.row');anchor.parentNode.insertBefore(guide,anchor);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize);else initialize();})();
(function(){'use strict';function reception(){
 var root=document.querySelector('#portal-column-content'),convert=document.querySelector('#intake-conversion');
 var listing=location.pathname.replace(/\/$/,'').match(/\/sampleintake(?:\/view)?$/)&&document.querySelector('.ajax-contents-table');
 if(!root||(!listing&&!convert)||root.classList.contains('iw-page'))return;
 root.classList.add('iw-page','iw-reception');
 var fa=(document.documentElement.lang||'fa').toLowerCase().indexOf('fa')===0;
 var guide=document.createElement('section');guide.className='iw-guide';var h=document.createElement('h2');h.textContent=fa?'پذیرش درخواست نمونه':'Sample request reception';guide.appendChild(h);
 var p=document.createElement('p');p.textContent=convert?(fa?'اطلاعات اعلام‌شدهٔ مشتری را با نمونهٔ تحویلی تطبیق دهید. سپس مشتری، نوع نمونه و آزمون‌های نهایی را برای ساخت نمونه انتخاب کنید.':'Match the customer request with the delivered sample, then choose its client, sample type and final analyses before creating the sample.'):(fa?'درخواست‌های ورودی را بررسی کنید. پیش از ساخت نمونه، اطلاعات مشتری، نمونهٔ تحویلی و آزمون‌های مورد نیاز را تطبیق دهید.':'Review incoming requests and match the customer details, delivered sample and required analyses before creating a sample.');guide.appendChild(p);
 var detail=document.createElement('details'),summary=document.createElement('summary');summary.textContent=fa?'راهنمای پذیرش':'Reception guide';detail.appendChild(summary);
 var text=document.createElement('p');text.textContent=fa?'درخواست مشتری با نمونهٔ ثبت‌شده متفاوت است. اگر ستون نمونهٔ ثبت‌شده پیوند دارد، همان نمونه را باز کنید. انتخاب آزمون‌ها باید با روش و خدمات قابل ارائهٔ آزمایشگاه مطابقت داشته باشد.':'A customer request is different from a registered sample. If a registered-sample link exists, open that sample. Choose analyses that match the laboratory’s methods and available services.';detail.appendChild(text);guide.appendChild(detail);
 var anchor=convert||(root.querySelector('#folderlisting-main-table'));if(anchor)anchor.parentNode.insertBefore(guide,anchor);
}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',reception);else reception();})();
