// helper: find nearest <tr>
function rowOf(elem) { return elem.closest("tr"); }

// zeige Diskette, wenn etwas geändert wurde
function markChanged(row) {
    row.querySelector(".saveIcon").style.display = "inline";
}

/* --- Events beim Laden zuweisen --- */
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".statusSel").forEach(sel => {
        sel.addEventListener("change", () => markChanged(rowOf(sel)));
    });

    document.querySelectorAll(".timeInp").forEach(inp => {
        inp.addEventListener("input", () => markChanged(rowOf(inp)));
    });

    document.querySelectorAll(".dateInp").forEach(inp => {
        inp.addEventListener("input", () => markChanged(rowOf(inp)));
    });

    document.querySelectorAll(".delIcon").forEach(icon => {
        icon.addEventListener("click", () => deleteRow(icon));
    });

    document.querySelectorAll(".saveIcon").forEach(icon => {
        icon.addEventListener("click", () => saveRow(icon));
    });
});

/* -------- löschen -------- */
function deleteRow(icon) {
    if (!confirm("Eintrag wirklich löschen?")) return;
    const row = rowOf(icon);
    const original = JSON.parse(row.querySelector("[data-original]").dataset.original);

    fetch("/api/delete_entry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(original)
    })
    .then(r => r.json())
    .then(res => {
        if (res.removed) row.remove();
        else alert("Löschen fehlgeschlagen");
    });
}

/* -------- speichern -------- */
function saveRow(icon) {
    const row = rowOf(icon);
    const original = JSON.parse(row.querySelector("[data-original]").dataset.original);

    const updated = {
        status: row.querySelector(".statusSel").value,
        timestamp: `${row.querySelector(".dateInp").value} ${row.querySelector(".timeInp").value}`
    };

    fetch("/api/update_entry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ original, updated })
    })
    .then(r => r.json())
    .then(res => {
        if (res.updated) {
            // Diskette ausblenden und Original-Daten ersetzen
            icon.style.display = "none";
            original.status = updated.status;
            original.timestamp = updated.timestamp;
            row.querySelector("[data-original]").dataset.original = JSON.stringify(original);
        } else {
            alert("Speichern fehlgeschlagen");
        }
    });
}