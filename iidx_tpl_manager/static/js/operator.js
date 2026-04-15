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
      fetch(monitorForm.action, {
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
})();
