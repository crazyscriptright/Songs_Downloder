// Build script to inject environment variables
const fs = require("fs");
const path = require("path");

// Get API URL from environment variable
const API_URL =
  process.env.VITE_API_URL ||
  process.env.API_URL ||
  "https://song-download-9889cf8e8f85.herokuapp.com";

console.log("🔧 Building with API_URL:", API_URL);

// Read index.html
let html = fs.readFileSync("index.html", "utf8");

// Inject environment script before config.js
const envScript = `
<script>
    window.ENV = {
        API_URL: '${API_URL}'
    };
</script>
`;

// Insert before closing </head> tag
html = html.replace("</head>", `${envScript}\n</head>`);

// Write to dist folder (or current folder for simple deployment)
fs.writeFileSync("index.html", html);

console.log("✅ Build complete!");
