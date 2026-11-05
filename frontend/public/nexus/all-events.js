
(() => {
  "use strict";

  const $ = id => document.getElementById(id);

  let currentPage = 1;
  let busy = false;

  function addCell(tr, value) {
    const td = document.createElement("td");
    td.textContent = String(value ?? "");
    td.style.overflowWrap = "anywhere";
    tr.appendChild(td);
  }

  function thaiTime(value) {
    if (!value) return "—";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString("en-GB", {
      timeZone: "Asia/Bangkok",
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    });
  }


  function addAiCell(tr, event) {
    const td = document.createElement("td");
    const status = event.ai_status;

    if (
      status === "matched" &&
      typeof event.ai_score === "number" &&
      Number.isFinite(event.ai_score) &&
      event.ai_score >= 0 &&
      event.ai_score <= 1 &&
      ["low_severity", "high_severity"].includes(event.ai_label)
    ) {
      const score = document.createElement("strong");
      score.textContent =
        (event.ai_score * 100).toFixed(1) + " / 100";

      const label = document.createElement("div");
      label.textContent = event.ai_label;
      label.style.fontSize = "12px";
      label.style.opacity = "0.8";

      td.append(score, label);
      td.title =
        "Raw AI score: " + event.ai_score +
        " | Learned Wazuh severity, not attack probability";
    } else {
      td.textContent =
        status === "not_scored" ? "Not scored" :
        status === "conflict" ? "Conflict" :
        "Unavailable";
    }

    td.style.whiteSpace = "nowrap";
    tr.appendChild(td);
  }

  async function loadHistory(page) {
    const root = $("history-view");
    if (!root || busy) return;

    busy = true;

    $("history-error").textContent = "";
    $("history-summary").textContent = "Loading history...";
    $("history-prev").disabled = true;
    $("history-next").disabled = true;

    const params = new URLSearchParams({
      page: String(page),
      hours: $("history-hours").value,
      search: $("history-search").value.trim()
    });

    try {
      const response = await fetch(
        "/api/nexus/v1/history?" + params,
        { cache: "no-store", credentials: "same-origin", redirect: "error", signal: AbortSignal.timeout(30000) }
      );

      if (!response.ok) {
        throw new Error("History API HTTP " + response.status);
      }

      const data = await response.json();

      if (
        !Array.isArray(data.events) ||
        !Number.isSafeInteger(data.total) || data.total < 0 ||
        data.events.length > 100
      ) {
        throw new Error("Invalid history response");
      }

      if ($("history-view") !== root) return;

      const fragment = document.createDocumentFragment();

      for (const event of data.events) {
        const tr = document.createElement("tr");

        addCell(tr, thaiTime(event.timestamp_utc));
        addCell(tr, event.rule_id);
        addCell(
          tr,
          (event.agent_name || "Unknown") +
          " (" + (event.agent_id || "—") + ")"
        );
        addCell(tr, event.description);
        addAiCell(tr, event);
        addCell(tr, event.event_uid || "—");


        fragment.appendChild(tr);
      }

      $("history-rows").replaceChildren(fragment);

      currentPage = data.page;

      $("history-summary").textContent =
        data.total.toLocaleString() +
        " matching events · " +
        data.events.length +
        " displayed · Historical snapshot";

      $("history-page").textContent =
        "Page " + currentPage + " of " + data.total_pages;

      $("history-prev").disabled = currentPage <= 1;
      $("history-next").disabled = !data.has_next;

    } catch (error) {
      if ($("history-view") === root) {
        $("history-rows").replaceChildren();
        $("history-summary").textContent =
          "History could not be loaded";
        $("history-error").textContent =
          error.message || "Unknown error";
      }
    } finally {
      busy = false;
    }
  }

  function activate() {
    if (location.hash === "#allevents") {
      loadHistory(1);
    }
  }

  document.addEventListener("click", event => {
    const id = event.target.closest("button")?.id;

    if (id === "history-go") loadHistory(1);
    if (id === "history-prev") loadHistory(currentPage - 1);
    if (id === "history-next") loadHistory(currentPage + 1);
  });

  document.addEventListener("change", event => {
    if (event.target.id === "history-hours") loadHistory(1);
  });

  document.addEventListener("keydown", event => {
    if (
      event.target.id === "history-search" &&
      event.key === "Enter"
    ) {
      event.preventDefault();
      loadHistory(1);
    }
  });

  window.addEventListener("hashchange", activate);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", activate);
  } else {
    activate();
  }
})();
