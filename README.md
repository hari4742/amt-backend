# AMT Backend - Automatic Music Transcription

A FastAPI-based backend service for automatic music transcription with audio-to-MIDI conversion capabilities.

## Features

- **Audio Upload & Processing**: Support for multiple audio formats (WAV, MP3, FLAC, M4A, OGG)
- **Async Transcription**: Background processing using Celery and Redis
- **MIDI Generation**: Convert audio to MIDI format with quality metrics
- **RESTful API**: Complete API with status polling and result retrieval
- **File Management**: Secure file upload, validation, and cleanup
- **Database Storage**: PostgreSQL/SQLite support with SQLAlchemy ORM
- **Docker Support**: Complete containerization for development and production

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (recommended)
- PostgreSQL (optional, SQLite for development)

### Using Docker (Recommended)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd amt-backend
   ```

2. **Copy environment file**

   ```bash
   cp env.example .env
   ```

3. **Start the services**

   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Celery Monitoring: http://localhost:5555

### Local Development

1. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**

   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Start Redis and PostgreSQL**

   ```bash
   # Using Docker for dependencies
   docker-compose up -d redis db
   ```

5. **Run the application**

   ```bash
   uvicorn app.main:app --reload
   ```

6. **Start Celery worker (in another terminal)**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   ```

## API Endpoints

### Core Endpoints

- `POST /api/transcribe` - Upload audio file and start transcription
- `GET /api/transcribe/{id}/status` - Get transcription status
- `GET /api/transcribe/{id}/result` - Get transcription result
- `GET /api/transcriptions` - List all transcriptions
- `DELETE /api/transcribe/{id}` - Delete transcription

### Utility Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

## Project Structure

```
amt-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   └── transcription.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   └── transcription.py
│   ├── api/                    # API routes
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           └── transcription.py
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   └── transcription_tasks.py
│   └── core/                   # Core functionality
│       ├── __init__.py
│       ├── database.py
│       └── celery_app.py
├── tests/                      # Test files
├── uploads/                    # File uploads
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker services
├── pyproject.toml             # Development tools
├── .flake8                    # Linting configuration
├── env.example                # Environment variables example
└── README.md                  # This file
```

## Configuration

### Environment Variables

| Variable        | Description                | Default                      |
| --------------- | -------------------------- | ---------------------------- |
| `DEBUG`         | Debug mode                 | `false`                      |
| `HOST`          | Server host                | `0.0.0.0`                    |
| `PORT`          | Server port                | `8000`                       |
| `DATABASE_URL`  | Database connection string | `sqlite:///./amt_backend.db` |
| `REDIS_URL`     | Redis connection string    | `redis://localhost:6379/0`   |
| `UPLOAD_DIR`    | File upload directory      | `./uploads`                  |
| `MAX_FILE_SIZE` | Maximum file size (bytes)  | `104857600` (100MB)          |
| `SECRET_KEY`    | Application secret key     | Required                     |
| `CORS_ORIGINS`  | Allowed CORS origins       | `["http://localhost:3000"]`  |

### Audio Processing Settings

- **Supported Formats**: WAV, MP3, FLAC, M4A, OGG
- **Sample Rate**: 44.1kHz (configurable)
- **Max Duration**: 10 minutes (configurable)
- **Quality Levels**: Low, Medium, High

## Development

### Code Quality

The project uses several tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing

### Running Quality Checks

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Deployment

### Production Considerations

1. **Security**

   - Change default secret keys
   - Configure proper CORS origins
   - Use HTTPS
   - Set up proper authentication

2. **Performance**

   - Use production database (PostgreSQL)
   - Configure Redis for production
   - Set up proper logging
   - Use reverse proxy (nginx)

3. **Monitoring**
   - Set up health checks
   - Configure logging aggregation
   - Monitor Celery tasks
   - Set up error tracking

### Docker Production

```bash
# Build production image
docker build -t amt-backend:latest .

# Run with production settings
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  -e SECRET_KEY=your-secret-key \
  amt-backend:latest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on GitHub or contact the development team.
