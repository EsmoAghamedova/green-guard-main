(function () {
    // Initialize location search components on page load
    document.addEventListener("DOMContentLoaded", function () {
        initializeLocationSearch();
    });

    function initializeLocationSearch() {
        const searchInputs = document.querySelectorAll("[data-location-search]");

        searchInputs.forEach(function (searchInput) {
            const searchContainer = searchInput.closest(".gg-location-search-container");
            const formElement = searchInput.closest("form");
            if (!formElement) return;

            const resultsContainer = searchContainer ? searchContainer.querySelector("[data-location-results]") : null;
            const gpsButton = searchContainer ? searchContainer.querySelector("[data-gps-button]") : null;
            const selectedDisplay = searchContainer ? searchContainer.querySelector("[data-selected-location]") : null;
            const latitudeField = formElement.querySelector("[data-latitude-field]");
            const longitudeField = formElement.querySelector("[data-longitude-field]");
            const locationSourceField = formElement.querySelector("input[name='location_source']");

            if (!latitudeField || !longitudeField) return;

            // Add input listener for location search
            let searchTimeout;
            searchInput.addEventListener("input", function () {
                clearTimeout(searchTimeout);
                const query = this.value.trim();

                clearCoordinates(latitudeField, longitudeField, selectedDisplay, locationSourceField);

                if (query.length < 2) {
                    if (resultsContainer) {
                        resultsContainer.innerHTML = "";
                        resultsContainer.style.display = "none";
                    }
                    return;
                }

                searchTimeout = setTimeout(function () {
                    searchLocations(query, resultsContainer, latitudeField, longitudeField, selectedDisplay, searchInput);
                }, 300);
            });

            // Handle result selection
            if (resultsContainer) {
                resultsContainer.addEventListener("click", function (e) {
                    const resultItem = e.target.closest("[data-result-item]");
                    if (resultItem) {
                        const lat = parseFloat(resultItem.dataset.latitude);
                        const lng = parseFloat(resultItem.dataset.longitude);
                        const name = resultItem.dataset.name;

                        if (!isNaN(lat) && !isNaN(lng)) {
                            latitudeField.value = lat.toFixed(6);
                            longitudeField.value = lng.toFixed(6);
                            searchInput.value = name;

                            resultsContainer.innerHTML = "";
                            resultsContainer.style.display = "none";

                            if (locationSourceField) {
                                locationSourceField.value = "search";
                            }

                            updateSelectedLocation(selectedDisplay, name, lat, lng);
                        }
                    }
                });
            }

            // Handle GPS button
            if (gpsButton) {
                if (!navigator.geolocation) {
                    gpsButton.disabled = true;
                    gpsButton.title = "Your browser does not support GPS geolocation.";
                    return;
                }

                if (!window.isSecureContext) {
                    gpsButton.disabled = true;
                    gpsButton.title = "GPS works only on HTTPS or localhost.";
                    return;
                }

                gpsButton.addEventListener("click", function (e) {
                    e.preventDefault();
                    getGPSLocation(latitudeField, longitudeField, selectedDisplay, searchInput, gpsButton, locationSourceField);
                });
            }

            // Close results when clicking outside
            document.addEventListener("click", function (e) {
                if (!e.target.closest(".gg-location-search-container") &&
                    !e.target.closest("[data-location-search-wrapper]")) {
                    if (resultsContainer) {
                        resultsContainer.style.display = "none";
                    }
                }
            });
        });
    }

    function searchLocations(query, resultsContainer, latField, lonField, displayElement, searchInput) {
        if (!resultsContainer) return;

        resultsContainer.innerHTML = '<div class="gg-location-loading">Searching...</div>';
        resultsContainer.style.display = "block";

        fetch(`/api/search-location?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (!data.results || data.results.length === 0) {
                    resultsContainer.innerHTML = '<div class="gg-location-no-results">No locations found. Try a different search.</div>';
                    return;
                }

                let html = '<ul class="gg-location-results-list">';
                data.results.forEach(function (location, index) {
                    const displayName = location.display_name || location.name || "";
                    const shortName = displayName.split(",")[0];

                    html += `
                        <li class="gg-location-result-item" data-result-item data-latitude="${location.latitude}" 
                            data-longitude="${location.longitude}" data-name="${escapeHtml(shortName)}">
                            <div class="gg-result-main">${escapeHtml(shortName)}</div>
                            <div class="gg-result-secondary">${escapeHtml(displayName.substring(0, 80))}</div>
                        </li>
                    `;
                });
                html += '</ul>';

                resultsContainer.innerHTML = html;
            })
            .catch(error => {
                console.error("Location search error:", error);
                resultsContainer.innerHTML = '<div class="gg-location-error">Error searching locations. Please try again.</div>';
            });
    }

    function getGPSLocation(latField, lonField, displayElement, searchInput, button, locationSourceField) {
        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span>Getting location...</span>';

        navigator.geolocation.getCurrentPosition(
            function (position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const accuracy = position.coords.accuracy;

                latField.value = lat.toFixed(6);
                lonField.value = lon.toFixed(6);
                if (locationSourceField) {
                    locationSourceField.value = "gps";
                }

                const accuracyText = accuracy ? ` (±${Math.round(accuracy)}m accuracy)` : "";
                updateSelectedLocation(displayElement, `Your GPS Location${accuracyText}`, lat, lon);

                searchInput.value = `GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;

                button.disabled = false;
                button.innerHTML = originalHtml;
            },
            function (error) {
                let errorMsg = "Could not get your location.";

                if (error.code === error.PERMISSION_DENIED) {
                    errorMsg = "GPS permission denied. Please enable location access in your browser.";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    errorMsg = "Location is unavailable. Please try again.";
                } else if (error.code === error.TIMEOUT) {
                    errorMsg = "GPS request timed out. Please try again.";
                }

                alert(errorMsg);
                button.disabled = false;
                button.innerHTML = originalHtml;
            },
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 0
            }
        );
    }

    function clearCoordinates(latField, lonField, displayElement, locationSourceField) {
        latField.value = "";
        lonField.value = "";
        if (locationSourceField) {
            locationSourceField.value = "";
        }
        if (displayElement) {
            displayElement.innerHTML = "";
            displayElement.style.display = "none";
        }
    }

    function updateSelectedLocation(displayElement, name, lat, lon) {
        if (!displayElement) return;

        displayElement.innerHTML = `
            <strong>Selected:</strong> ${escapeHtml(name)}<br>
            <small class="text-muted d-block">Latitude: ${lat.toFixed(6)}</small>
            <small class="text-muted d-block">Longitude: ${lon.toFixed(6)}</small>
        `;
        displayElement.style.display = "block";
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose initialization function globally if needed
    window.reinitializeLocationSearch = initializeLocationSearch;
})();
