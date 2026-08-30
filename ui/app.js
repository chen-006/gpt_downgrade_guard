const state = {
  current: null,
  groups: [],
  timer: null,
}

const $ = (id) => document.getElementById(id)

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function fmtTime(value) {
  if (!value) return "-"
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  return dt.toLocaleString("zh-CN")
}

function resultLabel(result) {
  return result || "证据不足"
}

function renderHistory(history) {
  const items = Array.isArray(history) ? history.slice(-100) : []
  const slots = Array.from({ length: 100 }, (_, index) => {
    const offset = items.length - 100 + index
    return offset >= 0 ? items[offset] : null
  })
  const bars = slots.map((item) => {
    if (!item) return `<span class="bar empty" title="无记录"></span>`
    const red = item.degraded ? "red" : "green"
    return `<span class="bar ${red}" title="${esc(item.ts || "")} · ${esc(item.result || "")}"></span>`
  }).join("")
  return `<div class="history-bars">${bars}</div>`
}

function renderProbeRows(rows) {
  const items = Array.isArray(rows) ? rows : []
  if (!items.length) return `<div class="muted">没有可显示的探针结果。</div>`
  return items.map((row) => {
    const samples = (row.samples || []).join(" / ")
    const matches = row.matches || {}
    return `
      <div class="probe-card">
        <div class="probe-head">
          <strong>${esc(row.probe_id)}</strong>
          <span>${row.complete ? "已完成" : "未完成"}</span>
        </div>
        <div class="probe-body">
          <div>样本：${esc(samples || "-")}</div>
          <div>匹配：Sol ${(Number(matches["gpt-5.6-sol"] || 0) * 100).toFixed(2)}% · Terra ${(Number(matches["gpt-5.6-terra"] || 0) * 100).toFixed(2)}% · Luna ${(Number(matches["gpt-5.6-luna"] || 0) * 100).toFixed(2)}%</div>
        </div>
      </div>
    `
  }).join("")
}

function renderAccounts(accounts) {
  const tbody = $("accounts-body")
  const items = Array.isArray(accounts) ? accounts : []
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">暂无账号。</td></tr>`
    return
  }
  tbody.innerHTML = items.map((account) => {
    const groups = Array.isArray(account.group_names) ? account.group_names.filter(Boolean).join("、") : ""
    const bars = renderHistory(account.history || [])
    const probeRows = renderProbeRows(account.last_probe_rows || [])
    return `
      <tr>
        <td>
          <div class="account-name">${esc(account.account_name || account.account_id)}</div>
          <div class="muted">#${esc(account.account_id)} · ${esc(account.platform || "")}</div>
        </td>
        <td>${esc(groups || "—")}</td>
        <td>${esc(resultLabel(account.last_result))}</td>
        <td><span class="pill ${account.last_degraded ? "bad" : "good"}">${account.last_degraded ? "降智" : "未降智"}</span></td>
        <td>${esc(fmtTime(account.last_checked_at))}</td>
        <td>
          <details class="row-details">
            <summary>看探针</summary>
            ${probeRows}
          </details>
        </td>
        <td>
          <details class="row-details">
            <summary>看历史</summary>
            ${bars}
          </details>
        </td>
      </tr>
    `
  }).join("")
}

function renderGroups(groups, config) {
  const items = Array.isArray(groups) ? groups : (groups?.items || [])
  state.groups = items
  const options = ['<option value="0">请选择分组</option>']
  for (const group of items) {
    const id = Number(group.id || 0)
    const name = String(group.name || `分组 ${id}`)
    options.push(`<option value="${id}">${esc(name)} #${id}</option>`)
  }
  const html = options.join("")
  $("cfg-group-a").innerHTML = html
  $("cfg-group-b").innerHTML = html
  const groupAId = Number(config?.group_a_id || 0)
  const groupBId = Number(config?.group_b_id || 0)
  $("cfg-group-a").value = String(groupAId)
  $("cfg-group-b").value = String(groupBId)
  const groupA = items.find((item) => Number(item.id || 0) === groupAId)
  const groupB = items.find((item) => Number(item.id || 0) === groupBId)
  $("group-a-name").textContent = groupA ? `${groupA.name || "-"} #${groupA.id}` : "-"
  $("group-b-name").textContent = groupB ? `${groupB.name || "-"} #${groupB.id}` : "-"
}

function renderConfig(config) {
  $("cfg-base-url").value = config?.sub2api_base_url || ""
  $("cfg-interval").value = config?.interval_seconds || 180
  $("cfg-rule").value = config?.downgrade_rule || "严格"
  $("runtime-badge").textContent = config?.admin_token_set ? "已连接" : "未填令牌"
}

async function refresh() {
  const [statusResponse, groupsResponse] = await Promise.all([
    fetch("/api/status", { cache: "no-store" }),
    fetch("/api/groups", { cache: "no-store" }),
  ])
  const data = await statusResponse.json()
  const groups = await groupsResponse.json()
  state.current = data
  $("status-running").textContent = data.running ? "运行中" : (data.paused ? "已暂停" : "空闲")
  $("status-next").textContent = fmtTime(data.next_run_at)
  $("status-a-count").textContent = data.group_a_count ?? 0
  $("status-b-count").textContent = data.group_b_count ?? 0
  $("status-checked").textContent = data.checked_count ?? 0
  $("status-error").textContent = data.last_error || ""
  renderConfig(data.config || {})
  renderGroups(groups, data.config || {})
  renderAccounts(data.accounts || [])
}

async function postJSON(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  })
  return response.json()
}

function collectConfig() {
  const payload = {
    sub2api_base_url: $("cfg-base-url").value.trim(),
    interval_seconds: Number($("cfg-interval").value || 180),
    downgrade_rule: $("cfg-rule").value,
    group_a_id: Number($("cfg-group-a").value || 0),
    group_b_id: Number($("cfg-group-b").value || 0),
    listen: state.current?.config?.listen || "127.0.0.1:8787",
  }
  const token = $("cfg-admin-token").value.trim()
  if (token) payload.admin_token = token
  return payload
}

async function wire() {
  $("btn-save").addEventListener("click", async () => {
    await postJSON("/api/config", collectConfig())
    await refresh()
  })
  $("btn-run").addEventListener("click", async () => {
    await postJSON("/api/run-now", {})
    await refresh()
  })
  $("btn-pause").addEventListener("click", async () => {
    await postJSON("/api/pause", {})
    await refresh()
  })
  $("btn-resume").addEventListener("click", async () => {
    await postJSON("/api/resume", {})
    await refresh()
  })
  $("btn-token-auto").addEventListener("click", async () => {
    const result = await postJSON("/api/token/auto", {})
    if (!result.ok) {
      $("status-error").textContent = result.error || "自动获取失败"
      return
    }
    $("cfg-admin-token").value = ""
    await refresh()
  })
  await refresh()
  if (state.timer) clearInterval(state.timer)
  state.timer = setInterval(refresh, 5000)
}

wire().catch((error) => {
  $("status-error").textContent = error?.message || String(error)
})
