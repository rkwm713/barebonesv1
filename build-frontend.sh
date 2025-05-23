#!/bin/bash
set -e

echo "🔨 Starting frontend build process..."

# Navigate to frontend directory
cd frontend

# Clean any existing dist
echo "🧹 Cleaning previous builds..."
rm -rf dist/

# Install dependencies
echo "📦 Installing frontend dependencies..."
npm ci

# Build the frontend
echo "🏗️  Building frontend..."
npm run build

# Verify build output
echo "✅ Verifying build output..."
if [ -d "dist" ]; then
    echo "✅ Build successful! Contents of dist:"
    ls -la dist/
    echo "✅ Index.html exists:" 
    ls -la dist/index.html
else
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "🎉 Frontend build complete!"
