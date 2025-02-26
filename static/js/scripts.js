// Function for searching patients by name
function filterPatients() {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let table = document.getElementById("patientTable");
    let rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {  // Start at 1 to skip the header row
        let cells = rows[i].getElementsByTagName("td");
        let name = cells[1].textContent.toLowerCase();  // Name is in the second column (index 1)

        // Show row if name or cancer type matches the search input
        if (name.includes(input)) {
            rows[i].style.display = "";
        } else {
            rows[i].style.display = "none";
        }
    }
}