# Changelog

All notable changes to the Episcopio project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-mvp] - 2025-01-15

### Added

#### Core Infrastructure
- Complete monorepo structure with modular architecture
- Docker Compose setup for easy deployment
- PostgreSQL + PostGIS database with complete schema
- Redis for caching (prepared for future use)
- Configuration management with YAML and environment variables
- Comprehensive .gitignore for Python projects
- MIT License

#### API (FastAPI)
- RESTful API with FastAPI framework
- Health check endpoint (`/api/v1/health`)
- Metadata endpoint (`/api/v1/meta`)
- KPI endpoint (`/api/v1/kpi`)
- Timeseries endpoint (`/api/v1/timeseries`)
- Map data endpoint (`/api/v1/map/entidad`)
- Alerts endpoint (`/api/v1/alerts`)
- Bulletin endpoint (`/api/v1/bulletin/{id}`)
- Clinical survey endpoint (`/api/v1/survey`)
- CORS middleware configuration
- Pydantic models for request/response validation
- Interactive API documentation (Swagger/OpenAPI)

#### Dashboard (Dash/Plotly)
- Interactive web dashboard
- KPI cards (Total Cases, Active Cases, Deaths)
- Time series visualization
- Social sentiment analysis chart
- Active alerts feed
- Entity and morbidity filters
- Responsive design with clean UI
- API client for backend communication

#### Database
- Complete schema with PostGIS support
- Tables: geo_entidad, geo_municipio, morbilidad, serie_oficial
- Social mentions table (social_menciones)
- Clinical survey table (sondeo_clinico)
- Alerts table (alerta)
- Bulletins table (boletin)
- QA events table (qa_evento)
- Ingestion logs table (ingesta_log)
- Seed data for 32 Mexican states
- Seed data for 15 common morbidities
- Proper indexes for performance
- Constraints for data integrity

#### Analytics Module
- KPI calculation functions
- Alert rule evaluation engine
- YAML-based alert rules configuration
- Two default alert rules (sudden increase, social spike)
- Sentiment aggregation functions

#### ETL Module
- Data normalization functions
- Date standardization (ISO-8601)
- Entity code normalization (INEGI 2-digit)
- Municipality code normalization (INEGI 5-digit)
- Morbidity name mapping
- ISO week calculation
- Data validation functions

#### Ingesta Module
- Official data connectors (DGE, INEGI, CONACYT, SSA)
- Social media connectors (Twitter, Facebook, Reddit, News)
- Relevance classification (keyword-based)
- Sentiment analysis (placeholder for NLTK/VADER)
- Source availability verification

#### Orchestrator
- Simple scheduler using Python schedule library
- Official data ingestion job (every 6 hours)
- Analytics job (every 1 hour)
- Automatic execution on startup
- Graceful shutdown handling

#### CI/CD
- GitHub Actions workflow for continuous integration
- Automated testing on push and pull requests
- Docker image building
- Configuration file validation
- Python linting with flake8
- Build caching for faster workflows

#### Documentation
- Comprehensive README with quick start guide
- QUICKSTART guide for 10-minute setup
- TESTING guide with complete test procedures
- Two technical specification documents
- Makefile with convenient commands
- Inline code documentation

#### Configuration
- settings.yaml for non-sensitive configuration
- secrets.sample.yaml template for credentials
- Support for environment variable overrides
- Alert rules configuration in YAML
- Timezone configuration (America/Merida)

### Technical Details

**Languages & Frameworks:**
- Python 3.11+
- FastAPI 0.109.0
- Dash 2.14.2
- Plotly 5.18.0
- Pydantic 2.5.3

**Databases:**
- PostgreSQL 16 with PostGIS 3.4
- Redis 7 (Alpine)

**Infrastructure:**
- Docker & Docker Compose
- Multi-container architecture
- Health checks for all services
- Automatic restart policies

**Architecture:**
- Microservices-style modular design
- API-first approach
- Separation of concerns
- Mock data for MVP demonstration

### Security
- No secrets in code repository
- Environment variable support
- CORS configuration
- Rate limiting prepared (not enforced in MVP)
- JWT authentication prepared (not enforced in MVP)
- Anonymous clinical surveys (no PII collection)

### Known Limitations (MVP)
- Mock data only (no real API connections)
- No actual database queries (returns mock data)
- Sentiment analysis is placeholder
- No user authentication/authorization
- No actual rate limiting enforcement
- No real-time data ingestion
- No data validation in ingestion pipelines
- No automated tests (manual testing only)

### Future Roadmap (V1)
- Real database integration
- Actual API connectors for data sources
- Advanced filters (municipality, age, sex)
- Anomaly detection (z-score, STL, CUSUM)
- User profiles and role-based access control
- Data quality dashboard
- Public API with rate limiting
- PDF/HTML report exports
- Webhook notifications
- Automated testing suite
- Performance optimizations

---

## Template for Future Releases

## [Unreleased]

### Added
- New features go here

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security improvements and fixes
