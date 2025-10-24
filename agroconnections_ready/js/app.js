// CONFIG: Reemplaza con tu Apps Script
const GAS_BASE = "https://script.google.com/macros/s/TU_ID/exec";
const ADMIN_TOKEN = "TU_TOKEN_SEGURO";

// NAV
document.getElementById('main-nav').addEventListener('click',(e)=>{
  if(e.target.matches('button[data-section]')){
    const id=e.target.getAttribute('data-section');
    document.querySelectorAll('main section').forEach(s=>s.classList.remove('active'));
    document.getElementById(id)?.classList.add('active');
    window.scrollTo({top:0,behavior:'smooth'});
  }
});

// GALERÍA
async function getLocalMedia(){ try{ const r=await fetch('data/media.json'); return await r.json(); }catch{return [];} }
async function getApiMedia(){ const r=await fetch(`${GAS_BASE}?fn=media`,{mode:'cors'}); if(!r.ok) throw new Error('API'); return await r.json(); }
function renderMedia(items){
  const cont=document.getElementById('galeria'); cont.innerHTML='';
  (items||[]).forEach(m=>{
    const card=document.createElement('div'); card.className='card';
    const fig=document.createElement('figure');
    if(m.type==='image'){
      const img=new Image(); img.src=m.src; img.alt=m.alt||'evidencia'; img.style.width='100%';
      img.addEventListener('click',()=>lb('image',m.src)); fig.appendChild(img);
    }else if(m.type==='video'){
      const v=document.createElement('video'); v.src=m.src; v.controls=true; v.className='media-video';
      v.addEventListener('click',()=>lb('video',m.src)); fig.appendChild(v);
    }
    const cap=document.createElement('figcaption'); cap.textContent=m.caption||''; fig.appendChild(cap);
    card.appendChild(fig); cont.appendChild(card);
  });
}
function lb(tipo,src){
  let b=document.querySelector('.lightbox');
  if(!b){
    b=document.createElement('div'); b.className='lightbox';
    b.innerHTML='<div class="lightbox-content" id="lbContent"></div>';
    b.addEventListener('click',(e)=>{ if(e.target===b) b.classList.remove('show');});
    document.body.appendChild(b);
  }
  const c=b.querySelector('#lbContent'); c.innerHTML='';
  if(tipo==='image'){ const i=new Image(); i.src=src; c.appendChild(i);}
  else{ const v=document.createElement('video'); v.src=src; v.controls=true; v.autoplay=true; c.appendChild(v); }
  b.classList.add('show');
}
async function cargarGaleria(){
  const cont=document.getElementById('galeria'); cont.innerHTML='Cargando evidencia...';
  try{
    const [api, local]=await Promise.allSettled([getApiMedia(), getLocalMedia()]);
    let items=[]; if(local.status==='fulfilled') items=[...local.value];
    if(api.status==='fulfilled') items=[...items, ...api.value];
    renderMedia(items);
  }catch(e){ renderMedia(await getLocalMedia()); }
}
document.getElementById('reload').addEventListener('click', cargarGaleria);

// SUBIDA A DRIVE
document.getElementById('uploadForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const file=document.getElementById('file').files[0];
  const caption=document.getElementById('caption').value;
  const alt=document.getElementById('alt').value;
  const token=document.getElementById('token').value;
  if(!file) return alert('Selecciona un archivo');
  if(!token) return alert('Ingresa el token');

  const fd=new FormData();
  fd.append('file',file,file.name);
  fd.append('caption',caption);
  fd.append('alt',alt);
  fd.append('token',token);

  try{
    const r=await fetch(GAS_BASE,{method:'POST',body:fd,mode:'cors'});
    const j=await r.json();
    if(!j.ok) throw new Error(j.error||'Error al subir');
    alert('✅ Evidencia subida'); cargarGaleria(); e.target.reset();
  }catch(err){ alert('❌ No se pudo subir: '+err.message); }
});

// FORM MULTIPASO + PDF
const form=document.getElementById('registroForm');
const steps=document.querySelectorAll('.step'); const panes=document.querySelectorAll('.step-pane');
function irPaso(n){ steps.forEach(s=>s.classList.toggle('active', s.getAttribute('data-step')==n)); panes.forEach(p=>p.classList.toggle('active', p.getAttribute('data-step')==n)); window.scrollTo({top:0,behavior:'smooth'}); }
steps.forEach(btn=>btn.addEventListener('click',()=>irPaso(btn.getAttribute('data-step'))));

document.getElementById('next1').addEventListener('click',()=>{
  if(!form.checkValidity()) return alert('Completa los campos.');
  const edad=parseInt(form.edad.value);
  if(edad<18||edad>45) return alert('⚠️ Edad fuera del rango preferido (18–45).');
  irPaso(2);
});
document.getElementById('back2')?.addEventListener('click',()=>irPaso(1));
document.getElementById('next2').addEventListener('click',()=>{
  const req=['ife','curp','domicilio','acta']; const tipos=['application/pdf','image/jpeg','image/png'];
  for(const id of req){
    const input=document.getElementById(id);
    if(!input.files||!input.files[0]) return alert('Falta: '+id.toUpperCase());
    const f=input.files[0];
    if(!tipos.includes(f.type)||f.size>5*1024*1024) return alert('Archivo inválido en '+id);
  }
  const rev=document.getElementById('revisión-lista'); rev.innerHTML='';
  [['Nombre',form.nombre.value],['Edad',form.edad.value],['Teléfono',form.telefono.value],['Correo',form.correo.value],
   ['Experiencia',form.experiencia.value],['Antecedentes',form.antecedentes.value]]
  .forEach(([k,v])=>{ const li=document.createElement('li'); li.textContent=k+': '+v; rev.appendChild(li); });
  irPaso(3);
});
document.getElementById('back3')?.addEventListener('click',()=>irPaso(2));
form.addEventListener('submit',(e)=>{
  e.preventDefault();
  if(!window.jspdf||!window.jspdf.jsPDF) return alert('PDF no disponible');
  const hoy=new Date(); const fecha=hoy.toISOString().slice(0,10).replace(/-/g,''); const suf=Math.floor(1000+Math.random()*9000);
  const folio=`AC-${fecha}-${suf}`;
  const doc=new window.jspdf.jsPDF(); doc.setFontSize(14);
  doc.text("Registro de candidato - Agro Connections",14,20); doc.setFontSize(11);
  [
    `Folio: ${folio}`,
    `Nombre: ${form.nombre.value}`,
    `Edad: ${form.edad.value}`,
    `Teléfono: ${form.telefono.value}`,
    `Correo: ${form.correo.value}`,
    `Experiencia: ${form.experiencia.value}`,
    `Antecedentes: ${form.antecedentes.value}`,
    `Fecha: ${new Date().toLocaleString()}`
  ].forEach((t,i)=>doc.text(t,14,34+i*8));
  const blob=doc.output('blob'); const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download=`registro_${folio}.pdf`; a.click();
  URL.revokeObjectURL(url);

  document.getElementById('folio').textContent='Folio: '+folio;
  const m=document.getElementById('modalExito'); m.classList.add('show'); m.setAttribute('aria-hidden','false');
});
document.getElementById('irInicio').addEventListener('click',()=>{
  const m=document.getElementById('modalExito'); m.classList.remove('show'); m.setAttribute('aria-hidden','true');
  document.querySelector('[data-section="inicio"]').click();
});

// INIT
cargarGaleria();
