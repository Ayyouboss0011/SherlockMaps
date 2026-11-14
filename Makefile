.PHONY: up down logs build check screenshots clean

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

check:
	python -m pytest -q
	python -m compileall -q core
	cd LeadGenUI && NEXT_PUBLIC_CRAWLER_API_URL=/api npm run build

screenshots:
	python scripts/capture_screenshots.py

clean:
	docker compose down -v
