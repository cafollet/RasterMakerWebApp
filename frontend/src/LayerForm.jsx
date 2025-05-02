import { useState, useEffect } from 'react';
import ColumnEntry from './ColumnEntry';
import './LayerForm.css';
import { apiEndpoint } from "./App";

const LayerForm = ({ existingLayer = {}, updateCallback}) => {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [file, setFile] = useState(null)
    const [columns, setColumns] = useState(existingLayer.columns ? ["Count", ...existingLayer.columns] : null);
    const [title, setTitle] = useState(existingLayer.title || "")
    const [colsUsed, setColsUsed] = useState(Object.keys(existingLayer.colWeights || {}));
    const [colWeights, setColWeights] = useState(existingLayer.colWeights || {})
    const [geomX, setGeomX] = useState(existingLayer.geomX || "");
    const [geomY, setGeomY] = useState(existingLayer.geomY || "");
    const [isColumnsLoaded, setIsColumnsLoaded] = useState(!!existingLayer.columns);

    const updating = Object.entries(existingLayer).length !== 0


    useEffect(() => {
        const fetchExistingColumns = async () => {
            if (updating && existingLayer.id) {
                try {
                    const response = await fetch(`${apiEndpoint}/get_columns/${existingLayer.id}`);
                    const data = await response.json();
                    const fullColumns = ["Count", ...data.columns];


                    let parsedWeights = {}
                    try {
                        parsedWeights = JSON.parse(existingLayer.colWeights);
                    } catch (error) {
                        console.error("Error parsing through colWeights JSON: ", error);
                    }

                    const loadedColsUsed = Object.keys(parsedWeights);

                    setColumns(fullColumns);
                    setIsColumnsLoaded(true);
                    setColsUsed(loadedColsUsed);
                    setColWeights(parsedWeights);
                    setGeomX(existingLayer.geomX || "");
                    setGeomY(existingLayer.geomY || "");
                    setNumCols(Object.keys(existingLayer.colWeights || {}).length || 1);
                } catch (err) {
                    console.error("Failed to fetch columns for existing layer:", err);
                }
            }
        };

        fetchExistingColumns();
    }, [updating, existingLayer]);


    const availableCols = columns?.filter(
        col => !colsUsed.includes(col) && col !== geomX && col !== geomY
    ) || [];

    const canAddColumn = availableCols.length > 0;


    const changeNumCols = (plusMinus) => {

        const newColsUsed = [...colsUsed];
        const newColWeights = { ...colWeights };


        if (plusMinus === "+") {
            const used = new Set([...colsUsed, geomX, geomY]);

            let defaultCol = columns.find(col => !used.has(col));

            if (!defaultCol) {
                alert("No cols found.");
                return;
            }

            newColsUsed.push(defaultCol);
            newColWeights[defaultCol] = ["", defaultCol === "Count" ? "Density": "IDW"];

        } else if (plusMinus === "-" && newColsUsed.length > 1) {
            const removedCol = newColsUsed.pop();
            delete newColWeights[removedCol];
        }

        setColsUsed(newColsUsed);
        setColWeights(newColWeights);

        console.log("updated colsUsed", newColsUsed);
        console.log("updated colWeights", newColWeights);
    };


    // =============================================== RemovedFunctions ===============================================


    // listOptions
    // Moved to ColumnEntry.jsx
    /*
    const listOptions = (columnList) => {
        const optionList = []
        console.log("TESTING", columnList, "ENDTESTING")
        for (const col in columnList) {
            optionList.push(<option value = {columnList[col]}>{columnList[col]}</option>)
        }

        return (
            optionList
        );
    };
    */


    // renderColumnEntry
    // Moved to ColumnEntry.jsx
    /* const renderColumnEntry = (columnsUsed, columnList) => {
        const inputs = [];
        for (let numCol in columnsUsed) {

            // Add column Label
            inputs.push(
                <label htmlFor={`col${numCol}`}>Column {numCol+1}:</label>
            )


            // Create a list of columns already being used in OTHER columns
            const nonInclusiveColsUsed = columnsUsed.slice(0, numCol).concat(columnsUsed.slice(numCol+1, columnsUsed.length));
            console.log("NONINCLUSIVE - SHOULD BE EMPTY ARRAY", nonInclusiveColsUsed);

            // Remove elements in the list from the options
            const updatedColumnList = columnList.filter(element => !nonInclusiveColsUsed.includes(element));

            // Add column drop-down menu
            inputs.push(
                <select
                    key={`col${numCol}`}
                    id={`col${numCol}`}
                    value={colsUsed[numCol]}
                    onChange={(e) => {
                            const oldColsUsed = [...columnsUsed];
                            const newColsUsed = [...columnsUsed];
                            newColsUsed[numCol] = e.target.value;

                            // remove old Cols Key from dictionary
                            // and copy values of that key to the new key (e.target.value)
                            const newColsWeights = {...colWeights};
                            const oldVal = newColsWeights[oldColsUsed[numCol]];
                            console.log("Test for old cols used", oldColsUsed[numCol])
                            delete newColsWeights[oldColsUsed[numCol]];
                            newColsWeights[columnsUsed[numCol]] = oldVal;


                            setColsUsed(columnsUsed);
                            setColWeights(newColsWeights);
                            console.log("NEW COLS WEIGHTS FOR UPDATE", newColsWeights);
                            renderColumnEntry(columnsUsed, columnList);
                        }}>
                    {
                        listOptions(updatedColumnList)
                    }
                </select>
            )

            // Add Weight label
            inputs.push(
                <label htmlFor={`val${numCol}`}>Weight:</label>
            )

            // Add Weight input
            inputs.push(
                <input
                    key={`val${numCol}`}
                    type="text"
                    id={`val${numCol}`}
                    value={Array.isArray(colWeights[columnsUsed[numCol]]) ? colWeights[columnsUsed[numCol]][0]: ""}
                    onChange={ (e) => {
                        const newColWeights = {...colWeights};
                        if (!Array.isArray(newColWeights[columnsUsed[numCol]])) {
                            newColWeights[columnsUsed[numCol]] = Array(2).fill("");
                        }
                            newColWeights[columnsUsed[numCol]][0] = e.target.value;
                            setColWeights(newColWeights);
                            console.log(colWeights);
                    }}
                />
            )
            inputs.push(
                <label htmlFor={`intMethod${numCol}`}>Interpolation Method:</label>
            )
            console.log(colWeights[columnsUsed[numCol]]);
            if (columnsUsed[numCol] === "Count") {
                const initColWeights = {...colWeights};
                console.log("INITIAL COLWEIGHTS", initColWeights);
                if ( !Array.isArray(initColWeights[columnsUsed[numCol]]) ) {
                    initColWeights[columnsUsed[numCol]] = Array(2)
                }
                initColWeights[columnsUsed[numCol]][1] = "Density"
                setColWeights(initColWeights);
                inputs.push(
                    <select
                        key={`intMethod${numCol}`}
                        id={`intMethod${numCol}`}
                        value={colWeights[columnsUsed[numCol]][1]}
                        onChange={(e) => {
                            const newColsUsed = [...columnsUsed];
                            const newColWeights = {...colWeights};

                            if ( !Array.isArray(newColWeights[newColsUsed[numCol]]) ) {
                                newColWeights[newColsUsed[numCol]] = Array(2);
                            }
                            newColWeights[newColsUsed[numCol]][1] = e.target.value;
                            console.log(newColWeights)
                            setColWeights(newColWeights);
                        }}>
                        <option value="Density">Density</option>
                    </select>
                )
            }
            else {
                inputs.push(
                    <select
                        key={`intMethod${numCol}`}
                        id={`intMethod${numCol}`}
                        value={colWeights[columnsUsed[numCol]][1]}
                        onChange={(e) => {
                            const newColsUsed = [...columnsUsed];
                            const newColWeights = {...colWeights};
                            if ( !Array.isArray(newColWeights[colsUsed[numCol]]) ) {
                                newColWeights[colsUsed[numCol]] = Array(2);
                            }
                            newColWeights[colsUsed[numCol]][1] = e.target.value;
                            console.log(newColWeights)
                            setColWeights(newColWeights);
                        }}>
                        <option value="IDW">IDW</option>
                        <option value="Linear">Linear</option>
                        <option value="Nearest">Nearest</option>
                        <option value="Density">Density</option>
                    </select>
                )
            }
                console.log("WOW", colWeights, "ENDWOW");
        }
        setColumnsRendering(
            <div className="individualColumnSelection">
                {inputs}
            </div>
        )
    } */


    // =============================================== END RemovedFunctions ===========================================


    const fetchColumns = async (file) => {
        const totData = new FormData()

        totData.append("file", file)
        const options = {
            method: "POST",
            body: totData
        }
        const response = await fetch(`${apiEndpoint}/upload`, options)
        const data = await response.json()

        // Initialize the drop-down menu render
        const totColumns = ["Count"].concat(data.columns);

        const newColsUsed = ["Count"];  // Special "Count" quantifier
        setColumns(totColumns);
        setIsColumnsLoaded(true);
        setColsUsed(newColsUsed);
        setColWeights({ "Count": ["", "Density"] });

    }

    const onSubmit = async (e) => {

        e.preventDefault();
        setIsSubmitting(true);

        const totData = new FormData()

        totData.append("title", title)
        if (file) {
            totData.append("file", file)
        }
        totData.append("colWeights", JSON.stringify(colWeights))
        totData.append("geom", `${geomX},${geomY}`)


        console.log("TOTDATA", totData)
        const url = apiEndpoint + "/" + (updating ? `update_layer/${existingLayer.id}` : "create_layer")
        const options = {
            method: updating ? "PATCH" : "POST",
            body: totData
        }
        try {
            const response = await fetch(url, options)
            if (response.status !== 201 && response.status !== 200) {
                const message = await response.json();
                alert(message.message);
            } else {
                updateCallback();
            }
        } catch (err) {
            alert("Submission failed. Please try again.");
            console.error(err);
        } finally {
            setIsSubmitting(false);
        }
    };
    return (
        <form onSubmit={onSubmit}>
            {isSubmitting && (
                <div className="loading-indicator">
                    <div className="spinner" />
                    <span>Uploading and processing... Please wait.</span>
                </div>
            )}
            <div>
                <label htmlFor={"title"}>Title:</label>
                <input
                    type = "text"
                    id = "title"
                    value = {title}
                    onChange={(e) => setTitle(e.target.value)}
                />
                <label htmlFor={"file"}>File:</label>
                <input
                    type = "file"
                    id = "file"
                    disabled={isSubmitting}
                    onChange={(e) => {
                        setFile(e.target.files[0]);
                        fetchColumns(e.target.files[0]);
                    }}
                />
                {updating && !file && existingLayer.filename && (
                    <p style={{ fontSize: "0.9em", color: "#555", marginTop: "0.25em" }}>
                        Currently using: <strong>{existingLayer.filename}</strong>
                    </p>
                )}
                {isColumnsLoaded && (
                    <div className="geometrySelection">

                        <label htmlFor="geomY">Latitude Column (Y):</label>
                        <select
                            id="geomY"
                            value={geomY}
                            onChange={(e) => setGeomY(e.target.value)}
                        >
                            <option value="">Select Latitude Column</option>
                            {columns
                                ?.filter(col => col !== "Count" && col !== geomX &&
                                    !colsUsed.includes(col))
                                .map((col, idx) => (
                                    <option key={idx} value={col}>
                                        {col}
                                    </option>
                                ))}
                        </select>

                        <label htmlFor="geomX">Longitude Column (X):</label>
                        <select
                            id="geomX"
                            value={geomX}
                            onChange={(e) => setGeomX(e.target.value)}
                        >
                            <option value="">Select Longitude Column</option>
                            {columns
                                ?.filter(col => col !== "Count" && col !== geomY && !colsUsed.includes(col))
                                .map((col, idx) => (
                                    <option key={idx} value={col}>
                                        {col}
                                    </option>
                                ))}
                        </select>
                    </div>

                )}
                { isColumnsLoaded && geomX && geomY && (
                    <div className="columnsIncluded">
                        <button type="button"
                                onClick={() => changeNumCols("+")}
                                disabled={!canAddColumn}>+</button>
                        <button type="button" onClick={() => changeNumCols("-")}>-</button>
                        { colsUsed.map((col, numCol) => (
                            <ColumnEntry
                                key={numCol}
                                numCol={numCol}
                                col={col}
                                colsUsed={colsUsed}
                                columns={columns}
                                colWeights={colWeights}
                                geomX={geomX}
                                geomY={geomY}
                                onColumnChange={(e, idx) => {
                                    const oldColsUsed = [...colsUsed];
                                    const newColsUsed = [...colsUsed];
                                    const newColWeights = { ...colWeights };

                                    const newCol = e.target.value;
                                    newColsUsed[idx] = newCol;

                                    const oldVal = newColWeights[oldColsUsed[idx]];
                                    delete newColWeights[oldColsUsed[idx]];
                                    newColWeights[newCol] = oldVal;

                                    setColsUsed(newColsUsed);
                                    setColWeights(newColWeights);
                                }}
                                onWeightChange={(e, columnName) => {
                                    const newColWeights = { ...colWeights };
                                    if (!Array.isArray(newColWeights[columnName])) {
                                        newColWeights[columnName] = ["", ""];
                                    }
                                    newColWeights[columnName][0] = e.target.value;
                                    setColWeights(newColWeights);
                                }}
                                onInterpChange={(e, columnName) => {
                                    const newColWeights = { ...colWeights };
                                    if (!Array.isArray(newColWeights[columnName])) {
                                        newColWeights[columnName] = ["", ""];
                                    }
                                    newColWeights[columnName][1] = e.target.value;
                                    setColWeights(newColWeights);
                                }}
                            />
                        ))}
                    </div>
                )}
            </div>
        <button type="submit">{isSubmitting ? "Creating Raster..." : updating ? "Update" : "Create"}</button>
    </form>
    )
}

export default LayerForm