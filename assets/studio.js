'use strict';
const publicSource = 'https://raw.githubusercontent.com/amuadosf-cyber/petnova-portugal/conteudos-publicos/latest.json';
const sampleSource = 'assets/exemplo/amostra.json';
const notice = 'Loja em demonstração. Não aceitamos encomendas nem pagamentos.';
let batch;
let selectedPost;
const statusNode = document.querySelector('#batch-status');
const video = document.querySelector('#video');
const caption = document.querySelector('#caption');
const platform = document.querySelector('#platform');
const contentSelect = document.querySelector('#content-select');
const refresh = document.querySelector('#refresh');
const sample = document.querySelector('#sample');
const mediaPrefix = '/amuadosf-cyber/petnova-portugal/releases/download/';
function safeMediaURL(value) {
  const url = new URL(value, location.href);
  const ownSample = new URL('assets/exemplo/', location.href);
  if (url.origin === ownSample.origin && url.pathname.startsWith(ownSample.pathname)) return url.href;
  if (url.protocol === 'https:' && url.hostname === 'github.com' && url.pathname.startsWith(mediaPrefix) && !url.username && !url.password) return url.href;
  throw new Error('Endereço de ficheiro inválido');
}
function validate(data) {
  if (data.schema_version !== 1 || data.mode !== 'demonstracao' || data.social_publishing_enabled !== false || !Array.isArray(data.posts) || data.posts.length < 1 || data.posts.length > 5) throw new Error('Lote inválido');
  for (const post of data.posts) {
    if (typeof post.hook !== 'string' || typeof post.product_name !== 'string' || typeof post.id !== 'string' || post.status !== 'rascunho') throw new Error('Rascunho inválido');
    for (const name of ['tiktok', 'instagram', 'youtube']) if (typeof post.captions[name] !== 'string' || !post.captions[name].includes(notice)) throw new Error('Falta o aviso de demonstração');
    for (const name of ['video', 'ad', 'subtitles']) safeMediaURL(post.media[name]);
    if (!Number.isFinite(Date.parse(post.scheduled_at))) throw new Error('Horário inválido');
  }
  if (data.bundle_url) safeMediaURL(data.bundle_url);
  return data;
}
function updateCaption() {
  caption.value = selectedPost.captions[platform.value];
  document.querySelector('#copy-status').textContent = '';
}
function showPost() {
  selectedPost = batch.posts.find(post => post.id === contentSelect.value) || batch.posts[0];
  document.querySelector('#hook').textContent = selectedPost.hook;
  document.querySelector('#product-name').textContent = selectedPost.product_name;
  document.querySelector('#generation-kind').textContent = selectedPost.ai_used ? 'Título assistido por IA · ilustração original · por rever' : 'Texto por modelo · ilustração original · por rever';
  video.poster = safeMediaURL(selectedPost.media.ad);
  video.src = safeMediaURL(selectedPost.media.video);
  document.querySelector('#video-error').hidden = true;
  document.querySelector('#video-info').textContent = 'Vídeo gráfico vertical · sem voz';
  video.load();
  document.querySelector('#download-video').href = safeMediaURL(selectedPost.media.video);
  document.querySelector('#download-ad').href = safeMediaURL(selectedPost.media.ad);
  document.querySelector('#download-srt').href = safeMediaURL(selectedPost.media.subtitles);
  document.querySelector('#ad-preview').src = safeMediaURL(selectedPost.media.ad);
  updateCaption();
}
function showBatch(data, fixedSample) {
  batch = validate(data);
  contentSelect.replaceChildren();
  const clock = new Intl.DateTimeFormat('pt-PT', {hour:'2-digit',minute:'2-digit',timeZone:'Europe/Lisbon'});
  for (const post of batch.posts) {
    const option = document.createElement('option');
    option.value = post.id;
    option.textContent = `${clock.format(new Date(post.scheduled_at))} · ${post.product_name}`;
    contentSelect.append(option);
  }
  document.querySelector('#batch-count').textContent = `${batch.posts.length} ${batch.posts.length === 1 ? 'rascunho' : 'rascunhos'} neste lote`;
  const day = new Intl.DateTimeFormat('pt-PT', {dateStyle:'long',timeZone:'Europe/Lisbon'}).format(new Date(batch.date+'T12:00:00Z'));
  statusNode.textContent = fixedSample ? `Amostra fixa de ${day}. Usa «Atualizar conteúdos» para procurar o lote mais recente.` : `Último lote preparado: ${day}. Horários de planeamento em Lisboa; rascunhos por rever.`;
  const all = document.querySelector('#download-all');
  all.hidden = !batch.bundle_url;
  if (batch.bundle_url) all.href = safeMediaURL(batch.bundle_url);
  document.querySelector('#gallery').hidden = false;
  showPost();
}
async function load(fixedSample=false) {
  refresh.disabled = true;
  sample.disabled = true;
  statusNode.textContent = fixedSample ? 'A abrir a amostra…' : 'A procurar o lote mais recente…';
  try {
    const response = await fetch(fixedSample ? sampleSource : `${publicSource}?minute=${Math.floor(Date.now()/60000)}`, {cache:'no-store'});
    if (!response.ok) throw new Error('Lote indisponível');
    showBatch(await response.json(), fixedSample);
  } catch (_) {
    if (!fixedSample) {
      try {
        const response = await fetch(sampleSource);
        if (!response.ok) throw new Error('Amostra indisponível');
        showBatch(await response.json(), true);
        statusNode.textContent = 'O lote recente ainda não ficou disponível. Estás a ver a amostra fixa; podes tentar atualizar mais tarde.';
      } catch (_) {statusNode.textContent = 'Não foi possível abrir os rascunhos. Tenta atualizar a página.';}
    } else {statusNode.textContent = 'Não foi possível abrir a amostra. Tenta atualizar a página.';}
  } finally {refresh.disabled=false; sample.disabled=false;}
}
contentSelect.addEventListener('change', showPost);
platform.addEventListener('change', updateCaption);
refresh.addEventListener('click', ()=>load());
sample.addEventListener('click', ()=>load(true));
document.querySelector('#copy').addEventListener('click', async ()=>{
  try {await navigator.clipboard.writeText(caption.value); document.querySelector('#copy-status').textContent='Legenda copiada.';}
  catch (_) {caption.focus(); caption.select(); document.querySelector('#copy-status').textContent='Seleciona «Copiar» no menu do teu dispositivo.';}
});
video.addEventListener('loadedmetadata', ()=>{
  document.querySelector('#video-info').textContent=`${Math.round(video.duration)} segundos · ${video.videoWidth} × ${video.videoHeight} · sem voz`;
});
video.addEventListener('error', ()=>{document.querySelector('#video-error').hidden=false;});
load();
