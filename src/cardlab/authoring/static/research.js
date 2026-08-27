const state = { proposals: [], selectedId: null, selected: null };
const $ = (selector) => document.querySelector(selector);
const STATUS_LABELS = {
  draft: "AI草稿",
  critic_reviewed: "反方已审查",
  awaiting_human: "等待人工审核",
  approved: "人工已批准",
  revision_requested: "退回修改",
  rejected: "已拒绝",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `请求失败：${response.status}`);
  return payload;
}

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.className = error ? "visible error" : "visible";
  window.setTimeout(() => { element.className = ""; }, 2600);
}

async function loadProposals(selectId = state.selectedId) {
  const payload = await api("/api/research/proposals");
  state.proposals = payload.proposals;
  renderProposalList();
  const target = selectId && state.proposals.some((item) => item.proposal_id === selectId)
    ? selectId
    : state.proposals[0]?.proposal_id;
  if (target) await selectProposal(target);
}

function renderProposalList() {
  const list = $("#proposal-list");
  list.replaceChildren();
  $("#proposal-count").textContent = `${state.proposals.length} 个提案`;
  for (const proposal of state.proposals) {
    const button = document.createElement("button");
    button.className = `card-row ${proposal.proposal_id === state.selectedId ? "active" : ""}`;
    const heading = document.createElement("span");
    heading.className = "card-row-heading";
    const title = document.createElement("strong");
    title.textContent = proposal.title;
    const badge = document.createElement("span");
    badge.className = proposal.status === "approved" ? "mini-gate ready" : "mini-gate";
    badge.textContent = STATUS_LABELS[proposal.status] || proposal.status;
    heading.append(title, badge);
    const question = document.createElement("span");
    question.className = "card-counts";
    question.textContent = proposal.question;
    button.append(heading, question);
    button.addEventListener("click", () => selectProposal(proposal.proposal_id));
    list.append(button);
  }
}

async function selectProposal(proposalId) {
  const payload = await api(`/api/research/proposals/${encodeURIComponent(proposalId)}`);
  state.selectedId = proposalId;
  state.selected = payload.proposal;
  renderProposalList();
  renderProposal();
}

function renderProposal() {
  const proposal = state.selected;
  $("#proposal-empty").classList.add("hidden");
  $("#proposal-detail").classList.remove("hidden");
  $("#proposal-id").textContent = proposal.proposal_id;
  $("#proposal-title").textContent = proposal.title;
  $("#proposal-question").textContent = proposal.question;
  $("#proposal-rationale").textContent = proposal.rationale;
  const status = $("#proposal-status");
  status.textContent = STATUS_LABELS[proposal.status] || proposal.status;
  status.className = proposal.status === "approved" ? "gate-badge ready" : "gate-badge";

  const evidence = $("#proposal-evidence");
  evidence.replaceChildren();
  if (!proposal.evidence.length) {
    const item = document.createElement("li");
    item.textContent = "尚未归档来源；反方审查前应补齐。";
    evidence.append(item);
  } else {
    for (const source of proposal.evidence) {
      const item = document.createElement("li");
      item.textContent = source.claim || JSON.stringify(source);
      evidence.append(item);
    }
  }
  renderReviewNote("#critic-review", "反方意见", proposal.critic_review);
  renderReviewNote("#human-review", "人工意见", proposal.human_review);
  renderActions(proposal.status);

  const events = $("#proposal-events");
  events.replaceChildren();
  for (const event of proposal.events.slice().reverse()) {
    const item = document.createElement("li");
    item.textContent = `${event.created_at} · ${event.actor} · ${event.from_status || "开始"} → ${event.to_status}：${event.note}`;
    events.append(item);
  }
}

function renderReviewNote(selector, title, value) {
  const node = $(selector);
  node.classList.toggle("hidden", !value);
  node.textContent = value ? `${title}：${value}` : "";
}

function renderActions(status) {
  const actions = $("#proposal-actions");
  actions.replaceChildren();
  const transitions = {
    draft: [["记录反方审查", "critic_reviewed"]],
    critic_reviewed: [["提交人工审核", "awaiting_human"], ["退回AI修改", "revision_requested"]],
    awaiting_human: [["人工批准", "approved"], ["要求修改", "revision_requested"], ["拒绝提案", "rejected"]],
    revision_requested: [["重新提交草稿", "draft"]],
  };
  const next = transitions[status] || [];
  $("#proposal-next-step").textContent = next.length
    ? "每次状态变化都必须填写审核意见，并追加到历史记录。"
    : "该提案已经形成最终人工决定。";
  for (const [label, toStatus] of next) {
    const button = document.createElement("button");
    button.textContent = label;
    if (["revision_requested", "rejected"].includes(toStatus)) button.className = "secondary";
    button.addEventListener("click", () => transitionProposal(toStatus));
    actions.append(button);
  }
}

async function transitionProposal(toStatus) {
  const actor = $("#review-actor").value.trim();
  const note = $("#review-note").value.trim();
  if (!actor || !note) {
    toast("请填写审核者和审核意见", true);
    return;
  }
  try {
    await api(`/api/research/proposals/${encodeURIComponent(state.selectedId)}/transitions`, {
      method: "POST",
      body: JSON.stringify({ to_status: toStatus, actor, note }),
    });
    $("#review-note").value = "";
    toast("提案状态已归档");
    await loadProposals(state.selectedId);
  } catch (error) {
    toast(error.message, true);
  }
}

$("#new-proposal-button").addEventListener("click", () => $("#proposal-dialog").showModal());
$("#close-proposal-dialog").addEventListener("click", () => $("#proposal-dialog").close());
$("#refresh-proposals").addEventListener("click", () => loadProposals().catch((error) => toast(error.message, true)));
$("#proposal-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  data.evidence = [];
  try {
    const payload = await api("/api/research/proposals", {
      method: "POST",
      body: JSON.stringify(data),
    });
    $("#proposal-dialog").close();
    form.reset();
    form.elements.proposed_by.value = "research-llm";
    toast("研究提案已保存为草稿，不会自动运行");
    await loadProposals(payload.proposal.proposal_id);
  } catch (error) {
    toast(error.message, true);
  }
});

loadProposals().catch((error) => toast(error.message, true));
