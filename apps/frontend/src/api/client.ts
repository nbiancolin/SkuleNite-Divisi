export const API_BASE_URL = import.meta.env.VITE_API_URL;
export const DISCORD_LOGIN_URL = `${API_BASE_URL}/accounts/discord/login/?process=login`;

export function getCsrfToken(): string | null {
  const name = "csrftoken";
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export function getHeadersWithCsrf(contentType: string = "application/json"): HeadersInit {
  const headers: HeadersInit = {
    Accept: "application/json",
    "Content-Type": contentType,
  };

  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }

  return headers;
}
