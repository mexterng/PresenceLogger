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
          throw new Error("Fehler beim Löschen der Log-Dateien.");
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
  const fileInput = document.getElementById("importASVFile");
  if (importASVBtn) {
    importASVBtn.addEventListener("click", () => {
      if (confirm("Möchten Sie die ASV-Datei und damit alle Gruppen überschreiben? Diese Aktion kann nicht rückgängig gemacht werden!")) {
        fileInput.click();
      }
    });
    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (file) {
        const formData = new FormData();
        formData.append("confirm", 'true');
        formData.append("file", file);

        // Sende die Datei mit einer POST-Anfrage
        fetch("/api/import-asv", {
          method: "POST",
          body: formData
        })
        .then(response => {
          if (response.ok) {
            return response.json();
          }
          throw new Error("Fehler beim Hochladen der ASV-Datei.");
        })
        .then(data => {
          alert(data.message);
          
          // generate groups from uploaded asv-data
          fetch("/api/generate-groups", {
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
            throw new Error("Fehler beim Erstellen der Gruppen.");
          })
          .then(message => {
            alert(message);
          })
          .catch(error => {
            alert(error.message);
          });

        })
        .catch(error => {
          alert(error.message);
        });
      }
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const importGroupsBtn = document.getElementById("importGroupsBtn");
  const fileInput = document.getElementById("importGroupFilesBtn");

  if (importGroupsBtn) {
    importGroupsBtn.addEventListener("click", () => {
      if (confirm("Möchten Sie Gruppen-Dateien importieren? Mögliche bestehende ASV-Datei und Gruppen-Dateien werden gelöscht.")) {
        fileInput.click();
      }
    });
    fileInput.addEventListener("change", () => {
      const files = fileInput.files;
      if (files.length === 0) {
        alert("Keine Dateien ausgewählt.");
        return;
      }

      const formData = new FormData();
      formData.append("confirm", "true");

      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }

      fetch("/api/import-groups", {
        method: "POST",
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          alert("Fehler: " + data.error);
        } else {
          alert(data.message);
        }
      })
      .catch(error => {
        alert("Fehler beim Hochladen: " + error.message);
      });
    });
  }
});