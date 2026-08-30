const state = { cards: [], selectedCardId: null, selectedCard: null };
const MAX_VISIBLE_CARDS = 160;
const SET_NAMES = {
  CORE: "核心",
  EMERALD_DREAM: "漫游翡翠梦境",
  THE_LOST_CITY: "安戈洛龟途",
  TIME_TRAVEL: "穿越时间流",
  CATACLYSM: "大灾变",
  ESCAPEFROM_VIOLET_HOLD: "逃离紫罗兰监狱",
};

const $ = (selector) => document.querySelector(selector);

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

function gateLabel(card) {
  if (card.ready_for_research) return "实现已核验";
  if (card.ready_to_generate && card.implementation_status !== "not_started") {
    return "等待实现核验";
  }
  if (card.ready_to_generate) return "允许制卡";
  if (card.authoring_ready) return "等待人工批准";
  if (!card.question_count) return "等待AI提问";
  if (!card.interview_complete) return "仍在提问";
  if (card.needs_verification_count) return "等待实机验证";
  return "等待人工回答";
}

function zeroQuestionApprovalCandidates() {
  return state.cards.filter((card) => (
    card.interview_complete
    && card.question_count === 0
    && !card.generation_approved
  ));
}

function renderBulkApprovalButton() {
  const button = $("#bulk-approve-zero-question-button");
  const count = zeroQuestionApprovalCandidates().length;
  button.textContent = `一键允许 ${count} 张无问题卡制卡`;
  button.classList.toggle("hidden", count === 0);
}

async function loadCards(selectId = state.selectedCardId) {
  const payload = await api("/api/cards");
  state.cards = payload.cards;
  populateSetFilter();
  renderCards();
  renderBulkApprovalButton();
  const target = selectId && state.cards.some((card) => card.card_id === selectId)
    ? selectId
    : state.cards[0]?.card_id;
  if (target) await selectCard(target);
}

function setLabel(cardSet) {
  return SET_NAMES[cardSet] || cardSet;
}

function populateSetFilter() {
  const select = $("#set-filter");
  const selected = select.value;
  const sets = [...new Set(state.cards.map((card) => card.card_set).filter(Boolean))].sort();
  select.replaceChildren(new Option("全部系列", "all"));
  for (const cardSet of sets) select.add(new Option(setLabel(cardSet), cardSet));
  select.value = sets.includes(selected) ? selected : "all";
}

function renderCards() {
  const list = $("#card-list");
  list.replaceChildren();
  const query = $("#card-search").value.trim().toLocaleLowerCase();
  const status = $("#status-filter").value;
  const cardSet = $("#set-filter").value;
  const cards = state.cards.filter((card) => {
    const haystack = `${card.name} ${card.card_id} ${card.card_set} ${setLabel(card.card_set)} ${card.card_class}`.toLocaleLowerCase();
    if (query && !haystack.includes(query)) return false;
    if (cardSet !== "all" && card.card_set !== cardSet) return false;
    if (status === "unasked") return !card.question_count && !card.interview_complete;
    if (status === "unresolved") return card.unresolved_blocking_count > 0;
    if (status === "verification") return card.needs_verification_count > 0;
    if (status === "approval") return card.authoring_ready && !card.generation_approved;
    if (status === "ready") {
      return card.ready_to_generate && card.implementation_status === "not_started";
    }
    if (status === "implementation") {
      return card.ready_to_generate && !card.ready_for_research
        && card.implementation_status !== "not_started";
    }
    if (status === "research-ready") return card.ready_for_research;
    return true;
  });
  const visibleCards = cards.slice(0, MAX_VISIBLE_CARDS);
  $("#filter-summary").textContent = cards.length > MAX_VISIBLE_CARDS
    ? `找到 ${cards.length} 张，当前列出前 ${MAX_VISIBLE_CARDS} 张`
    : `显示 ${cards.length} / ${state.cards.length} 张卡牌`;
  if (!cards.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = state.cards.length ? "没有符合筛选条件的卡牌" : "尚未导入或登记卡牌";
    list.append(empty);
    return;
  }
  for (const card of visibleCards) {
    const button = document.createElement("button");
    button.className = `card-row ${card.card_id === state.selectedCardId ? "active" : ""}`;
    const heading = document.createElement("span");
    heading.className = "card-row-heading";
    const name = document.createElement("strong");
    name.textContent = card.name;
    const badge = document.createElement("span");
    badge.className = card.ready_to_generate ? "mini-gate ready" : "mini-gate";
    badge.textContent = gateLabel(card);
    heading.append(name, badge);
    const counts = document.createElement("span");
    counts.className = "card-counts";
    const identity = [setLabel(card.card_set), card.card_class].filter(Boolean).join(" · ");
    counts.textContent = `${identity}${identity ? " · " : ""}${card.answered_count}/${card.question_count} 已回答 · ${card.unresolved_blocking_count} 项阻塞`;
    button.append(heading, counts);
    button.addEventListener("click", () => selectCard(card.card_id));
    list.append(button);
  }
}

async function selectCard(cardId) {
  const payload = await api(`/api/cards/${encodeURIComponent(cardId)}`);
  state.selectedCardId = cardId;
  state.selectedCard = payload.card;
  renderCards();
  renderDetail();
}

function renderDetail() {
  const card = state.selectedCard;
  $("#empty-state").classList.add("hidden");
  $("#detail").classList.remove("hidden");
  $("#card-id").textContent = card.card_id;
  $("#card-name").textContent = card.name;
  $("#card-metadata").textContent = [
    setLabel(card.card_set),
    card.card_class,
    card.card_type,
    card.cost === null ? "" : `${card.cost}费`,
    card.source_version ? `数据版本 ${card.source_version}` : "",
  ].filter(Boolean).join(" · ");
  $("#source-text").textContent = card.source_text || "尚未记录原始卡牌文本";
  const badge = $("#gate-badge");
  badge.textContent = gateLabel(card);
  badge.className = card.ready_to_generate ? "gate-badge ready" : "gate-badge";
  if (card.ready_for_research) {
    $("#gate-summary").textContent = "卡牌实现已核验，可加入待冻结研究牌池";
  } else if (card.ready_to_generate && card.implementation_status !== "not_started") {
    $("#gate-summary").textContent = "首版实现已生成，等待人工核验";
  } else if (card.ready_to_generate) {
    $("#gate-summary").textContent = "人工已批准，等待正式制卡与实现核验";
  } else if (card.authoring_ready) {
    $("#gate-summary").textContent = "规则澄清已完成，等待人工批准制卡";
  } else {
    $("#gate-summary").textContent = `${card.unresolved_blocking_count} 个阻塞问题未解决`;
  }
  $("#implementation-summary").textContent = `实现状态：${card.implementation_status}`;
  const interviewButton = $("#interview-button");
  interviewButton.textContent = card.interview_complete ? "重新开放提问" : "AI已完成本轮提问";
  interviewButton.className = card.interview_complete ? "secondary" : "";
  const approvalButton = $("#generation-approval-button");
  approvalButton.classList.toggle("hidden", !card.authoring_ready);
  approvalButton.textContent = card.generation_approved ? "撤销制卡批准" : "人工批准制卡";
  approvalButton.className = card.generation_approved ? "secondary" : "";
  approvalButton.classList.toggle("hidden", !card.authoring_ready);
  const implementationApprovalButton = $("#implementation-approval-button");
  const implementationEvidence = card.implementation_evidence || {};
  const hasReviewEvidence = Boolean(
    implementationEvidence.automated_tests
    && implementationEvidence.scenario_document
  );
  const awaitingImplementationReview = card.implementation_status === "under_review";
  implementationApprovalButton.classList.toggle("hidden", !awaitingImplementationReview);
  implementationApprovalButton.disabled = awaitingImplementationReview && !hasReviewEvidence;
  implementationApprovalButton.textContent = hasReviewEvidence
    ? "核验准出"
    : "核验材料不完整";
  implementationApprovalButton.title = hasReviewEvidence
    ? "人工确认代码、测试和前后局面后准出"
    : "需要自动测试结果和固定格式核验局面";
  renderImplementationReview(card);
  $("#question-summary").textContent = `${card.answered_count}/${card.question_count} 已回答，${card.needs_verification_count} 项等待实机验证`;
  renderQuestions(card.questions);
}

function renderImplementationReview(card) {
  const panel = $("#implementation-review");
  const evidence = card.implementation_evidence || {};
  const reviewDocument = evidence.scenario_document;
  const scenario = reviewDocument && reviewDocument.scenario;
  const visible = Boolean(
    reviewDocument &&
    reviewDocument.schema_version === "cardlab.authoring-review.v1" &&
    scenario &&
    scenario.before &&
    scenario.after
  );
  panel.classList.toggle("hidden", !visible);
  if (!visible) return;

  $("#implementation-artifact").textContent = [
    evidence.card_module ? `实现：${evidence.card_module}` : "",
    evidence.artifact_path ? `JSON：${evidence.artifact_path}` : "",
    evidence.summary_path ? `中文说明：${evidence.summary_path}` : "",
  ].filter(Boolean).join(" · ");
  $("#implementation-test-state").textContent = evidence.automated_tests || "等待自动测试";
  $("#implementation-narrative").textContent = evidence.review_text_zh || "尚未生成中文说明";
  $("#implementation-json").textContent = JSON.stringify(reviewDocument, null, 2);

  const specialCases = scenario.special_cases || [];
  const specialCasesPanel = $("#implementation-special-cases");
  specialCasesPanel.classList.toggle("hidden", specialCases.length === 0);
  const specialCaseList = $("#implementation-special-case-list");
  specialCaseList.replaceChildren();
  for (const specialCase of specialCases) {
    const item = document.createElement("li");
    item.textContent = specialCase.summary_zh;
    specialCaseList.append(item);
  }
}

function renderQuestions(questions) {
  const list = $("#question-list");
  list.replaceChildren();
  if (!questions.length) {
    const empty = document.createElement("div");
    empty.className = "question-empty";
    empty.textContent = "AI尚未提交澄清问题。完成语义检查后，即使没有问题也需要结束本轮提问。";
    list.append(empty);
    return;
  }
  for (const question of questions) {
    const fragment = $("#question-template").content.cloneNode(true);
    const article = fragment.querySelector(".question");
    fragment.querySelector(".category").textContent = question.category;
    const status = fragment.querySelector(".question-state");
    status.textContent = question.blocking ? "阻塞" : "备注";
    status.classList.toggle("resolved", question.current_resolution === "answered");
    fragment.querySelector(".asked-by").textContent = `由 ${question.asked_by} 提出`;
    fragment.querySelector(".prompt").textContent = question.prompt;
    const rationale = fragment.querySelector(".rationale");
    rationale.textContent = question.rationale;
    rationale.classList.toggle("hidden", !question.rationale);
    const current = fragment.querySelector(".current-answer");
    if (question.current_resolution === "answered") {
      current.textContent = `当前答案：${question.current_answer}`;
      current.className = "current-answer answered";
    } else if (question.current_resolution === "needs_verification") {
      current.textContent = `等待实机验证：${question.current_answer}`;
      current.className = "current-answer verify";
    } else {
      current.textContent = "尚未回答";
    }
    const form = fragment.querySelector(".answer-form");
    const assessment = question.current_ai_assessment;
    if (assessment) {
      const panel = fragment.querySelector(".ai-assessment");
      panel.classList.remove("hidden");
      const confidenceLabels = { low: "低", medium: "中", high: "高" };
      const disposition = assessment.disposition === "needs_verification"
        ? "AI建议实机验证"
        : "AI候选答案";
      fragment.querySelector(".ai-assessment-state").textContent =
        `${disposition} · ${confidenceLabels[assessment.confidence] || assessment.confidence}置信度`;
      fragment.querySelector(".ai-candidate-answer").textContent = assessment.answer;
      const reasoning = fragment.querySelector(".ai-candidate-reasoning");
      reasoning.textContent = assessment.reasoning;
      reasoning.classList.toggle("hidden", !assessment.reasoning);
      const sources = fragment.querySelector(".ai-sources");
      for (const source of assessment.sources) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = source.title;
        item.append(`${source.source_type} · `, link);
        if (source.claim) item.append(` — ${source.claim}`);
        sources.append(item);
      }
      fragment.querySelector(".adopt-ai").addEventListener("click", () => {
        form.elements.answer.value = assessment.answer;
        form.elements.answer.focus();
        toast("AI候选已填入，请核对或修改后再保存");
      });
      const aiHistory = fragment.querySelector(".ai-history");
      if (question.ai_assessments.length > 1) {
        aiHistory.classList.remove("hidden");
        const historyList = aiHistory.querySelector("ol");
        for (const item of question.ai_assessments.slice(0, -1).reverse()) {
          const historyItem = document.createElement("li");
          historyItem.textContent = `${item.created_at} · ${item.researched_by} · ${item.confidence}：${item.answer}`;
          historyList.append(historyItem);
        }
      }
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await submitAnswer(question.question_id, form, "answered");
    });
    fragment.querySelector(".verify").addEventListener("click", async () => {
      await submitAnswer(question.question_id, form, "needs_verification");
    });
    const history = fragment.querySelector(".history");
    const historyList = history.querySelector("ol");
    if (!question.answers.length) {
      history.classList.add("hidden");
    } else {
      for (const answer of question.answers.slice().reverse()) {
        const item = document.createElement("li");
        item.textContent = `${answer.created_at} · ${answer.respondent} · ${answer.resolution}：${answer.answer}`;
        historyList.append(item);
      }
    }
    article.dataset.questionId = question.question_id;
    list.append(fragment);
  }
}

async function submitAnswer(questionId, form, resolution) {
  const data = new FormData(form);
  let answer = String(data.get("answer") || "").trim();
  if (!answer && resolution === "needs_verification") answer = "需要在客户端构造局面并记录结果";
  if (!answer) {
    toast("请先填写答案", true);
    return;
  }
  try {
    await api(`/api/questions/${encodeURIComponent(questionId)}/answers`, {
      method: "POST",
      body: JSON.stringify({ answer, respondent: data.get("respondent"), resolution }),
    });
    toast(resolution === "answered" ? "答案已归档" : "已加入实机验证队列");
    await loadCards(state.selectedCardId);
  } catch (error) {
    toast(error.message, true);
  }
}

$("#refresh-button").addEventListener("click", () => loadCards().catch((error) => toast(error.message, true)));
$("#card-search").addEventListener("input", renderCards);
$("#status-filter").addEventListener("change", renderCards);
$("#set-filter").addEventListener("change", renderCards);
$("#new-card-button").addEventListener("click", () => $("#card-dialog").showModal());
$("#add-question-button").addEventListener("click", () => $("#question-dialog").showModal());
$("#close-card-dialog").addEventListener("click", () => $("#card-dialog").close());
$("#close-question-dialog").addEventListener("click", () => $("#question-dialog").close());
$("#close-implementation-review-dialog").addEventListener("click", () => {
  $("#implementation-review-dialog").close();
  $("#implementation-review-form").reset();
});

$("#implementation-approval-button").addEventListener("click", () => {
  const card = state.selectedCard;
  if (!card || card.implementation_status !== "under_review") return;
  $("#implementation-review-form").reset();
  $("#implementation-review-context").textContent = `${card.name}（${card.card_id}）`;
  $("#implementation-review-dialog").showModal();
});

$("#card-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  try {
    const payload = await api("/api/cards", { method: "POST", body: JSON.stringify(data) });
    $("#card-dialog").close();
    form.reset();
    toast("卡牌已登记");
    await loadCards(payload.card.card_id);
  } catch (error) {
    toast(error.message, true);
  }
});

$("#question-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  data.blocking = form.elements.blocking.checked;
  try {
    await api(`/api/cards/${encodeURIComponent(state.selectedCardId)}/questions`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    $("#question-dialog").close();
    form.reset();
    form.elements.category.value = "interaction";
    form.elements.asked_by.value = "llm";
    form.elements.blocking.checked = true;
    toast("问题已加入队列，制卡门禁已关闭");
    await loadCards(state.selectedCardId);
  } catch (error) {
    toast(error.message, true);
  }
});

$("#implementation-review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const reviewer = String(data.get("reviewer") || "").trim();
  const note = String(data.get("note") || "").trim();
  const existingEvidence = state.selectedCard.implementation_evidence || {};
  const evidence = {
    ...existingEvidence,
    code_review: `人工核验通过（${reviewer}）`,
    human_scenario_review: `人工核验通过（${reviewer}）`,
  };
  try {
    await api(`/api/cards/${encodeURIComponent(state.selectedCardId)}/implementation`, {
      method: "POST",
      body: JSON.stringify({
        status: "implementation_ready",
        reviewer,
        note: note || "通过审核台完成人工实现核验",
        evidence,
      }),
    });
    $("#implementation-review-dialog").close();
    form.reset();
    toast("实现核验已准出，卡牌进入研究就绪");
    await loadCards(state.selectedCardId);
  } catch (error) {
    toast(error.message, true);
  }
});

$("#interview-button").addEventListener("click", async () => {
  const complete = !state.selectedCard.interview_complete;
  try {
    await api(`/api/cards/${encodeURIComponent(state.selectedCardId)}/interview`, {
      method: "POST",
      body: JSON.stringify({ complete }),
    });
    toast(complete ? "本轮提问已结束" : "已重新开放提问");
    await loadCards(state.selectedCardId);
  } catch (error) {
    toast(error.message, true);
  }
});

$("#generation-approval-button").addEventListener("click", async () => {
  const approved = !state.selectedCard.generation_approved;
  try {
    await api(`/api/cards/${encodeURIComponent(state.selectedCardId)}/generation-approval`, {
      method: "POST",
      body: JSON.stringify({ approved, reviewer: "human" }),
    });
    toast(approved ? "已批准进入正式制卡队列" : "已撤销制卡批准");
    await loadCards(state.selectedCardId);
  } catch (error) {
    toast(error.message, true);
  }
});

$("#bulk-approve-zero-question-button").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const count = zeroQuestionApprovalCandidates().length;
  if (!count) {
    toast("当前没有可批量批准的无问题卡");
    return;
  }
  const confirmed = window.confirm(
    `确认允许 ${count} 张无问题卡进入制卡队列？\n\n`
    + "只会处理已结束提问、问题数为 0 且尚未批准的卡牌。",
  );
  if (!confirmed) return;
  button.disabled = true;
  try {
    const payload = await api("/api/cards/bulk-generation-approval", {
      method: "POST",
      body: JSON.stringify({
        reviewer: "human",
        note: "通过审核台一键批准无问题卡",
      }),
    });
    const approved = payload.bulk_approval.approved_count;
    toast(`已允许 ${approved} 张无问题卡进入制卡队列`);
    await loadCards(state.selectedCardId);
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
});

loadCards().catch((error) => toast(error.message, true));
