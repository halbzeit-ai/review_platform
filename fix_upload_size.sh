#!/bin/bash
# Fix nginx upload size limit

echo "🔧 Fixing nginx upload size limit..."

# Update nginx configuration
cat > /etc/nginx/sites-available/review-platform << 'EOF'
server {
    listen 80;
    server_name your-domain.com $public_ipv4;
    
    # Increase max upload size for PDF files (50MB)
    client_max_body_size 50M;

    # Frontend
    location / {
        root /opt/review-platform/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for file uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static {
        root /opt/review-platform/frontend/build;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Test nginx configuration
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    # Reload nginx
    systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
    echo "📝 Upload size limit increased to 50MB"
else
    echo "❌ Nginx configuration error"
    exit 1
fi