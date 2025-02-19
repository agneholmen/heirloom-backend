const boxHeight = 160;
const boxWidth = 120;
const coupleDistance = 48;
const generationDistance = 88;
const familyDistance = 88;
const coupleLineHeight = 48;
const curveDistance = 24;
const firstPersonX = 100;
const firstPersonY = 550;
const childrenYPath = 30;
const pathArc = 15;

document.addEventListener('DOMContentLoaded', function() {
    const panel = document.getElementById("settings-panel");
    const button = document.getElementById("toggle-panel-button");

    button.addEventListener("click", () => {
        panel.classList.toggle("panel-open");
        button.textContent = panel.classList.contains("panel-open") ? "→" : "←";
    });

    const colorSelector = document.getElementById('color-selector');
    var treeContainer = document.getElementById('tree-container');

    const defaultColor = colorSelector.value;

    colorSelector.addEventListener("change", function(event) {
        var selectedColor = event.target.value;
        treeContainer.style.setProperty("background-color", selectedColor, "important");
    });

    const resetButton = document.getElementById('reset-color-button');

    resetButton.addEventListener("click", () => {
        treeContainer.style.removeProperty("background-color");
        colorSelector.value = defaultColor;
    });

    if (typeof familyData === 'undefined') {
        return
    }

    calculatePositions(familyData);
    calculatePositionsFamily(familyData);
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

    if (node.partner) {
        treeContainer.appendChild(createPersonBox(node.partner));
        svgContainer.appendChild(createCouplePath(node))
    }

    if (node.children) {
        var paths = createChildrenPaths(node.children);
        for (const path of paths) {
            svgContainer.appendChild(path);
        }
        node.children.forEach((child, index) => {
            treeContainer.appendChild(createPersonBox(child));
        });
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
        console.log(`${node.first_name} has x ${node.x}`);
    } else {
        node.x = x;
        console.log(`${node.first_name} has x ${node.x}`);
    }

    return { totalWidth: parentOffset - xOffset, node };
}

function calculatePositionsFamily(node) {
    if (node.partner) {
        node.partner.y = node.y;
        node.partner.x = node.x + (coupleDistance + boxWidth);
        var childrenCenterX = node.x + boxWidth + (coupleDistance / 2);
    }
    else {
        var childrenCenterX = node.x + (boxWidth / 2);
    }
    if (node.children) {
        var totalWidth = (node.children.length * boxWidth) + ((node.children.length - 1) * coupleDistance);
        var currentX = childrenCenterX - (totalWidth / 2); 
        const childrenY = node.y + boxHeight + generationDistance;

        node.children.forEach((child, index) => {
            child.y = childrenY;
            child.x = currentX;
            currentX += boxWidth + coupleDistance;
        });
    }
}

function createPersonBox(personData) {
    var boxHTML = `
    <div class="tree-node-container" style="top: ${personData['y']}px; left: ${personData['x']}px;">
        <div class="tree-node">
            <a href="${personData['person_url']}">
                <button id="${personData['id']}" class="tree-node-button">
                    <span class="avatar">
                        <img src="${personData['image']}" alt="avatar" class="avatar-image" />
                    </span>
                    <span>${personData['first_name'] != null ? personData['first_name'] : ''}</span>
                    <span>${personData['last_name'] != null ? personData['last_name'] : ''}</span>
                    <span>${personData['years'] != null ? personData['years'] : ''}</span>
                </button>
            </a>
        </div>
        <div class="link-list">
			<a href="#" hx-get="${personData['edit_url']}" hx-target="#modal-content" hx-trigger="click" hx-swap="innerHTML" data-bs-toggle="modal" data-bs-target="#modal">
				<svg xmlns="http://www.w3.org/2000/svg" width="1.4em" height="1.4em" fill="#007bff" class="bi bi-pencil-square" viewBox="0 0 16 16">
					<path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"></path>
					<path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"></path>
				</svg>
			</a>
			<a href="${personData['tree_url']}">
				<svg xmlns="http://www.w3.org/2000/svg" width="1.4em" height="1.4em" fill="#57b94e" class="bi bi-tree" viewBox="0 0 16 16">
					<path d="M8.416.223a.5.5 0 0 0-.832 0l-3 4.5A.5.5 0 0 0 5 5.5h.098L3.076 8.735A.5.5 0 0 0 3.5 9.5h.191l-1.638 3.276a.5.5 0 0 0 .447.724H7V16h2v-2.5h4.5a.5.5 0 0 0 .447-.724L12.31 9.5h.191a.5.5 0 0 0 .424-.765L10.902 5.5H11a.5.5 0 0 0 .416-.777l-3-4.5zM6.437 4.758A.5.5 0 0 0 6 4.5h-.066L8 1.401 10.066 4.5H10a.5.5 0 0 0-.424.765L11.598 8.5H11.5a.5.5 0 0 0-.447.724L12.69 12.5H3.309l1.638-3.276A.5.5 0 0 0 4.5 8.5h-.098l2.022-3.235a.5.5 0 0 0 .013-.507z"></path>
				</svg>
			</a>
        </div>
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
            <span class="avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="3em" height="3em" fill="#198754" class="bi bi-person-add" viewBox="0 0 16 16">
	                <path d="M12.5 16a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7m.5-5v1h1a.5.5 0 0 1 0 1h-1v1a.5.5 0 0 1-1 0v-1h-1a.5.5 0 0 1 0-1h1v-1a.5.5 0 0 1 1 0m-2-6a3 3 0 1 1-6 0 3 3 0 0 1 6 0M8 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4"></path>
	                <path d="M8.256 14a4.474 4.474 0 0 1-.229-1.004H3c.001-.246.154-.986.832-1.664C4.484 10.68 5.711 10 8 10c.26 0 .507.009.74.025.226-.341.496-.65.804-.918C9.077 9.038 8.564 9 8 9c-5 0-6 3-6 4s1 1 1 1z"></path>
                </svg>
            </span>
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

    var d = `m ${personData.x + (boxWidth / 2)},${personData.y} 
             v -${(generationDistance + coupleLineHeight)}`

    yPath.setAttribute('d', d);

    paths.push(yPath);

    var xPath = document.createElementNS(svgNS, 'path');
    d = `m ${fatherX + boxWidth},${personData.y - generationDistance - coupleLineHeight} 
         h ${motherX - fatherX - boxWidth}`

    xPath.setAttribute('d', d);

    paths.push(xPath);

    return paths;
}

function createCouplePath(personData) {
    const svgNS = "http://www.w3.org/2000/svg";

    var xPath = document.createElementNS(svgNS, 'path');
    d = `m ${personData.x + boxWidth},${personData.y + boxHeight - coupleLineHeight} 
         h ${coupleDistance}`

    xPath.setAttribute('d', d);

    return xPath;
}

function createChildrenPaths(childrenData) {
    const svgNS = "http://www.w3.org/2000/svg";

    var paths = [];

    // Create vertical path for middle children
    childrenData.forEach((child, index) => {
        if (index !== 0 && index !== (childrenData.length - 1)) {
            var yPath = document.createElementNS(svgNS, 'path');
            d = `m ${child.x + (boxWidth / 2)}, ${child.y} 
                 v -${childrenYPath}`
    
            yPath.setAttribute('d', d);
    
            paths.push(yPath);
        }
    });

    // Create horizontal path that goes vertically to children on the left and right
    if (childrenData.length > 1) {
        var horizontalPath = document.createElementNS(svgNS, 'path');
        d = `m ${childrenData[0].x + (boxWidth / 2)}, ${childrenData[0].y} 
             v -${childrenYPath - pathArc} 
             a ${pathArc} -${pathArc} 0 0 1 ${pathArc} -${pathArc} 
             h ${((childrenData.length - 1) * boxWidth) + ((childrenData.length - 1) * coupleDistance) - 2 * pathArc} 
             a ${pathArc} ${pathArc} 0 0 1 ${pathArc} ${pathArc} 
             v ${childrenYPath}`

        horizontalPath.setAttribute('d', d);
        
        paths.push(horizontalPath);
    }

    // Create vertical path from horizontal path to parents
    var verticalPath = document.createElementNS(svgNS, 'path');
    d = `m ${childrenData[0].x + (((childrenData.length) * boxWidth) + ((childrenData.length - 1) * coupleDistance)) / 2}, ${childrenData[0].y - childrenYPath} 
         v -${generationDistance - childrenYPath + coupleLineHeight}`

    verticalPath.setAttribute('d', d);
        
    paths.push(verticalPath);

    return paths;
}