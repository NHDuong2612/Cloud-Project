const note = document.querySelector('#note');
const status = document.querySelector('#status');
async function load() {
  try { const response = await fetch('/api/note'); if (!response.ok) throw new Error(); note.value = (await response.json()).text; }
  catch { status.textContent = 'Chưa đọc được ghi chú. Hãy tải lại sau.'; }
}
document.querySelector('#note-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const response = await fetch('/api/note', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:note.value})});
    if (!response.ok) throw new Error(); status.textContent = 'Đã lưu ghi chú.';
  } catch { status.textContent = 'Chưa lưu được ghi chú. Hãy thử lại.'; }
});
load();
