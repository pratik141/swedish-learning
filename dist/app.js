
const state={category:'all',level:'all',set:'all',type:'all',query:'',view:'cards'};
const data=window.VOCAB_DATA;
const byId=new Map(data.items.map(item=>[item.id,item]));
const quickSet=new Set(data.quickIds);
const els={category:document.getElementById('categorySelect'),level:document.getElementById('levelSelect'),set:document.getElementById('setSelect'),type:document.getElementById('typeSelect'),search:document.getElementById('searchInput'),chips:document.getElementById('chapterChips'),cards:document.getElementById('cards'),tableWrap:document.getElementById('tableWrap'),tableBody:document.getElementById('tableBody'),visible:document.getElementById('visibleCount'),empty:document.getElementById('emptyState'),cardsView:document.getElementById('cardsView'),tableView:document.getElementById('tableView'),notes:document.getElementById('grammarNotes')};
function norm(s){return String(s||'').toLocaleLowerCase('sv-SE').normalize('NFD').replace(/[\u0300-\u036f]/g,'');}
function escapeHTML(s){return String(s||'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function setup(){
  els.category.innerHTML='<option value="all">All categories</option>'+data.chapters.map(ch=>`<option value="${escapeHTML(ch.title)}">${escapeHTML(ch.label)} (${ch.count})</option>`).join('');
  els.chips.innerHTML='<button class="chip active" type="button" data-category="all">All</button>'+data.chapters.slice(0,10).map(ch=>`<button class="chip" type="button" data-category="${escapeHTML(ch.title)}">${escapeHTML(ch.label.split(' ').slice(0,3).join(' '))}</button>`).join('');
  els.notes.innerHTML=data.notes.map(note=>`<article class="note"><h3>${escapeHTML(note.title)}</h3><p>${escapeHTML(note.body)}</p></article>`).join('');
  for(const control of [els.category,els.level,els.set,els.type]) control.addEventListener('change',e=>{state[control.id.replace('Select','')]=e.target.value; syncChips(); render();});
  els.search.addEventListener('input',e=>{state.query=e.target.value; render();});
  els.chips.addEventListener('click',e=>{const button=e.target.closest('button[data-category]'); if(!button)return; state.category=button.dataset.category; els.category.value=state.category; syncChips(); render();});
  els.cardsView.addEventListener('click',()=>setView('cards'));
  els.tableView.addEventListener('click',()=>setView('table'));
  render();
}
function syncChips(){document.querySelectorAll('.chip').forEach(chip=>chip.classList.toggle('active',chip.dataset.category===state.category));}
function setView(view){state.view=view;els.cardsView.classList.toggle('active',view==='cards');els.tableView.classList.toggle('active',view==='table');els.cards.hidden=view!=='cards';els.tableWrap.hidden=view!=='table';render();}
function filtered(){
  const q=norm(state.query.trim());
  return data.items.filter(item=>{
    if(state.category!=='all' && item.category!==state.category) return false;
    if(state.level!=='all' && item.level!==state.level) return false;
    if(state.type!=='all' && item.kind!==state.type) return false;
    if(state.set==='quick' && !quickSet.has(item.id)) return false;
    if(q){const hay=norm([item.sv,item.en,item.hi,item.pron,item.forms,item.categoryLabel,item.example?.sv,item.example?.en,item.example?.hi].join(' ')); if(!hay.includes(q)) return false;}
    return true;
  });
}
function render(){
  const rows=filtered();
  els.visible.textContent=rows.length.toLocaleString();
  els.empty.hidden=rows.length!==0;
  if(state.view==='cards') renderCards(rows);
  else renderTable(rows);
}
function renderCards(rows){
  els.cards.innerHTML=rows.map(item=>`<article class="vocab-card"><div class="card-meta"><span>${escapeHTML(item.categoryLabel)}</span><span class="badge">${escapeHTML(item.level)} · ${escapeHTML(item.kind)}</span></div><div class="swedish">${escapeHTML(item.sv)}</div><div class="meaning"><div><strong>English:</strong> ${escapeHTML(item.en)}</div><div class="hindi"><strong>हिन्दी:</strong> ${escapeHTML(item.hi)}</div></div><div class="forms">${escapeHTML(item.forms||'')}</div>${item.pron?`<div class="pron">Say it: ${escapeHTML(item.pron)}</div>`:''}<div class="example"><p><span>SV</span> ${escapeHTML(item.example.sv)}</p><p><span>EN</span> ${escapeHTML(item.example.en)}</p><p class="hindi"><span>HI</span> ${escapeHTML(item.example.hi)}</p></div></article>`).join('');
}
function renderTable(rows){
  els.tableBody.innerHTML=rows.map(item=>`<tr><td>${escapeHTML(item.sv)}<br><small>${escapeHTML(item.level)} · ${escapeHTML(item.kind)}</small></td><td>${escapeHTML(item.en)}</td><td class="hindi">${escapeHTML(item.hi)}</td><td>${escapeHTML(item.forms||'')}${item.pron?`<br><small>Say it: ${escapeHTML(item.pron)}</small>`:''}</td><td><strong>SV</strong> ${escapeHTML(item.example.sv)}<br><strong>EN</strong> ${escapeHTML(item.example.en)}<br><span class="hindi"><strong>HI</strong> ${escapeHTML(item.example.hi)}</span></td></tr>`).join('');
}
setup();
