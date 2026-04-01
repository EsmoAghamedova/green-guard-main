(function () {
    if (!document.getElementById("map")) {
        return;
    }

    const gpsButton = document.getElementById("gps-locate-btn");
    const gpsStatus = document.getElementById("gps-status");

    function setGpsStatus(message, isError) {
        if (!gpsStatus) {
            return;
        }

        gpsStatus.textContent = message;
        gpsStatus.classList.remove("text-muted", "text-danger", "text-success");
        gpsStatus.classList.add(isError ? "text-danger" : "text-success");
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

    function addTreeMarkers(treesData) {
        if (!Array.isArray(treesData)) {
            return;
        }

        treesData.forEach(function (tree) {
            const marker = L.marker([tree.latitude, tree.longitude], { icon: treeIcon }).addTo(map);
            bounds.extend([tree.latitude, tree.longitude]);
            marker.bindPopup(
                `<strong>Tree Planted</strong><br>` +
                `Species: ${tree.species}<br>` +
                `Quantity: ${tree.quantity}<br>` +
                `By: ${tree.username}`
            );
        });
    }

    function addReportMarkers(reportsData) {
        if (!Array.isArray(reportsData)) {
            return;
        }

        reportsData.forEach(function (report) {
            const marker = L.marker([report.latitude, report.longitude], { icon: reportIcon }).addTo(map);
            bounds.extend([report.latitude, report.longitude]);
            marker.bindPopup(
                `<strong>Cutting Report</strong><br>` +
                `Status: ${report.status}<br>` +
                `By: ${report.username}<br>` +
                `${(report.description || "").substring(0, 120)}`
            );
        });
    }

    function updateBoundsView() {
        if (bounds.isValid()) {
            map.fitBounds(bounds.pad(0.15));
        }
    }

    async function loadMapData() {
        try {
            const response = await fetch("/api/map-data", { cache: "no-store" });
            if (response.ok) {
                const payload = await response.json();
                return {
                    trees: Array.isArray(payload.trees) ? payload.trees : [],
                    reports: Array.isArray(payload.reports) ? payload.reports : []
                };
            }
        } catch (error) {
        }

        return {
            trees: parseJsonScript("trees-data"),
            reports: parseJsonScript("reports-data")
        };
    }

    loadMapData().then(function (data) {
        addTreeMarkers(data.trees);
        addReportMarkers(data.reports);
        updateBoundsView();
    });

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
