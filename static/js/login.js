function updateOfficeID() {  // Function to update displayed office ID
  const select = document.getElementById('officeSelect');  // Get dropdown element
  const display = document.getElementById('officeIdDisplay');  // Get display element

  if (select.value) {  // Check if an option is selected
    const idNumber = select.value.split('_')[1];  // Extract number after underscore
    display.textContent = "Office ID-" + idNumber;  // Show formatted office ID
  } else {  // If nothing selected
    display.textContent = "Office ID: Select to see ID";  // Show default message
  }
}


document.addEventListener("DOMContentLoaded", () => {  // Run when page loads
    const counters = document.querySelectorAll('.stat-number');  // Get all counter elements
    const speed = 200;  // Control animation speed

    counters.forEach(counter => {  // Loop through each counter
        const updateCount = () => {  // Function to update counter
            const target = +counter.getAttribute('data-target');  // Get target value
            const count = +counter.innerText;  // Get current value

            const inc = target / speed;  // Calculate increment value

            if (count < target) {  // If current value is less than target
                counter.innerText = Math.ceil(count + inc);  // Increase value
                setTimeout(updateCount, 10);  // Repeat after delay
            } else {  // If target reached
                counter.innerText = target;  // Set final value
            }
        };

        updateCount();  // Start counter animation
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
    console.error("Error loading offices:", err);
  }
}

window.onload = loadOffices;  // Call function when page fully loads