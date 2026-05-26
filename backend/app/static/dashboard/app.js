/**
 * Dashboard bác sĩ — WebSocket telemetry + REST điều khiển lực
 */
(function () {
  const MAX_POINTS = 120;
  const WS_RECONNECT_MS = 2500;

  const els = {
    patientId: document.getElementById("patientId"),
    kpiConnection: document.querySelector("#kpiConnection .status-pill"),
    kpiMaxAngle: document.getElementById("kpiMaxAngle"),
    kpiRom: document.getElementById("kpiRom"),
    kpiSafety: document.getElementById("kpiSafety"),
    kpiAlertCard: document.getElementById("kpiAlert"),
    emergencyBanner: document.getElementById("emergencyBanner"),
    forceSlider: document.getElementById("forceSlider"),
    forceValue: document.getElementById("forceValue"),
    forceDirection: document.getElementById("forceDirection"),
    btnApply: document.getElementById("btnApply"),
    btnRelease: document.getElementById("btnRelease"),
    controlStatus: document.getElementById("controlStatus"),
  };

  const labels = [];
  const angleData = [];
  const flexForceData = [];
  const appliedForceData = [];
  let sessionPeak = 0;
  let ws = null;
  let wsTimer = null;

  const chartCommon = {
    responsive: true,
    animation: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      x: {
        display: true,
        ticks: { maxTicksLimit: 8, font: { size: 10 } },
      },
      y: {
        beginAtZero: true,
        ticks: { font: { size: 10 } },
      },
    },
    plugins: { legend: { display: false } },
  };

  const angleChart = new Chart(document.getElementById("angleChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Góc khớp",
          data: angleData,
          borderColor: "#0d7ea8",
          backgroundColor: "rgba(13, 126, 168, 0.08)",
          fill: true,
          tension: 0.25,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: { ...chartCommon, scales: { ...chartCommon.scales, y: { ...chartCommon.scales.y, title: { display: true, text: "°" } } } },
  });

  const forceChart = new Chart(document.getElementById("forceChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Flex proxy",
          data: flexForceData,
          borderColor: "#2bb896",
          tension: 0.25,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Lực cản",
          data: appliedForceData,
          borderColor: "#e65100",
          tension: 0.25,
          pointRadius: 0,
          borderWidth: 2,
          borderDash: [4, 2],
        },
      ],
    },
    options: {
      ...chartCommon,
      plugins: { legend: { display: true, position: "bottom", labels: { boxWidth: 12, font: { size: 10 } } } },
      scales: { ...chartCommon.scales, y: { ...chartCommon.scales.y, max: 255, title: { display: true, text: "0–255" } } },
    },
  });

  function apiBase() {
    return window.location.origin;
  }

  function wsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/ws/dashboard`;
  }

  function pushPoint(label, angle, flexForce, applied) {
    labels.push(label);
    angleData.push(angle);
    flexForceData.push(flexForce);
    appliedForceData.push(applied);
    if (labels.length > MAX_POINTS) {
      labels.shift();
      angleData.shift();
      flexForceData.shift();
      appliedForceData.shift();
    }
    angleChart.update("none");
    forceChart.update("none");
  }

  function setConnected(on) {
    els.kpiConnection.textContent = on ? "Connected" : "Disconnected";
    els.kpiConnection.dataset.state = on ? "on" : "off";
  }

  function setSafety(text, danger) {
    els.kpiSafety.textContent = text;
    els.kpiAlertCard.classList.toggle("danger", danger);
  }

  async function fetchDailyMax() {
    const pid = els.patientId.value.trim() || "P001";
    try {
      const res = await fetch(`${apiBase()}/api/dashboard/summary/${encodeURIComponent(pid)}`);
      if (!res.ok) return;
      const data = await res.json();
      const max = data.max_angle_today_deg ?? 0;
      els.kpiMaxAngle.textContent = `${max.toFixed(1)} °`;
      sessionPeak = Math.max(sessionPeak, max);
    } catch (_) {
      /* ignore */
    }
  }

  function handleTelemetry(msg) {
    const t = msg.timestamp ?? Date.now();
    const label = new Date(t).toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    const angle = msg.angle ?? msg.joint_angle ?? 0;
    const flex = msg.flex_force_proxy ?? (msg.raw_flex != null ? (msg.raw_flex * 255) / 4095 : 0);
    const applied = msg.applied_force_level ?? 0;

    sessionPeak = Math.max(sessionPeak, angle, msg.max_angle_deg ?? 0);
    els.kpiMaxAngle.textContent = `${sessionPeak.toFixed(1)} °`;
    els.kpiRom.textContent = `${(msg.rom_session_deg ?? 0).toFixed(1)} ° · ${(msg.completion_percent ?? 0).toFixed(0)} %`;

    pushPoint(label, angle, flex, applied);
  }

  function handleStatus(msg) {
    setConnected(!!msg.hardware_connected);
  }

  function handleAlert(msg) {
    if (msg.status === "EMERGENCY_STOP") {
      els.emergencyBanner.classList.remove("hidden");
      setSafety("EMERGENCY STOP", true);
    }
  }

  function connectWs() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    ws = new WebSocket(wsUrl());

    ws.onopen = () => {
      setConnected(false);
      els.controlStatus.textContent = "Dashboard WS đã kết nối server";
      els.controlStatus.className = "control-status ok";
      fetchDailyMax();
    };

    ws.onmessage = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      const type = msg.type;
      if (type === "telemetry" || msg.angle != null) {
        handleTelemetry(msg);
      } else if (type === "status") {
        handleStatus(msg);
      } else if (type === "alert" || msg.status === "EMERGENCY_STOP") {
        handleAlert(msg);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      els.controlStatus.textContent = "Mất kết nối WS — thử lại…";
      els.controlStatus.className = "control-status err";
      wsTimer = setTimeout(connectWs, WS_RECONNECT_MS);
    };

    ws.onerror = () => ws.close();
  }

  async function sendForce(level, direction) {
    const body = { force_level: level, direction: direction };
    els.controlStatus.textContent = "Đang gửi lệnh…";
    els.controlStatus.className = "control-status";

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "set_force", ...body }));
    }

    try {
      const res = await fetch(`${apiBase()}/api/control/force`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || res.statusText);
      }
      els.controlStatus.textContent = `Đã áp dụng lực cản: ${level} (chiều ${direction})`;
      els.controlStatus.className = "control-status ok";
    } catch (e) {
      els.controlStatus.textContent = e.message || "Gửi lệnh thất bại";
      els.controlStatus.className = "control-status err";
    }
  }

  els.forceSlider.addEventListener("input", () => {
    els.forceValue.textContent = els.forceSlider.value;
  });

  els.btnApply.addEventListener("click", () => {
    const level = parseInt(els.forceSlider.value, 10);
    const direction = parseInt(els.forceDirection.value, 10);
    sendForce(level, direction);
  });

  els.btnRelease.addEventListener("click", () => {
    els.forceSlider.value = "0";
    els.forceValue.textContent = "0";
    sendForce(0, 0);
  });

  els.patientId.addEventListener("change", fetchDailyMax);

  connectWs();
  setInterval(fetchDailyMax, 30000);
})();
