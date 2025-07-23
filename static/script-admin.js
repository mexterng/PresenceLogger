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
  const deleteLogsBtn = document.getElementById("deleteLogsBtn");
  if (deleteLogsBtn) {
    deleteLogsBtn.addEventListener("click", () => {
      if (confirm("Möchten Sie alle Log-Dateien unwiderruflich löschen? Diese Aktion kann nicht rückgängig gemacht werden!")) {
        fetch("/api/delete-log", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ confirm: true })
        })
        .then(response => {
          if (response.ok) {
            return response.text();
          }
          throw new Error("Fehler beim Löschen der Log-Dateien");
        })
        .then(message => {
          alert(message);
        })
        .catch(error => {
          alert(error.message);
        });
      }
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