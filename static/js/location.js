document.addEventListener('DOMContentLoaded', function () {
const modal = new bootstrap.Modal(document.getElementById('locationModal'));
const cards = document.querySelectorAll('.location-card');
const seeMoreButton = document.getElementById('see-more-btn');
const modalMap = document.getElementById('modal-map');
const modalLocationName = document.getElementById('modal-location-name');
const modalLocationAddress = document.getElementById('modal-location-address');

// Handle "See More" button
if (seeMoreButton) {
seeMoreButton.addEventListener('click', function () {
cards.forEach((card, index) => {
if (index >= 3) card.style.display = 'block';
});
seeMoreButton.style.display = 'none';
});
}

// Handle "Detail" button for each card
cards.forEach(card => {
const detailButton = card.querySelector('.btn-primary');

detailButton.addEventListener('click', function () {
const locationId = card.getAttribute('data-id');
const locationName = card.querySelector('.card-title').innerText;
const locationAddress = card.querySelector('.card-text').innerText;
const latitude = card.getAttribute('data-lat');
const longitude = card.getAttribute('data-lng');

// Set modal data
modalLocationName.innerText = locationName;
modalLocationAddress.innerText = locationAddress;

// Set map content
if (latitude && longitude) {
modalMap.src = `https://www.google.com/maps?q=${latitude},${longitude}&z=15&output=embed`;
} else if (locationId) {
fetch(`/location/map/${locationId}`)
.then(response => {
if (!response.ok) throw new Error("Failed to load map, display map default");
return response.text();
})
.then(html => {
modalMap.srcdoc = html;
})
.catch(error => {
console.error(error);
alert("Failed to load map, display map default");
});
} else {
modalMap.src = "/static/preview/preview_map.html"; // Default map
}

modal.show();
});
});

// Clean up modal backdrop on close
document.addEventListener('hidden.bs.modal', function () {
document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
});
});