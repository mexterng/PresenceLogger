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
      alert("ASV-Datei exportieren Funktion noch nicht implementiert.");
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const uploadASVBtn = document.getElementById("uploadASVBtn");
  if (uploadASVBtn) {
    uploadASVBtn.addEventListener("click", () => {
      alert("ASV-Datei auswählen Funktion noch nicht implementiert.");
    });
  }
});