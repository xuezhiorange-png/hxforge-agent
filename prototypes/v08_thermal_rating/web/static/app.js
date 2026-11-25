const $ = (sel) => document.querySelector(sel);

function field(name) {
  return document.querySelector(`[name="${name}"]`);
}

const presetMap = {
  "330kw": "330 kW 严格压降",
  "250kw": "250 kW 独立工况",
  "constraint_change": "约束收紧",
  infeasible: "无解工况",
};

async function loadPreset(key) {
  const res = await fetch(`/api/presets/${key}`);
  if (!res.ok) throw new Error("preset failed");
  const data = await res.json();
  for (const [k, v] of Object.entries(data)) {
    const el = field(k);
    if (el && v != null) el.value = v;
  }
  logProgress(`已载入预设：${presetMap[key]}`);
}

function logProgress(msg) {
  const box = $("#progress-log");
  const line = document.createElement("div");
  line.className = "line active";
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function clearResults() {
  $("#results-root").innerHTML =
    '<p class="disclaimer">填写左侧参数并点击「运行自动设计」。</p>';
  $("#progress-log").innerHTML = "";
}

function formPayload() {
  const names = [
    "engineering_case_id",
    "tube_fluid",
    "shell_fluid",
    "tube_inlet_temperature_k",
    "shell_inlet_temperature_k",
    "tube_inlet_pressure_pa",
    "shell_inlet_pressure_pa",
    "tube_mass_flow_kg_s",
    "shell_mass_flow_kg_s",
    "target_duty_kw",
    "max_tube_side_pressure_drop_pa",
    "max_shell_side_pressure_drop_pa",
    "max_shell_inside_diameter_m",
    "max_tube_length_m",
    "notes",
  ];
  const body = { max_candidates: 32, run_mdot_verification: true };
  for (const n of names) {
    const el = field(n);
    if (!el) continue;
    body[n] = el.value;
  }
  return body;
}

let lastReport = null;

function renderReport(report) {
  lastReport = report;
  const spec = report.design_specification;
  const rec = report.recommended_layout_key;
  const root = $("#results-root");
  if (!report.ingestion.ok) {
    root.innerHTML = `<div class="card"><h3>输入阻断</h3><ul>${report.ingestion.blockers
      .map((b) => `<li class="fail">${b.code}: ${b.detail}</li>`)
      .join("")}</ul></div>`;
    return;
  }

  let html = `<div class="card"><h3>推荐方案 · ${rec || "无合格候选"}</h3>`;
  html += `<p class="disclaimer">${report.engineering_design_status} · production_rating_validated=false</p>`;
  html += `<div class="kpi-row">
    <div class="kpi"><div class="l">结构候选</div><div class="v">${report.structural_candidates_generated}</div></div>
    <div class="kpi"><div class="l">已评估</div><div class="v">${report.structural_candidates_evaluated}</div></div>
    <div class="kpi"><div class="l">耗时(s)</div><div class="v">${report.elapsed_s ?? "—"}</div></div>
  </div></div>`;

  if (spec) {
    const g = spec.geometry;
    const th = spec.thermal_experimental_prescreen;
    const hy = spec.hydraulic_baseline;
    html += `<div class="card"><h3>结构参数</h3>
      <table>
        <tr><th>壳体内径</th><td>${g.shell_inside_diameter_m} m</td>
            <th>管数</th><td>${g.physical_tube_count}</td></tr>
        <tr><th>管外/内径</th><td>${g.tube_outer_diameter_m} / ${g.tube_inner_diameter_m} m</td>
            <th>管长</th><td>${g.tube_length_m} m</td></tr>
        <tr><th>管程</th><td>${g.tube_pass_count}</td>
            <th>管间距</th><td>${g.tube_pitch_m} m (${g.tube_layout_pattern})</td></tr>
        <tr><th>折流板</th><td>${g.baffle_count} × 间距 ${g.baffle_spacing_m} m</td>
            <th>切口</th><td>${g.baffle_cut_fraction}</td></tr>
      </table></div>`;

    html += `<div class="card"><h3>热工 / 水力</h3>
      <div class="kpi-row">
        <div class="kpi"><div class="l">Q prescreen</div><div class="v">${th.clean_q_w} W</div></div>
        <div class="kpi"><div class="l">目标</div><div class="v">${th.target_duty_w} W</div></div>
        <div class="kpi"><div class="l">面积</div><div class="v">${th.heat_transfer_area_basis_m2} m²</div></div>
        <div class="kpi"><div class="l">U·A</div><div class="v">${th.overall_ua_w_per_k} W/K</div></div>
      </div>
      <p>管 ${th.tube_inlet_k} → ${th.tube_outlet_k} K · 壳 ${th.shell_inlet_k} → ${th.shell_outlet_k} K</p>
      <p>全路径 Δp (高损): 管 ${hy.high_full_path_tube_dp_pa} Pa (余量 ${hy.tube_margin_high_pa}) ·
         壳 ${hy.high_full_path_shell_dp_pa} Pa (余量 ${hy.shell_margin_high_pa})</p></div>`;

    if (spec.nozzles_four_port?.length) {
      html += `<div class="card"><h3>四接管</h3><table><tr><th>端口</th><th>内径 m</th><th>流速 m/s</th></tr>`;
      for (const p of spec.nozzles_four_port) {
        html += `<tr><td>${p.port_id}</td><td>${p.inside_diameter_m}</td><td>${p.velocity_m_s}</td></tr>`;
      }
      html += `</table></div>`;
    }

    if (report.diagrams?.shell_cross_section_svg) {
      html += `<div class="card diagrams"><div id="d1">${report.diagrams.shell_cross_section_svg}</div>
        <div id="d2">${report.diagrams.tube_bundle_plan_svg}</div></div>`;
    }
  }

  html += `<div class="card"><h3>候选对比</h3><table>
    <tr><th>布局</th><th>Q W</th><th>热工</th><th>水力</th><th>联合</th><th>阻断</th></tr>`;
  for (const r of report.candidate_records) {
    const cls = r.engineering_joint_pass ? "pass" : "fail";
    html += `<tr><td>${r.layout_key}</td><td>${r.thermal_q_w ?? "—"}</td>
      <td class="${r.thermal_pass ? "pass" : "fail"}">${r.thermal_pass}</td>
      <td class="${r.hydraulic_all_tiers_pass ? "pass" : "fail"}">${r.hydraulic_all_tiers_pass}</td>
      <td class="${cls}">${r.engineering_joint_pass}</td>
      <td>${(r.block_reasons || []).join(", ") || "—"}</td></tr>`;
  }
  html += `</table></div>`;

  if (report.mdot_verdicts?.length) {
    html += `<div class="card"><h3>变化工况验证</h3><table>
      <tr><th>工况</th><th>Q</th><th>联合通过</th><th>原因</th></tr>`;
    for (const v of report.mdot_verdicts) {
      html += `<tr><td>${v.scenario_key}</td><td>${v.thermal_q_w ?? "—"}</td>
        <td class="${v.engineering_joint_pass ? "pass" : "fail"}">${v.engineering_joint_pass}</td>
        <td>${(v.joint_block_reasons || []).join(", ") || "—"}</td></tr>`;
    }
    html += `</table></div>`;
  }

  root.innerHTML = html;
}

async function runDesign() {
  clearResults();
  $("#btn-run").disabled = true;
  logProgress("提交计算请求…");
  const body = formPayload();
  try {
    const res = await fetch("/api/design/run-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const chunk of parts) {
        const lines = chunk.split("\n");
        let event = "message";
        let data = "";
        for (const line of lines) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          if (line.startsWith("data:")) data = line.slice(5).trim();
        }
        if (!data) continue;
        const payload = JSON.parse(data);
        if (event === "progress") {
          logProgress(`${payload.stage}: ${payload.message || ""}`);
        } else if (event === "result") {
          renderReport(payload.report);
          logProgress("计算完成");
        }
      }
    }
  } catch (e) {
    logProgress(`错误: ${e.message}`);
  } finally {
    $("#btn-run").disabled = false;
  }
}

function exportJson() {
  if (!lastReport) return alert("请先运行计算");
  const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `hxforge_design_${lastReport.engineering_case_id || "report"}.json`;
  a.click();
}

function exportMd() {
  if (!lastReport?.markdown_report) return alert("无报告内容");
  const blob = new Blob([lastReport.markdown_report], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `hxforge_design_${lastReport.engineering_case_id || "report"}.md`;
  a.click();
}

document.querySelectorAll("[data-preset]").forEach((btn) => {
  btn.addEventListener("click", () => loadPreset(btn.dataset.preset));
});
$("#btn-run").addEventListener("click", runDesign);
$("#btn-export-json").addEventListener("click", exportJson);
$("#btn-export-md").addEventListener("click", exportMd);