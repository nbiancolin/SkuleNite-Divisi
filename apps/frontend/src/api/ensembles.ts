import { API_BASE_URL, getHeadersWithCsrf } from "./client";

export const ensembleApi = {
  async getEnsembles() {
    const response = await fetch(`${API_BASE_URL}/ensembles/`, {
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
      throw new Error(`Failed to fetch ensembles (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async removeUserFromEnsemble(user_id: number, ensemble: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${ensemble}/remove-user`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({ user_id: user_id }),
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
      throw new Error(`Failed to create ensemble (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async changeUserRole(user_id: number, ensemble: string, role: "M" | "A") {
    const response = await fetch(`${API_BASE_URL}/ensembles/${ensemble}/change-user-role/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({ user_id: user_id, role: role }),
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
      throw new Error(`Failed to change user role (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async createEnsemble(name: string, selected_style: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({ name: name, default_style: selected_style }),
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
      throw new Error(`Failed to create ensemble (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async getEnsemble(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/`, {
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
      throw new Error(`Failed to fetch ensemble (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async getEnsembleArrangements(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/arrangements/`, {
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
      throw new Error(`Failed to fetch arrangements (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async generatePartBooksForEnsemble(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/generate_part_books/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
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
      throw new Error(`Failed to generate part books (status: ${response.status}) - ${errorDetails}`);
    }

    return response.json();
  },

  async getInviteLink(slug: string) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/invite-link/`, {
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
      throw new Error(`Failed to get invite link (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async getEnsembleByToken(token: string) {
    const response = await fetch(`${API_BASE_URL}/join/?token=${encodeURIComponent(token)}`, {
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
      throw new Error(`Failed to get ensemble info (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async joinEnsemble(token: string) {
    const response = await fetch(`${API_BASE_URL}/join/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({ token }),
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
      throw new Error(`Failed to join ensemble (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async updatePartOrder(slug: string, partOrders: Array<{ id: number; order: number }>) {
    const response = await fetch(`${API_BASE_URL}/ensembles/${slug}/update-part-order/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify({ part_orders: partOrders }),
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
      throw new Error(`Failed to update part order (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async mergePartNames(
    ensembleSlug: string,
    firstId: number,
    secondId: number,
    new_displayname?: string | null
  ) {
    const payload = {
      first_id: firstId,
      second_id: secondId,
      ...(new_displayname ? { new_displayname } : {}),
    };

    const response = await fetch(`${API_BASE_URL}/ensembles/${ensembleSlug}/merge_part_names/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify(payload),
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
      throw new Error(`Failed to merge part names (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },
};
