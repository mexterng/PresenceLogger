function highlightFavoriteOptions() {
  const favs = JSON.parse(localStorage.getItem("favoriteGroups") || "[]");
  const select = document.getElementById("groupSelect");

  // Alle echten Gruppen-Optionen (erste Option ist Platzhalter) erfassen
  const allOpts = [...select.options].slice(1);

  // Beschriftung aktualisieren + in zwei Listen aufteilen
  const favOpts = [];
  const otherOpts = [];
  for (const opt of allOpts) {
    if (favs.includes(opt.value)) {
      opt.textContent = `★ ${opt.value}`;
      favOpts.push(opt);
    } else {
      opt.textContent = opt.value;
      otherOpts.push(opt);
    }
  }

  // Neu anordnen: Favoriten zuerst (alphabetisch), dann der Rest
  [
    ...favOpts.sort((a, b) => a.value.localeCompare(b.value)),
    ...otherOpts.sort((a, b) => a.value.localeCompare(b.value)),
  ].forEach((o) => select.appendChild(o));
}

function loadMembers(group) {
  if (!group) return;

  updateFavoriteStar();

  fetch("/get_members", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ group: group }),
  })
    .then((response) => response.json())
    .then((data) => {
      const list = data.members;
      const memberList = document.getElementById("memberList");
      memberList.innerHTML = "";

      if (!list || list.length === 0) {
        memberList.innerText = "Keine Mitglieder gefunden.";
        return;
      } else {
        document.getElementById("statusMsg").innerText = "";
      }

      let table = `<table><tr><th></th><th>Nachname</th><th>Vorname</th></tr>`;
      list.forEach((person, index) => {
        table += `<tr>
                        <td><input type="checkbox" class="personRadio" name="selectedPerson" data-index="${index}"></td>
                        <td onclick="selectPerson(${index})" style="cursor:pointer;">${person.lastname}</td>
                        <td onclick="selectPerson(${index})" style="cursor:pointer;">${person.firstname}</td>
                      </tr>`;
      });
      table += "</table>";
      memberList.innerHTML = table;

      memberList.dataset.members = JSON.stringify(list);
    });
}

function selectPerson(index) {
  const radio = document.querySelector(
    `input.personRadio[data-index="${index}"]`
  );
  if (radio) {
    radio.checked = !radio.checked;
    radio.dispatchEvent(new Event("change"));
  }
}

document.getElementById("groupSelect").addEventListener("change", () => {
  updateFavoriteStar();
  const group = document.getElementById("groupSelect").value;
  loadMembers(group);
});

function submitAction(fileType) {
  const group = document.getElementById("groupSelect").value;
  const memberList = document.getElementById("memberList");
  const radiobuttons = document.querySelectorAll(".personRadio");
  const fullList = JSON.parse(memberList.dataset.members || "[]");

  missingFields = false;
  document.getElementById("statusMsg").innerText = "";
  if (!group) {
    document.getElementById("statusMsg").innerText +=
      "\nBitte eine Gruppe auswählen.";
    missingFields = true;
  }
  if (group && radiobuttons.length === 0) {
    document.getElementById("statusMsg").innerText +=
      "\nKeine Mitglieder gefunden.";
    missingFields = true;
  }

  const selected = [];
  radiobuttons.forEach((rb) => {
    rb.addEventListener("change", () => {
      document.getElementById("statusMsg").innerText = "";
    });
    if (rb.checked) {
      const person = fullList[rb.dataset.index];
      selected.push(person);
    }
  });

  if (selected.length === 0 && radiobuttons.length > 0) {
    document.getElementById("statusMsg").innerText +=
      "\nBitte eine Person auswählen.";
    missingFields = true;
  }
  if (missingFields) {
    return;
  }
  
  // TODO: hier export!
  if (fileType == "CSV"){
    fetch('/api/exportCSV-group', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileType: 'CSV', group: group, selected: selected })
    })
    .then(response => {
      const disposition = response.headers.get("Content-Disposition");
      let filename = "export.zip";  // fallback
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)["']?/i);
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]);
        }
      }
      return response.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    });
  }
  else if(fileType == "PDF"){
    const params = new URLSearchParams();
    selected.forEach(item => params.append("id", item.id));
    window.location.href = `/api/exportPDF-group?${params.toString()}`;
  }
  else{
    console.log("Filetype not supported!")
  }
}

function updateFavoriteStar() {
  const group = document.getElementById("groupSelect").value;
  const favoriteGroups = JSON.parse(
    localStorage.getItem("favoriteGroups") || "[]"
  );
  const star = document.getElementById("favoriteStar");
  if (!group) {
    star.className = "fa-regular fa-star";
    star.style.opacity = 0.3;
    star.style.pointerEvents = "none";
    return;
  }
  star.style.opacity = 1;
  star.style.pointerEvents = "auto";
  if (favoriteGroups.includes(group)) {
    star.className = "fa-solid fa-star";
  } else {
    star.className = "fa-regular fa-star";
  }
  if (favoriteGroups.includes(group)) {
    star.classList.add("filled");
    document
      .getElementById("groupSelect")
      .querySelector(`option[value="${group}"]`).innerHTML = `★ ${group}`;
  } else {
    star.classList.remove("filled");
    document
      .getElementById("groupSelect")
      .querySelector(`option[value="${group}"]`).innerHTML = group;
  }
}

document.getElementById("favoriteStar").addEventListener("click", () => {
  const group = document.getElementById("groupSelect").value;
  if (!group) return;

  let favoriteGroups = JSON.parse(
    localStorage.getItem("favoriteGroups") || "[]"
  );
  const index = favoriteGroups.indexOf(group);
  if (index >= 0) {
    favoriteGroups.splice(index, 1);
  } else {
    favoriteGroups.push(group);
  }
  favoriteGroups.sort((a, b) => a.localeCompare(b));
  localStorage.setItem("favoriteGroups", JSON.stringify(favoriteGroups));
  updateFavoriteStar();
  highlightFavoriteOptions();
});

document.getElementById("pdfExportBtn").addEventListener("click", () => {
  submitAction("PDF");
});

document.getElementById("csvExportBtn").addEventListener("click", () => {
  submitAction("CSV");
});