/* Persian presentation defaults; selection values and handlers are unchanged. */
(function(){'use strict';
 if(!/^fa(?:-|$)/i.test(document.documentElement.lang||''))return;
 var $=window.jQuery;if(!$||!$.fn||!$.fn.selectpicker)return;
 $.fn.selectpicker.defaults=$.extend({},$.fn.selectpicker.defaults||{}, {
  noneSelectedText:'انتخاب نشده',noneResultsText:'نتیجه‌ای برای «{0}» پیدا نشد.',
  countSelectedText:'{0} مورد از {1} مورد انتخاب شده',selectAllText:'انتخاب همه',
  deselectAllText:'لغو انتخاب همه',multipleSeparator:'، '
 });
})();
