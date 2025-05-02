import React from "react"
import { apiEndpoint } from "App";

const layerList = ({layers, updateLayer, updateCallback}) => {
    const onDelete = async (id) => {
        try {
            const options = {
                method: "DELETE"
            }
            const response = await fetch(`${apiEndpoint}/delete_layer/${id}`, options)
            if (response.status === 200) {
                updateCallback()
            } else {
                console.error("Failed to delete layer")
            }
        } catch (error) {
            alert(error)
            }
        }

    return <div className="layer-list">
        <h2>Layers</h2>
        <table>
            <thead>
                <tr>
                    <th>Raster Title</th>
                    <th>columns: weights</th>
                    <th>Geometry Columns (LatLng)</th>
                </tr>
            </thead>
            <tbody>
                {layers.map((layer) => (
                    <tr key={layer.id}>
                        <td>{layer.title}</td>
                        <td>{layer.colWeights}</td>
                        <td>{layer.geomY}, {layer.geomX}</td>
                        <td>
                            <button onClick={() => updateLayer(layer)}>Update</button>
                            <button onClick={() => onDelete(layer.id)}>Delete</button>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
}

export default layerList