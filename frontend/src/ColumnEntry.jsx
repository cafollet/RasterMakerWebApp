import React from 'react';

const ColumnEntry = ({
                         numCol,
                         col,
                         colsUsed,
                         columns,
                         colWeights,
                         geomX,
                         geomY,
                         onColumnChange,
                         onWeightChange,
                         onInterpChange
                     }) => {
    const availableColumns = columns?.filter(
        (option) =>
            !colsUsed
                .filter((_, i) => i !== numCol) // exclude current entry's own value
                .includes(option) &&
            option !== geomX &&
            option !== geomY
    ) || [];

    const weight = Array.isArray(colWeights[col]) ? colWeights[col][0] : "";
    const interpMethod = Array.isArray(colWeights[col]) ? colWeights[col][1] : (col === "Count" ? "Density" : "");

    return (
        <div className="individualColumnSelection" key={numCol}>
            <label htmlFor={`col${numCol}`}>Column {numCol + 1}:</label>
            <select
                id={`col${numCol}`}
                value={col}
                onChange={(e) => onColumnChange(e, numCol)}
            >
                {availableColumns.map((option, idx) => (
                    <option key={idx} value={option}>
                        {option}
                    </option>
                ))}
            </select>

            <label htmlFor={`val${numCol}`}>Weight:</label>
            <input
                type="text"
                id={`val${numCol}`}
                value={weight}
                onChange={(e) => onWeightChange(e, col)}
            />

            <label htmlFor={`intMethod${numCol}`}>Interpolation Method:</label>
            <select
                id={`intMethod${numCol}`}
                value={interpMethod}
                onChange={(e) => onInterpChange(e, col)}
            >
                {col === "Count" ? (
                    <option value="Density">Density</option>
                ) : (
                    <>
                        <option value="IDW">IDW</option>
                        <option value="Linear">Linear</option>
                        <option value="Nearest">Nearest</option>
                        <option value="Density">Density</option>
                    </>
                )}
            </select>
        </div>
    );
};

export default ColumnEntry;
