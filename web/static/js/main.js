document.addEventListener('DOMContentLoaded', () => {
  let results = null;
  let split = 'train';
  let enrollFile = null;
  let authFile = null;

  const enrollInput = document.getElementById('enroll-file');
  const authInput = document.getElementById('auth-file');
  enrollInput.addEventListener('change', () => { enrollFile = enrollInput.files[0] || null; });
  authInput.addEventListener('change', () => { authFile = authInput.files[0] || null; });

  document.getElementById('btn-quick-genuine').addEventListener('click', (event) => runDemo('genuine', event.currentTarget));
  document.getElementById('btn-quick-impostor').addEventListener('click', (event) => runDemo('impostor', event.currentTarget));
  document.getElementById('enroll-form').addEventListener('submit', enroll);
  document.getElementById('auth-form').addEventListener('submit', authenticate);

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
      tab.classList.add('active');
      split = tab.dataset.split;
      showScores();
    });
  });

  loadScores();
  loadNames();

  async function runDemo(kind, button) {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Checking…';
    const body = new FormData();
    body.append('demo_type', kind);
    try {
      const response = await fetch('/api/quick-demo', { method: 'POST', body });
      const data = await response.json();
      if (!data.success) {
        alert(data.error || 'The demo could not run.');
        return;
      }
      showResult(data);
      loadNames();
    } catch (error) {
      alert('Could not reach the server. Start it with python start_interface.py');
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  async function enroll(event) {
    event.preventDefault();
    const name = document.getElementById('enroll-username').value.trim();
    if (!name) return;
    if (!enrollFile) {
      alert('Choose a fingerprint image first.');
      return;
    }
    const button = document.getElementById('btn-submit-enroll');
    button.disabled = true;
    const body = new FormData();
    body.append('username', name);
    body.append('file', enrollFile);
    try {
      const response = await fetch('/api/enroll', { method: 'POST', body });
      const data = await response.json();
      const note = document.getElementById('enroll-result');
      note.classList.remove('hidden');
      if (data.success) {
        note.textContent = name + ' is signed up. The picture was not stored.';
        document.getElementById('auth-username').value = name;
        loadNames();
      } else {
        note.textContent = data.error || 'Sign-up failed.';
      }
    } catch (error) {
      alert('Sign-up could not be sent.');
    } finally {
      button.disabled = false;
    }
  }

  async function authenticate(event) {
    event.preventDefault();
    const name = document.getElementById('auth-username').value.trim();
    if (!name) return;
    if (!authFile) {
      alert('Choose a new scan first.');
      return;
    }
    const button = document.getElementById('btn-submit-auth');
    button.disabled = true;
    button.textContent = 'Checking…';
    const body = new FormData();
    body.append('username', name);
    body.append('file', authFile);
    try {
      const response = await fetch('/api/authenticate', { method: 'POST', body });
      const data = await response.json();
      if (!data.success) {
        alert(data.error || 'This name is not signed up.');
        return;
      }
      showResult(data);
    } catch (error) {
      alert('Login could not be sent.');
    } finally {
      button.disabled = false;
      button.textContent = 'Check this scan';
    }
  }

  function showResult(data) {
    const box = document.getElementById('result-section');
    box.classList.remove('hidden', 'ok', 'no');
    box.classList.add(data.access_granted ? 'ok' : 'no');
    document.getElementById('result-title').textContent = data.access_granted ? 'Door open' : 'Door stays shut';
    document.getElementById('result-subtitle').textContent = data.access_granted
      ? 'This scan matches ' + data.username + '.'
      : 'This scan does not match ' + data.username + '.';
    const percent = data.metrics && data.metrics.error_rate_pct != null ? data.metrics.error_rate_pct + '%' : '—';
    document.getElementById('kpi-hd').textContent = percent;
    const matched = data.decision_diamond && data.decision_diamond.hash_match;
    document.getElementById('kpi-hash').textContent = matched ? 'Yes' : 'No';
    document.getElementById('kpi-zkp').textContent = data.access_granted ? 'Yes' : 'Not needed';
    const picture = data.steps && (data.steps.query_image || data.steps.query_minutiae);
    const image = document.getElementById('detail-minutiae-img');
    if (picture) {
      image.src = picture;
      image.classList.remove('hidden');
    }
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  async function loadScores() {
    try {
      const response = await fetch('/api/benchmark');
      const payload = await response.json();
      if (payload.available) {
        results = payload.data;
        showScores();
      } else {
        document.getElementById('bench-metrics-body').innerHTML = '<tr><td>No SOCOFing results file was found.</td></tr>';
      }
    } catch (error) {
      document.getElementById('bench-metrics-body').innerHTML = '<tr><td>Results could not be loaded.</td></tr>';
    }
  }

  function showScores() {
    if (!results) return;
    const data = results['kaggle_' + split];
    document.getElementById('split-dataset-label').textContent = split === 'train'
      ? 'People the system saw during the study'
      : 'People the system had never seen';
    if (!data) return;

    document.getElementById('bench-eer').textContent = data.eer_percentage + '%';
    document.getElementById('bench-far').textContent = data.cryptographic_far_percentage + '%';
    document.getElementById('bench-frr').textContent = data.cryptographic_frr_percentage + '%';
    document.getElementById('bench-auc').textContent = Number(data.auc).toFixed(3);

    const lines = [
      ['People', data.num_subjects],
      ['Fingers', data.num_fingers],
      ['Real logins tried', data.total_genuine_attempts],
      ['Real logins accepted', data.genuine_crypto_success],
      ['Proofs that passed', data.genuine_zkp_success],
      ['Fake logins tried', data.total_impostor_attempts],
      ['Fake logins that got in', data.impostor_crypto_success],
      ['Average gap, same finger', data.mean_genuine_hd],
      ['Average gap, different person', data.mean_impostor_hd]
    ];
    document.getElementById('bench-metrics-body').innerHTML = lines.map(([label, value]) =>
      '<tr><td>' + label + '</td><td><strong>' + value + '</strong></td></tr>'
    ).join('');

    const names = { CR: 'Rotated', Obl: 'Smudged', Zcut: 'Cut' };
    const breakdown = data.alteration_breakdown || {};
    document.getElementById('bench-alt-body').innerHTML = Object.keys(breakdown).map((key) => {
      const item = breakdown[key];
      return '<tr><td>' + (names[key] || key) + '</td><td>' + item.trials + '</td><td>' + item.accepted + '</td><td>' + item.frr_percentage + '%</td></tr>';
    }).join('');

    const plot = document.getElementById('benchmark-plot-img');
    if (data.plot_b64) {
      plot.src = String(data.plot_b64).startsWith('data:') ? data.plot_b64 : 'data:image/png;base64,' + data.plot_b64;
    }
  }

  async function loadNames() {
    try {
      const response = await fetch('/api/database/users');
      const users = await response.json();
      document.getElementById('user-count').textContent = users.length;
      const body = document.getElementById('user-table-body');
      if (!users.length) {
        body.innerHTML = '<tr><td colspan="3">No one yet. Use the buttons at the top, or sign up.</td></tr>';
        return;
      }
      body.innerHTML = users.map((user) =>
        '<tr><td>' + user.username + '</td><td>' + (user.commitment_h_preview || '') + '</td><td><button class="linkish" data-user="' + user.username + '" type="button">Remove</button></td></tr>'
      ).join('');
      body.querySelectorAll('.linkish').forEach((button) => {
        button.addEventListener('click', async () => {
          await fetch('/api/database/user/' + encodeURIComponent(button.dataset.user), { method: 'DELETE' });
          loadNames();
        });
      });
    } catch (error) {
      document.getElementById('user-table-body').innerHTML = '<tr><td colspan="3">The account list is unavailable.</td></tr>';
    }
  }
});
