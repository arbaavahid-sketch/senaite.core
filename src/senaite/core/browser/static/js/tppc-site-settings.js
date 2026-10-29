(function(){
  var root=document.querySelector('.cp-page'),input=root.querySelector('#cp-search');
  var items=[].slice.call(root.querySelectorAll('.cp-item')),groups=[].slice.call(root.querySelectorAll('.cp-group'));
  var empty=root.querySelector('#cp-empty'),status=root.querySelector('#cp-search-status'),fa=root.dir==='rtl';
  function normalize(value){return value.toLocaleLowerCase().replace(/[يى]/g,'ی').replace(/ك/g,'ک').replace(/[\u200c\s]+/g,' ').trim();}
  function filter(){
    var query=normalize(input.value),count=0;
    items.forEach(function(item){item.hidden=query!=='' && normalize(item.textContent+' '+item.getAttribute('data-search')).indexOf(query)===-1;if(!item.hidden)count++;});
    groups.forEach(function(group){group.hidden=![].some.call(group.querySelectorAll('.cp-item'),function(item){return !item.hidden;});});
    empty.hidden=count!==0;
    status.textContent=fa?(count+' بخش'+(query?' مطابق جست‌وجو':' در دسترس')):(count+(query?' matching settings':' available settings'));
  }
  input.addEventListener('input',filter);filter();
}());
      