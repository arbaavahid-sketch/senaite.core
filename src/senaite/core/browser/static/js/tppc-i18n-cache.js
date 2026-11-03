/* Expire only this release's Persian core translation cache, before UI bundles. */
(function(){'use strict';
 var language=document.documentElement.lang||'en';
 if(!/^fa(?:-|$)/i.test(language))return;
 var parts=language.split('-');language=parts[0]+(parts.length>1?'_'+parts[1].toUpperCase():'');
 try{
  var marker='tppc-core-i18n-revision-'+language,revision='20261103-tables3';
  if(localStorage.getItem(marker)===revision)return;
  localStorage.removeItem('senaite.core-'+language);
  localStorage.removeItem('senaite.core-'+language+'-updated');
  localStorage.setItem(marker,revision);
 }catch(error){/* Storage may be unavailable; native i18n still runs. */}
})();
