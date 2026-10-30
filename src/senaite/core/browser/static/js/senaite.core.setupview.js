/* Grouped setup navigation. No configuration or record mutations. */
window.SetupViewController = class SetupViewController {
  load() {
    var root = document.querySelector('.setup-workspace');
    if (!root || root.dataset.enhanced) return;
    root.dataset.enhanced = 'true';
    var search = root.querySelector('#searchbox');
    var cards = Array.from(root.querySelectorAll('.su-card'));
    var groups = Array.from(root.querySelectorAll('.su-group'));
    var filters = Array.from(root.querySelectorAll('.su-filter'));
    var selected = 'all';
    var savedOpen = null;
    function normalize(value) {
      return value.toLowerCase().replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/[\u064B-\u065F\u200c]/g,'').replace(/\s+/g,' ').trim();
    }
    function update() {
      var term = normalize(search.value);
      if (term && !savedOpen) savedOpen = groups.map(function(g){return g.open;});
      var count = 0;
      groups.forEach(function(group,index){
        var visible = 0;
        group.querySelectorAll('.su-card').forEach(function(card){
          var match = (selected === 'all' || selected === group.dataset.groupId) && normalize(card.dataset.search).includes(term);
          card.hidden = !match;
          if (match) {visible++; count++;}
        });
        group.hidden = visible === 0;
        group.querySelector('.su-group-count span').textContent = visible;
        if (term && visible) group.open = true;
        else if (!term && savedOpen) group.open = savedOpen[index];
      });
      if (!term) savedOpen = null;
      root.querySelector('#setup-empty').hidden = count !== 0;
      root.querySelector('#setup-clear').hidden = !search.value;
      root.querySelector('#setup-result-count').textContent = count + ' ' + (term ? root.dataset.resultsLabel : root.dataset.sectionLabel);
    }
    search.addEventListener('input',update);
    search.addEventListener('keydown',function(event){
      if (event.key === 'Escape') {search.value='';update();}
      // Enter retains focus; it never follows an unexpected result.
    });
    filters.forEach(function(button){button.addEventListener('click',function(){
      selected = button.dataset.group;
      filters.forEach(function(item){var active=item===button;item.classList.toggle('is-active',active);item.setAttribute('aria-pressed',String(active));});
      update();
      if (selected !== 'all') groups.forEach(function(group){if(group.dataset.groupId===selected)group.open=true;});
    });});
    ['#setup-clear','#setup-reset'].forEach(function(id){root.querySelector(id).addEventListener('click',function(){search.value='';selected='all';filters.forEach(function(button){var active=button.dataset.group==='all';button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});update();search.focus();});});
    update();
  }
};
function initializeGroupedSetup(){new window.SetupViewController().load();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initializeGroupedSetup);else initializeGroupedSetup();
