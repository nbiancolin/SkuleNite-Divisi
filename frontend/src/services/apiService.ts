const API_BASE_URL = import.meta.env.VITE_API_URL;

export interface ArrangementVersion {
  id: number;
  arrangementId: number;
  versionNum: string;
  timestamp: string;
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
  actNumber?: number;
  pieceNumber: number;
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
  piece_number?: number;
  act_number?: number | null;
  style: string;
}

// New interface for version history
export interface VersionHistoryItem {
  id: number;
  version_label: string;
  timestamp: string;
  is_latest: boolean;
}

export const apiService = {
  async getEnsembles() {
    const response = await fetch(`${API_BASE_URL}/ensembles/`);
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
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'}, 
        body: JSON.stringify({"name": name, "default_style": selected_style})
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
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/`);
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
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/arrangements/`);
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
    const response = await fetch(`${API_BASE_URL}/arrangements/${slug}/`);
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
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${id}/`);
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

  updateArrangement: async (id: number, data: EditableArrangementData) => {
    // Make API call to update arrangement
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${id}/`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  async createArrangement(ensembleId: number, title: string, subtitle: string, composer: string, actNumber: string, pieceNumber: string, style: string){
    const body: Record<string, any> = {
      ensemble: ensembleId,
      title,
      subtitle,
      composer,
      piece_number: pieceNumber,
      style,
    };

    if (actNumber !== "") {
      body["act_number"] = actNumber;
    }
    const response = await fetch(`${API_BASE_URL}/arrangements/`, 
      {
        method: 'POST', 
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'}, 
        body: JSON.stringify(body)
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
    const response = await fetch(`${API_BASE_URL}/get-download-links/?version_id=${versionId}`);
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

  // NEW: Get version history for an arrangement
  async getVersionHistory(arrangementId: number): Promise<VersionHistoryItem[]> {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${arrangementId}/versions/`);
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

  // NEW: Get specific version details
  async getVersionDetails(versionId: number): Promise<ArrangementVersion> {
    const response = await fetch(`${API_BASE_URL}/versions/${versionId}/`);
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
  }
};