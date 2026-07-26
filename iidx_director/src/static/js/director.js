/* 共享：SocketIO 连接、导航徽标、toast、postJSON。页面脚本挂在 window.onSessionUpdate。 */
(function () {
  const socket = io();
  window.directorSocket = socket;
  window.lastSnapshot = null;

  const PHASE_LABELS = {
    IDLE: '空闲', PREP: '回合准备', LIVE: '比赛进行中',
    REVIEW: '待确认比分', PUSHED: '已写入', MATCH_END: '比赛结束',
  };

  function setBadge(id, text, on) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('on', !!on);
  }

  function renderNav(snap) {
    setBadge('badge-obs', snap.obs_connected ? 'OBS ✓' : 'OBS ✗', snap.obs_connected);
    setBadge('badge-monitor', snap.monitor_running ? '监控 ✓' : '监控 ✗', snap.monitor_running);
    setBadge('badge-mode', snap.mode === 'team' ? '团队赛' : '个人淘汰赛', true);
    const phase = snap.session ? snap.session.phase : 'IDLE';
    setBadge('badge-phase', PHASE_LABELS[phase] || phase, phase !== 'IDLE');
    renderSceneActions(snap);
    renderPending(snap.pending);
  }

  function renderPending(pending) {
    const bar = document.getElementById('pending-bar');
    if (!bar) return;
    bar.classList.toggle('hidden', !pending);
    if (!pending) return;
    document.getElementById('pending-label').textContent =
      `待应用：${pending.scene} / ${pending.template}（${pending.status}）` +
      (pending.error ? `：${pending.error}` : '');
    const confirmButton = document.getElementById('pending-confirm');
    confirmButton.textContent = pending.status === 'failed' ? '重试应用' : '确认应用';
    confirmButton.onclick = async () => {
      const result = await window.postJSON('/api/scene/pending/confirm', { id: pending.id });
      if (result.success) window.toast('待应用操作已完成');
    };
    document.getElementById('pending-cancel').onclick = async () => {
      const result = await window.postJSON('/api/scene/pending/cancel', { id: pending.id });
      if (result.success) window.toast('已取消待应用操作');
    };
  }

  const SCENE_LABELS = {
    live: '现场',
    team_sp_1v1: 'SP 团队 1V1', team_sp_2v2: 'SP 团队 2V2',
    team_dp_1v1: 'DP 团队 1V1', team_dp_2v2: 'DP 团队 2V2',
    individual_sp: 'SP 个人赛', individual_dp: 'DP 个人赛',
    scoreboard: '计分板',
  };

  function renderSceneActions(snap) {
    const area = document.getElementById('scene-actions');
    if (!area) return;
    area.innerHTML = '';
    const scenes = snap.scenes || {};
    const seen = new Set();
    for (const [key, scene] of Object.entries(scenes)) {
      if (!scene || seen.has(scene)) continue;
      seen.add(scene);
      const button = document.createElement('button');
      button.className = 'scene-button';
      button.textContent = SCENE_LABELS[key] || key;
      button.title = scene;
      button.disabled = !snap.obs_connected;
      button.onclick = () => switchScene(key, button);
      area.appendChild(button);
    }
  }

  async function switchScene(scene, button) {
    if (button) button.disabled = true;
    try {
      const resp = await window.postJSON('/api/obs/switch', { scene });
      if (resp.success) window.toast(`已创建待应用场景：${button ? button.textContent : '目标场景'}`);
    } finally {
      if (button) button.disabled = !window.lastSnapshot || !window.lastSnapshot.obs_connected;
    }
  }

  socket.on('session_update', (snap) => {
    window.lastSnapshot = snap;
    renderNav(snap);
    if (window.onSessionUpdate) window.onSessionUpdate(snap);
  });
  socket.on('cabinet_update', (data) => {
    if (window.onCabinetUpdate) window.onCabinetUpdate(data);
  });

  window.toast = function (msg, isError) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'show' + (isError ? ' error' : '');
    setTimeout(() => { el.className = ''; }, 3500);
  };

  window.postJSON = async function (url, body) {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const data = await resp.json();
    if (!data.success) toast(data.error || '操作失败', true);
    else if (data.warnings && data.warnings.length) toast('警告: ' + data.warnings.join('；'), true);
    return data;
  };

  window.setButtonBusy = function (button, busy, text) {
    if (!button) return;
    if (busy) {
      button.dataset.originalText = button.textContent;
      button.textContent = text || '处理中…';
      button.disabled = true;
    } else {
      button.textContent = button.dataset.originalText || button.textContent;
      button.disabled = false;
    }
  };

  window.esc = function (s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  };

  // 高亮当前导航项
  const page = document.body.dataset.page;
  document.querySelectorAll('nav a').forEach(a => {
    if (a.dataset.nav === page) a.classList.add('active');
  });
})();
