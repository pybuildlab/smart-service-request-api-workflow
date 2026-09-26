# Smart Service Request & API Workflow System

A lightweight service-request management system built with Python and FastAPI, backed by SQLite and supported by a vanilla HTML/CSS/JavaScript dashboard.

The project demonstrates a complete workflow from API request creation and persistence through status management and a user-facing dashboard.

## Overview

The system provides an API for creating, viewing, and updating internal service requests such as IT/helpdesk requests.

Each request follows a simple workflow:

```text
pending → in_progress → completed
    ↘
     cancelled

     The application combines:

REST API development
SQLite persistence
Request validation
Status management
API documentation
Automated testing
A dynamic browser dashboard

Key Features
Create and manage service requests through a REST API
Persistent SQLite database storage
Request status management
Input validation and error handling
JSON API responses
Interactive web dashboard
Dashboard statistics and request listing
API documentation through FastAPI
Automated test suite
High test coverage
Lightweight architecture with no frontend framework or heavy infrastructure

Technology Stack
Technology	Purpose
Python	Backend development
FastAPI	REST API framework
SQLite	Data persistence
HTML	Dashboard structure
CSS	Dashboard styling
JavaScript	Dashboard interactivity and API integration
Pytest	Automated testing
Git / GitHub	Version control and project hosting

Application Workflow
Client / Dashboard
       ↓
   FastAPI API
       ↓
 Validation
       ↓
 SQLite Database
       ↓
 Request Status
       ↓
 Dashboard / API Response

 A typical request moves through:

pending
   ↓
in_progress
   ↓
completed

A request can also be cancelled where applicable.

API

The application provides endpoints for:

Health checking
Creating service requests
Listing service requests
Retrieving individual requests
Updating request status
Interactive API documentation

The API documentation is available through FastAPI's built-in documentation interface when running the application locally.

Dashboard

The project includes a dynamic browser dashboard available at:

/app

The dashboard provides:

Request statistics
Request listing
Status information
Request data loaded from the API
Connection/error feedback
Interactive status-oriented workflow presentation

The dashboard is implemented using vanilla HTML, CSS, and JavaScript without React, Vue, or other frontend frameworks.

Project Structure
smart-service-request-api-workflow/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   │
│   └── static/
│       ├── index.html
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
│
├── docs/
│   └── api.md
│
├── tests/
│   ├── test_health.py
│   ├── test_requests_api.py
│   └── test_static_frontend.py
│
├── .gitignore
├── CHANGELOG.md
├── README.md
└── requirements.txt

Running Locally
1. Clone the repository
git clone https://github.com/pybuildlab/smart-service-request-api-workflow.git
cd smart-service-request-api-workflow
2. Create a virtual environment

Windows:

python -m venv .venv

Activate it:

.\.venv\Scripts\Activate.ps1
3. Install dependencies
python -m pip install -r requirements.txt
4. Start the application
python -m uvicorn app.main:app --reload

The API will be available at:

http://127.0.0.1:8000/

The user-facing dashboard is available at:

http://127.0.0.1:8000/app

FastAPI documentation is available locally at:

http://127.0.0.1:8000/docs

Testing

Run the complete test suite with:

python -m pytest

The project includes automated tests covering:

Health endpoint behavior
Service-request API behavior
Validation and error handling
Database-backed request operations
Static dashboard resources
Frontend/API integration behavior

The current project test suite contains 35 passing tests.

Documentation

Additional API documentation is available in:

docs/api.md

Project changes are tracked in:

CHANGELOG.md

Design Approach

The project intentionally uses a lightweight architecture:

FastAPI instead of a heavier backend stack
SQLite instead of a separate database server
Vanilla JavaScript instead of a frontend framework
Python virtual environment for dependency isolation
Automated tests for regression protection

This keeps the system easy to run locally while demonstrating backend API development, persistence, testing, documentation, and frontend integration in a single project.

Future Scope

Possible future extensions include:

Authentication and authorization
User and role management
Request assignment
Search and advanced filtering
Notifications
Deployment to a public cloud platform
Additional reporting and analytics

## License

This project is intended as a portfolio and learning project.