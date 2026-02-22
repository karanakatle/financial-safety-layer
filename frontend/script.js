async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  return res.json();
}

function renderState(state) {
  const stateEl = document.getElementById('state');
  stateEl.innerHTML = `
    <div><strong>Balance</strong><br/>₹${state.balance}</div>
    <div><strong>Avg Daily Spend</strong><br/>₹${state.avg_daily_spend}</div>
    <div><strong>Days to Zero</strong><br/>${state.days_to_zero}</div>
    <div><strong>Safe Spend Today</strong><br/>₹${state.safe_spend_today}</div>
    <div><strong>Events</strong><br/>${state.transaction_count}</div>
  `;
}

function renderAlerts(alerts) {
  const ul = document.getElementById('alerts');
  ul.innerHTML = '';
  alerts.slice().reverse().forEach((a) => {
    const li = document.createElement('li');
    li.className = `priority-${a.priority}`;
    // message text
    const msg = document.createElement('div');
    msg.textContent = `${a.message}`;
    li.appendChild(msg);
    
    // show buttons ONLY for saving suggestion
    if (a.reason === "income_event") {
      const btnYes = document.createElement('button');
      btnYes.textContent = "Yes";
      btnYes.onclick = () => respondYes();

      const btnNo = document.createElement('button');
      btnNo.textContent = "No";
      btnNo.onclick = () => respondNo();

      li.appendChild(btnYes);
      li.appendChild(btnNo);
    }
    // li.textContent = `${a.message} (${a.reason})`;
    ul.appendChild(li);
  });
}

async function respondYes() {
  const data = await fetchJSON('/api/voice-query', {
    method: 'POST',
    body: JSON.stringify({ query: "yes" }),
  });
  document.getElementById('voice-response').textContent = data.response;
  await refresh();
}

async function respondNo() {
  const data = await fetchJSON('/api/voice-query', {
    method: 'POST',
    body: JSON.stringify({ query: "no" }),
  });
  document.getElementById('voice-response').textContent = data.response;
  await refresh();
}

async function refresh() {
  const [state, alerts] = await Promise.all([
    fetchJSON('/api/state'),
    fetchJSON('/api/alerts'),
  ]);
  renderState(state);
  renderAlerts(alerts);
}

async function askQuery(q) {
  const data = await fetchJSON('/api/voice-query', {
    method: 'POST',
    body: JSON.stringify({ query: q }),
  });
  const responseText = data.response;
  document.getElementById('voice-response').textContent = responseText;
  if ('speechSynthesis' in window) {
    const utter = new SpeechSynthesisUtterance(responseText);
    utter.lang = 'hi-IN';
    window.speechSynthesis.speak(utter);
  }
}

document.getElementById('tx-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  await fetchJSON('/api/transaction', {
    method: 'POST',
    body: JSON.stringify({
      user_id: 1,   // ⭐ add this
      type: form.get('type'),
      amount: Number(form.get('amount')),
      category: form.get('category'),
    }),
  });
  e.target.reset();
  refresh();
});

document.getElementById('ask-btn').addEventListener('click', async () => {
  const q = document.getElementById('query').value;
  if (q) await askQuery(q);
});

document.getElementById('mic-btn').addEventListener('click', () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('Speech recognition not supported in this browser.');
    return;
  }
  const rec = new SpeechRecognition();
  rec.lang = 'hi-IN';
  rec.onresult = async (event) => {
    const q = event.results[0][0].transcript;
    document.getElementById('query').value = q;
    await askQuery(q);
  };
  rec.start();
});

refresh();
