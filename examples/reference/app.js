const $ = id => document.getElementById(id);
const editor = $('editor');
let requestId;
let saving = false;
let lastPayload = null;
let uncertain = false;

async function api(path, options) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, {...options, signal:controller.signal});
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || 'İşlem tamamlanamadı.');
    return value;
  } finally {
    clearTimeout(timeout);
  }
}

async function loadNotes(successMessage = '') {
  $('retry').hidden = true;
  $('status').classList.remove('error');
  $('status').textContent = 'Notlar yükleniyor…';
  try {
    const notes = await api('/api/notes');
    $('notes').replaceChildren();
    for (const note of notes) {
      const card = document.createElement('li');
      card.className = 'note';
      const title = document.createElement('h3');
      title.textContent = note.title;
      card.append(title);
      if (note.body) {
        const body = document.createElement('p');
        body.textContent = note.body;
        card.append(body);
      }
      const date = document.createElement('time');
      date.dateTime = note.created;
      date.textContent = new Date(note.created).toLocaleString('tr-TR', {dateStyle:'medium', timeStyle:'short'});
      card.append(date);
      $('notes').append(card);
    }
    $('count').textContent = `${notes.length} kayıt`;
    $('empty').hidden = notes.length !== 0;
    $('status').textContent = successMessage;
  } catch (error) {
    $('status').textContent = successMessage
      ? 'Not kaydedildi; liste yenilenemedi. Yeniden yükleyin.'
      : 'Notlar yüklenemedi. Bağlantıyı kontrol edip yeniden deneyin.';
    $('status').classList.add('error');
    $('retry').hidden = false;
  }
}

$('new-note').addEventListener('click', () => {
  $('note-form').reset();
  $('title').removeAttribute('aria-invalid');
  $('form-error').hidden = true;
  requestId = crypto.randomUUID();
  lastPayload = null;
  uncertain = false;
  editor.showModal();
  $('title').focus();
});
$('cancel').addEventListener('click', () => editor.close());
editor.addEventListener('cancel', event => { if (saving || uncertain) event.preventDefault(); });
editor.addEventListener('close', () => $('new-note').focus());
$('retry').addEventListener('click', () => loadNotes());
$('note-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  const title = $('title').value.trim();
  const body = $('body').value.trim();
  $('form-error').hidden = true;
  $('title').removeAttribute('aria-invalid');
  if (!title) {
    $('title').setAttribute('aria-invalid', 'true');
    $('form-error').textContent = 'Notuna bir başlık yaz.';
    $('form-error').hidden = false;
    $('title').focus();
    return;
  }
  // Uncertain requests retain both identity and content until readback/retry resolves them.
  const content = JSON.stringify({title, body});
  if (lastPayload !== null && lastPayload !== content) requestId = crypto.randomUUID();
  lastPayload = content;
  saving = true;
  for (const id of ['save', 'cancel', 'title', 'body', 'new-note']) $(id).disabled = true;
  $('save').textContent = 'Kaydediliyor…';
  $('note-form').setAttribute('aria-busy', 'true');
  try {
    if (uncertain) {
      const existing = (await api('/api/notes')).find(note => note.id === requestId);
      if (existing) {
        uncertain = false;
        editor.close();
        await loadNotes('Önceki denemede not kaydedilmiş. İkinci bir kayıt oluşturulmadı.');
        return;
      }
    }
    await api('/api/notes', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:requestId, title, body})});
    uncertain = false;
    editor.close();
    await loadNotes('Not kaydedildi. Yenilesen de burada kalır.');
  } catch (error) {
    uncertain = uncertain || error.name === 'AbortError' || error instanceof TypeError;
    $('form-error').textContent = error.name === 'AbortError' || error instanceof TypeError
      ? 'Kayıt sonucu bilinmiyor. Metnin korunuyor. Kaydı kontrol et düğmesi önceki sonucu okuyup gerekirse aynı notu tekrar dener.' : error.message;
    $('form-error').hidden = false;
  } finally {
    saving = false;
    for (const id of ['save', 'cancel', 'title', 'body', 'new-note']) $(id).disabled = false;
    if (uncertain) for (const id of ['cancel', 'title', 'body', 'new-note']) $(id).disabled = true;
    $('save').textContent = uncertain ? 'Kaydı kontrol et' : 'Notu kaydet';
    $('note-form').removeAttribute('aria-busy');
    if (editor.open) $('save').focus();
    else $('new-note').focus();
  }
});
loadNotes();
