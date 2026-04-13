# API Testing Guide

This guide shows how to authenticate and test the orchestrator API using Swagger UI, curl, and Postman.

## Base URLs

- Backend: `https://ipsec-lcir.onrender.com`
- Swagger UI: `https://ipsec-lcir.onrender.com/docs`
- OpenAPI schema: `https://ipsec-lcir.onrender.com/openapi.json`

## 1. Authentication Flow

The API uses OAuth2 password flow for admin endpoints.

### Swagger UI authorization

1. Open `/docs`.
2. Click `Authorize`.
3. Enter your admin `username` and `password`.
4. Leave `client_id` and `client_secret` empty.
5. Click `Authorize`.

If the admin account has TOTP enabled, the login endpoint also accepts `totp_code` as an additional form field.

### What the token is

- The login response returns an `access_token` and often a `refresh_token`.
- The `access_token` is the token you use for API calls.
- The token is signed with RSA and verified by the server public key.

### How Swagger stores it

Swagger uses the OAuth2 password flow configured at `/api/auth/login` and will attach the bearer token to protected endpoints after you authorize.

## 2. Login Endpoint

### Request

`POST /api/auth/login`

Content type: `application/x-www-form-urlencoded`

Required form fields:

- `username`
- `password`

Optional field:

- `totp_code`

### Example curl

```bash
curl -X POST "https://ipsec-lcir.onrender.com/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin&password=YourPasswordHere"
```

### Example response

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOi..."
}
```

## 3. Using the Bearer Token

For protected endpoints, send the token in the `Authorization` header:

```bash
curl "https://ipsec-lcir.onrender.com/api/policies/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 4. Common Protected Endpoints

### Policies

- `GET /api/policies/`
- `POST /api/policies/`
- `GET /api/policies/{policy_id}`
- `DELETE /api/policies/{policy_id}`
- `POST /api/policies/{policy_id}/assign/{device_id}`
- `DELETE /api/policies/unassign/{device_id}`
- `POST /api/policies/upload`

### Devices

- `GET /api/devices/`
- `GET /api/devices/{device_id}`
- `POST /api/devices/register`
- `GET /api/devices/{device_id}/config`

### Compliance

- `POST /api/devices/{device_id}/heartbeat`
- `POST /api/devices/{device_id}/compliance`
- `GET /api/devices/{device_id}/compliance`

### Admin MFA

- `POST /api/auth/totp/setup`
- `POST /api/auth/totp/verify`

## 5. Testing with curl

### Check health

```bash
curl "https://ipsec-lcir.onrender.com/health"
```

### Login and store token on Windows PowerShell

```powershell
$body = @{
  username = "admin"
  password = "YourPasswordHere"
}

$response = Invoke-RestMethod -Method Post `
  -Uri "https://ipsec-lcir.onrender.com/api/auth/login" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body $body

$token = $response.access_token
```

### Call a protected endpoint

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "https://ipsec-lcir.onrender.com/api/policies/" `
  -Headers @{ Authorization = "Bearer $token" }
```

## 6. Testing with Postman

1. Create a `POST` request to `https://ipsec-lcir.onrender.com/api/auth/login`.
2. Set body type to `x-www-form-urlencoded`.
3. Add `username` and `password`.
4. Send the request and copy `access_token`.
5. For protected requests, add header `Authorization: Bearer <token>`.

## 7. Testing in Swagger UI

1. Open `/docs`.
2. Click `Authorize`.
3. Enter admin credentials.
4. Run a protected endpoint such as `GET /api/policies/`.
5. If the account uses TOTP, use the login endpoint with `totp_code` first.

## 8. CORS and Frontend Testing

If testing from the Vercel frontend:

- Frontend should use `VITE_API_URL=https://ipsec-lcir.onrender.com`
- Backend should allow the Vercel origin in `ALLOWED_ORIGINS`

If you see a browser CORS error, confirm whether the backend is returning a `500` first, because browser CORS messages often hide server-side failures.

## 9. Troubleshooting

### 401 Unauthorized

- Wrong username or password
- Missing bearer token on a protected route
- TOTP enabled but `totp_code` not provided

### 403 Forbidden

- Admin token used on a non-admin route
- Zero Trust policy rejected the request

### 422 Validation Error

- Missing required form fields or JSON fields
- Wrong request content type

### CORS error in browser

- Check the backend response directly with curl or Postman
- Confirm the backend is not returning `500`
- Verify Render `ALLOWED_ORIGINS` includes the Vercel domain

## 10. Recommended Testing Order

1. Test `GET /health`
2. Test `POST /api/auth/login`
3. Use the bearer token on `GET /api/policies/`
4. Test `POST /api/devices/register`
5. Test policy upload and assignment
6. Test compliance and heartbeat endpoints
