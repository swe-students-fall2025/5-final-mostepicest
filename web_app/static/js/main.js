console.log("PolyPaper frontend loaded");

document.addEventListener("DOMContentLoaded", () => {
  const mockTradeBtn = document.querySelector(".trade-ticket .btn-primary");
  if (mockTradeBtn) {
    mockTradeBtn.addEventListener("click", () => {
      alert("Trading will be enabled once the backend/API is connected.");
    });
  }

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

  const toggleGroup = document.querySelector(".toggle-group");
  const estPriceEl = document.getElementById("est-price");

  if (toggleGroup && estPriceEl) {
    // Only run this if we are on a market detail page
    const buttons = toggleGroup.querySelectorAll("button");
    const outcomePrices = JSON.parse(estPriceEl.dataset.outcomePrices); // see note below

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        // Remove active from all
        buttons.forEach((b) => b.classList.remove("chip-active"));
        // Add active to clicked
        btn.classList.add("chip-active");

        const index = parseInt(btn.dataset.index);
        const price = parseFloat(outcomePrices[index]) * 100;
        estPriceEl.textContent = `$${price.toFixed(2)} / share`;
      });
    });
  }

  // Settings form: basic validation and "changed" detection to enable the Save button
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
    const usernameInput = settingsForm.querySelector('input[name="username"]');
    const bioInput = settingsForm.querySelector('textarea[name="bio"]');
    const saveBtn = settingsForm.querySelector(".btn-save");
    const usernameNote = settingsForm.querySelector(
      '.validation-note[data-for="username"]'
    );

    const initialState = {
      username: usernameInput ? usernameInput.value : "",
      bio: bioInput ? bioInput.value : "",
    };

    // Here we validate the username so it must be within 3-24 characters
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
      // Validate before submitting - if invalid, prevent submission
      if (!validateUsername()) {
        e.preventDefault();
        return;
      }
    });

    // Initialize state on load
    markChanged();
  }

  // Historical price chart rendering (only on market detail page)
  const priceChartCanvas = document.getElementById("priceChart");
  if (priceChartCanvas) {
    // Set up interval selector buttons
    const intervalButtons = document.querySelectorAll('.interval-btn');
    console.log("Found interval buttons:", intervalButtons.length);
    
    if (intervalButtons.length > 0) {
      intervalButtons.forEach(btn => {
        console.log("Setting up button:", btn.dataset.interval);
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          console.log("Button clicked:", this.dataset.interval);
          // Remove active class from all buttons
          intervalButtons.forEach(b => b.classList.remove('active'));
          // Add active class to clicked button
          this.classList.add('active');
          // Get interval and reload chart
          const interval = this.dataset.interval;
          console.log("Loading interval:", interval);
          loadChartWithInterval(interval);
        });
      });
    } else {
      console.warn("No interval buttons found");
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
    console.log("Loading chart with interval:", interval);
    const assetIdsElement = document.getElementById("assetIdsData");
    if (!assetIdsElement) {
      console.error("assetIdsData element not found");
      return;
    }

    let assetIds;
    try {
      const parsed = JSON.parse(assetIdsElement.textContent);
      console.log("Parsed asset IDs:", parsed, typeof parsed);
      
      // Ensure assetIds is an array
      if (Array.isArray(parsed)) {
        assetIds = parsed;
      } else if (typeof parsed === 'string') {
        // If it's a string, try to parse it again or convert to array
        try {
          assetIds = JSON.parse(parsed);
        } catch {
          assetIds = [parsed];
        }
      } else if (parsed !== null && parsed !== undefined) {
        // If it's an object or other type, try to convert to array
        assetIds = [parsed];
      } else {
        console.error("Invalid asset IDs format:", parsed);
        return;
      }
      
      // Ensure it's still an array
      if (!Array.isArray(assetIds)) {
        assetIds = [assetIds];
      }
      
      console.log("Final asset IDs:", assetIds);
    } catch (e) {
      console.error("Error parsing asset IDs:", e);
      return;
    }

    if (!assetIds || assetIds.length === 0) {
      console.error("No asset IDs found");
      return;
    }

    // Ensure assetIds is an array
    if (!Array.isArray(assetIds)) {
      console.error("assetIds is not an array:", assetIds);
      assetIds = [assetIds];
    }
    
    // Build query string for multiple assets
    const params = new URLSearchParams();
    assetIds.forEach(id => {
      if (id) {
        params.append('assets', id);
      }
    });
    params.append('interval', interval);
    
    // Add fidelity parameter based on interval
    if (interval === '1m') {
      params.append('fidelity', '10');
    } else if (interval === '1w') {
      params.append('fidelity', '5');
    }
    // Other intervals don't need fidelity

    console.log("Fetching from:", `/api/historical_prices?${params.toString()}`);

    // Fetch new data
    fetch(`/api/historical_prices?${params.toString()}`)
      .then(response => {
        console.log("Response status:", response.status);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log("Received data:", data);
        // Update the hidden data element
        const dataElement = document.getElementById("historicalPricesData");
        if (dataElement) {
          dataElement.textContent = JSON.stringify(data);
        }
        // Reinitialize chart with new data
        initializePriceChart(interval);
      })
      .catch(error => {
        console.error("Error fetching historical prices:", error);
      });
  }

  function initializePriceChart(interval = '1h') {
    console.log("Initializing chart with interval:", interval);
    const dataElement = document.getElementById("historicalPricesData");
    if (!dataElement) {
      console.error("historicalPricesData element not found");
      return;
    }
    
    let historicalPrices;
    try {
      historicalPrices = JSON.parse(dataElement.textContent);
      console.log("Parsed historical prices:", historicalPrices);
    } catch (e) {
      console.error("Error parsing historical prices JSON:", e);
      return;
    }
    
    const ctx = document.getElementById("priceChart");
    if (!ctx) {
      console.error("priceChart canvas element not found");
      return;
    }
    
    // Process historical price data
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
      console.log(`Processing asset ${assetId}:`, priceData);
      if (!priceData || typeof priceData !== 'object') {
        console.log(`Skipping ${assetId}: not an object`);
        continue;
      }
      
      // Extract price points from different possible data structures
      let pricePoints = [];
      
      // Primary structure: history array with t (timestamp) and p (price)
      if (priceData.history && Array.isArray(priceData.history)) {
        pricePoints = priceData.history;
      } else if (Array.isArray(priceData)) {
        pricePoints = priceData;
      } else if (priceData.prices && Array.isArray(priceData.prices)) {
        pricePoints = priceData.prices;
      } else if (priceData.data && Array.isArray(priceData.data)) {
        pricePoints = priceData.data;
      } else if (priceData.values && Array.isArray(priceData.values)) {
        pricePoints = priceData.values;
      }
      
      console.log(`Found ${pricePoints.length} price points for ${assetId}`);
      if (pricePoints.length === 0) {
        console.log(`No price points found for ${assetId}`);
        continue;
      }
      
      // Fidelity filtering is now handled on the server side via API parameter
      // No need to filter on client side anymore
      let filteredPricePoints = pricePoints;
      
      // Process price points to extract time and price
      const chartData = filteredPricePoints
        .map((point, index) => {
          // Extract timestamp - check for 't' field first (Polymarket format)
          let timestamp = null;
          if (point.t !== undefined && point.t !== null) {
            // 't' is Unix timestamp in seconds, convert to milliseconds for JavaScript Date
            timestamp = typeof point.t === 'number' ? point.t * 1000 : new Date(point.t).getTime();
          } else if (point.timestamp) {
            timestamp = typeof point.timestamp === 'number' 
              ? point.timestamp 
              : new Date(point.timestamp).getTime();
          } else if (point.time) {
            timestamp = typeof point.time === 'number' 
              ? point.time 
              : new Date(point.time).getTime();
          } else if (point.date) {
            timestamp = typeof point.date === 'number' 
              ? point.date 
              : new Date(point.date).getTime();
          } else if (point[0] !== undefined && typeof point[0] === 'number') {
            // Handle array format [timestamp, price]
            timestamp = point[0];
          } else {
            // Fallback: use index as timestamp if no timestamp available
            timestamp = index;
          }
          
          // Extract price - check for 'p' field first (Polymarket format)
          let price = null;
          if (point.p !== undefined && point.p !== null) {
            price = parseFloat(point.p);
          } else if (point.price !== undefined && point.price !== null) {
            price = parseFloat(point.price);
          } else if (point.value !== undefined && point.value !== null) {
            price = parseFloat(point.value);
          } else if (point.close !== undefined && point.close !== null) {
            price = parseFloat(point.close);
          } else if (point[1] !== undefined && typeof point[1] === 'number') {
            // Handle array format [timestamp, price]
            price = parseFloat(point[1]);
          }
          
          return { timestamp, price };
        })
        .filter(point => point.timestamp !== null && point.price !== null && !isNaN(point.price))
        .sort((a, b) => a.timestamp - b.timestamp);
      
      console.log(`Processed ${chartData.length} valid data points for ${assetId}`);
      if (chartData.length === 0) {
        console.log(`No valid chart data for ${assetId}`);
        continue;
      }
      
      const color = colors[colorIndex % colors.length];
      colorIndex++;
      
      // Create labels from the first dataset (use timestamps from chartData)
      // Note: timestamps in chartData are already converted to milliseconds
      if (allLabels === null) {
        allLabels = chartData.map(point => {
          if (point.timestamp && typeof point.timestamp === 'number') {
            // Timestamps are already in milliseconds (converted from Unix seconds)
            // Convert to ISO date string for display
            return new Date(point.timestamp).toISOString();
          }
          return `Point ${point.timestamp}`;
        });
      }
      
      const label =
        datasetIndex === 1
          ? "Yes"
          : datasetIndex === 0
            ? "No"
            : `Asset ${assetId.substring(0, 8)}...`;

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
    
    console.log(`Created ${datasets.length} datasets`);
    if (datasets.length === 0) {
      console.error("No datasets created");
      // Don't destroy the chart, just show a message or keep the existing chart
      if (!currentChart) {
        // Only show placeholder if there's no existing chart
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
    
    // Use labels from first dataset or create default labels
    const labels = allLabels || datasets[0].data.map((_, i) => `Point ${i + 1}`);
    
    console.log("Creating chart with", datasets.length, "datasets and", labels.length, "labels");
    
    // Remove any placeholder messages
    const container = ctx.parentElement;
    const placeholder = container.querySelector('.chart-placeholder');
    if (placeholder) {
      placeholder.remove();
    }
    
    // Destroy existing chart if it exists
    if (currentChart) {
      currentChart.destroy();
      currentChart = null;
    }
    
    // Create the chart
    try {
      currentChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: 'index'
          },
          plugins: {
            legend: {
              display: datasets.length > 1,
              position: 'top',
              labels: {
                usePointStyle: true,
                padding: 15,
                font: {
                  size: 12
                }
              }
            },
            tooltip: {
              callbacks: {
                title: function(context) {
                  // Get the label (ISO date) for the x-axis value
                  const labelIndex = context[0].dataIndex;
                  return labels[labelIndex] || '';
                },
                label: function(context) {
                  return `${context.dataset.label}: $${context.parsed.y.toFixed(4)}`;
                }
              }
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Time'
              },
              grid: {
                color: 'rgba(0, 0, 0, 0.05)'
              },
              ticks: {
                maxRotation: 45,
                minRotation: 45
              }
            },
            y: {
              title: {
                display: true,
                text: 'Price (USD)'
              },
              min: 0,
              max: 1,
              grid: {
                color: 'rgba(0, 0, 0, 0.05)'
              },
              ticks: {
                callback: function(value) {
                  return '$' + value.toFixed(4);
                }
              }
            }
          }
        }
      });
      console.log("Chart created successfully");
    } catch (error) {
      console.error("Error creating chart:", error);
      // Don't replace the canvas, just log the error
      // Keep the existing chart if it exists
      if (!currentChart) {
        const container = ctx.parentElement;
        if (!container.querySelector('.chart-placeholder')) {
          const placeholder = document.createElement('div');
          placeholder.className = 'chart-placeholder';
          placeholder.innerHTML = '<span>Error rendering chart. Check console for details.</span>';
          container.appendChild(placeholder);
        }
      }
    }
  }
});
