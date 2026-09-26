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