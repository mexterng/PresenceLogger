// Load initials from localStorage
document.addEventListener("DOMContentLoaded", () => {
    const savedInitials = localStorage.getItem("initials");
    if (savedInitials) {
        document.getElementById("initials").value = savedInitials;
    }
});

document.getElementById("groupSelect").addEventListener("change", () => {
    const group = document.getElementById("groupSelect").value;
    if (!group) return;
    
    fetch("/get_members", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ group: group })
    })
    .then(response => response.json())
    .then(data => {
        const list = data.members;
        const memberList = document.getElementById("memberList");
        memberList.innerHTML = "";

        if (!list || list.length === 0) {
            memberList.innerText = "Keine Mitglieder gefunden.";
            return;
        }
        else{
            document.getElementById("statusMsg").innerText = "";
        }

        let table = `<table><tr><th></th><th>Nachname</th><th>Vorname</th></tr>`;
        list.forEach((person, index) => {
            table += `<tr>
                        <td><input type="checkbox" class="personCheck" data-index="${index}"></td>
                        <td>${person.lastname}</td>
                        <td>${person.firstname}</td>
                        <td><a href="/edit?group=${encodeURIComponent(group)}&id=${person.id}" class="editIcon" title="Bearbeiten">&#9998;</a></td>
                    </tr>`;
        });
        table += "</table>";
        memberList.innerHTML = table;

        // Save member list to element
        memberList.dataset.members = JSON.stringify(list);
    });
});

function submitAction(actionType) {
    const initials = document.getElementById("initials").value.trim();
    const group = document.getElementById("groupSelect").value;
    const memberList = document.getElementById("memberList");
    const checkboxes = document.querySelectorAll(".personCheck");
    const fullList = JSON.parse(memberList.dataset.members || "[]");

    missingFields = false;
    document.getElementById("statusMsg").innerText = "";
    if (!initials) {
        document.getElementById("statusMsg").innerText = "Bitte Kürzel angeben.";
        missingFields = true;
    }
    if (!group) {
        document.getElementById("statusMsg").innerText += "\nBitte eine Gruppe auswählen.";
        missingFields = true;
    }
    if (group && checkboxes.length === 0) {
        document.getElementById("statusMsg").innerText += "\nKeine Mitglieder gefunden.";
        missingFields = true;
    }
    
    const selected = [];
    checkboxes.forEach(cb => {
        if (cb.checked) {
            const person = fullList[cb.dataset.index];
            selected.push(person);
        }
    });

    if (selected.length === 0 && checkboxes.length > 0) {
        document.getElementById("statusMsg").innerText += "\nBitte eine Person auswählen.";
        missingFields = true;
    }
    if (missingFields) {
        return;
    }
    
    // Save initials
    localStorage.setItem("initials", initials);

    fetch("/submit_action", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            initials: initials,
            group: group,
            people: selected,
            action: actionType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.error) {
            document.getElementById("statusMsg").innerText = "Änderung gespeichert: " + data.action;
        } else {
            document.getElementById("statusMsg").innerText = "Fehler: " + data.error;
        }
    })
    .catch(error => {
        console.error(error);
        document.getElementById("statusMsg").innerText = "Fehler beim Speichern.";
    });
}

document.getElementById("entryBtn").addEventListener("click", () => {
    submitAction("eingetreten");
});

document.getElementById("exitBtn").addEventListener("click", () => {
    submitAction("ausgetreten");
});