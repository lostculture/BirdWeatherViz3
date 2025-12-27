#!/bin/bash
# BirdWeatherViz3 Test Script (Linux/Mac)
# Automated testing script for local development.
# Version: 1.0.0

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Trap Ctrl+C
cleanup() {
    print_header "Shutting Down"
    print_info "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    print_success "All servers stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main script
print_header "BirdWeatherViz3 Test Script"

# Check dependencies
print_header "Checking Dependencies"

if command -v python3 &> /dev/null; then
    print_success "Python 3 is installed"
else
    print_error "Python 3 is NOT installed"
    exit 1
fi

if command -v node &> /dev/null; then
    print_success "Node.js is installed"
else
    print_error "Node.js is NOT installed"
    exit 1
fi

if command -v npm &> /dev/null; then
    print_success "npm is installed"
else
    print_error "npm is NOT installed"
    exit 1
fi

# Setup backend
print_header "Setting Up Backend"

if [ ! -f "backend/.env" ] && [ -f "backend/.env.example" ]; then
    print_info "Creating .env from .env.example..."
    cp backend/.env.example backend/.env
    print_success ".env file created"
else
    print_success ".env file already exists"
fi

# Check Python dependencies
print_info "Checking Python dependencies..."
if python3 -c "import fastapi, sqlalchemy, plotly" 2>/dev/null; then
    print_success "Backend dependencies are installed"
else
    print_warning "Some backend dependencies missing"
    print_info "Installing backend dependencies..."
    pip install -r backend/requirements.txt
fi

# Setup frontend
print_header "Setting Up Frontend"

if [ ! -f "frontend/.env" ] && [ -f "frontend/.env.example" ]; then
    print_info "Creating .env from .env.example..."
    cp frontend/.env.example frontend/.env
    print_success ".env file created"
else
    print_success ".env file already exists"
fi

if [ ! -d "frontend/node_modules" ]; then
    print_warning "node_modules not found"
    print_info "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    print_success "Frontend dependencies installed"
else
    print_success "node_modules already exists"
fi

# Start backend
print_header "Starting Backend Server"

print_info "Starting uvicorn on http://localhost:8000..."
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

print_info "Waiting for backend to start..."
sleep 3

if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    print_success "Backend is running at http://localhost:8000"
    print_info "API docs available at http://localhost:8000/api/v1/docs"
else
    print_error "Backend failed to start (check backend.log)"
    exit 1
fi

# Start frontend
print_header "Starting Frontend Dev Server"

print_info "Starting Vite dev server on http://localhost:3000..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

print_info "Waiting for frontend to start..."
sleep 5

if curl -s http://localhost:3000 > /dev/null; then
    print_success "Frontend is running at http://localhost:3000"
else
    print_warning "Frontend might not be ready yet (check frontend.log)"
fi

# Open browser
print_header "Opening Browser"
print_info "Opening http://localhost:3000 in your browser..."

if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
elif command -v open &> /dev/null; then
    open http://localhost:3000
else
    print_warning "Could not auto-open browser"
fi

# Keep running
print_header "Servers Running"
print_success "Backend: http://localhost:8000"
print_success "Frontend: http://localhost:3000"
print_success "API Docs: http://localhost:8000/api/v1/docs"
echo ""
print_warning "Press Ctrl+C to stop all servers"
echo ""
print_info "Logs available in backend.log and frontend.log"

# Wait for Ctrl+C
wait
