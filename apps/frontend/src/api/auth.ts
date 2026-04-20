import { API_BASE_URL, DISCORD_LOGIN_URL, getCsrfToken, getHeadersWithCsrf } from "./client";
import type { AuthResponse } from "./types";

export function getDiscordLoginUrl(nextUrl?: string): string {
  const feBase =
    (import.meta.env.VITE_FE_URL && import.meta.env.VITE_FE_URL.replace(/\/$/, "")) || window.location.origin;
  let next: string;

  if (nextUrl) {
    try {
      const maybeAbsolute = new URL(nextUrl, feBase);
      next = maybeAbsolute.href;
    } catch {
      next = nextUrl.startsWith("/") ? `${feBase}${nextUrl}` : `${feBase}/${nextUrl}`;
    }
  } else {
    next = `${feBase}${window.location.pathname}${window.location.search}`;
  }

  const separator = DISCORD_LOGIN_URL.includes("?") ? "&" : "?";
  return `${DISCORD_LOGIN_URL}${separator}next=${encodeURIComponent(next)}`;
}

export const authApi = {
  async fetchCsrfToken(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/get-csrf-token/`, {
        method: "GET",
        credentials: "include",
      });
      if (!response.ok) {
        console.warn("Failed to fetch CSRF token:", response.status);
      }
    } catch (error) {
      console.warn("Error fetching CSRF token:", error);
    }
  },

  async getCurrentUser(): Promise<AuthResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/current-user/`, {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Failed to get current user (status: ${response.status})`);
    }
    return response.json();
  },

  handleLogin(targetUrl = "/app/ensembles") {
    const url = getDiscordLoginUrl(targetUrl);
    const form = document.createElement("form");
    form.method = "POST";
    form.action = url;
    form.style.display = "none";

    const csrf = getCsrfToken();
    if (csrf) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "csrfmiddlewaretoken";
      input.value = csrf;
      form.appendChild(input);
    }

    document.body.appendChild(form);
    form.submit();
  },

  getDiscordLoginUrl,

  async logout(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Failed to logout (status: ${response.status})`);
    }
  },

  async getWarnings() {
    const response = await fetch(`${API_BASE_URL}/get-warnings/`, {
      credentials: "include",
    });
    if (!response.ok) {
      let errorDetails = "";
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(`Failed to fetch warning labels (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },
};
