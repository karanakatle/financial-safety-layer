async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  return res.json();
}

function getParticipantId() {
  const key = 'arthamantriParticipantId';
  let participantId = localStorage.getItem(key);
  if (!participantId) {
    participantId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `web_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(key, participantId);
  }
  return participantId;
}

function withParticipant(url) {
  const resolved = new URL(url, window.location.origin);
  resolved.searchParams.set('participant_id', getParticipantId());
  return `${resolved.pathname}${resolved.search}`;
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
    li.innerHTML = `${a.message}`;

    if (a.reason === "income_event") {
      li.innerHTML += `
        <br/>
        <button onclick="confirmSavings(true)">Yes</button>
        <button onclick="confirmSavings(false)">No</button>
      `;
    }
    if (a.type === "fraud_warning") {
      alert(a.message);   // MVP popup
    }
    ul.appendChild(li);
  });
}

async function confirmSavings(choice) {
  const res = await fetch("/api/confirm-savings", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ accept: choice, participant_id: getParticipantId() })
  });

  const data = await res.json();

  alert(data.message);
  refresh();
}

function renderSchemes(data) {
  const container = document.getElementById("scheme-results");
  container.innerHTML = "";

  if (!data.eligible_schemes.length) {
    container.innerHTML = "<p>No schemes found based on inputs.</p>";
    return;
  }

  data.eligible_schemes.forEach((s) => {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <strong>${s.name}</strong><br/>
      <em>${s.reason}</em><br/>
      👉 ${s.benefit}<br/>
      💰 ${s.cost}<br/>
      📍 ${s.next_step}
    `;
    container.appendChild(div);
  });
}

let mediaRecorder;
let audioChunks = [];

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  mediaRecorder = new MediaRecorder(stream);

  audioChunks = [];

  mediaRecorder.ondataavailable = event => {
    audioChunks.push(event.data);
  };

  mediaRecorder.onstop = sendAudioToBackend;

  mediaRecorder.start();

  document.getElementById("mic-btn").textContent = "⏹ Stop";
}

function stopRecording() {
  mediaRecorder.stop();
  document.getElementById("mic-btn").textContent = "🎤 Speak";
}

async function sendAudioToBackend() {
  const blob = new Blob(audioChunks, { type: "audio/webm" });

  const reader = new FileReader();
  reader.readAsDataURL(blob);

  reader.onloadend = async () => {
    const base64Audio = reader.result.split(",")[1];

    const res = await fetch("/api/voice-audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio: base64Audio, participant_id: getParticipantId() })
    });

    const data = await res.json();

    document.getElementById("voice-response").textContent = data.response;

    // play returned audio if present
    if (data.audio) {
      const audio = new Audio("data:audio/wav;base64," + data.audio);
      audio.play();
    }
  };
}

let recording = false;

document.getElementById("mic-btn").addEventListener("click", () => {
  if (!recording) {
    startRecording();
    recording = true;
  } else {
    stopRecording();
    recording = false;
  }
});

async function refresh() {
  const [state, alerts] = await Promise.all([
    fetchJSON(withParticipant('/api/state')),
    fetchJSON(withParticipant('/api/alerts')),
  ]);
  renderState(state);
  renderAlerts(alerts);
}

async function askQuery(q) {
  const data = await fetchJSON('/api/voice-query', {
    method: 'POST',
    body: JSON.stringify({ query: q, participant_id: getParticipantId() }),
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
      participant_id: getParticipantId(),
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

document.getElementById("scheme-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const form = new FormData(e.target);

  const payload = {
    age: Number(form.get("age")),
    income: Number(form.get("income")),
    occupation: form.get("occupation"),
    gender: form.get("gender"),
    rural: form.get("rural") === "true",
    bank_account: form.get("bank_account") === "true",
    farmer: form.get("farmer") === "true",
    business_owner: form.get("business_owner") === "true",
  };

  const res = await fetch("/api/schemes", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  renderSchemes(data);
});

refresh();


if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.warn('Service worker registration failed:', error);
    });
  });
}
