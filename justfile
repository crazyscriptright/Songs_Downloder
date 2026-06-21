format:
    npx prettier --write spotiflac-frontend/
    npx eslint spotiflac-frontend/ --fix
    ruff check backend/ --fix
    black backend/

lint:
    npx eslint spotiflac-frontend/
    ruff check backend/
