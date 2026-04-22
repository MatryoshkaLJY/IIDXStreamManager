(function () {
  const socket = io();

  const banner = document.getElementById('obs-banner');
  const bannerText = document.getElementById('obs-banner-text');
  const statusLabel = document.getElementById('obs-status-label');
  const sceneButtons = document.querySelectorAll('.scene-btn');
  const configForm = document.getElementById('obs-config-form');
  const monitorForm = document.getElementById('monitor-control-form');
  const monitorBtn = document.getElementById('monitor-toggle-btn');
  const monitorAction = document.getElementById('monitor-action');
  const monitorStatusLabel = document.getElementById('monitor-status-label');

  function setMonitoringUI(active) {
    if (monitorStatusLabel) {
      monitorStatusLabel.textContent = active ? 'Monitoring: Active' : 'Monitoring: Stopped';
      monitorStatusLabel.className = active ? 'status-ok' : 'status-warning';
    }
    if (monitorBtn) {
      monitorBtn.textContent = active ? 'Stop Monitoring' : 'Start Monitoring';
    }
    if (monitorAction) {
      monitorAction.value = active ? 'stop' : 'start';
    }
  }

  function setSceneButtonsDisabled(disabled) {
    sceneButtons.forEach((btn) => {
      btn.disabled = disabled;
    });
  }

  function ensureBannerButton(label) {
    if (!bannerText) return;
    let btn = document.getElementById('obs-reconnect-btn');
    if (!btn) {
      btn = document.createElement('button');
      btn.id = 'obs-reconnect-btn';
      btn.type = 'button';
      bannerText.appendChild(btn);
    }
    btn.textContent = label;
  }

  socket.on('obs_status', (data) => {
    const connected = !!data.connected;
    const scenesValid = !!data.scenes_valid;

    if (connected && scenesValid) {
      if (banner) banner.style.display = 'none';
      if (statusLabel) {
        statusLabel.textContent = 'OBS: Connected';
        statusLabel.className = 'status-ok';
      }
      setSceneButtonsDisabled(false);
    } else if (connected && !scenesValid) {
      if (banner) banner.style.display = 'block';
      const missing = Array.isArray(data.missing_scenes) ? data.missing_scenes : [];
      if (bannerText) {
        bannerText.textContent = `OBS scenes missing: ${missing.join(', ')}. Please add them in OBS, then click Retry Validation.`;
        bannerText.className = 'status-error';
        ensureBannerButton('Retry Validation');
      }
      if (statusLabel) {
        statusLabel.textContent = 'OBS: Disconnected';
        statusLabel.className = 'status-error';
      }
      setSceneButtonsDisabled(true);
    } else {
      if (banner) banner.style.display = 'block';
      if (bannerText) {
        bannerText.textContent = 'OBS disconnected. Scene switching and auto-transitions are paused.';
        bannerText.className = 'status-error';
        ensureBannerButton('Reconnect to OBS');
      }
      if (statusLabel) {
        statusLabel.textContent = 'OBS: Disconnected';
        statusLabel.className = 'status-error';
      }
      setSceneButtonsDisabled(true);
    }
  });

  if (banner) {
    banner.addEventListener('click', (event) => {
      if (event.target && event.target.tagName === 'BUTTON') {
        const label = event.target.textContent || '';
        if (label === 'Reconnect to OBS' || label === 'Retry Validation') {
          socket.emit('obs_reconnect');
        }
      }
    });
  }

  socket.on('monitoring_status', (data) => {
    setMonitoringUI(!!data.active);
  });

  socket.on('cabinet_update', (data) => {
    // Console logging for Phase 5 backend verification (D-01 defers monitor page)
    console.log('cabinet_update', data);
  });

  if (configForm) {
    configForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const formData = new FormData(configForm);
      const payload = {
        host: formData.get('host') || '',
        port: parseInt(formData.get('port') || '0', 10),
        password: formData.get('password') || '',
      };
      fetch(configForm.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then((resp) => {
          if (!resp.ok) {
            console.error('OBS config save failed', resp.status);
          }
        })
        .catch((err) => {
          console.error('OBS config save error', err);
        });
    });
  }

  if (monitorForm) {
    monitorForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const formData = new FormData(monitorForm);
      const payload = {
        action: formData.get('action') || 'start',
      };
      fetch(monitorForm.getAttribute('action'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then((resp) => resp.json())
        .then((data) => {
          if (data && typeof data.active === 'boolean') {
            setMonitoringUI(data.active);
          }
        })
        .catch((err) => {
          console.error('Monitor control error', err);
        });
    });
  }

  // Score review panel
  const reviewPanel = document.getElementById('score-review-panel');
  const reviewRows = document.getElementById('score-review-rows');
  const reviewToggle = document.getElementById('score-review-toggle');
  const confirmBtn = document.getElementById('confirm-score-btn');
  const countdownEl = document.getElementById('score-countdown');
  const delayInput = document.getElementById('scoreboard-delay');
  const reviewError = document.getElementById('score-review-error');
  const reviewEmpty = document.getElementById('score-review-empty');

  let pendingScores = window.initialPendingScores || {};
  let scoreboardDelay = window.initialScoreboardDelay || 5.0;
  let countdownInterval = null;
  let isCollapsed = false;

  function renderReviewPanel() {
    if (!reviewRows) return;
    reviewRows.innerHTML = '';
    const machineIds = ['IIDX#1', 'IIDX#2', 'IIDX#3', 'IIDX#4'];
    const hasAny = machineIds.some((id) => pendingScores[id]);

    if (!hasAny) {
      if (reviewEmpty) reviewEmpty.style.display = 'block';
      if (confirmBtn) {
        confirmBtn.style.display = 'none';
        confirmBtn.disabled = true;
      }
      if (reviewError) reviewError.style.display = 'none';
      return;
    }

    if (reviewEmpty) reviewEmpty.style.display = 'none';
    if (confirmBtn) confirmBtn.style.display = 'inline-block';

    let hasInvalid = false;
    machineIds.forEach((machineId) => {
      const data = pendingScores[machineId];
      if (!data) return;
      const scores = data.scores || {};
      const p1Score = scores['1p_score'] != null ? String(scores['1p_score']) : '';
      const p2Score = scores['2p_score'] != null ? String(scores['2p_score']) : '';
      const p1Valid = scores['1p_valid'];
      const p2Valid = scores['2p_valid'];
      if (!p1Valid || !p2Valid) hasInvalid = true;

      const row = document.createElement('div');
      row.className = 'score-review-row';
      row.innerHTML = `
        <div class="label">${machineId}</div>
        <div class="label"></div>
        <div class="score-cell ${p1Valid ? '' : 'score-invalid'}" data-machine-id="${machineId}" data-side="1p">${p1Score}</div>
        <div class="score-cell ${p2Valid ? '' : 'score-invalid'}" data-machine-id="${machineId}" data-side="2p">${p2Score}</div>
        <div class="score-validity ${(!p1Valid || !p2Valid) ? 'invalid' : ''}"></div>
      `;
      reviewRows.appendChild(row);
    });

    if (reviewError) reviewError.style.display = hasInvalid ? 'block' : 'none';
    if (confirmBtn) confirmBtn.disabled = hasInvalid;
  }

  // Inline editing
  if (reviewRows) {
    reviewRows.addEventListener('click', (event) => {
      const cell = event.target.closest('.score-cell');
      if (!cell) return;
      const machineId = cell.dataset.machineId;
      const side = cell.dataset.side;
      const currentValue = cell.textContent.trim();

      const input = document.createElement('input');
      input.type = 'number';
      input.value = currentValue;
      input.style.width = '100%';
      input.style.background = 'transparent';
      input.style.border = 'none';
      input.style.color = 'inherit';
      input.style.textAlign = 'right';
      input.style.fontSize = 'inherit';
      input.style.outline = 'none';

      cell.innerHTML = '';
      cell.appendChild(input);
      input.focus();

      function commitEdit() {
        const newValue = input.value.trim();
        const numValue = newValue === '' ? 0 : parseInt(newValue, 10);
        if (pendingScores[machineId] && pendingScores[machineId].scores) {
          pendingScores[machineId].scores[side + '_score'] = numValue;
        }
        renderReviewPanel();
      }

      input.addEventListener('blur', commitEdit);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          input.blur();
        }
      });
    });
  }

  // Toggle collapse
  if (reviewToggle && reviewRows) {
    reviewToggle.addEventListener('click', () => {
      isCollapsed = !isCollapsed;
      reviewRows.style.display = isCollapsed ? 'none' : 'block';
      if (confirmBtn) confirmBtn.style.display = isCollapsed ? 'none' : 'inline-block';
      if (countdownEl) countdownEl.style.display = 'none';
      reviewToggle.textContent = isCollapsed ? 'Show' : 'Hide';
    });
  }

  // Scoreboard delay save
  function saveDelay() {
    const value = parseFloat(delayInput.value);
    if (Number.isNaN(value)) return;
    fetch('/api/scoreboard_delay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delay: value }),
    }).catch((err) => {
      console.error('Scoreboard delay save error', err);
    });
  }

  if (delayInput) {
    delayInput.addEventListener('blur', saveDelay);
    delayInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        delayInput.blur();
      }
    });
  }

  // Confirm & Push
  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      fetch('/confirm_score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
        .then((resp) => resp.json())
        .then((data) => {
          if (data && data.success) {
            if (countdownEl) {
              countdownEl.style.display = 'block';
              let remaining = Math.ceil(scoreboardDelay);
              countdownEl.textContent = `Pushing in ${remaining}s...`;
              countdownInterval = setInterval(() => {
                remaining -= 1;
                if (remaining > 0) {
                  countdownEl.textContent = `Pushing in ${remaining}s...`;
                } else {
                  countdownEl.textContent = 'Pushing scores...';
                  countdownEl.classList.add('pulsing');
                  clearInterval(countdownInterval);
                  countdownInterval = null;
                  setTimeout(() => {
                    countdownEl.style.display = 'none';
                    countdownEl.classList.remove('pulsing');
                  }, 1000);
                }
              }, 1000);
            }
          } else {
            console.error('Confirm score failed', data && data.error);
          }
        })
        .catch((err) => {
          console.error('Confirm score error', err);
        });
    });
  }

  // SocketIO integration
  socket.on('cabinet_update', (data) => {
    console.log('cabinet_update', data);
    if (data.state === 'score' && data.score_validation_pending) {
      pendingScores[data.machine_id] = {
        machine_id: data.machine_id,
        scores: data.scores || {},
      };
      renderReviewPanel();
    } else if (data.state !== 'score' && pendingScores[data.machine_id]) {
      delete pendingScores[data.machine_id];
      renderReviewPanel();
    }
  });

  socket.on('scores_pushed', () => {
    pendingScores = {};
    renderReviewPanel();
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
    if (countdownEl) {
      countdownEl.style.display = 'none';
      countdownEl.classList.remove('pulsing');
    }
  });

  socket.on('scoreboard_delay_updated', (data) => {
    if (typeof data.delay === 'number') {
      scoreboardDelay = data.delay;
      if (delayInput) delayInput.value = scoreboardDelay;
    }
  });

  // Initial render
  renderReviewPanel();
})();
