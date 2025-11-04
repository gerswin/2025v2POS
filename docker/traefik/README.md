# Traefik Configuration for Tiquemax POS

This directory contains Traefik configuration files for the Tiquemax POS system.

## 📁 Files

- **traefik.yml** - Static configuration (entry points, providers, Let's Encrypt)
- **dynamic.yml** - Dynamic configuration (middlewares, TLS options)

## 🎯 What is Traefik?

Traefik is a modern HTTP reverse proxy and load balancer that:
- ✅ Automatically discovers services
- ✅ Provides SSL/TLS certificates via Let's Encrypt
- ✅ Includes a built-in dashboard
- ✅ Supports dynamic configuration
- ✅ Offers integrated middlewares (rate limiting, headers, auth, etc.)

## 🚀 Features Configured

### 1. SSL/TLS Automation
- Automatic Let's Encrypt certificate generation
- Automatic renewal
- HTTP to HTTPS redirection
- Modern TLS configuration (TLS 1.2+)

### 2. Security
- Security headers (HSTS, X-Frame-Options, etc.)
- Rate limiting (different rates for different endpoints)
- Basic authentication for dashboard
- IP whitelisting support (optional)

### 3. Performance
- Gzip compression
- HTTP/2 support
- Connection pooling
- Prometheus metrics

### 4. Monitoring
- Dashboard at `/dashboard/`
- Access logs in JSON format
- Prometheus metrics endpoint
- Real-time service discovery

## 🔐 Dashboard Access

The Traefik dashboard is available at:
- **URL**: `https://your-domain.com/dashboard/`
- **Default User**: `admin`
- **Default Password**: `admin` (change in `.env.production`!)

To generate a new password hash:
```bash
# Install apache2-utils if not available
sudo apt-get install apache2-utils

# Generate password hash
echo $(htpasswd -nB admin) | sed -e s/\\$/\\$\\$/g
```

Copy the generated hash to `docker/traefik/dynamic.yml` in the `dashboard-auth` middleware.

## ⚙️ Configuration

### Environment Variables

Set these in `.env.production`:

```bash
# Domain for SSL certificates
DOMAIN=your-domain.com

# Email for Let's Encrypt notifications
ACME_EMAIL=admin@your-domain.com

# Traefik log level (DEBUG, INFO, WARN, ERROR)
TRAEFIK_LOG_LEVEL=INFO
```

### Entry Points

- **web** (port 80): HTTP traffic, redirects to HTTPS
- **websecure** (port 443): HTTPS traffic with TLS

### Middlewares

#### security-headers
Adds security headers:
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Strict-Transport-Security: max-age=31536000
- X-XSS-Protection: 1; mode=block

#### rate-limit-general
- Average: 100 requests/second
- Burst: 50 requests

#### rate-limit-api
- Average: 50 requests/second
- Burst: 20 requests

#### rate-limit-admin
- Average: 20 requests/second
- Burst: 10 requests

#### rate-limit-auth
- Average: 5 requests/minute
- Burst: 10 requests

#### compress
Enables gzip compression for responses.

#### cors-headers
Adds CORS headers for API access.

## 🔄 Routes

Traefik automatically routes traffic based on labels in `docker-compose.prod.yml`:

### Main Application
- **Rule**: `Host(your-domain.com)`
- **Middlewares**: security-headers, compress, rate-limit-general

### Admin Panel
- **Rule**: `Host(your-domain.com) && PathPrefix(/admin)`
- **Middlewares**: security-headers, compress, rate-limit-admin

### API
- **Rule**: `Host(your-domain.com) && PathPrefix(/api)`
- **Middlewares**: security-headers, compress, rate-limit-api, cors-headers

### Auth Endpoints
- **Rule**: `Host(your-domain.com) && PathPrefix(/accounts/login)`
- **Middlewares**: security-headers, compress, rate-limit-auth

### Flower (Celery Monitoring)
- **Rule**: `Host(your-domain.com) && PathPrefix(/flower)`
- **Middlewares**: security-headers, compress, rate-limit-general

### Traefik Dashboard
- **Rule**: `Host(your-domain.com) && (PathPrefix(/dashboard) || PathPrefix(/api))`
- **Middlewares**: dashboard-auth, security-headers

## 📝 Logs

Traefik generates two types of logs:

### Application Logs
- **Location**: `/var/log/traefik/traefik.log`
- **Format**: JSON
- **Level**: Configurable via `TRAEFIK_LOG_LEVEL`

### Access Logs
- **Location**: `/var/log/traefik/access.log`
- **Format**: JSON
- **Includes**: All HTTP requests

View logs:
```bash
# Docker Compose
docker-compose -f docker-compose.prod.yml logs -f traefik

# Podman Pod
podman logs -f tiquemax-pos-traefik
```

## 🔧 Testing SSL/TLS

### Test Certificate Generation (Staging)

For testing, use Let's Encrypt staging server to avoid rate limits:

1. Edit `traefik.yml` and uncomment:
```yaml
caServer: https://acme-staging-v02.api.letsencrypt.org/directory
```

2. Restart Traefik
3. Remove the staging config when ready for production

### Verify SSL Configuration

```bash
# Check SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Test with curl
curl -I https://your-domain.com

# Check SSL Labs
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
```

## 📊 Metrics

Traefik exposes Prometheus metrics which can be scraped:

### Metrics Endpoint
- **Path**: Internal (not exposed externally)
- **Format**: Prometheus
- **Includes**:
  - HTTP request counts
  - Response times
  - Error rates
  - TLS information

### Integration with Prometheus

Add to your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'traefik'
    static_configs:
      - targets: ['traefik:8080']
```

## 🛡️ Security Best Practices

### 1. Change Default Passwords
- Dashboard basic auth password
- Flower basic auth password

### 2. Enable TLS
- Set `DOMAIN` to your real domain
- Set `ACME_EMAIL` to your email
- Ensure ports 80 and 443 are accessible

### 3. Configure Firewall
```bash
# Allow only HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 4. Rate Limiting
Adjust rate limits in `dynamic.yml` based on your needs:
- Increase for high-traffic sites
- Decrease for better protection

### 5. IP Whitelisting (Optional)
Uncomment and configure in `dynamic.yml`:
```yaml
ip-whitelist:
  ipWhiteList:
    sourceRange:
      - "10.0.0.0/8"
      - "192.168.0.0/16"
```

## 🔄 Dynamic Configuration Updates

Traefik watches `dynamic.yml` for changes. To apply new configuration:

1. Edit `docker/traefik/dynamic.yml`
2. Save the file
3. Traefik will automatically reload (no restart needed!)

## 🐛 Troubleshooting

### Certificate Issues

```bash
# Check acme.json permissions
ls -l /letsencrypt/acme.json
# Should be: -rw------- (600)

# View certificate details
docker-compose exec traefik cat /letsencrypt/acme.json | jq .
```

### Service Not Found

```bash
# Check Traefik dashboard for registered services
# Visit: https://your-domain.com/dashboard/#/http/routers

# Verify service labels
docker-compose config | grep traefik.enable
```

### Rate Limiting Issues

```bash
# Check access logs for 429 errors
docker-compose logs traefik | grep "429"

# Adjust rate limits in dynamic.yml if needed
```

## 📚 Resources

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Traefik Dashboard](https://doc.traefik.io/traefik/operations/dashboard/)
- [Traefik Middlewares](https://doc.traefik.io/traefik/middlewares/overview/)

## 🆘 Support

For issues specific to this Traefik configuration:
1. Check Traefik logs: `docker-compose logs -f traefik`
2. Visit Traefik dashboard: `https://your-domain.com/dashboard/`
3. Review this README and Traefik documentation
4. Open an issue on GitHub

---

**Last Updated**: November 2025
**Traefik Version**: 2.11
**Compatibility**: Docker 20.10+, Podman 4.0+
