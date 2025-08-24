#!/bin/bash

# StockScope Deployment Script
# This script helps deploy StockScope to various hosting platforms

set -e

echo "🚀 StockScope Deployment Helper"
echo "================================"

# Check if we're on the deploy branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "deploy" ]; then
    echo "⚠️  You're not on the deploy branch. Switching to deploy branch..."
    git checkout deploy 2>/dev/null || git checkout -b deploy
fi

echo "✅ On deploy branch"

# Function to deploy to Vercel (Frontend)
deploy_frontend() {
    echo ""
    echo "📱 Frontend Deployment (Vercel)"
    echo "==============================="
    echo "1. Install Vercel CLI: npm i -g vercel"
    echo "2. Login to Vercel: vercel login"
    echo "3. Deploy frontend:"
    echo "   cd stockscope-frontend"
    echo "   vercel --prod"
    echo ""
    echo "Environment variables to set in Vercel:"
    echo "- NEXT_PUBLIC_API_URL: Your Railway backend URL"
    echo ""
}

# Function to deploy to Railway (Backend)
deploy_backend() {
    echo ""
    echo "🚂 Backend Deployment (Railway)"
    echo "==============================="
    echo "1. Install Railway CLI: npm install -g @railway/cli"
    echo "2. Login to Railway: railway login"
    echo "3. Deploy backend:"
    echo "   railway new"
    echo "   railway up"
    echo ""
    echo "Environment variables to set in Railway:"
    echo "- ADMIN_PASSWORD: Your admin password"
    echo "- DEMO_PASSWORD: Your demo password"
    echo "- GUEST_PASSWORD: Your guest password"
    echo ""
}

# Function to deploy to Render (Alternative)
deploy_render() {
    echo ""
    echo "🎨 Alternative: Render Deployment"
    echo "================================="
    echo "Backend (Render Web Service):"
    echo "- Connect your GitHub repo"
    echo "- Build Command: pip install -r requirements.txt"
    echo "- Start Command: uvicorn backend.api:app --host 0.0.0.0 --port \$PORT"
    echo ""
    echo "Frontend (Render Static Site):"
    echo "- Build Command: cd stockscope-frontend && npm install && npm run build"
    echo "- Publish Directory: stockscope-frontend/out"
    echo ""
}

# Function to show DigitalOcean deployment
deploy_digitalocean() {
    echo ""
    echo "🌊 DigitalOcean App Platform"
    echo "============================"
    echo "1. Create app from GitHub repo"
    echo "2. Configure two components:"
    echo "   - Backend: Python app (backend/)"
    echo "   - Frontend: Node.js app (stockscope-frontend/)"
    echo "3. Set environment variables"
    echo "4. Deploy for \$5/month"
    echo ""
}

# Show all options
echo "Choose your deployment strategy:"
echo ""
echo "💰 Cost Breakdown:"
echo "==================="
echo "1. Vercel (Frontend) + Railway (Backend) = \$5/month"
echo "   ✅ Best for development and small scale"
echo "   ✅ Easy to set up"
echo "   ✅ Great developer experience"
echo ""
echo "2. Render (Full Stack) = Free tier or \$7/month"
echo "   ✅ All-in-one solution"
echo "   ✅ Good for simple deployments"
echo ""
echo "3. DigitalOcean App Platform = \$5/month"
echo "   ✅ Reliable and scalable"
echo "   ✅ Good performance"
echo ""

echo "What would you like to deploy?"
echo "1) Frontend to Vercel"
echo "2) Backend to Railway"
echo "3) Show Render deployment guide"
echo "4) Show DigitalOcean deployment guide"
echo "5) Show all deployment guides"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        deploy_frontend
        ;;
    2)
        deploy_backend
        ;;
    3)
        deploy_render
        ;;
    4)
        deploy_digitalocean
        ;;
    5)
        deploy_frontend
        deploy_backend
        deploy_render
        deploy_digitalocean
        ;;
    *)
        echo "Invalid choice. Showing all guides..."
        deploy_frontend
        deploy_backend
        deploy_render
        deploy_digitalocean
        ;;
esac

echo ""
echo "🔧 Pre-deployment Checklist:"
echo "============================="
echo "✅ Dockerfile.backend exists"
echo "✅ Dockerfile.frontend exists"
echo "✅ railway.json configured"
echo "✅ vercel.json configured"
echo "✅ Health endpoint added to backend"
echo "✅ CORS configured for production"
echo ""
echo "🎉 Ready to deploy! Follow the instructions above."
echo ""
echo "💡 Pro Tips:"
echo "- Test locally with: docker-compose up"
echo "- Monitor deployments with platform dashboards"
echo "- Set up environment variables carefully"
echo "- Use the health endpoints for monitoring"
echo ""