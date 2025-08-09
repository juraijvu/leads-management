# Training Center CRM

## Overview

A comprehensive Customer Relationship Management (CRM) system specifically designed for training centers to manage leads, track sales pipelines, schedule meetings, handle course management, and track student progress. The application provides a complete business management solution with features for lead tracking, conversion management, corporate training deals, and comprehensive reporting.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Flask with Jinja2 templating engine for server-side rendering
- **UI Framework**: Bootstrap 5 for responsive design and component styling
- **JavaScript Libraries**: Chart.js for data visualization, vanilla JavaScript for interactive features
- **CSS Architecture**: Custom CSS with CSS variables for theming, modular stylesheets for different components
- **Responsive Design**: Mobile-first approach with breakpoint-based layouts

### Backend Architecture
- **Web Framework**: Flask (Python) with Blueprint-based modular routing
- **Database ORM**: SQLAlchemy with declarative base for database operations
- **Authentication**: Flask-Login for session management and user authentication
- **Form Handling**: WTForms with Flask-WTF for form validation and CSRF protection
- **File Structure**: Modular separation with dedicated files for models, routes, forms, and utilities

### Data Storage Solutions
- **Primary Database**: SQLite for offline functionality and simplicity
- **Database Schema**: Relational design with entities for Users, Leads, Students, Courses, Meetings, and Lead Interactions
- **Session Management**: Flask's built-in session handling with configurable secret keys
- **Data Relationships**: Foreign key relationships between leads, courses, students, and user interactions

### Authentication and Authorization
- **User Management**: Username/password authentication with password hashing
- **Session Security**: Secure session cookies with environment-configurable secret keys
- **Access Control**: Flask-Login decorators for protecting routes
- **Role-Based Access**: User role system with different permission levels

### Core Business Logic
- **Lead Management**: Complete lead lifecycle tracking from initial contact to conversion
- **Pipeline Management**: Visual sales funnel with drag-and-drop functionality
- **Course Management**: Training program creation and management with pricing
- **Student Tracking**: Enrollment management and progress monitoring
- **Meeting Scheduler**: Calendar integration for appointments and follow-ups
- **Reporting System**: Analytics and insights generation for business intelligence

## External Dependencies

### Frontend Libraries
- **Bootstrap 5**: UI framework for responsive design and components
- **Font Awesome 6**: Icon library for consistent iconography
- **Chart.js**: JavaScript charting library for data visualization and analytics

### Backend Dependencies
- **Flask**: Core web framework for Python
- **Flask-SQLAlchemy**: Database ORM integration
- **Flask-Login**: User session management
- **Flask-Mail**: Email functionality for notifications
- **Flask-WTF**: Form handling and validation
- **WTForms**: Form field definitions and validation
- **Werkzeug**: Password hashing and security utilities

### Email Services
- **SMTP Integration**: Gmail SMTP for email notifications and communication
- **Email Configuration**: Environment-based email credentials for production deployment

### Development Tools
- **SQLite**: Embedded database for development and offline functionality
- **Environment Variables**: Configuration management for secrets and settings