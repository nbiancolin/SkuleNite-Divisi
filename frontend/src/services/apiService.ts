const API_BASE_URL = import.meta.env.VITE_API_URL;

export const apiService = {
  async getEnsembles() {
    const response = await fetch(`${API_BASE_URL}/ensembles/`);
    if (!response.ok) throw new Error('Failed to fetch ensembles');
    return response.json();
  },

  async createEnsemble(name: string){
    const response = await fetch(`${API_BASE_URL}/ensembles/`, {method: 'POST', body: JSON.stringify({"name": name})})
    if (!response.ok) throw new Error('Failed to fetch ensembles');
    return response.json();
  },

  async getEnsemble(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/`);
    if (!response.ok) throw new Error('Failed to fetch ensemble');
    return response.json();
  },

  async getEnsembleArrangements(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/arrangements/`);
    if (!response.ok) throw new Error('Failed to fetch arrangements');
    return response.json();
  }
};