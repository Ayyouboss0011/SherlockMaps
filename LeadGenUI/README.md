# SherlockMaps - Lead Generation Dashboard

Eine NextJS Web-Oberflache zum Steuern des Google Maps Crawler Docker-Containers.

## Funktionen

- **Dashboard-Overview**: Echtzeit-Status des Crawlers mit Statistiken
- **Crawl starten**: Suchbegriff eingeben, Optionen wahlen und Crawl starten
- **Job-Verwaltung**: Alle Crawl-Jobs uberwachen, Details ansehen und Jobs abbrechen
- **Ergebnisse**: Gesammelte Daten durchsuchen, exportieren (JSON/CSV) und verwalten
- **Echtzeit-Updates**: Automatische Aktualisierung alle 10 Sekunden

## Voraussetzungen

- Node.js 18+ 
- npm oder yarn
- Laufender Google Maps Crawler Docker-Container (auf Port 8000)

## Installation

1. Abhangigkeiten installieren:

```bash
cd LeadGenUI
npm install
```

2. Umgebungsvariablen konfigurieren:

Die Datei `.env.local` enthält die Konfiguration:

```
CRAWLER_API_URL=http://localhost:8000
```

Falls der Crawler auf einem anderen Port oder Host lauft, bitte hier anpassen.

3. Development-Server starten:

```bash
npm run dev
```

Die Anwendung ist nun unter http://localhost:3000 verfullbar.

## Produktion

Build fur Produktion:

```bash
npm run build
npm start
```

## Projektstruktur

```
LeadGenUI/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root-Layout
│   │   ├── page.tsx            # Hauptseite (Dashboard)
│   │   └── globals.css         # Globale Styles (Tailwind)
│   ├── components/
│   │   ├── Dashboard/
│   │   │   └── DashboardStats.tsx   # Statistik-Karten
│   │   ├── Crawl/
│   │   │   └── CrawlForm.tsx         # Crawl-Start Formular
│   │   ├── Jobs/
│   │   │   └── JobList.tsx           # Job-Liste mit Details
│   │   ├── Results/
│   │   │   └── ResultsTable.tsx      # Ergebnisse Tabelle
│   │   └── Shared/
│   │       └── StatusBadge.tsx       # Status-Anzeige
│   └── lib/
│       ├── api.ts              # API-Client fur Crawler-API
│       └── types.ts            # TypeScript Typ-Definitionen
├── public/                     # Statische Dateien
├── .env.local                  # Umgebungsvariablen
├── next.config.js              # NextJS Konfiguration
├── tailwind.config.ts          # Tailwind Konfiguration
├── tsconfig.json               # TypeScript Konfiguration
└── package.json
```

## Verfullbare API-Endpunkte

Die UI kommuniziert mit dem Google Maps Crawler uber folgende Endpunkte:

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/health` | Health Check |
| GET | `/status` | Aktueller Status |
| GET | `/stats` | Statistiken |
| POST | `/crawl` | Neuen Crawl starten |
| GET | `/crawl/{id}` | Job-Status abrufen |
| GET | `/crawl/{id}/results` | Job-Ergebnisse |
| DELETE | `/crawl/{id}` | Job abbrechen |
| GET | `/crawl/history` | Crawl-Historie |
| GET | `/results` | Alle Ergebnisse |
| DELETE | `/results/clear` | Ergebnisse loschen |

## Lizenz

MIT