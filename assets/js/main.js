/**
 * FulfillSense — interaction layer.
 *
 * Everything here degrades gracefully: if JS fails the page is still a
 * complete, readable document. Motion is disabled wholesale when the visitor
 * has asked for reduced motion.
 */
(() => {
  "use strict";

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* ---------------------------------------------------------------------
   * Sticky navigation
   * ------------------------------------------------------------------- */
  const nav = document.querySelector(".nav");
  if (nav) {
    const onScroll = () => nav.classList.toggle("is-stuck", window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------------------------------------------------------------------
   * Scroll reveal
   * ------------------------------------------------------------------- */
  const revealables = document.querySelectorAll("[data-reveal]");
  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    revealables.forEach((el) => el.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.12 }
    );
    revealables.forEach((el) => observer.observe(el));
  }

  /* ---------------------------------------------------------------------
   * Cursor spotlight on glass surfaces
   * ------------------------------------------------------------------- */
  if (!prefersReducedMotion && window.matchMedia("(hover: hover)").matches) {
    document.querySelectorAll(".surface").forEach((card) => {
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
        card.style.setProperty("--my", `${event.clientY - rect.top}px`);
      });
    });

    /* Magnetic buttons: a few pixels of pull, nothing cartoonish. */
    document.querySelectorAll("[data-magnetic]").forEach((btn) => {
      const strength = 0.22;
      btn.addEventListener("pointermove", (event) => {
        const rect = btn.getBoundingClientRect();
        const x = (event.clientX - rect.left - rect.width / 2) * strength;
        const y = (event.clientY - rect.top - rect.height / 2) * strength;
        btn.style.transform = `translate(${x}px, ${y}px)`;
      });
      btn.addEventListener("pointerleave", () => {
        btn.style.transform = "";
      });
    });
  }

  /* ---------------------------------------------------------------------
   * Count-up statistics
   * ------------------------------------------------------------------- */
  const counters = document.querySelectorAll("[data-count]");
  const runCounter = (el) => {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || "";
    const prefix = el.dataset.prefix || "";
    const duration = 1400;
    const start = performance.now();

    const frame = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      el.textContent = prefix + value.toLocaleString("en-IN") + suffix;
      if (progress < 1) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  };

  if (counters.length) {
    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      counters.forEach((el) => {
        const target = parseFloat(el.dataset.count);
        el.textContent =
          (el.dataset.prefix || "") +
          target.toLocaleString("en-IN") +
          (el.dataset.suffix || "");
      });
    } else {
      const counterObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            runCounter(entry.target);
            counterObserver.unobserve(entry.target);
          });
        },
        { threshold: 0.6 }
      );
      counters.forEach((el) => counterObserver.observe(el));
    }
  }

  /* ---------------------------------------------------------------------
   * Live risk console
   *
   * A faithful miniature of the real engine: four behavioural signals in,
   * an RTO probability out, quarantined above the 75% threshold.
   * ------------------------------------------------------------------- */
  /* Two markets, interleaved, so the feed reads as a global stream. Each order
     carries its own currency: cash-on-delivery dominates in India, while the
     US risk signal leans on guest checkout and cart value. */
  const ORDERS = [
    { id: "#88392", city: "Kanpur", cur: "INR", value: 4820, cod: true, guest: true, risk: 94 },
    { id: "#US4410", city: "Miami", cur: "USD", value: 489, cod: true, guest: true, risk: 91 },
    { id: "#1104A", city: "Bengaluru", cur: "INR", value: 1290, cod: false, guest: false, risk: 12 },
    { id: "#US7725", city: "Seattle", cur: "USD", value: 128, cod: false, guest: false, risk: 9 },
    { id: "#77510", city: "Patna", cur: "INR", value: 6350, cod: true, guest: true, risk: 88 },
    { id: "#US3041", city: "Houston", cur: "USD", value: 312, cod: true, guest: true, risk: 86 },
    { id: "#9921B", city: "Mumbai", cur: "INR", value: 2480, cod: false, guest: false, risk: 4 },
    { id: "#US9183", city: "Phoenix", cur: "USD", value: 254, cod: false, guest: true, risk: 47 },
    { id: "#45028", city: "Jaipur", cur: "INR", value: 3990, cod: true, guest: false, risk: 61 },
    { id: "#US2268", city: "Chicago", cur: "USD", value: 76, cod: false, guest: false, risk: 6 },
    { id: "#61180", city: "Lucknow", cur: "INR", value: 5410, cod: true, guest: true, risk: 79 },
    { id: "#US5502", city: "Austin", cur: "USD", value: 198, cod: false, guest: false, risk: 15 },
    { id: "#20347", city: "Pune", cur: "INR", value: 899, cod: false, guest: true, risk: 23 },
    { id: "#US6117", city: "Newark", cur: "USD", value: 402, cod: false, guest: true, risk: 68 },
    { id: "#33925", city: "Chennai", cur: "INR", value: 1750, cod: false, guest: false, risk: 8 },
    { id: "#US8830", city: "Denver", cur: "USD", value: 145, cod: false, guest: false, risk: 11 },
  ];

  const money = (order) =>
    order.cur === "USD"
      ? `$${order.value.toLocaleString("en-US")}`
      : `₹${order.value.toLocaleString("en-IN")}`;

  const verdictFor = (risk) => {
    if (risk >= 75) return { state: "risk", label: "QUARANTINE" };
    if (risk >= 40) return { state: "review", label: "REVIEW" };
    return { state: "safe", label: "FULFILL" };
  };

  const feed = document.getElementById("order-feed");
  const gaugeValue = document.getElementById("gauge-value");
  const gaugePct = document.getElementById("gauge-pct");
  const gaugeVerdict = document.getElementById("gauge-verdict");
  const gaugeOrder = document.getElementById("gauge-order");

  if (feed && gaugeValue) {
    const RADIUS = 64;
    const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
    gaugeValue.style.strokeDasharray = `${CIRCUMFERENCE}`;
    gaugeValue.style.strokeDashoffset = `${CIRCUMFERENCE}`;

    const strokeFor = (state) =>
      state === "risk"
        ? "hsl(8 78% 61%)"
        : state === "review"
        ? "hsl(38 88% 62%)"
        : "hsl(163 64% 45%)";

    const renderOrder = (order) => {
      const verdict = verdictFor(order.risk);
      const row = document.createElement("div");
      row.className = "order";
      row.innerHTML = `
        <div class="order__id">${order.id}</div>
        <div class="order__meta">${order.city} · ${money(order)} · ${
        order.cod ? "COD" : "Prepaid"
      } · ${order.guest ? "guest" : "registered"}</div>
        <div class="order__chip" data-state="${verdict.state}">${
        order.risk
      }% ${verdict.label}</div>`;
      feed.prepend(row);

      while (feed.children.length > 4) {
        const last = feed.lastElementChild;
        last.classList.add("is-leaving");
        window.setTimeout(() => last.remove(), 420);
        if (feed.children.length > 6) last.remove();
      }
    };

    const renderGauge = (order) => {
      const verdict = verdictFor(order.risk);
      gaugeValue.style.strokeDashoffset = `${
        CIRCUMFERENCE * (1 - order.risk / 100)
      }`;
      gaugeValue.style.stroke = strokeFor(verdict.state);
      gaugePct.firstChild.textContent = order.risk;
      gaugeVerdict.textContent =
        verdict.state === "risk"
          ? "High RTO risk"
          : verdict.state === "review"
          ? "Manual review"
          : "Safe to fulfill";
      gaugeVerdict.dataset.state = verdict.state;
      gaugeOrder.textContent = `order ${order.id}`;
    };

    let cursor = 0;
    const tick = () => {
      const order = ORDERS[cursor % ORDERS.length];
      renderOrder(order);
      renderGauge(order);
      cursor += 1;
    };

    // Seed the feed so the console never looks empty on first paint.
    [ORDERS[3], ORDERS[2], ORDERS[1]].forEach((order) => renderOrder(order));
    tick();

    if (!prefersReducedMotion) {
      let timer = window.setInterval(tick, 2600);
      document.addEventListener("visibilitychange", () => {
        window.clearInterval(timer);
        if (!document.hidden) timer = window.setInterval(tick, 2600);
      });
    }
  }

  /* ---------------------------------------------------------------------
   * Sandbox modal
   *
   * The Streamlit app is only loaded on demand, and cold starts are
   * explained rather than hidden behind a blank frame.
   * ------------------------------------------------------------------- */
  const modal = document.getElementById("sandbox");
  const frame = document.getElementById("sandbox-frame");
  const loader = document.getElementById("sandbox-loader");
  const APP_SRC = "https://fulfill-sense.streamlit.app/?embed=true";
  let lastFocused = null;

  const openModal = () => {
    if (!modal) return;
    lastFocused = document.activeElement;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    if (!frame.getAttribute("src")) {
      frame.setAttribute("src", APP_SRC);
      frame.addEventListener(
        "load",
        () => window.setTimeout(() => loader.classList.add("is-hidden"), 900),
        { once: true }
      );
    }
    modal.querySelector("[data-close]").focus();
  };

  const closeModal = () => {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    if (lastFocused) lastFocused.focus();
  };

  document
    .querySelectorAll("[data-open-sandbox]")
    .forEach((trigger) =>
      trigger.addEventListener("click", (event) => {
        event.preventDefault();
        openModal();
      })
    );

  if (modal) {
    modal.querySelectorAll("[data-close]").forEach((el) =>
      el.addEventListener("click", closeModal)
    );
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && modal.classList.contains("is-open")) {
        closeModal();
      }
    });
  }

  /* ---------------------------------------------------------------------
   * Current year in the footer
   * ------------------------------------------------------------------- */
  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();
})();
