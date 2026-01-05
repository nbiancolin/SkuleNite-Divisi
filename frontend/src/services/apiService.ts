const API_BASE_URL = import.meta.env.VITE_API_URL;
const DISCORD_LOGIN_URL = `${API_BASE_URL}/accounts/discord/login/?process=login`

export interface User {
  id: number;
  username: string;
  email: string;
  discord?: {
    id: string;
    username: string;
    discriminator: string;
    avatar: string | null;
  };
}

export interface AuthResponse {
  is_authenticated: boolean;
  user: User | null;
}

export interface ArrangementVersion {
  id: number;
  arrangementId: number;
  versionNum: string;
  timestamp: string;
  audio_state: 'none' | 'processing' | 'complete' | 'error';
}

export interface Arrangement {
  id: number;
  ensemble: number;
  ensemble_name: string;
  ensemble_slug: string;
  title: string;
  subtitle: string;
  slug: string;
  composer: string | null;
  mvt_no: string;
  latest_version: ArrangementVersion;
  latest_version_num: string;
  style: string;
}

export interface UserObj {
  id: number;
  username: string;
  email: string;
}

export interface EnsembleUsership {
  id: number;
  user: UserObj;
  role: 'M' | 'A'; // 'M' for member, 'A' for admin
  date_joined: string;
}

export interface Ensemble {
  id: number,
  name: string,
  slug: string,
  arrangements: [Arrangement],
  join_link?: string | null,
  is_admin: boolean, //if the requesting user is an admin in the esnemble
  userships?: EnsembleUsership[]
}

export interface EditableArrangementData {
  ensemble: number,
  title: string;
  subtitle: string;
  composer: string;
  mvt_no: string;
  style: string;
}

export interface VersionHistoryItem {
  id: number;
  version_label: string;
  timestamp: string;
  is_latest: boolean;
}

// export interface DiffData {
//   id: number;
//   from_version: number;
//   to_version: number;
//   file_name: string;
//   timestamp: string;
//   status: 'pending' | 'in_progress' | 'completed' | 'failed';
//   file_url: string;
//   error_msg: string;
// }

// Helper function to get CSRF token from cookies
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Helper to get headers with CSRF token for POST/PUT/DELETE requests
function getHeadersWithCsrf(contentType: string = 'application/json'): HeadersInit {
  const headers: HeadersInit = {
    'Accept': 'application/json',
    'Content-Type': contentType,
  };
  
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  return headers;
}

export const apiService = {
  /**
   * Fetch CSRF token from backend - ensures cookie is set
   * Call this on app initialization
   */
  async fetchCsrfToken(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/get-csrf-token/`, {
        method: 'GET',
        credentials: 'include', // Important: include cookies
      });
      if (!response.ok) {
        console.warn('Failed to fetch CSRF token:', response.status);
      }
      // The cookie is set automatically by Django, we don't need the response body
    } catch (error) {
      console.warn('Error fetching CSRF token:', error);
    }
  },

  /**
   * Get the current authenticated user
   */
  async getCurrentUser(): Promise<AuthResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/current-user/`, {
      credentials: 'include', // Include cookies for session auth
    });
    if (!response.ok) {
      throw new Error(`Failed to get current user (status: ${response.status})`);
    }
    return response.json();
  },

  /**
   * Handle login requests
   */
  handleLogin(targetUrl = "/app/ensembles") {
    const url = apiService.getDiscordLoginUrl(targetUrl);
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    form.style.display = 'none';

    // include CSRF token as hidden form field (Django expects 'csrfmiddlewaretoken')
    const csrf = getCsrfToken();
    if (csrf) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'csrfmiddlewaretoken';
      input.value = csrf;
      form.appendChild(input);
    }

    document.body.appendChild(form);
    form.submit();
  },
  
  /**
   * Get Discord OAuth login URL with optional next parameter
   * @param nextUrl - Optional URL (absolute or path) to redirect to after login
   */
  getDiscordLoginUrl(nextUrl?: string): string {
    const feBase = (import.meta.env.VITE_FE_URL && import.meta.env.VITE_FE_URL.replace(/\/$/, '')) || window.location.origin;
    let next: string;

    if (nextUrl) {
      // If nextUrl is already an absolute URL, use it; otherwise make it absolute relative to FE base
      try {
        const maybeAbsolute = new URL(nextUrl, feBase);
        next = maybeAbsolute.href;
      } catch {
        // Fallback: join manually
        next = nextUrl.startsWith('/') ? `${feBase}${nextUrl}` : `${feBase}/${nextUrl}`;
      }
    } else {
      // Default to current location
      next = `${feBase}${window.location.pathname}${window.location.search}`;
    }

    const separator = DISCORD_LOGIN_URL.includes('?') ? '&' : '?';
    return `${DISCORD_LOGIN_URL}${separator}next=${encodeURIComponent(next)}`;
  },

  /**
   * Logout the current user
   */
  async logout(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
      method: 'POST',
      headers: getHeadersWithCsrf(),
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error(`Failed to logout (status: ${response.status})`);
    }
  },

  async getWarnings() {
    const response = await fetch(`${API_BASE_URL}/get-warnings/`, {
      credentials: 'include',
    });
    if( !response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to fetch warning labels (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  },

  async getEnsembles() {
    const response = await fetch(`${API_BASE_URL}/ensembles/`, {
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to fetch ensembles (status: ${response.status}) - ${errorDetails}`
      );
    }
  return response.json();
  },

  async removeUserFromEnsemble(user_id: number, ensemble: string){
    const response = await fetch(`${API_BASE_URL}/ensembles/${ensemble}/remove-user`, 
      {
        method: 'POST', 
        headers: getHeadersWithCsrf(), 
        body: JSON.stringify({"user_id": user_id}),
        credentials: 'include',
      }
    )
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to create ensemble (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async changeUserRole(user_id: number, ensemble: string, role: 'M' | 'A'){
    const response = await fetch(`${API_BASE_URL}/ensembles/${ensemble}/change-user-role/`, 
      {
        method: 'POST', 
        headers: getHeadersWithCsrf(), 
        body: JSON.stringify({"user_id": user_id, "role": role}),
        credentials: 'include',
      }
    )
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to change user role (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async createEnsemble(name: string, selected_style: string){
    const response = await fetch(`${API_BASE_URL}/ensembles/`, 
      {
        method: 'POST', 
        headers: getHeadersWithCsrf(), 
        body: JSON.stringify({"name": name, "default_style": selected_style}),
        credentials: 'include',
      }
    )
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to create ensemble (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async getEnsemble(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/`, {
      credentials: 'include',
    });
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to fetch ensemble (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async getEnsembleArrangements(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/arrangements/`, {
      credentials: 'include',
    });
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to fetch arrangements (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async getArrangement(slug: string) {
    const response = await fetch(`${API_BASE_URL}/arrangements/${slug}/`, {
      credentials: 'include',
    });
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to fetch arrangement (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async getArrangementById(id: number) {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${id}/`, {
      credentials: 'include',
    });
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to fetch arrangement (status: ${response.status}) - ${errorDetails}`
    );
  }
  return response.json();
  },

  async updateArrangement (id: number, data: EditableArrangementData) {
    // Make API call to update arrangement
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${id}/`, {
      method: 'PUT',
      headers: getHeadersWithCsrf(),
      body: JSON.stringify(data),
      credentials: 'include',
    });
    return response.json();
  },

  async createArrangement(ensembleId: number, title: string, subtitle: string, composer: string, mvtNo: string, style: string){
    const body: Record<string, any> = {
      ensemble: ensembleId,
      title,
      subtitle,
      composer,
      mvt_no: mvtNo,
      style,
    };


    const response = await fetch(`${API_BASE_URL}/arrangements/`, 
      {
        method: 'POST', 
        headers: getHeadersWithCsrf(), 
        body: JSON.stringify(body),
        credentials: 'include',
      }
    )
    if (!response.ok) {
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to Create Arrangement (status: ${response.status}) - ${errorDetails}`
    );
  }

  return response.json();
  },

  async getDownloadLinksForVersion(versionId: number) {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/get_download_links/`, {
      credentials: 'include',
    });
    if (!response.ok){
    let errorDetails = '';
    try {
      const errorData = await response.json();
      errorDetails = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorDetails = await response.text();
    }
    throw new Error(
      `Failed to get download links (status: ${response.status}) - ${errorDetails}`
    );
    }

    return response.json()
  },

  async getPartsForVersion(versionId: number) {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/list_parts/`, {
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to get parts (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  },

  async getVersionHistory(arrangementId: number): Promise<VersionHistoryItem[]> {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${arrangementId}/versions/`, {
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to fetch version history (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  },

  async getVersionDetails(versionId: number): Promise<ArrangementVersion> {
    const response = await fetch(`${API_BASE_URL}/versions/${versionId}/`, {
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to fetch version details (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  },


  //TODO[SC-262]: When new diff functionality is set up (with new git-based arrangementversions), uncomment this and have it use new endpoints

  // /**
  //  * Compute a diff between two arrangement versions
  //  * @param fromVersionId - ID of the source version
  //  * @param toVersionId - ID of the target version
  //  * @returns Promise<DiffData>
  //  */
  // async computeDiff(fromVersionId: number, toVersionId: number): Promise<DiffData> {
  //   const response = await fetch(`${API_BASE_URL}/diffs/`, {
  //     method: 'POST',
  //     headers: getHeadersWithCsrf(),
  //     body: JSON.stringify({
  //       from_version_id: fromVersionId,
  //       to_version_id: toVersionId,
  //     }),
  //     credentials: 'include',
  //   });

  //   if (!response.ok) {
  //     const errorData = await response.json().catch(() => ({}));
  //     throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
  //   }

  //   return await response.json();
  // },

  // /**
  //  * Get an existing diff by ID
  //  * @param diffId - ID of the diff
  //  * @returns Promise<DiffData>
  //  */
  // async getDiff(diffId: number): Promise<DiffData> {
  //   const response = await fetch(`${API_BASE_URL}/diffs/?diff_id=${diffId}`, {
  //     method: 'GET',
  //     headers: {
  //       'Content-Type': 'application/json',
  //     },
  //     credentials: 'include',
  //   });

  //   if (!response.ok) {
  //     const errorData = await response.json().catch(() => ({}));
  //     throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
  //   }

  //   return await response.json();
  // },

  // /**
  //  * Alternative method to get diff by version IDs (if it already exists)
  //  * @param fromVersionId - ID of the source version
  //  * @param toVersionId - ID of the target version
  //  * @returns Promise<DiffData>
  //  */
  // async getDiffByVersions(fromVersionId: number, toVersionId: number): Promise<DiffData> {
  //   const response = await fetch(`${API_BASE_URL}/diffs/`, {
  //     method: 'GET',
  //     headers: {
  //       'Content-Type': 'application/json',
  //     },
  //     body: JSON.stringify({
  //       from_version_id: fromVersionId,
  //       to_version_id: toVersionId,
  //     }),
  //     credentials: 'include',
  //   });

  //   if (!response.ok) {
  //     const errorData = await response.json().catch(() => ({}));
  //     throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
  //   }

  //   return await response.json();
  // },

  async triggerAudioExport(versionId: number) {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/trigger_audio_export/`, {
      method: 'POST',
      headers: getHeadersWithCsrf(),
      credentials: 'include',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  },

  /**
   * Get or generate invite link for an ensemble
   * @param slug - Ensemble slug
   * @returns Promise with invite link information
   */
  async getInviteLink(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/invite-link/`, {
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to get invite link (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  },

  /**
   * Get ensemble info from invite token (for preview before joining)
   * @param token - Invite token
   * @returns Promise with ensemble information
   */
  async getEnsembleByToken(token: string) {
    const response = await fetch(`${API_BASE_URL}/join/?token=${encodeURIComponent(token)}`, {
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to get ensemble info (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  },

  /**
   * Join an ensemble using an invite token
   * @param token - Invite token
   * @returns Promise with ensemble information
   */
  async joinEnsemble(token: string) {
    const response = await fetch(`${API_BASE_URL}/join/`, {
      method: 'POST',
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({ token }),
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetails = '';
      try {
        const errorData = await response.json();
        errorDetails = errorData.detail || JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }
      throw new Error(
        `Failed to join ensemble (status: ${response.status}) - ${errorDetails}`
      );
    }
    return response.json();
  }

};

