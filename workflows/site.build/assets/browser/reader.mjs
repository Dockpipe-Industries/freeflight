import {marked} from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js/lib/common';
import bundle from './documents.json';
const escape = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scheme = matchMedia('(prefers-color-scheme: dark)');
window.freeflightTheme = mode => {
  if (!['system','light','dark'].includes(mode)) mode='system';
  try { localStorage.setItem('freeflight-theme', mode); } catch {}
  document.documentElement.dataset.theme = mode==='dark'||mode==='system'&&scheme.matches?'dark':'light';
};
let mode='system';try{mode=localStorage.getItem('freeflight-theme')||mode;}catch{}
window.freeflightTheme(mode);
scheme.addEventListener('change',()=>{try{window.freeflightTheme(localStorage.getItem('freeflight-theme')||'system');}catch{}});
const dialog=document.createElement('dialog');dialog.id='docs-reader';dialog.setAttribute('aria-label','FreeFlight documentation');
dialog.innerHTML='<header><strong>FreeFlight <span>/ Documentation</span></strong><button id="docs-close" aria-label="Close documentation">Close ×</button></header><div class="docs-layout"><aside><label for="docs-search">Search guides</label><input id="docs-search" type="search" placeholder="Search documentation…"><nav aria-label="Documentation"></nav></aside><article tabindex="0"></article></div>';
document.body.append(dialog);
const nav=dialog.querySelector('nav'), article=dialog.querySelector('article'), search=dialog.querySelector('input');
let current=bundle.pages[0], previousFocus;
function navigation(){const term=search.value.toLowerCase();nav.replaceChildren();for(const page of bundle.pages.filter(p=>(p.title+' '+p.markdown).toLowerCase().includes(term))){const a=document.createElement('a');a.textContent=page.title;a.href='#docs/'+encodeURIComponent(page.id);a.setAttribute('aria-current',page.id===current.id?'page':'false');nav.append(a);}if(!nav.children.length)nav.textContent='No guides match your search.';}
function render(page, fragment=''){
 current=page;
 const renderer=new marked.Renderer();renderer.html=({text})=>escape(text);renderer.image=({text})=>escape(text);
 const clean=DOMPurify.sanitize(marked.parse(page.markdown,{renderer}),{FORBID_TAGS:['img','iframe','style','form','input'],FORBID_ATTR:['style']});
 article.innerHTML='<div class="docs-meta">'+escape(page.group)+' · Source '+bundle.revision.slice(0,12)+(bundle.workingTreeChanges?' · Local modifications':'')+'</div>'+clean;
 for(const h of article.querySelectorAll('h1,h2,h3,h4'))h.id=h.textContent.toLowerCase().replace(/[^\p{L}\p{N} -]/gu,'').replace(/\s+/g,'-');
 for(const a of article.querySelectorAll('a')){
   const href=a.getAttribute('href'); if(!href)continue;
   if(href.startsWith('#')){a.href='#docs/'+encodeURIComponent(page.id)+'/'+encodeURIComponent(href.slice(1));continue;}
   const resolved=new URL(href,'https://docs.invalid/'+page.id);
   if(resolved.origin==='https://docs.invalid'){
     const target=resolved.pathname.slice(1);
     a.href=bundle.pages.some(p=>p.id===target)?'#docs/'+encodeURIComponent(target)+(resolved.hash?'/'+encodeURIComponent(resolved.hash.slice(1)):''):'https://github.com/Dockpipe-Industries/freeflight/blob/'+bundle.revision+'/'+target+resolved.hash;
   } else if(resolved.protocol!=='https:' && resolved.protocol!=='http:'){a.removeAttribute('href');}
   if(a.href.startsWith('http')){a.rel='noopener noreferrer';a.target='_blank';}
 }
 for(const code of article.querySelectorAll('pre code')){
   const pre=code.parentElement;const raw=code.textContent;hljs.highlightElement(code);const button=document.createElement('button');button.className='code-copy';button.textContent='Copy';button.setAttribute('aria-label','Copy code example');button.onclick=async()=>{try{await navigator.clipboard.writeText(raw);button.textContent='Copied';}catch{button.textContent='Select and copy';}};pre.prepend(button);
 }
 const source=document.createElement('a');source.href=page.source;source.className='source-link';source.textContent='View this guide at its source revision ↗';source.target='_blank';source.rel='noopener noreferrer';article.append(source);
 navigation();article.scrollTop=0;if(fragment)article.querySelector('#'+CSS.escape(fragment))?.scrollIntoView();
}
function route(){if(!location.hash.startsWith('#docs/')){if(dialog.open)dialog.close();return;}const parts=location.hash.slice(6).split('/');let id,fragment;try{id=decodeURIComponent(parts[0]);fragment=decodeURIComponent(parts[1]||'');}catch{return;}const page=bundle.pages.find(p=>p.id===id);if(!page)return;if(!dialog.open){previousFocus=document.activeElement;dialog.showModal();}render(page,fragment);}
window.freeflightDocs={open(id){const page=bundle.pages.find(p=>p.id===id)||current;location.hash='docs/'+encodeURIComponent(page.id);route();}};
function close(){history.pushState(null,'',location.pathname+location.search);dialog.close();previousFocus?.focus();}
dialog.querySelector('#docs-close').onclick=close;dialog.addEventListener('cancel',e=>{e.preventDefault();close();});search.addEventListener('input',navigation);window.addEventListener('hashchange',route);window.addEventListener('popstate',route);route();
