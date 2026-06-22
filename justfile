set shell := ["powershell.exe", "-NoProfile", "-Command"]

format:
	npx prettier --write "spotiflac-frontend/**/*.{ts,tsx}"
	npx eslint "spotiflac-frontend/**/*.{ts,tsx}" --fix
	ruff check backend/ --fix
	black backend/

lint:
	npx eslint "spotiflac-frontend/**/*.{ts,tsx}"
	ruff check backend/
