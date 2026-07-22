# FileConverter - Flutter Frontend

Flutter desktop UI for FileConverter, working with the Python FastAPI backend.

## Development

```bash
flutter pub get
flutter run -d windows
```

## Build

```bash
flutter build windows --debug
```

Build Artifacts:`build\windows\x64\runner\Debug\flutter_app.exe`

## Architecture

- Flutter automatically launches `python_backend/main.py` as a child process on startup
- Communicates with the backend via HTTP REST API (localhost:8700)
- Supports file upload, format selection, conversion progress polling, and result display
