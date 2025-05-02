import { useState, useEffect } from 'react'
import LayerList from './LayerList.jsx'
import LayerForm from './LayerForm.jsx'
import {map as currentMap, createLayer, deleteLayer} from './MapRasterOverlay.jsx'
import 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
import './App.css'

export let allOverlays = {}
export const apiEndpoint = import.meta.env.apiEndpoint // endpoint in environment -- should be localhost when testing locally

function removeValue(value, index, arr, valToRemove) {
    if (value !== valToRemove) {
        arr.splice(index, 1)
        return true
    }
    else {
        return false
    }
}


function App() {
    const [layers, setLayers] = useState([])
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [currentLayer, setCurrentLayer] = useState({})
    const [layersInMap, setLayersInMap] = useState([])
    useEffect(() => {
        console.log("Running useEffect")
        fetchLayers()
    }, [])

    const fetchLayers = async () => {
        const response = await fetch(`${apiEndpoint}/layers`)
        const data = await response.json()
        setLayers(data.layers)
        let imageLayers = { ...allOverlays };
        let layerTitles = [];
        let leftoverLayers = [...layersInMap];
        for (let layer of data.layers) {
            let layerId = layer.id;
            console.log(layer);

            let indivResponse = await fetch(`${apiEndpoint}/get_raster/${layerId}`);
            let indivData = await indivResponse.json();
            let imageContent = indivData.layerImage.image
            let imageType = indivData.layerImage.contentType
            let imageJson = indivData.layerJson


            const image = new Image();
            image.src = `data:${imageType};base64, ${imageContent}`;
            console.log("IMAGE SRC", image.src)
            if (!(layersInMap.includes(layer.title))) {
                imageLayers[layer.title] = createLayer(image, imageJson, currentMap, layer.title)
            } else {
                leftoverLayers.filter(function(value, index, arr) {
                    removeValue(value, index, arr, layer)
                })
            }
            layerTitles.push(layer.title)
        }
        for (let layer of leftoverLayers) {
            deleteLayer(currentMap, allOverlays[layer]);
            delete allOverlays[layer];
        }
        allOverlays = {...imageLayers};
        setLayersInMap(layerTitles);


    }

    const closeModal = () => {
        setIsModalOpen(false)
        setCurrentLayer({})
    }

    const openCreateModal = () => {
        if (!isModalOpen) setIsModalOpen(true)
    }

    const openEditModal = (layer) => {
        if (isModalOpen) return
        setCurrentLayer(layer)
        setIsModalOpen(true)
    }

    const onUpdate = () => {
        console.log("Running onUpdate")
        closeModal()
        fetchLayers()
    }

    return <>
        <LayerList layers={layers} updateLayer={openEditModal} updateCallback={onUpdate} />
        <button onClick={openCreateModal}>Create New Layer</button>
        { isModalOpen && <div className="modal">
            <div className="modal-content">
                <span className="close" onClick={closeModal}>&times;</span>
                <LayerForm existingLayer={currentLayer} updateCallback={onUpdate}/>
            </div>
        </div>
        }
        <div id="map"></div>

    </>
}

export default App;