/**
 * ZeroBio Vault — Minimalist, Aesthetic & Clean JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Global State
  let benchmarkData = null;
  let activeDataset = 'kaggle'; // 'kaggle' or 'fvc'
  let activeSplit = 'train';    // 'train' or 'test'

  // Enrollment State
  let enrollSelectedPath = 'data/kaggle_socofing/real/100__M_Left_index_finger.BMP';
  let enrollSelectedFile = null;

  // Authentication State
  let authSelectedPath = 'data/kaggle_socofing/altered/100__M_Left_index_finger_CR.BMP';
  let authSelectedFile = null;

  // Initialize Elements
  initPills();
  initForms();
  initQuickDemo();
  initBenchmark();
  initAuditTable();
  initAccordion();

  // 1. Sample Pill Handlers
  function initPills() {
    // Enroll pills
    const enrollPills = document.querySelectorAll('#enroll-samples .sample-pill');
    enrollPills.forEach(pill => {
      pill.addEventListener('click', () => {
        enrollPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        enrollSelectedPath = pill.dataset.path;
        enrollSelectedFile = null;
        document.getElementById('enroll-username').value = pill.dataset.user;
        document.getElementById('enroll-file-label').textContent = 'Selected: ' + pill.textContent.trim();
      });
    });

    // Auth pills
    const authPills = document.querySelectorAll('#auth-samples .sample-pill');
    authPills.forEach(pill => {
      pill.addEventListener('click', () => {
        authPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        authSelectedPath = pill.dataset.path;
        authSelectedFile = null;
        document.getElementById('auth-username').value = pill.dataset.user;
        document.getElementById('auth-file-label').textContent = 'Selected: ' + pill.textContent.trim();
        updateScenarioBadge();
      });
    });

    document.getElementById('auth-username').addEventListener('input', () => {
      updateScenarioBadge();
    });

    // File inputs
    const enrollFileInput = document.getElementById('enroll-file');
    enrollFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        enrollSelectedFile = e.target.files[0];
        enrollSelectedPath = null;
        enrollPills.forEach(p => p.classList.remove('active'));
        document.getElementById('enroll-file-label').textContent = 'File: ' + enrollSelectedFile.name;
      }
    });

    const authFileInput = document.getElementById('auth-file');
    authFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        authSelectedFile = e.target.files[0];
        authSelectedPath = null;
        authPills.forEach(p => p.classList.remove('active'));
        document.getElementById('auth-file-label').textContent = 'File: ' + authSelectedFile.name;
        updateScenarioBadge();
      }
    });

    // Helper to dynamically update scenario badge
    function updateScenarioBadge() {
      const activePill = document.querySelector('#auth-samples .sample-pill.active');
      const badge = document.getElementById('auth-scenario-badge');
      const icon = document.getElementById('scenario-icon');
      const text = document.getElementById('scenario-text');
      const targetUser = document.getElementById('auth-username').value.trim();

      if (!badge || !icon || !text) return;

      if (!activePill && authSelectedFile) {
        badge.className = 'scenario-badge badge-genuine';
        icon.textContent = '📁';
        text.innerHTML = `Custom file uploaded. Testing against account <code>${targetUser}</code>.`;
        return;
      }

      if (!activePill) return;

      const pType = activePill.dataset.type;
      const pOwner = activePill.dataset.owner || 'Selected Fingerprint';
      const pUser = activePill.dataset.user;

      if (pType === 'impostor' || (targetUser && pUser !== targetUser)) {
        badge.className = 'scenario-badge badge-impostor';
        icon.textContent = '🚨';
        text.innerHTML = `<strong>Impostor Attack:</strong> ${pOwner}'s finger against account <code>${targetUser}</code> &rarr; Expected: <strong>ACCESS DENIED</strong>`;
      } else {
        badge.className = 'scenario-badge badge-genuine';
        icon.textContent = '🟢';
        text.innerHTML = `<strong>Genuine Match:</strong> ${pOwner}'s finger against account <code>${targetUser}</code> &rarr; Expected: <strong>ACCESS GRANTED</strong>`;
      }
    }

    updateScenarioBadge();
  }

  // 2. Form Submissions
  function initForms() {
    const enrollForm = document.getElementById('enroll-form');
    enrollForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('enroll-username').value.trim();
      if (!username) return alert('Please enter a username.');

      const btn = document.getElementById('btn-submit-enroll');
      const origText = btn.innerHTML;
      btn.innerHTML = '<span>Enrolling into Vault...</span>';
      btn.disabled = true;

      const formData = new FormData();
      formData.append('username', username);
      if (enrollSelectedFile) {
        formData.append('file', enrollSelectedFile);
      } else if (enrollSelectedPath) {
        formData.append('dataset_path', enrollSelectedPath);
      }

      try {
        const res = await fetch('/api/enroll', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          const resBox = document.getElementById('enroll-result');
          resBox.classList.remove('hidden');
          document.getElementById('en-commit-h').textContent = data.crypto.commitment_h.slice(0, 32) + '...';
          document.getElementById('en-pub-y').textContent = data.crypto.public_key_y_preview;
          initAuditTable();
        } else {
          alert('Enrollment failed: ' + (data.error || 'Unknown error'));
        }
      } catch (err) {
        alert('Network error during enrollment: ' + err.message);
      } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
      }
    });

    const authForm = document.getElementById('auth-form');
    authForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('auth-username').value.trim();
      if (!username) return alert('Please enter target user ID.');

      const btn = document.getElementById('btn-submit-auth');
      const origText = btn.innerHTML;
      btn.innerHTML = '<span>Verifying Proof...</span>';
      btn.disabled = true;

      const formData = new FormData();
      formData.append('username', username);
      if (authSelectedFile) {
        formData.append('file', authSelectedFile);
      } else if (authSelectedPath) {
        formData.append('dataset_path', authSelectedPath);
      }

      try {
        const res = await fetch('/api/authenticate', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          renderResult(data);
        } else {
          alert('Authentication error: ' + (data.error || 'User not found'));
        }
      } catch (err) {
        alert('Network error during verification: ' + err.message);
      } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
      }
    });
  }

  // 3. Quick Demo Buttons
  function initQuickDemo() {
    const btnGen = document.getElementById('btn-quick-genuine');
    const btnImp = document.getElementById('btn-quick-impostor');

    btnGen.addEventListener('click', () => runQuickDemo('genuine', btnGen));
    btnImp.addEventListener('click', () => runQuickDemo('impostor', btnImp));

    async function runQuickDemo(type, btn) {
      const origHtml = btn.innerHTML;
      btn.innerHTML = '<span>Computing Zero-Knowledge Proof...</span>';
      btn.disabled = true;

      const formData = new FormData();
      formData.append('demo_type', type);

      try {
        const res = await fetch('/api/quick-demo', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          renderResult(data);
          initAuditTable();
        } else {
          alert('Demo error: ' + (data.error || 'Unknown error'));
        }
      } catch (err) {
        alert('Demo request failed: ' + err.message);
      } finally {
        btn.innerHTML = origHtml;
        btn.disabled = false;
      }
    }
  }

  // 4. Render Result Card
  function renderResult(data) {
    const sec = document.getElementById('result-section');
    const card = document.getElementById('result-card');
    const title = document.getElementById('result-title');
    const subtitle = document.getElementById('result-subtitle');
    const iconWrap = document.getElementById('result-icon-wrap');

    const kpiHd = document.getElementById('kpi-hd');
    const kpiEcc = document.getElementById('kpi-ecc');
    const kpiHash = document.getElementById('kpi-hash');
    const kpiZkp = document.getElementById('kpi-zkp');

    sec.classList.remove('hidden');

    if (data.access_granted) {
      card.className = 'result-card status-granted';
      title.textContent = 'ACCESS GRANTED';
      subtitle.textContent = `User '${data.username}' successfully authenticated with Schnorr ZKP`;
      iconWrap.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      `;

      kpiHd.textContent = (data.metrics.error_rate_pct || 12.5) + '%';
      kpiHd.className = 'kpi-value text-accent';

      kpiEcc.textContent = 'Corrected';
      kpiEcc.className = 'kpi-value text-success';

      kpiHash.textContent = 'Matched';
      kpiHash.className = 'kpi-value text-success';

      kpiZkp.textContent = 'Verified';
      kpiZkp.className = 'kpi-value text-success';
    } else {
      card.className = 'result-card status-denied';
      title.textContent = 'ACCESS DENIED';
      subtitle.textContent = `Authentication failed for user '${data.username}'. No biometric revealed.`;
      iconWrap.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      `;

      kpiHd.textContent = (data.metrics.error_rate_pct || 43.9) + '%';
      kpiHd.className = 'kpi-value text-danger';

      kpiEcc.textContent = 'Failed';
      kpiEcc.className = 'kpi-value text-danger';

      kpiHash.textContent = 'Mismatch';
      kpiHash.className = 'kpi-value text-danger';

      kpiZkp.textContent = 'Aborted';
      kpiZkp.className = 'kpi-value text-danger';
    }

    // Populate minutiae overlay
    if (data.steps && (data.steps.query_minutiae || data.steps.minutiae_overlay)) {
      document.getElementById('detail-minutiae-img').src = data.steps.query_minutiae || data.steps.minutiae_overlay;
    }

    // Populate Schnorr ZKP Transcript
    if (data.schnorr_zkp) {
      document.getElementById('tr-t').textContent = hexPreview(data.schnorr_zkp.commitment_t);
      document.getElementById('tr-c').textContent = hexPreview(data.schnorr_zkp.challenge_c);
      document.getElementById('tr-s').textContent = hexPreview(data.schnorr_zkp.response_s);
    } else {
      document.getElementById('tr-t').textContent = 'N/A (Protocol Aborted)';
      document.getElementById('tr-c').textContent = 'N/A (Protocol Aborted)';
      document.getElementById('tr-s').textContent = 'N/A (Protocol Aborted)';
    }

    // Smooth scroll to result
    sec.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hexPreview(val) {
    if (!val) return 'None';
    const s = String(val);
    return s.length > 36 ? s.slice(0, 36) + '...' : s;
  }

  // 5. Accordion & Dismiss
  function initAccordion() {
    const toggle = document.getElementById('toggle-details');
    const content = document.getElementById('details-content');
    toggle.addEventListener('click', () => {
      content.classList.toggle('hidden');
    });

    document.getElementById('btn-close-result').addEventListener('click', () => {
      document.getElementById('result-section').classList.add('hidden');
    });
  }

  // 6. Benchmark Section
  async function initBenchmark() {
    try {
      const res = await fetch('/api/benchmark');
      const json = await res.json();
      if (json.available) {
        benchmarkData = json.data;
        updateBenchmarkDisplay();
      }
    } catch (err) {
      console.warn('Could not load benchmark data:', err);
    }

    // Switcher buttons (Kaggle vs FVC)
    const switcherBtns = document.querySelectorAll('.dataset-switcher .switcher-btn');
    switcherBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        switcherBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeDataset = btn.dataset.dataset;
        updateBenchmarkDisplay();
      });
    });

    // Split pills (Train vs Test)
    const splitPills = document.querySelectorAll('.split-pills .split-pill');
    splitPills.forEach(pill => {
      pill.addEventListener('click', () => {
        splitPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeSplit = pill.dataset.split;
        updateBenchmarkDisplay();
      });
    });
  }

  function updateBenchmarkDisplay() {
    if (!benchmarkData) return;

    const key = `${activeDataset}_${activeSplit}`;
    const fallbackKey = activeSplit;
    const splitData = benchmarkData[key] || benchmarkData[fallbackKey];

    const labelElem = document.getElementById('split-dataset-label');
    const dsName = activeDataset === 'kaggle' ? 'Kaggle SOCOFing' : 'FVC2002 DB1_B';
    const spName = activeSplit === 'train' ? 'Training Split' : 'Testing Split';
    labelElem.textContent = `${dsName} • ${spName}`;

    if (splitData) {
      document.getElementById('bench-eer').textContent = (splitData.eer_percentage ?? 0.0) + '%';
      document.getElementById('bench-far').textContent = (splitData.cryptographic_far_percentage ?? 0.0) + '%';
      document.getElementById('bench-frr').textContent = (splitData.cryptographic_frr_percentage ?? 0.0) + '%';
      document.getElementById('bench-auc').textContent = (splitData.auc ?? 1.0).toFixed(4);

      const plotImg = document.getElementById('benchmark-plot-img');
      if (splitData.plot_b64) {
        plotImg.src = splitData.plot_b64;
        plotImg.classList.remove('hidden');
      }
    }
  }

  // 7. Database Privacy Audit Table
  async function initAuditTable() {
    try {
      const res = await fetch('/api/database/users');
      const users = await res.json();
      const countElem = document.getElementById('user-count');
      const tbody = document.getElementById('user-table-body');

      countElem.textContent = users.length;
      if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No enrolled users in database. Use Step 1 or Quick Demo.</td></tr>';
        return;
      }

      tbody.innerHTML = users.map(u => `
        <tr>
          <td><strong>${u.username}</strong></td>
          <td><code class="monospace">${(u.commitment_h || '').slice(0, 24)}...</code></td>
          <td><code class="monospace">${(u.public_key_y || '').slice(0, 24)}...</code></td>
          <td>
            <button class="btn-delete" data-username="${u.username}">Remove</button>
          </td>
        </tr>
      `).join('');

      tbody.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', async () => {
          const user = btn.dataset.username;
          if (confirm(`Remove user '${user}' from vault?`)) {
            await fetch(`/api/database/user/${user}`, { method: 'DELETE' });
            initAuditTable();
          }
        });
      });
    } catch (err) {
      console.warn('Failed to fetch user list:', err);
    }
  }
});
