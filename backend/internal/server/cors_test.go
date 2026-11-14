package server

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"homework_ai2easy/backend/internal/conf"
)

func TestCORSFilter_OPTIONS_preflight(t *testing.T) {
	t.Run("enabled_with_wildcard", func(t *testing.T) {
		c := &conf.CORS{
			Enabled:      true,
			AllowOrigins: []string{"*"},
			AllowMethods: []string{"GET", "POST", "OPTIONS"},
			AllowHeaders: []string{"Content-Type", "Authorization"},
		}
		f := CORSFilter(c)
		h := f(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(200) }))
		req := httptest.NewRequest(http.MethodOptions, "http://example.com/api/v1/auth/login", nil)
		req.Header.Set("Origin", "http://localhost:3000")
		req.Header.Set("Access-Control-Request-Method", "POST")
		req.Header.Set("Access-Control-Request-Headers", "Content-Type,Authorization")
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		require.Equal(t, http.StatusNoContent, rec.Code)
		assert.Equal(t, "*", rec.Header().Get("Access-Control-Allow-Origin"))
		assert.Equal(t, "GET, POST, OPTIONS", rec.Header().Get("Access-Control-Allow-Methods"))
		assert.Equal(t, "Content-Type, Authorization", rec.Header().Get("Access-Control-Allow-Headers"))
		assert.NotEmpty(t, rec.Header().Get("Access-Control-Max-Age"))
	})

	t.Run("enabled_with_credentials_and_specific_origin", func(t *testing.T) {
		c := &conf.CORS{
			Enabled:          true,
			AllowOrigins:     []string{"http://localhost:5173", "http://127.0.0.1:5173"},
			AllowMethods:     []string{"GET", "POST", "OPTIONS"},
			AllowHeaders:     []string{"Content-Type", "Authorization"},
			AllowCredentials: true,
		}
		f := CORSFilter(c)
		h := f(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(200) }))
		req := httptest.NewRequest(http.MethodOptions, "http://example.com/api/v1/auth/send-sms", nil)
		req.Header.Set("Origin", "http://localhost:5173")
		req.Header.Set("Access-Control-Request-Method", "POST")
		req.Header.Set("Access-Control-Request-Headers", "Content-Type,Authorization")
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		require.Equal(t, http.StatusNoContent, rec.Code)
		assert.Equal(t, "http://localhost:5173", rec.Header().Get("Access-Control-Allow-Origin"))
		assert.Equal(t, "true", rec.Header().Get("Access-Control-Allow-Credentials"))
	})

	t.Run("origin_trailing_slash_normalized", func(t *testing.T) {
		c := &conf.CORS{
			Enabled:          true,
			AllowOrigins:     []string{"http://localhost:5173"},
			AllowMethods:     []string{"POST", "OPTIONS"},
			AllowHeaders:     []string{"Content-Type"},
			AllowCredentials: true,
		}
		f := CORSFilter(c)
		h := f(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(200) }))
		req := httptest.NewRequest(http.MethodOptions, "http://example.com/api/v1/auth/send-sms", nil)
		req.Header.Set("Origin", "http://localhost:5173/")
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		require.Equal(t, http.StatusNoContent, rec.Code)
		assert.Equal(t, "http://localhost:5173/", rec.Header().Get("Access-Control-Allow-Origin"))
	})
}
