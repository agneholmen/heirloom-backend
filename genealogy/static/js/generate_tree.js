const boxHeight = 160;
const boxWidth = 120;
const coupleDistance = 48;
const generationDistance = 88;
const familyDistance = 88;
const coupleLineHeight = 48;
const curveDistance = 24;
const firstPersonX = 100;
const firstPersonY = 550;

document.addEventListener('DOMContentLoaded', function() {
    if (typeof familyData === 'undefined') {
        return
    }

    calculatePositions(familyData);
    drawTree(familyData);
    treeContainer = document.getElementById('tree-container');
    htmx.process(treeContainer);
});

function drawTree(node) {
    if (node.parents.length > 0) {
        node.parents.forEach((parent, index) => {
            drawTree(parent);
        });
        var fatherX = node.parents[0].x;
        var motherX = node.parents[1].x;
    }

    svgContainer = document.getElementById('tree-svg-container');
    if (typeof fatherX !== 'undefined' && typeof motherX !== 'undefined') {
        var paths = createPersonPath(node, fatherX, motherX);
        for (const path of paths) {
            svgContainer.appendChild(path);
        }
    }

    treeContainer = document.getElementById('tree-container');
    if (node.id === 0) {
        treeContainer.appendChild(createAddPersonBox(node));
    } else {
        treeContainer.appendChild(createPersonBox(node));
    }
}

function calculatePositions(node, depth = 0, xOffset = firstPersonX) {
    const x = xOffset;
    const y = depth * (generationDistance + boxHeight);

    let parentOffset = xOffset;
    node.y = firstPersonY - y;
    if (node.parents.length > 0) {
        node.parents.forEach((parent, index) => {
            const parentPositions = calculatePositions(parent, depth + 1, parentOffset);
            parentOffset += parentPositions.totalWidth + (coupleDistance + boxWidth);
        });

        const firstParent = node.parents[0];
        const lastParent = node.parents[1];
        node.x = (firstParent.x + lastParent.x) / 2;
    } else {
        node.x = x;
    }

    return { totalWidth: parentOffset - xOffset, node };
}

function createPersonBox(personData) {
    var boxHTML = `
    <div style="top: ${personData['y']}px; left: ${personData['x']}px;" class="tree-node">
        <a href="${personData['person_url']}">
            <button id="${personData['id']}" class="tree-node-button">
                <span class="avatar"></span>
                <span>${personData['first_name'] != null ? personData['first_name'] : ''}</span>
                <span>${personData['last_name'] != null ? personData['last_name'] : ''}</span>
                <span>${personData['years'] != null ? personData['years'] : ''}</span>
            </button>
        </a>
    </div>`

    var temp = document.createElement('div');
    temp.innerHTML = boxHTML.trim();

    return temp.firstChild;
}

function createAddPersonBox(personData) {
    var boxHTML = `
    <div style="top: ${personData['y']}px; left: ${personData['x']}px;" class="tree-node tree-node-new">
        <button id="${personData['child_id']}-${personData['parent_type']}" class="tree-node-button" 
            hx-get="${personData['person_url']}" hx-target="#modal-content" hx-trigger="click" 
            hx-swap="innerHTML" data-bs-toggle="modal" data-bs-target="#modal">
            <span class="avatar"></span>
            <span>Add ${personData['parent_type']}</span>
        </button>
    </div>`

    var temp = document.createElement('div');
    temp.innerHTML = boxHTML.trim();

    return temp.firstChild;
}

function createPersonPath(personData, fatherX, motherX) {
    const svgNS = "http://www.w3.org/2000/svg";
    var paths = [];

    var yPath = document.createElementNS(svgNS, 'path');

    var d = `m ${personData.x + (boxWidth / 2)},${personData.y} v -${(generationDistance + coupleLineHeight)}`

    yPath.setAttribute('d', d);

    paths.push(yPath);

    var xPath = document.createElementNS(svgNS, 'path');
    d = `m ${fatherX + boxWidth},${personData.y - generationDistance - coupleLineHeight} h ${motherX - fatherX - boxWidth}`

    xPath.setAttribute('d', d);

    paths.push(xPath);

    return paths;
}