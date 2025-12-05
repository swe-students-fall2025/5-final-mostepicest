console.log("PolyPaper frontend loaded");

document.addEventListener("DOMContentLoaded", () => {
  const mockTradeBtn = document.querySelector(".trade-ticket .btn-primary");
  if (mockTradeBtn) {
    mockTradeBtn.addEventListener("click", () => {
      alert("Trading will be enabled once the backend/API is connected.");
    });
  }
});