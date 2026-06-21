# New York Archival Society

A Flask web application for the New York Archival Society that allows users to adopt historical records and purchase vintage NYC bonds. Built with Flask, PostgreSQL, and integrated with PayPal for payments.

## 🚀 Features

- **Adopt New York's Past**: Browse and adopt historical records with detailed descriptions
- **Vintage Bonds**: Purchase authentic NYC bonds from the 1920s-1980s
- **PayPal Integration**: Secure payment processing for adoptions and purchases
- **Email Notifications**: Automated confirmation emails via EmailJS
- **Responsive Design**: Mobile-friendly interface with Bootstrap
- **Database Optimization**: Enhanced queries with caching and indexing
- **Pagination**: Efficient browsing with paginated results

## 🛠️ Technology Stack

- **Backend**: Flask 3.0.3, SQLAlchemy, Alembic migrations
- **Database**: PostgreSQL (Neon.tech hosting)
- **Frontend**: Jinja2 templates, Bootstrap 5, JavaScript
- **Payments**: PayPal API integration
- **Email**: EmailJS service
- **Caching**: Flask-Caching with Redis support
- **Deployment**: Vercel-ready configuration

## 📋 Prerequisites

- Python 3.10.2 or higher
- PostgreSQL database (or Neon.tech account)
- PayPal developer account
- EmailJS account

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd New-York-Archival-Society
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install from requirements.txt
pip install -r api/requirements.txt

# Alternative: Use Pipenv
pipenv install
pipenv shell
```

### 4. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# Database Configuration
DATABASE_URI=postgresql://username:password@host:port/database_name

# Flask Configuration
SECRET_KEY=your_strong_secret_key_here
FLASK_ENV=development
FLASK_DEBUG=True

# PayPal Configuration
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET_KEY=your_paypal_client_secret
PAYPAL_API_BASE_URL=https://api-m.sandbox.paypal.com

# EmailJS Configuration
EMAILJS_SERVICE_ID=your_emailjs_service_id
EMAILJS_API_ID=your_emailjs_api_key
EMAILJS_PRIVATE_KEY=your_emailjs_private_key
EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM=your_contact_template_id
EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL=your_confirmation_template_id
RECIPIENT_EMAILS=admin@yourdomain.com
```

### 5. Database Setup

```bash
# Initialize database migrations (if needed)
flask db init

# Run migrations to create tables
flask db upgrade
```

### 6. Run the Application

```bash
# Development server
python api/index.py

# Alternative: Using Flask CLI
flask run
```

The application will be available at `http://localhost:5000`

## 🔧 Configuration Details

### Environment Variables

| Variable                                            | Description                   | Required | Example                                                                         |
| --------------------------------------------------- | ----------------------------- | -------- | ------------------------------------------------------------------------------- |
| `DATABASE_URI`                                      | PostgreSQL connection string  | Yes      | `postgresql://user:pass@host:5432/dbname`                                       |
| `SECRET_KEY`                                        | Flask secret key for sessions | Yes      | `your-super-secret-key`                                                         |
| `FLASK_ENV`                                         | Environment mode              | No       | `development` or `production`                                                   |
| `FLASK_DEBUG`                                       | Debug mode toggle             | No       | `True` or `False`                                                               |
| `PAYPAL_CLIENT_ID`                                  | PayPal API client ID          | Yes      | `your_paypal_client_id`                                                         |
| `PAYPAL_CLIENT_SECRET_KEY`                          | PayPal API secret             | Yes      | `your_paypal_client_secret`                                                     |
| `PAYPAL_API_BASE_URL`                               | PayPal API endpoint           | Yes      | Sandbox: `https://api-m.sandbox.paypal.com`<br>Live: `https://api-m.paypal.com` |
| `EMAILJS_SERVICE_ID`                                | EmailJS service identifier    | Yes      | `your_emailjs_service_id`                                                       |
| `EMAILJS_API_ID`                                    | EmailJS public key            | Yes      | `your_emailjs_api_key`                                                          |
| `EMAILJS_PRIVATE_KEY`                               | EmailJS private key for server-side API requests | Yes | `your_emailjs_private_key`                                      |
| `EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM`              | Contact form template         | Yes      | `your_contact_template_id`                                                      |
| `EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL` | Payment confirmation template | Yes      | `your_confirmation_template_id`                                                 |
| `RECIPIENT_EMAILS`                                  | Admin notification emails     | Yes      | `admin@example.com`                                                             |

### PayPal Setup

1. Create a PayPal developer account at [developer.paypal.com](https://developer.paypal.com)
2. Create a new application to get your Client ID and Secret
3. For development, use sandbox credentials
4. For production, use live credentials and update the API base URL

### EmailJS Setup

1. Sign up at [EmailJS](https://www.emailjs.com/)
2. Create email service and templates
3. In **Account > Security**, enable the EmailJS API for non-browser applications and enable **Use Private Key**
4. Copy the service ID, public key, private key, and template IDs into `.env`
5. Configure email templates for contact forms and payment confirmations
6. If you use Gmail, connect or reconnect the Gmail service and grant all requested sending scopes

`EMAILJS_PRIVATE_KEY` is required because purchase notifications are sent from the Flask server. Never commit the real private key or expose it to browser-side code.

### Database Configuration

**For Neon.tech (recommended):**

1. Create account at [neon.tech](https://neon.tech)
2. Create a new database
3. Copy the connection string to `DATABASE_URI`

**For local PostgreSQL:**

```bash
# Install PostgreSQL
# Create database
createdb new_york_archival_society

# Update DATABASE_URI
DATABASE_URI=postgresql://localhost/new_york_archival_society
```

## 🚀 Deployment

### Vercel Deployment

The application is configured for Vercel deployment:

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Configure environment variables in Vercel dashboard
4. Set `FLASK_ENV=production` in Vercel environment

### Production Configuration

Create `.env.production` for production settings:

```env
FLASK_ENV=production
FLASK_DEBUG=False
PAYPAL_API_BASE_URL=https://api-m.paypal.com
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
```

## 📁 Project Structure

```
New-York-Archival-Society/
├── api/
│   ├── index.py              # Application entry point
│   └── requirements.txt      # Python dependencies
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── db/
│   │   ├── models.py        # Database models
│   │   └── db.py           # Database configuration
│   ├── routes/
│   │   └── main/           # Main route handlers
│   ├── services/           # Business logic services
│   ├── static/             # CSS, JS, images
│   ├── templates/          # Jinja2 templates
│   └── utils/              # Utility functions
├── migrations/             # Database migrations
├── .env.example           # Environment template
├── .env                   # Environment configuration
├── vercel.json           # Vercel deployment config
└── README.md             # This file
```

## 🔧 Development

### Database Migrations

```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# View migration history
flask db history
```

### Adding New Features

1. Create database models in `app/db/models.py`
2. Generate migration: `flask db migrate`
3. Apply migration: `flask db upgrade`
4. Add routes in `app/routes/main/views.py`
5. Create templates in `app/templates/`
6. Add static assets in `app/static/`
