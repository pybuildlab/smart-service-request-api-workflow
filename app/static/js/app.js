(() => {
  "use strict";

  const REQUESTS_ENDPOINT = "/requests";
  const FEEDBACK_DURATION_MS = 5000;

  const STATUS_OPTIONS = ["pending", "in_progress", "completed", "cancelled"];
  const STATUS_LABELS = {
    pending: "Pending",
    in_progress: "In Progress",
    completed: "Completed",
    cancelled: "Cancelled",
  };

  const form = document.getElementById("request-form");
  const titleInput = document.getElementById("title");
  const descriptionInput = document.getElementById("description");
  const submitButton = document.getElementById("submit-button");
  const refreshButton = document.getElementById("refresh-button");
  const newRequestCta = document.getElementById("new-request-cta");
  const listEl = document.getElementById("request-list");
  const loadingEl = document.getElementById("loading");
  const emptyStateEl = document.getElementById("empty-state");
  const emptyStateTextEl = document.getElementById("empty-state-text");
  const feedbackEl = document.getElementById("feedback");
  const feedbackMessageEl = document.getElementById("feedback-message");
  const feedbackProgressEl = document.getElementById("feedback-progress");
  const lastUpdatedEl = document.getElementById("last-updated");
  const filterBarEl = document.getElementById("filter-bar");
  const connectionDotEl = document.getElementById("connection-status-dot");
  const connectionTextEl = document.getElementById("connection-status-text");

  const statEls = {
    total: document.getElementById("stat-total"),
    pending: document.getElementById("stat-pending"),
    in_progress: document.getElementById("stat-in_progress"),
    completed: document.getElementById("stat-completed"),
    cancelled: document.getElementById("stat-cancelled"),
  };

  let feedbackTimer = null;
  let allRequests = [];
  let activeFilter = "all";
  let previousStats = { total: 0, pending: 0, in_progress: 0, completed: 0, cancelled: 0 };
  let pendingHighlightId = null;

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  function showFeedback(message, kind) {
    feedbackMessageEl.textContent = message;
    feedbackEl.className = `feedback feedback--${kind}`;
    feedbackEl.hidden = false;

    // Restart the progress-bar animation even if a toast is already
    // showing: force a reflow between removing and re-adding the class
    // that carries the animation, and reset its duration explicitly so
    // it always matches the JS auto-dismiss timer below.
    feedbackProgressEl.classList.remove("is-running");
    feedbackProgressEl.style.animationDuration = "0s";
    void feedbackProgressEl.offsetWidth;
    feedbackProgressEl.style.animationDuration = `${FEEDBACK_DURATION_MS}ms`;
    feedbackProgressEl.classList.add("is-running");

    window.clearTimeout(feedbackTimer);
    feedbackTimer = window.setTimeout(() => {
      feedbackEl.hidden = true;
    }, FEEDBACK_DURATION_MS);
  }

  // Reads the API's own error response (a string `detail` for 404s, a list
  // of Pydantic validation issues for 422s) and turns it into one readable
  // line. This only *reads* what the backend already decided - it does not
  // reimplement any validation or business rule.
  async function extractErrorMessage(response) {
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        return body.detail;
      }
      if (Array.isArray(body.detail)) {
        return body.detail
          .map((issue) => {
            const field = Array.isArray(issue.loc) ? issue.loc[issue.loc.length - 1] : "value";
            return `${field}: ${issue.msg}`;
          })
          .join("; ");
      }
    } catch (error) {
      // Response body wasn't JSON - fall through to the generic message.
    }
    return `Request failed (HTTP ${response.status}).`;
  }

  function setConnectionStatus(isOnline) {
    connectionDotEl.classList.toggle("is-online", isOnline);
    connectionDotEl.classList.toggle("is-offline", !isOnline);
    connectionTextEl.textContent = isOnline ? "Live" : "Connection issue";
  }

  function setLoading(isLoading) {
    loadingEl.hidden = !isLoading;
    if (isLoading) {
      listEl.hidden = true;
      emptyStateEl.hidden = true;
    }
  }

  // Stats are derived entirely from the requests the API just returned -
  // nothing here is hard-coded or estimated.
  function computeStats(requests) {
    const counts = { pending: 0, in_progress: 0, completed: 0, cancelled: 0 };
    for (const request of requests) {
      if (Object.prototype.hasOwnProperty.call(counts, request.status)) {
        counts[request.status] += 1;
      }
    }
    return { total: requests.length, ...counts };
  }

  // Animates a stat's displayed number from its previous real value to its
  // new real value. Purely a display transition - the source of truth is
  // always the count passed in, never a fabricated number.
  function animateStatValue(el, from, to) {
    if (from === to) {
      el.textContent = to;
      return;
    }
    const duration = 450;
    const start = performance.now();

    function step(now) {
      const elapsed = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - elapsed, 3);
      el.textContent = Math.round(from + (to - from) * eased);
      if (elapsed < 1) {
        window.requestAnimationFrame(step);
      } else {
        el.textContent = to;
      }
    }

    window.requestAnimationFrame(step);
  }

  function renderStats(requests) {
    const stats = computeStats(requests);
    animateStatValue(statEls.total, previousStats.total, stats.total);
    animateStatValue(statEls.pending, previousStats.pending, stats.pending);
    animateStatValue(statEls.in_progress, previousStats.in_progress, stats.in_progress);
    animateStatValue(statEls.completed, previousStats.completed, stats.completed);
    animateStatValue(statEls.cancelled, previousStats.cancelled, stats.cancelled);
    previousStats = stats;
  }

  function applyFilter(requests) {
    if (activeFilter === "all") {
      return requests;
    }
    return requests.filter((request) => request.status === activeFilter);
  }

  function renderRequestCard(request) {
    const item = document.createElement("li");
    item.className = `request-card request-card--${request.status}`;
    item.dataset.requestId = String(request.id);

    const statusOptionsHtml = STATUS_OPTIONS.map((value) => {
      const selected = value === request.status ? "selected" : "";
      return `<option value="${value}" ${selected}>${STATUS_LABELS[value]}</option>`;
    }).join("");

    item.innerHTML = `
      <div class="request-card__header">
        <span class="request-card__id">#${request.id}</span>
        <span class="status-badge status-badge--${request.status}">${STATUS_LABELS[request.status]}</span>
      </div>
      <h3 class="request-card__title">${escapeHtml(request.title)}</h3>
      <p class="request-card__description">${escapeHtml(request.description)}</p>
      <div class="request-card__actions">
        <label>
          Update status:
          <select class="status-select" data-request-id="${request.id}">
            ${statusOptionsHtml}
          </select>
        </label>
      </div>
    `;

    return item;
  }

  function renderRequests() {
    const visible = applyFilter(allRequests);
    listEl.innerHTML = "";

    if (visible.length === 0) {
      emptyStateEl.hidden = false;
      listEl.hidden = true;
      emptyStateTextEl.textContent =
        allRequests.length === 0
          ? "No service requests yet. Create one above."
          : `No requests with status "${STATUS_LABELS[activeFilter]}".`;
      return;
    }

    emptyStateEl.hidden = true;
    listEl.hidden = false;

    const fragment = document.createDocumentFragment();
    visible.forEach((request, index) => {
      const card = renderRequestCard(request);
      card.style.animationDelay = `${Math.min(index, 8) * 30}ms`;
      fragment.appendChild(card);
    });
    listEl.appendChild(fragment);

    // If a create/update just succeeded, briefly highlight that specific
    // card now that it exists in the freshly-rendered list.
    if (pendingHighlightId !== null) {
      const highlighted = listEl.querySelector(`[data-request-id="${pendingHighlightId}"]`);
      if (highlighted) {
        highlighted.classList.add("is-highlighted");
        highlighted.addEventListener(
          "animationend",
          () => highlighted.classList.remove("is-highlighted"),
          { once: true }
        );
      }
      pendingHighlightId = null;
    }
  }

  function updateLastUpdatedLabel() {
    const now = new Date();
    lastUpdatedEl.textContent = `Last updated ${now.toLocaleTimeString()}`;
  }

  function setActiveFilter(filter) {
    activeFilter = filter;
    for (const chip of filterBarEl.querySelectorAll(".filter-chip")) {
      const isActive = chip.dataset.filter === filter;
      chip.classList.toggle("is-active", isActive);
      chip.setAttribute("aria-pressed", String(isActive));
    }
    renderRequests();
  }

  async function loadRequests() {
    setLoading(true);
    try {
      const response = await fetch(REQUESTS_ENDPOINT, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(await extractErrorMessage(response));
      }
      allRequests = await response.json();
      setConnectionStatus(true);
      renderStats(allRequests);
      renderRequests();
      updateLastUpdatedLabel();
    } catch (error) {
      setConnectionStatus(false);
      showFeedback(`Couldn't load requests: ${error.message}`, "error");
      allRequests = [];
      listEl.innerHTML = "";
      listEl.hidden = true;
      emptyStateEl.hidden = true;
      lastUpdatedEl.textContent = "Failed to load";
    } finally {
      setLoading(false);
    }
  }

  async function createRequest(event) {
    event.preventDefault();

    const title = titleInput.value.trim();
    const description = descriptionInput.value.trim();

    if (!title || !description) {
      showFeedback("Title and description are both required.", "error");
      return;
    }

    submitButton.disabled = true;
    submitButton.querySelector(".button-label").textContent = "Creating...";

    try {
      const response = await fetch(REQUESTS_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description }),
      });

      if (!response.ok) {
        throw new Error(await extractErrorMessage(response));
      }

      const created = await response.json();
      form.reset();
      pendingHighlightId = created.id;
      showFeedback(`Request #${created.id} created.`, "success");
      await loadRequests();
    } catch (error) {
      showFeedback(`Couldn't create request: ${error.message}`, "error");
    } finally {
      submitButton.disabled = false;
      submitButton.querySelector(".button-label").textContent = "Create Request";
    }
  }

  async function updateStatus(event) {
    const select = event.target;
    if (!select.classList.contains("status-select")) {
      return;
    }

    const requestId = select.dataset.requestId;
    const newStatus = select.value;
    select.disabled = true;

    try {
      const response = await fetch(`${REQUESTS_ENDPOINT}/${requestId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!response.ok) {
        throw new Error(await extractErrorMessage(response));
      }

      pendingHighlightId = Number(requestId);
      showFeedback(`Request #${requestId} updated to "${STATUS_LABELS[newStatus]}".`, "success");
    } catch (error) {
      showFeedback(`Couldn't update request #${requestId}: ${error.message}`, "error");
    } finally {
      await loadRequests();
    }
  }

  form.addEventListener("submit", createRequest);
  refreshButton.addEventListener("click", loadRequests);
  listEl.addEventListener("change", updateStatus);
  filterBarEl.addEventListener("click", (event) => {
    const chip = event.target.closest(".filter-chip");
    if (chip) {
      setActiveFilter(chip.dataset.filter);
    }
  });
  newRequestCta.addEventListener("click", () => {
    titleInput.scrollIntoView({ behavior: "smooth", block: "center" });
    titleInput.focus();
  });

  loadRequests();
})();
