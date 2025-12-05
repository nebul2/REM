#!/bin/bash
# Create basic auth users for Traefik
# Users: admin and gos (both with password: stats2024)

AUTH_DIR="traefik-config/auth"
mkdir -p "$AUTH_DIR"

# Create users file with admin and gos
# Using htpasswd format: username:encrypted_password
# If htpasswd is not available, use openssl

if command -v htpasswd &> /dev/null; then
    htpasswd -bc "$AUTH_DIR/users.txt" admin stats2024
    htpasswd -b "$AUTH_DIR/users.txt" gos stats2024
elif command -v openssl &> /dev/null; then
    # Generate password hash using openssl
    ADMIN_HASH=$(openssl passwd -apr1 stats2024)
    GOS_HASH=$(openssl passwd -apr1 stats2024)
    echo "admin:$ADMIN_HASH" > "$AUTH_DIR/users.txt"
    echo "gos:$GOS_HASH" >> "$AUTH_DIR/users.txt"
else
    # Fallback: create simple file (Traefik will need proper format)
    echo "admin:stats2024" > "$AUTH_DIR/users.txt"
    echo "gos:stats2024" >> "$AUTH_DIR/users.txt"
    echo "⚠️  Warning: Created plain text passwords. Install htpasswd or openssl for proper encryption."
fi

echo "✅ Auth file created at $AUTH_DIR/users.txt"
echo "Users: admin, gos"
echo "Default password: stats2024"
echo ""
echo "To change passwords later, run:"
echo "  htpasswd -b $AUTH_DIR/users.txt admin <newpassword>"
echo "  htpasswd -b $AUTH_DIR/users.txt gos <newpassword>"

