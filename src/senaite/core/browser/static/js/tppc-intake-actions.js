/* Keep the original React workflow buttons in view. Never copy or invoke them. */
(function(){'use strict';function initialize(){
 if(!/\/sampleintake(?:\/view)?\/?$/.test(location.pathname))return;
 var root=document.querySelector('#portal-column-content');
 if(!root||root.classList.contains('intake-workbench'))return;
 var listing=root.querySelector('.ajax-contents-table');if(!listing)return;
 root.classList.add('intake-workbench');
 var fa=(document.documentElement.lang||'fa').toLowerCase().indexOf('fa')===0;
 var live=document.createElement('p');live.className='intake-selection-status sr-only';live.setAttribute('role','status');live.setAttribute('aria-live','polite');live.setAttribute('aria-atomic','true');root.appendChild(live);
 var frame=0;
 function schedule(){if(!frame)frame=requestAnimationFrame(synchronize);}
 function synchronize(){
  frame=0;var bar=listing.querySelector('.buttonbar'),active=!!bar;
  root.classList.toggle('intake-has-actions',active);
  var summary='';
  if(bar){
   var badge=bar.querySelector('.badge');
   var count=badge?badge.textContent.trim():String(listing.querySelectorAll('input[name="uids:list"]:checked').length);
   summary=Number(count)>0?(fa?count+' درخواست انتخاب شده':count+' request'+(Number(count)===1?'':'s')+' selected'):(fa?'درخواست‌های انتخاب‌شده':'Selected requests');
   if(bar.getAttribute('data-intake-summary')!==summary)bar.setAttribute('data-intake-summary',summary);
   bar.setAttribute('role','group');bar.setAttribute('aria-label',fa?'عملیات درخواست‌های انتخاب‌شده':'Actions for selected requests');
   var clear=bar.querySelector('#clear_selection');if(clear)clear.setAttribute('aria-label',fa?'لغو انتخاب‌ها':'Clear selection');
   var bounds=root.getBoundingClientRect(),left=Math.max(12,bounds.left),right=Math.min(innerWidth-12,bounds.right);
   root.style.setProperty('--intake-actions-left',left+'px');root.style.setProperty('--intake-actions-width',Math.max(0,right-left)+'px');
   root.style.setProperty('--intake-actions-space',(bar.getBoundingClientRect().height+40)+'px');
  }
  if(live.textContent!==summary)live.textContent=summary;
 }
 new MutationObserver(schedule).observe(listing,{childList:true,subtree:true,characterData:true});
 if(window.ResizeObserver)new ResizeObserver(schedule).observe(root);
 window.addEventListener('resize',schedule);schedule();
}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize);else initialize();})();
