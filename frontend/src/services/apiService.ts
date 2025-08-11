const API_BASE_URL = import.meta.env.VITE_API_URL;

export interface ArrangementVersion {
  id: number,
  uuid: string,
  arrangement: number,
  version_label: string,
  timestamp: string,
}

export interface Arrangement {
  id: number,
  ensemble: number
  title: string,
  slug: string,
  composer: string|null,
  actNumber: number|null,
  pieceNumber: number,
  mvt_no: string,
  latestVersion: ArrangementVersion,
  latestVersionNum: string,
}

export interface Ensemble {
  id: number,
  name: string,
  slug: string,
  arrangements: [Arrangement]
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

  async createArrangement(ensembleId: number, title: string, subtitle: string, composer: string, actNumber: number|undefined, pieceNumber: number|undefined, style: string){
    const response = await fetch(`${API_BASE_URL}/arrangements/`, 
      {
        method: 'POST', 
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'}, 
        body: JSON.stringify({"ensemble": ensembleId, "title": title, "subtitle": subtitle, "composer": composer, "act_number": actNumber, "piece_number": pieceNumber, "default_style": style})
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
};