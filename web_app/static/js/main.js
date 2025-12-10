console.log("PolyPaper frontend loaded");

document.addEventListener("DOMContentLoaded", () => {
  // ... [Keep existing Trade Button Logic] ...
  const mockTradeBtn = document.querySelector(".trade-ticket .btn-primary");

  if (mockTradeBtn) {
    mockTradeBtn.addEventListener("click", async (e) => {
      e.preventDefault();

      const tradeAmountInput = document.getElementById("trade-amount");
      const activeBtn = document.querySelector(".toggle-group .chip-active");
      const chosenIndex = activeBtn ? parseInt(activeBtn.dataset.index) : null;
      const estPriceEl = document.getElementById("est-price");
      const question = document.getElementsByClassName("page-title")[0].innerText
      const assetIds = JSON.parse(estPriceEl.dataset.assetids || "[]");
      const assetId = chosenIndex !== null ? assetIds[chosenIndex] : null;

      const bidText = tradeAmountInput?.value?.trim();
      const processedQuestion = question?.trim();
      const bid = parseFloat(bidText);

      if (!assetId || !bidText || isNaN(bid) || bid <= 0) {
        alert("Please enter a valid bid amount.");
        return;
      }

      try {
        const resp = await fetch("/trade", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            asset_id: assetId,
            bid: bid,
            question: processedQuestion
          }),
        });

        if (!resp.ok) {
          const errText = await resp.text();
          throw new Error(errText || "Trade failed");
        }
        const data = await resp.json();

        if (data.success && data.redirect) {
            // Redirect to portfolio page
          window.location.href = data.redirect;
        } else {
          alert("Trade placed successfully!");
        }

      } catch (err) {
        console.error("Trade error:", err);
        alert(`Error placing trade: ${err.message}`);
      }
    });
  }



  // ... [Keep existing Profile Menu Logic] ...
  const profileMenu = document.querySelector(".profile-menu");
  const profileTrigger = document.querySelector(".profile-trigger");
  if (profileMenu && profileTrigger) {
    profileTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      profileMenu.classList.toggle("open");
    });
    document.addEventListener("click", () => {
      profileMenu.classList.remove("open");
    });
  }

  // --- START FIXED LIVE PRICE SECTION ---
  const toggleGroup = document.querySelector(".toggle-group");
  const estPriceEl = document.getElementById("est-price");
  const tradeButton= document.getElementById("submit-trade");

  if (toggleGroup && estPriceEl) {
    console.log("Initializing Live Price Polling...");

    // 1. Safely Parse Data Attributes
    let assetIds = [];
    let outcomePrices = [];

    try {
      assetIds = JSON.parse(estPriceEl.dataset.assetids || "[]");
      outcomePrices = JSON.parse(estPriceEl.dataset.outcomePrices || "[]");
    } catch (e) {
      console.error("Error parsing price data attributes:", e);
    }

    if (assetIds.length === 0) {
      console.warn("No asset IDs found, live polling aborted.");
    } else {
      const latestPrices = {};
      let selectedIndex = 0;
      const POLLING_INTERVAL = 3000; // 3 seconds
      let pollingTimer = null;
      const buttons = toggleGroup.querySelectorAll("button");

      const updatePriceDisplay = () => {
        const assetId = assetIds[selectedIndex];
        const fallback = parseFloat(outcomePrices[selectedIndex] || 0);
        const live = latestPrices[assetId];
        const displayPrice = live !== undefined && live !== null ? live : fallback;
        console.log("Called Update")
        estPriceEl.textContent = `$${displayPrice.toFixed(3)} / share`;
      };

      const fetchCurrentPrice = async () => {
        const assetId = assetIds[selectedIndex];
        if (!assetId) {
            console.warn("fetchCurrentPrice: No Asset ID for index", selectedIndex);
            return;
        }

        // console.log("Fetching live price for:", assetId); // Uncomment to debug spam
        try {
          const resp = await fetch(`/live_prices?tokens=${assetId}`);
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const data = await resp.json();

          if (data[assetId] !== undefined) {
            latestPrices[assetId] = parseFloat(data[assetId]);
            updatePriceDisplay();
          }
        } catch (err) {
          console.error("Error fetching live price:", err);
        }
      };

      if (buttons.length > 0) {
        buttons.forEach((btn) => {
          btn.addEventListener("click", () => {
            buttons.forEach((b) => b.classList.remove("chip-active"));
            btn.classList.add("chip-active");
            selectedIndex = parseInt(btn.dataset.index) || 0;

            updatePriceDisplay();
            fetchCurrentPrice();

            // Reset Timer
            if (pollingTimer) clearInterval(pollingTimer);
            pollingTimer = setInterval(fetchCurrentPrice, POLLING_INTERVAL);
          });
        });

        // Initialize
        buttons[0].classList.add("chip-active");
        updatePriceDisplay();
        fetchCurrentPrice();
        pollingTimer = setInterval(fetchCurrentPrice, POLLING_INTERVAL);
        console.log("Live polling started for asset:", assetIds[0]);
      } else {
        console.warn("No outcome buttons found in .toggle-group");
      }
    }
  } else {
    // This logs if the elements are missing (e.g., on Portfolio page)
    // console.log("Market detail elements not found, skipping live polling.");
  }
  // --- END FIXED LIVE PRICE SECTION ---

  // ... [Keep existing Settings Form Logic] ...
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
      // ... (keep existing code)
      const usernameInput = settingsForm.querySelector('input[name="username"]');
      const bioInput = settingsForm.querySelector('textarea[name="bio"]');
      const saveBtn = settingsForm.querySelector(".btn-save");
      const usernameNote = settingsForm.querySelector('.validation-note[data-for="username"]');

      const initialState = {
        username: usernameInput ? usernameInput.value : "",
        bio: bioInput ? bioInput.value : "",
      };

      const validateUsername = () => {
        if (!usernameInput) return true;
        const val = usernameInput.value.trim();
        let valid = true;
        if (val.length < 3) {
          usernameNote.textContent = "Username must be at least 3 characters.";
          valid = false;
        } else if (val.length > 24) {
          usernameNote.textContent = "Username cannot exceed 24 characters.";
          valid = false;
        } else {
          usernameNote.textContent = "";
        }
        usernameNote.classList.toggle("error", !valid);
        return valid;
      };

      const markChanged = () => {
        const changed =
          (usernameInput && usernameInput.value !== initialState.username) ||
          (bioInput && bioInput.value !== initialState.bio);
        if (saveBtn) {
          saveBtn.disabled = !changed || !validateUsername();
          saveBtn.classList.toggle("disabled", saveBtn.disabled);
        }
      };

      if (usernameInput) {
        usernameInput.addEventListener("input", () => {
          validateUsername();
          markChanged();
        });
      }
      if (bioInput) {
        bioInput.addEventListener("input", markChanged);
      }

      settingsForm.addEventListener("submit", (e) => {
        if (!validateUsername()) {
          e.preventDefault();
          return;
        }
      });
      markChanged();
  }

  // ... [Keep Chart Logic] ...
  // Historical price chart rendering (only on market detail page)
  const priceChartCanvas = document.getElementById("priceChart");
  // ... (keep the rest of the file as is)
  if (priceChartCanvas) {
    // Set up interval selector buttons
    const intervalButtons = document.querySelectorAll('.interval-btn');

    if (intervalButtons.length > 0) {
      intervalButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          // Remove active class from all buttons
          intervalButtons.forEach(b => b.classList.remove('active'));
          // Add active class to clicked button
          this.classList.add('active');
          // Get interval and reload chart
          const interval = this.dataset.interval;
          loadChartWithInterval(interval);
        });
      });
    }

    // Load Chart.js dynamically if not already loaded
    if (typeof Chart === 'undefined') {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
      script.onload = () => initializePriceChart('1h');
      document.head.appendChild(script);
    } else {
      initializePriceChart('1h');
    }
  }

  let currentChart = null;

  function loadChartWithInterval(interval) {
    // ... (Keep existing loadChartWithInterval implementation)
    const assetIdsElement = document.getElementById("assetIdsData");
    if (!assetIdsElement) return;

    let assetIds;
    try {
      const parsed = JSON.parse(assetIdsElement.textContent);
      // Ensure assetIds is an array
      if (Array.isArray(parsed)) {
        assetIds = parsed;
      } else if (typeof parsed === 'string') {
        try { assetIds = JSON.parse(parsed); } catch { assetIds = [parsed]; }
      } else if (parsed !== null && parsed !== undefined) {
        assetIds = [parsed];
      }
      if (!Array.isArray(assetIds)) assetIds = [assetIds];
    } catch (e) {
      console.error("Error parsing asset IDs:", e);
      return;
    }

    if (!assetIds || assetIds.length === 0) return;

    const params = new URLSearchParams();
    assetIds.forEach(id => {
      if (id) params.append('assets', id);
    });
    params.append('interval', interval);

    if (interval === '1m') params.append('fidelity', '10');
    else if (interval === '1w') params.append('fidelity', '5');

    fetch(`/api/historical_prices?${params.toString()}`)
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
      })
      .then(data => {
        const dataElement = document.getElementById("historicalPricesData");
        if (dataElement) dataElement.textContent = JSON.stringify(data);
        initializePriceChart(interval);
      })
      .catch(error => console.error("Error fetching historical prices:", error));
  }

  function initializePriceChart(interval = '1h') {
      // ... (Keep existing initializePriceChart implementation)
      const dataElement = document.getElementById("historicalPricesData");
      if (!dataElement) return;

      let historicalPrices;
      try {
        historicalPrices = JSON.parse(dataElement.textContent);
      } catch (e) {
        console.error("Error parsing historical prices JSON:", e);
        return;
      }

      const ctx = document.getElementById("priceChart");
      if (!ctx) return;

      const datasets = [];
      const colors = [
        { border: 'rgba(239, 68, 68, 1)', background: 'rgba(239, 68, 68, 0.1)' },
        { border: 'rgba(34, 197, 94, 1)', background: 'rgba(34, 197, 94, 0.1)' },
        { border: 'rgba(99, 102, 241, 1)', background: 'rgba(99, 102, 241, 0.1)' },
        { border: 'rgba(251, 146, 60, 1)', background: 'rgba(251, 146, 60, 0.1)' }
      ];

      let colorIndex = 0;
      let datasetIndex = 0;
      let allLabels = null;

      for (const [assetId, priceData] of Object.entries(historicalPrices)) {
        if (!priceData || typeof priceData !== 'object') continue;

        let pricePoints = [];
        if (priceData.history && Array.isArray(priceData.history)) pricePoints = priceData.history;
        else if (Array.isArray(priceData)) pricePoints = priceData;
        else if (priceData.prices && Array.isArray(priceData.prices)) pricePoints = priceData.prices;
        else if (priceData.data && Array.isArray(priceData.data)) pricePoints = priceData.data;
        else if (priceData.values && Array.isArray(priceData.values)) pricePoints = priceData.values;

        if (pricePoints.length === 0) continue;

        const chartData = pricePoints
          .map((point, index) => {
            let timestamp = null;
            if (point.t !== undefined && point.t !== null) timestamp = typeof point.t === 'number' ? point.t * 1000 : new Date(point.t).getTime();
            else if (point.timestamp) timestamp = typeof point.timestamp === 'number' ? point.timestamp : new Date(point.timestamp).getTime();
            else if (point.time) timestamp = typeof point.time === 'number' ? point.time : new Date(point.time).getTime();
            else if (point.date) timestamp = typeof point.date === 'number' ? point.date : new Date(point.date).getTime();
            else if (point[0] !== undefined && typeof point[0] === 'number') timestamp = point[0];
            else timestamp = index;

            let price = null;
            if (point.p !== undefined && point.p !== null) price = parseFloat(point.p);
            else if (point.price !== undefined && point.price !== null) price = parseFloat(point.price);
            else if (point.value !== undefined && point.value !== null) price = parseFloat(point.value);
            else if (point.close !== undefined && point.close !== null) price = parseFloat(point.close);
            else if (point[1] !== undefined && typeof point[1] === 'number') price = parseFloat(point[1]);

            return { timestamp, price };
          })
          .filter(point => point.timestamp !== null && point.price !== null && !isNaN(point.price))
          .sort((a, b) => a.timestamp - b.timestamp);

        if (chartData.length === 0) continue;

        const color = colors[colorIndex % colors.length];
        colorIndex++;

        if (allLabels === null) {
          allLabels = chartData.map(point => {
            if (point.timestamp && typeof point.timestamp === 'number') return new Date(point.timestamp).toISOString();
            return `Point ${point.timestamp}`;
          });
        }

        const label = datasetIndex === 1 ? "Yes" : datasetIndex === 0 ? "No" : `Asset ${assetId.substring(0, 8)}...`;

        datasets.push({
          label,
          data: chartData.map(point => point.price),
          borderColor: color.border,
          backgroundColor: color.background,
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 4
        });
        datasetIndex++;
      }

      if (datasets.length === 0) {
        if (!currentChart) {
          const container = ctx.parentElement;
          if (!container.querySelector('.chart-placeholder')) {
            const placeholder = document.createElement('div');
            placeholder.className = 'chart-placeholder';
            placeholder.innerHTML = '<span>No valid price data to display.</span>';
            container.appendChild(placeholder);
          }
        }
        return;
      }

      const labels = allLabels || datasets[0].data.map((_, i) => `Point ${i + 1}`);
      const container = ctx.parentElement;
      const placeholder = container.querySelector('.chart-placeholder');
      if (placeholder) placeholder.remove();

      if (currentChart) {
        currentChart.destroy();
        currentChart = null;
      }

      try {
        currentChart = new Chart(ctx, {
          type: 'line',
          data: { labels: labels, datasets: datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
              legend: { display: datasets.length > 1, position: 'top', labels: { usePointStyle: true, padding: 15, font: { size: 12 } } },
              tooltip: {
                callbacks: {
                  title: function(context) { return labels[context[0].dataIndex] || ''; },
                  label: function(context) { return `${context.dataset.label}: $${context.parsed.y.toFixed(4)}`; }
                }
              }
            },
            scales: {
              x: { title: { display: true, text: 'Time' }, grid: { color: 'rgba(0, 0, 0, 0.05)' }, ticks: { maxRotation: 45, minRotation: 45 } },
              y: { title: { display: true, text: 'Price (USD)' }, min: 0, max: 1, grid: { color: 'rgba(0, 0, 0, 0.05)' }, ticks: { callback: function(value) { return '$' + value.toFixed(4); } } }
            }
          }
        });
      } catch (error) {
        console.error("Error creating chart:", error);
      }
  }
});
