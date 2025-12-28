const API_BASE_URL = import.meta.env.VITE_API_URL;

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

export interface Ensemble {
  id: number,
  name: string,
  slug: string,
  arrangements: [Arrangement]
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

export interface DiffData {
  id: number;
  from_version: number;
  to_version: number;
  file_name: string;
  timestamp: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  file_url: string;
  error_msg: string;
}

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

  /**
   * Get Discord OAuth login URL
   */
  getDiscordLoginUrl(): string {
    return `${API_BASE_URL}/accounts/discord/login/?process=login`;
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

  /**
   * Compute a diff between two arrangement versions
   * @param fromVersionId - ID of the source version
   * @param toVersionId - ID of the target version
   * @returns Promise<DiffData>
   */
  async computeDiff(fromVersionId: number, toVersionId: number): Promise<DiffData> {
    const response = await fetch(`${API_BASE_URL}/diffs/`, {
      method: 'POST',
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({
        from_version_id: fromVersionId,
        to_version_id: toVersionId,
      }),
      credentials: 'include',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  },

  /**
   * Get an existing diff by ID
   * @param diffId - ID of the diff
   * @returns Promise<DiffData>
   */
  async getDiff(diffId: number): Promise<DiffData> {
    const response = await fetch(`${API_BASE_URL}/diffs/?diff_id=${diffId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  },

  /**
   * Alternative method to get diff by version IDs (if it already exists)
   * @param fromVersionId - ID of the source version
   * @param toVersionId - ID of the target version
   * @returns Promise<DiffData>
   */
  async getDiffByVersions(fromVersionId: number, toVersionId: number): Promise<DiffData> {
    const response = await fetch(`${API_BASE_URL}/diffs/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from_version_id: fromVersionId,
        to_version_id: toVersionId,
      }),
      credentials: 'include',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  },

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
  }

};

