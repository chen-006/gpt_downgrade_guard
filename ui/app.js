const state = {
  current: null,
  groups: [],
  timer: null,
  saveTimer: null,
  dirty: false,
  saving: false,
  editVersion: 0,
  configSignature: "",
  accountsSignature: "",
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
  const items = Array.isArray(history) ? history.slice(-100).reverse() : []
  const slots = Array.from({ length: 100 }, (_, index) => items[index] || null)
  const bars = slots.map((item) => {
    if (!item) return `<span class="bar empty" title="无记录"></span>`
    const requestError = Boolean(item.request_error)
    const color = requestError ? "network" : (item.degraded ? "red" : "green")
    const label = item.result || ""
    return `<span class="bar ${color}" title="${esc(item.ts || "")} · ${esc(label)}"></span>`
  }).join("")
  return `<div class="history-bars">${bars}</div>`
}

function renderProbeSummary(account) {
  const matches = account.last_scores || {}
  return `
    <div class="probe-card">
      <div class="probe-body">
        <div>请求数：${Number(account.last_request_count || 0)} · 成功数：${Number(account.last_success_count || 0)}</div>
        <div>Sol ${(Number(matches["gpt-5.6-sol"] || 0) * 100).toFixed(2)}% · Terra ${(Number(matches["gpt-5.6-terra"] || 0) * 100).toFixed(2)}% · Luna ${(Number(matches["gpt-5.6-luna"] || 0) * 100).toFixed(2)}%</div>
      </div>
    </div>
  `
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
    const probeSummary = renderProbeSummary(account)
    const requestError = Boolean(account.last_request_error)
    const result = resultLabel(account.last_result)
    const pillClass = requestError ? "network" : (account.last_degraded ? "bad" : "good")
    const pillLabel = requestError ? result : (account.last_degraded ? "降智" : "未降智")
    return `
      <tr>
        <td>
          <div class="account-name">${esc(account.account_name || account.account_id)}</div>
          <div class="muted">#${esc(account.account_id)} · ${esc(account.platform || "")}</div>
        </td>
        <td>${esc(groups || "—")}</td>
        <td>${esc(result)}</td>
        <td><span class="pill ${pillClass}">${pillLabel}</span></td>
        <td>${esc(fmtTime(account.last_checked_at))}</td>
        <td>
          <details class="row-details">
            <summary>探针详情</summary>
            ${probeSummary}
          </details>
        </td>
        <td>${bars}</td>
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
  state.groups = Array.isArray(groups) ? groups : (groups?.items || [])
  state.current = data
  const scrollX = window.scrollX
  const scrollY = window.scrollY
  let rendered = false
  $("status-running").textContent = data.running ? "运行中" : (data.paused ? "已暂停" : "空闲")
  $("status-next").textContent = fmtTime(data.next_run_at)
  $("status-a-count").textContent = data.group_a_count ?? 0
  $("status-b-count").textContent = data.group_b_count ?? 0
  $("status-checked").textContent = data.checked_count ?? 0
  $("status-error").textContent = data.last_error || ""
  const configSignature = JSON.stringify([data.config || {}, state.groups])
  if (!state.dirty && !state.saving && configSignature !== state.configSignature) {
    renderConfig(data.config || {})
    renderGroups(state.groups, data.config || {})
    state.configSignature = configSignature
    rendered = true
  }
  const accounts = data.accounts || []
  const accountsSignature = JSON.stringify(accounts)
  if (accountsSignature !== state.accountsSignature) {
    renderAccounts(accounts)
    state.accountsSignature = accountsSignature
    rendered = true
  }
  if (rendered) requestAnimationFrame(() => window.scrollTo(scrollX, scrollY))
}

async function postJSON(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  })
  const result = await response.json()
  if (!response.ok || result.ok === false) {
    throw new Error(result.error || `请求失败：${response.status}`)
  }
  return result
}

function collectConfig(includeToken = false) {
  const payload = {
    sub2api_base_url: $("cfg-base-url").value.trim(),
    interval_seconds: Number($("cfg-interval").value || 180),
    downgrade_rule: $("cfg-rule").value,
    group_a_id: Number($("cfg-group-a").value || 0),
    group_b_id: Number($("cfg-group-b").value || 0),
    listen: state.current?.config?.listen || "127.0.0.1:8787",
  }
  if (includeToken) {
    const token = $("cfg-admin-token").value.trim()
    if (token) payload.admin_token = token
  }
  return payload
}

function scheduleSave() {
  state.dirty = true
  state.editVersion += 1
  if (state.saveTimer) clearTimeout(state.saveTimer)
  state.saveTimer = setTimeout(saveConfig, 400)
}

async function saveConfig(includeToken = false) {
  if (state.saving) return
  const version = state.editVersion
  state.saving = true
  try {
    const result = await postJSON("/api/config", collectConfig(includeToken))
    if (version === state.editVersion) {
      state.dirty = false
      renderConfig(result.config || {})
      renderGroups(state.groups, result.config || {})
      state.configSignature = JSON.stringify([result.config || {}, state.groups])
      $("cfg-admin-token").value = ""
      $("status-error").textContent = ""
    }
  } catch (error) {
    $("status-error").textContent = error?.message || String(error)
  } finally {
    state.saving = false
    if (state.dirty && version !== state.editVersion) {
      if (state.saveTimer) clearTimeout(state.saveTimer)
      state.saveTimer = setTimeout(saveConfig, 400)
    }
  }
}

async function wire() {
  $("btn-save").addEventListener("click", async () => {
    if (state.saveTimer) clearTimeout(state.saveTimer)
    state.dirty = true
    state.editVersion += 1
    await saveConfig(true)
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
    try {
      await postJSON("/api/token/auto", {})
      $("cfg-admin-token").value = ""
      await refresh()
    } catch (error) {
      $("status-error").textContent = error?.message || String(error)
    }
  })
  await refresh()
  for (const id of ["cfg-base-url", "cfg-interval"]) {
    $(id).addEventListener("input", scheduleSave)
  }
  for (const id of ["cfg-rule", "cfg-group-a", "cfg-group-b"]) {
    $(id).addEventListener("change", scheduleSave)
  }
  if (state.timer) clearInterval(state.timer)
  state.timer = setInterval(refresh, 5000)
}

wire().catch((error) => {
  $("status-error").textContent = error?.message || String(error)
})
