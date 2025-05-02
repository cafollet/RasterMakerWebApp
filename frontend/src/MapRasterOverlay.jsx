import 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
import { allOverlays, apiEndpoint } from './App';


// Initialize the map and set its view to Vancouver
const map = L.map('map').setView([49.2827, -123.1207], 13);

// Add OpenStreetMap tiles
const osmTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
});

// Add a basemap layer (e.g., CartoDB Positron)
const basemapTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.carto.com/">CARTO</a>'
});

// Add both layers to the map
osmTiles.addTo(map);

// Add layer control to toggle between base layers
var layerControl = L.control.layers({
    "OpenStreetMap": osmTiles,
    "CartoDB Positron": basemapTiles
}).addTo(map);

// Add a marker at Vancouver's coordinates
L.marker([49.2827, -123.1207]).addTo(map)
    .bindPopup('Vancouver, BC')
    .openPopup();


// On mouse click, do something -- THIS SHOULD BE MOVED TO MAIN SCRIPT AND ITERATED THROUGH ALL PRESENT LAYERS
map.on('click', async function (e) {

    const response = await fetch(`${apiEndpoint}/layers`);
    const data = await response.json();

    const allLayers = [...data.layers]
    let indexValues = ""

    for (let singleLayer in allLayers) {
        let indivResponse = await fetch(`${apiEndpoint}/get_json/${allLayers[singleLayer].id}`)
        let indivData = await indivResponse.json()

        console.log(indivData)

        const indexValue = findIndex(e, indivData.jsonFile, map, allLayers[singleLayer].title);
        indexValues += (singleLayer === 0) ? `${allLayers[singleLayer].title} Index: ${indexValue}` : `\n${allLayers[singleLayer].title} Index: ${indexValue}`
    }
    L.popup(e.latlng, {content: indexValues})
        .openOn(map);

    // Create marker to show info [Replaced with above]
    /*
    L.marker(e.latlng).addTo(map)
        .bindPopup(indexValues)
        .openPopup();

     */
})

function findIndex(pos, layer, map, title) {
    console.log("ALLOVERLAYS", allOverlays);
    const centre = allOverlays[title].getCenter(); // Center in lat/lng map coords

    const imageT = layer["tbound"];
    const imageB = layer["bbound"];
    const imageL = layer["lbound"];
    const imageR = layer["rbound"];

    const imageBounds = [[imageT, imageL], [imageB, imageR]];

    console.log(imageBounds, pos.latlng, centre)

    if (pos.latlng.lat < imageBounds[0][0]
        && pos.latlng.lat > imageBounds[1][0]
        && pos.latlng.lng > imageBounds[0][1]
        && pos.latlng.lng < imageBounds[1][1]) {


        // Image W and H in lat-long deg
        const imageDiffH = imageR - imageL;
        const imageDiffV = imageT - imageB;

        // Scaling factor for latlng to pixels
        const scaleH = layer["sizex"] / imageDiffH;
        const scaleV = layer["sizey"] / imageDiffV;

        // Calculate mouse to centre of image pixel distance
        const mouseToCentreV = scaleV * (pos.latlng.lat - centre.lat);
        const mouseToCentreH = scaleH * (pos.latlng.lng - centre.lng);

        // Calculate mouse to origin pixel distance
        const mouseToOriginH = mouseToCentreH + (layer["sizex"] / 2);
        const mouseToOriginV = (layer["sizey"] / 2) - mouseToCentreV;  // Opposite direction for y-axis

        // Calculate nearest pixel coordinate
        const pixelCoord = Math.round(1000
            * layer[ Math.floor(mouseToOriginH).toString() + "," + Math.floor(mouseToOriginV).toString() ]["name"]) / 1000

        // logging pixel coord for debugging
        console.log(pixelCoord)

        return (pixelCoord)


    }
}

function createLayer(layerImg, layerJson, mapToUse, layerTitle) {
    let transparency = 1.0;

    // Image bound dimensions
    const imageT = layerJson["tbound"];
    const imageB = layerJson["bbound"];
    const imageL = layerJson["lbound"];
    const imageR = layerJson["rbound"];
    const imageBounds = [[imageT, imageL], [imageB, imageR]];
    const imageUrl = layerImg.src;
    const rasterOverlay = L.imageOverlay(
        imageUrl,
        imageBounds,
        {alt: 'Raster', interactive: true, crossOrigin: 'anonymous'})
        .setOpacity(transparency);
    rasterOverlay.addTo(mapToUse);

    // Ensure transparent background for the layer (Alpha working)
    var imgTag = rasterOverlay.getElement()
    imgTag.style.background="transparent";

    // Add layer to the layer list
    layerControl.addOverlay(rasterOverlay, layerTitle);


    return (rasterOverlay);
}
function deleteLayer(mapToUse, layer) {
    mapToUse.removeLayer(layer)
    layerControl.removeLayer(layer)
}
export { createLayer, deleteLayer, map };