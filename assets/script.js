// Global variables
let eventsData = []
let filteredData = []

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners()
  fetchEventsData()
})

// Setup event listeners
function setupEventListeners() {
  // Background upload functionality
  const backgroundUpload = document.getElementById("background-upload")
  if (backgroundUpload) {
    backgroundUpload.addEventListener("change", handleBackgroundUpload)
  }

  // Filter inputs
  const filterInputs = document.querySelectorAll(".filter-input")
  filterInputs.forEach((input) => {
    input.addEventListener("input", handleFilterChange)
  })
}

// Handle background image upload
function handleBackgroundUpload(event) {
  const file = event.target.files[0]
  if (file && file.type.startsWith("image/")) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const backgroundImage = document.getElementById("background-image")
      if (backgroundImage) {
        backgroundImage.src = e.target.result
      }
    }
    reader.readAsDataURL(file)
  }
}

// Fetch events data from JSON file
async function fetchEventsData() {
  try {
    const response = await fetch("/data/events_upcoming.json")
    if (response.ok) {
      eventsData = await response.json()
      filteredData = [...eventsData]
      renderTable()
    } else {
      console.warn("Failed to fetch events data")
      eventsData = []
      filteredData = []
      renderTable()
    }
  } catch (error) {
    console.warn("Error fetching events data:", error)
    eventsData = []
    filteredData = []
    renderTable()
  }
}

// Handle filter changes
function handleFilterChange() {
  const filters = {
    name: document.getElementById("filter-name").value.toLowerCase(),
    start: document.getElementById("filter-start").value.toLowerCase(),
    end: document.getElementById("filter-end").value.toLowerCase(),
    location: document.getElementById("filter-location").value.toLowerCase(),
    url: document.getElementById("filter-url").value.toLowerCase(),
  }

  filteredData = eventsData.filter((event) => {
    return (
      event.name.toLowerCase().includes(filters.name) &&
      event.start_date.toLowerCase().includes(filters.start) &&
      event.end_date.toLowerCase().includes(filters.end) &&
      event.location.toLowerCase().includes(filters.location) &&
      event.url.toLowerCase().includes(filters.url)
    )
  })

  renderTable()
}

// Render the events table
function renderTable() {
  const tbody = document.getElementById("events-tbody")
  if (!tbody) return

  tbody.innerHTML = ""

  filteredData.forEach((event) => {
    const row = document.createElement("tr")

    // Event name
    const nameCell = document.createElement("td")
    nameCell.textContent = event.name || ""
    row.appendChild(nameCell)

    // Start date
    const startCell = document.createElement("td")
    startCell.textContent = event.start_date || ""
    row.appendChild(startCell)

    // End date
    const endCell = document.createElement("td")
    endCell.textContent = event.end_date || ""
    row.appendChild(endCell)

    // Location
    const locationCell = document.createElement("td")
    locationCell.textContent = event.location || ""
    row.appendChild(locationCell)

    // URL
    const urlCell = document.createElement("td")
    if (event.url && event.url.trim()) {
      const link = document.createElement("a")
      link.href = event.url
      link.target = "_blank"
      link.rel = "noopener"
      link.textContent = "Visit"
      urlCell.appendChild(link)
    }
    row.appendChild(urlCell)

    tbody.appendChild(row)
  })
}
