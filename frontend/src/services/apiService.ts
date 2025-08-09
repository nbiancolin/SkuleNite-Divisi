const API_BASE_URL = import.meta.env.VITE_API_URL;

export const apiService = {
  async getEnsembles() {
    const response = await fetch(`${API_BASE_URL}/ensembles/`);
    if (!response.ok) throw new Error('Failed to fetch ensembles');
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
    if (!response.ok) throw new Error('Failed to create ensemble');
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
  },

  async createArrangement(ensembleSlug: string, title: string, subtitle: string, composer: string, actNumber: number|null, pieceNumber: number|null, style: string){
    const response = await fetch(`${API_BASE_URL}/arrangements/`, 
      {
        method: 'POST', 
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'}, 
        body: JSON.stringify({"ensemble": ensembleSlug, "title": title, "subtitle": subtitle, "composer": composer, "act_number": actNumber, "piece_number": pieceNumber, "default_style": style})
      }
    )
    if (!response.ok) throw new Error('Failed to create arrangement');
    return response.json();
  },
};