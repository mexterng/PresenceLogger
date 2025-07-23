document.addEventListener("DOMContentLoaded", () => {
  const exportLogsBtn = document.getElementById("exportLogsBtn");
  if (exportLogsBtn) {
    exportLogsBtn.addEventListener("click", () => {
      window.location.href = "/api/export-logs";
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const exportGroupsBtn = document.getElementById("exportGroupsBtn");
  if (exportGroupsBtn) {
    exportGroupsBtn.addEventListener("click", () => {
      window.location.href = "/api/export-groups";
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const exportASVBtn = document.getElementById("exportASVBtn");
  if (exportASVBtn) {
    exportASVBtn.addEventListener("click", () => {
      window.location.href = "/api/export-asv";
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const importASVBtn = document.getElementById("importASVBtn");
  if (importASVBtn) {
    importASVBtn.addEventListener("click", () => {
      alert("ASV-Datei importieren Funktion noch nicht implementiert.");
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const importGroupsBtn = document.getElementById("importGroupsBtn");
  if (importGroupsBtn) {
    importGroupsBtn.addEventListener("click", () => {
      alert("Gruppen importieren Funktion noch nicht implementiert.");
    });
  }
});