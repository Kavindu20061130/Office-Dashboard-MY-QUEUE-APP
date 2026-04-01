function updateOfficeID() {
  const select = document.getElementById('officeSelect');
  const display = document.getElementById('officeIdDisplay');

  if (select.value) {
    // Extract number from "office_1"
    const idNumber = select.value.split('_')[1];
    display.textContent = "Office ID-" + idNumber;
  } else {
    display.textContent = "Office ID: Select to see ID";
  }
}

document.addEventListener("DOMContentLoaded", () => {
    const counters = document.querySelectorAll('.stat-number');
    const speed = 200; // The lower the slower

    counters.forEach(counter => {
        const updateCount = () => {
            const target = +counter.getAttribute('data-target');
            const count = +counter.innerText;

            // Calculate increment based on target
            const inc = target / speed;

            if (count < target) {
                // Add increment and recurse
                counter.innerText = Math.ceil(count + inc);
                setTimeout(updateCount, 10);
            } else {
                counter.innerText = target;
            }
        };

        updateCount();
    });
});

async function loadOffices() {
  try {
    const response = await fetch('/get-offices');
    const data = await response.json();

    const select = document.getElementById('officeSelect');
    select.innerHTML = '<option value="">-- Select Office --</option>';

    data.forEach(office => {
      let option = document.createElement('option');
      option.value = office.id;
      option.textContent = office.name;
      select.appendChild(option);
    });

  } catch (err) {
    const select = document.getElementById('officeSelect');
    select.innerHTML = `
      <option value="">Select Office</option>
      <option value="office_1">DS Kandy</option>
    `;
  }
}

window.onload = loadOffices;