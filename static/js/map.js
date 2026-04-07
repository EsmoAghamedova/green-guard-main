(function () {
    if (!document.getElementById("map")) {
        return;
    }

    const gpsButton = document.getElementById("gps-locate-btn");
    const gpsStatus = document.getElementById("gps-status");
    const gfwStatus = document.getElementById("gfw-status");

    const apiMapDataUrl = "/api/map-data";
    const apiGfwLocationsUrl = "/api/gfw-locations";

    function setGpsStatus(message, isError) {
        if (!gpsStatus) {
            return;
        }

        gpsStatus.textContent = message;
        gpsStatus.classList.remove("text-muted", "text-danger", "text-success");
        gpsStatus.classList.add(isError ? "text-danger" : "text-success");
    }

    function setGfwStatus(message, isError) {
        if (!gfwStatus) {
            return;
        }

        gfwStatus.textContent = message;
        gfwStatus.classList.remove("text-muted", "text-danger", "text-success");
        gfwStatus.classList.add(isError ? "text-danger" : "text-success");
    }

    function parseJsonScript(id) {
        const node = document.getElementById(id);
        if (!node || !node.textContent) {
            return [];
        }

        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return [];
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    const map = L.map("map").setView([42.3154, 43.3569], 7);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const treeIcon = L.icon({
        iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    const reportIcon = L.icon({
        iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    let bounds = L.latLngBounds([]);
    let userMarker = null;
    let accuracyCircle = null;
    const treeLayer = L.layerGroup().addTo(map);
    const reportLayer = L.layerGroup().addTo(map);
    const restorationLayer = L.layerGroup().addTo(map);

    L.control.layers(
        null,
        {
            "Sponsored / planted trees": treeLayer,
            "Citizen reporting": reportLayer,
            "Deforestation zones": restorationLayer
        },
        { collapsed: false }
    ).addTo(map);

    function addTreeMarkers(treesData) {
        if (!Array.isArray(treesData)) {
            return;
        }

        treesData.forEach(function (tree) {
            const latitude = Number(tree.latitude);
            const longitude = Number(tree.longitude);
            if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
                return;
            }

            const marker = L.marker([latitude, longitude], { icon: treeIcon }).addTo(treeLayer);
            bounds.extend([latitude, longitude]);
            marker.bindPopup(
                `<strong>Sponsored Tree Record</strong><br>` +
                `Species: ${escapeHtml(tree.species)}<br>` +
                `Quantity: ${escapeHtml(tree.quantity)}<br>` +
                `Sponsor: ${escapeHtml(tree.username)}`
            );
        });
    }

    function addReportMarkers(reportsData) {
        if (!Array.isArray(reportsData)) {
            return;
        }

        reportsData.forEach(function (report) {
            const latitude = Number(report.latitude);
            const longitude = Number(report.longitude);
            if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
                return;
            }

            const marker = L.marker([latitude, longitude], { icon: reportIcon }).addTo(reportLayer);
            bounds.extend([latitude, longitude]);
            const reporterLabel = report.username ? escapeHtml(report.username) : "Anonymous";
            marker.bindPopup(
                `<strong>Illegal Logging Report</strong><br>` +
                `Status: ${escapeHtml(report.status)}<br>` +
                `Reporter: ${reporterLabel}<br>` +
                `${escapeHtml((report.description || "").substring(0, 120))}`
            );
        });
    }

    function addRestorationMarkers(locations) {
        restorationLayer.clearLayers();

        if (!Array.isArray(locations) || locations.length === 0) {
            setGfwStatus("No deforestation zones available right now.", false);
            return;
        }

        locations.forEach(function (location) {
            const latitude = Number(location.latitude);
            const longitude = Number(location.longitude);
            const isReforestation = Boolean(location.is_reforestation);

            if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
                return;
            }

            const marker = L.circleMarker([latitude, longitude], {
                radius: 7,
                color: isReforestation ? "#0f766e" : "#c2410c",
                weight: 2,
                fillColor: isReforestation ? "#14b8a6" : "#f97316",
                fillOpacity: 0.8
            }).addTo(restorationLayer);

            bounds.extend([latitude, longitude]);

            marker.bindPopup(
                `<strong>${escapeHtml(location.name || "Deforestation Zone")}</strong><br>` +
                `Country: ${escapeHtml(location.country_name || location.region_label || "Unknown")} (${escapeHtml(location.country_code || "n/a")})<br>` +
                `Reforestation tag: ${escapeHtml(location.reforestation_type || "Not tagged")}<br>` +
                `Last seen: ${escapeHtml(location.last_seen_label || location.alert_date || "Unknown")}<br>` +
                `Source: ${escapeHtml(location.source || "n/a")}`
            );
        });

        setGfwStatus(`Showing ${locations.length} deforestation zone${locations.length === 1 ? "" : "s"}.`, false);
    }

    function updateBoundsView() {
        if (bounds.isValid()) {
            map.fitBounds(bounds.pad(0.15));
        }
    }

    async function loadMapData() {
        try {
            const response = await fetch(apiMapDataUrl, { cache: "no-store" });
            if (!response.ok) {
                throw new Error(`Map data request failed with status ${response.status}`);
            }

            const payload = await response.json();
            return {
                trees: Array.isArray(payload.trees) ? payload.trees : [],
                reports: Array.isArray(payload.reports) ? payload.reports : []
            };
        } catch (error) {
            return {
                trees: parseJsonScript("trees-data"),
                reports: parseJsonScript("reports-data")
            };
        }
    }

    Promise.all([loadMapData(), loadGfwLocations()]).then(function (results) {
        const mapData = results[0];
        addTreeMarkers(mapData.trees);
        addReportMarkers(mapData.reports);
        map.invalidateSize();
        updateBoundsView();
    });

    window.setTimeout(function () {
        map.invalidateSize();
    }, 200);

    async function loadGfwLocations() {
        setGfwStatus("Loading global deforestation zones...", false);

        try {
            const response = await fetch(apiGfwLocationsUrl, { cache: "no-store" });

            if (!response.ok) {
                throw new Error(`GFW request failed with status ${response.status}`);
            }

            const payload = await response.json();
            addRestorationMarkers(Array.isArray(payload.locations) ? payload.locations : []);
        } catch (error) {
            setGfwStatus("Unable to load deforestation zones from API right now.", true);
        }
    }

    function updateUserLocation(position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        const accuracy = position.coords.accuracy || 0;
        const userLatLng = [latitude, longitude];

        if (userMarker) {
            userMarker.setLatLng(userLatLng);
        } else {
            userMarker = L.circleMarker(userLatLng, {
                radius: 8,
                color: "#1466d6",
                fillColor: "#2d8cff",
                fillOpacity: 0.95,
                weight: 2
            }).addTo(map);
            userMarker.bindPopup("Your current GPS location");
        }

        if (accuracyCircle) {
            accuracyCircle.setLatLng(userLatLng);
            accuracyCircle.setRadius(accuracy);
        } else {
            accuracyCircle = L.circle(userLatLng, {
                radius: accuracy,
                color: "#2d8cff",
                fillColor: "#2d8cff",
                fillOpacity: 0.15,
                weight: 1
            }).addTo(map);
        }

        map.flyTo(userLatLng, 15, { duration: 1.0 });
        setGpsStatus("GPS location found. Map centered on your position.", false);
    }

    function handleGpsError(error) {
        if (error.code === error.PERMISSION_DENIED) {
            setGpsStatus("Location permission denied. Please allow GPS access in your browser.", true);
            return;
        }

        if (error.code === error.POSITION_UNAVAILABLE) {
            setGpsStatus("Location is unavailable right now. Please try again.", true);
            return;
        }

        if (error.code === error.TIMEOUT) {
            setGpsStatus("GPS request timed out. Please try again.", true);
            return;
        }

        setGpsStatus("Could not get your location. Please try again.", true);
    }

    if (gpsButton) {
        if (!navigator.geolocation) {
            gpsButton.disabled = true;
            setGpsStatus("Your browser does not support GPS geolocation.", true);
            return;
        }

        gpsButton.addEventListener("click", function () {
            setGpsStatus("Requesting GPS location...", false);
            navigator.geolocation.getCurrentPosition(updateUserLocation, handleGpsError, {
                enableHighAccuracy: true,
                timeout: 12000,
                maximumAge: 0
            });
        });
    }
})();
