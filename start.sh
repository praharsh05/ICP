#!/bin/bash

# ICP Project Local Startup Script

echo "🚀 Starting ICP Project locally..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create backend .env if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env file..."
    cat > backend/.env << 'EOF'
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DB=neo4j
EOF
fi

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 5

# Check service health
echo "🔍 Checking service health..."

# Check Neo4j
if docker exec icp-neo4j cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; then
    echo "✅ Neo4j is running"
else
    echo "⏳ Neo4j is starting..."
fi

# Check Backend
sleep 3
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running at http://localhost:8000"
else
    echo "⏳ Backend is starting..."
fi

# Check Frontend
sleep 3
if curl -s http://localhost:6693 > /dev/null; then
    echo "✅ Frontend is running at http://localhost:6693"
else
    echo "⏳ Frontend is starting..."
fi

echo ""
echo "🎉 Services are starting up!"
echo ""
echo "📍 Access points:"
echo "   Frontend:  http://localhost:6693"
echo "   Backend:   http://localhost:8000"
echo "   Neo4j:     http://localhost:7474 (neo4j/password)"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop:         docker-compose down"
echo "   Restart:      docker-compose restart"







