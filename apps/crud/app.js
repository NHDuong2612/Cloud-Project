const list = document.querySelector('#tasks');
const status = document.querySelector('#status');
async function request(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  if (!response.ok) throw new Error('Không kết nối được dữ liệu. Hãy thử lại.');
  return response.json();
}
async function load() {
  try {
    const tasks = await request('/api/tasks');
    list.replaceChildren();
    for (const task of tasks) {
      const row = document.createElement('li');
      const check = document.createElement('input'); check.type = 'checkbox'; check.checked = task.done;
      const text = document.createElement('span'); text.textContent = task.title;
      const remove = document.createElement('button'); remove.textContent = 'Xóa';
      check.addEventListener('change', () => act(`/api/tasks/${task.id}`, {method:'PATCH', body:JSON.stringify({done:check.checked})}));
      remove.addEventListener('click', () => act(`/api/tasks/${task.id}`, {method:'DELETE'}));
      row.append(check, text, remove); list.append(row);
    }
    status.textContent = tasks.length ? '' : 'Chưa có công việc. Hãy thêm công việc đầu tiên.';
  } catch (error) { status.textContent = error.message; }
}
async function act(path, options) {
  try { await request(path, options); await load(); } catch (error) { status.textContent = error.message; }
}
document.querySelector('#new-task').addEventListener('submit', async event => {
  event.preventDefault(); const input = document.querySelector('#title');
  await act('/api/tasks', {method:'POST', body:JSON.stringify({title:input.value})}); input.value = '';
});
load();
