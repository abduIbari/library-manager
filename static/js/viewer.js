//viewer.js
const BACKEND = "neo4j"; // or "postgres"
const port = 5001;

const ROUTES = {
  postgres: {
    entity: "/api/display_entity"
  },
  neo4j: {
    entity: "/api/neo4j/display_entity" 
  }
};

window.onload = function () {
    const params = getQueryParams();
    const entity = params['entity'];
    const id = params['id'];

    if (entity && id) {
        viewEntity(entity, id, port, ROUTES[BACKEND].entity);
    } else {
        document.getElementById('content').innerHTML = '<p>Invalid parameters.</p>';
    }
};


function viewEntity(entity, id, port, route){
    fetch(`http://127.0.0.1:${port}${ROUTES[BACKEND].entity}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ entity: entity, id: id })
    })
    .then(response => response.json())
    .then(data => {
        let html = `<h1>${entity} Details</h1><ul>`;
        for (const key in data) {
            html += `<li><strong>${key}:</strong> ${data[key]}</li>`;
        }
        html += "</ul>";

        document.getElementById('content').innerHTML = html;

        // If there's a name/title, fetch Gemini description
        const name = data.Name || data.Title;
        if (name) {
            fetchGeminiDescription(name);
        }
    })
    .catch(error => {
        console.error("Error displaying entity:", error);
        document.getElementById('content').innerHTML = `<p>Error loading entity.</p>`;
    });
}









/**
 * Function to retrieve query parameters from the URL.
 * @returns {Object} An object containing key-value pairs of query parameters.
 */
function getQueryParams() {
    const params = {};
    window.location.search.substring(1).split("&").forEach(pair => {
        const [key, value] = pair.split("=");
        if (key) {
            params[decodeURIComponent(key)] = decodeURIComponent(value || '');
        }
    });
    return params;
}

/**
 * Fetches a description from the Gemini API for the given entity.
 * @param {string} entityName - The name of the entity (book, author, genre, etc.).
 */
async function fetchGeminiDescription(entityName) {
    console.log('Fetching description for:', entityName); // Debug
    try {
        const response = await fetch(`/api/description?name=${encodeURIComponent(entityName)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        console.log('Fetch response status:', response.status); // Debug

        if (response.status === 400) {
            throw new Error('Invalid request. Entity name is missing.');
        } else if (response.status === 500) {
            throw new Error('Server error while fetching description.');
        } else if (!response.ok) {
            throw new Error('Unexpected error occurred.');
        }

        const data = await response.json();
        console.log('Received data:', data); // Debug
        const descriptionMarkdown = data.description || 'No description available.';

        // Convert Markdown to HTML using Marked.js
        const descriptionHTML = marked.parse(descriptionMarkdown);

        // Display the description in the "description" div
        document.getElementById('description').innerHTML = `<h2>Description</h2>${descriptionHTML}`;
    } catch (error) {
        console.error('Error fetching description from Gemini API:', error);
        document.getElementById('description').innerHTML = `<p>${error.message}</p>`;
    }
}
