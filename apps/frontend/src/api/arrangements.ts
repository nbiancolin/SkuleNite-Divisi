import { API_BASE_URL, getCsrfToken, getHeadersWithCsrf } from "./client";
import type {
  Arrangement,
  ArrangementVersion,
  ArrangementVersionCommentThread,
  Commit,
  EditableArrangementData,
  StaffSpacingStrategy,
  VersionHistoryItem,
} from "./types";

export const arrangementApi = {
  getLatestCommitMsczDownloadUrl(arrangementId: number): string {
    return `${API_BASE_URL}/arrangements-by-id/${arrangementId}/download-latest-commit-mscz/`;
  },

  async getArrangement(slug: string) {
    const response = await fetch(`${API_BASE_URL}/arrangements/${slug}/`, {
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
      throw new Error(`Failed to fetch arrangement (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async getArrangementById(id: number) {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${id}/`, {
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
      throw new Error(`Failed to fetch arrangement (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async updateArrangement(id: number, data: EditableArrangementData) {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${id}/`, {
      method: "PUT",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify(data),
      credentials: "include",
    });
    return response.json();
  },

  async createArrangement(
    ensembleId: number,
    title: string,
    subtitle: string,
    composer: string,
    mvtNo: string,
    style: string
  ) {
    const body: Record<string, unknown> = {
      ensemble: ensembleId,
      title,
      subtitle,
      composer,
      mvt_no: mvtNo,
      style,
    };

    const response = await fetch(`${API_BASE_URL}/arrangements/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify(body),
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
      throw new Error(`Failed to Create Arrangement (status: ${response.status}) - ${errorDetails}`);
    }

    return response.json();
  },

  async getDownloadLinksForVersion(versionId: number) {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/get_download_links/`, {
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
      throw new Error(`Failed to get download links (status: ${response.status}) - ${errorDetails}`);
    }

    return response.json();
  },

  async getPartsForVersion(versionId: number) {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/list_parts/`, {
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
      throw new Error(`Failed to get parts (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async getVersionHistory(arrangementId: number): Promise<VersionHistoryItem[]> {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${arrangementId}/versions/`, {
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
      throw new Error(`Failed to fetch version history (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async getVersionDetails(versionId: number): Promise<ArrangementVersion> {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/`, {
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
      throw new Error(`Failed to fetch version details (status: ${response.status}) - ${errorDetails}`);
    }
    return response.json();
  },

  async createArrangementCommit(
    arrangementId: number,
    file: File,
    message?: string
  ): Promise<{ arrangement: Arrangement }> {
    const formData = new FormData();
    const csrfToken = getCsrfToken();
    formData.append("file", file);
    if (message && message.trim()) {
      formData.append("message", message.trim());
    }

    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${arrangementId}/new-commit/`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      body: formData,
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
      throw new Error(`Failed to create commit (status: ${response.status}) - ${errorDetails}`);
    }

    return response.json();
  },

  async createArrangementVersionFromCommit(
    commitId: number,
    options?: {
      version_type?: string;
      num_measures_per_line_score?: number;
      num_measures_per_line_part?: number;
      num_lines_per_page?: number;
      staff_spacing_strategy?: StaffSpacingStrategy;
      staff_spacing_value?: string | number;
      format_parts?: boolean;
      formatting_steps?: Record<string, boolean>;
    }
  ) {
    const body: Record<string, string | number | boolean | Record<string, boolean>> = {
      commit_id: commitId,
    };
    if (options?.version_type != null) body.version_type = options.version_type;
    if (options?.num_measures_per_line_score != null) {
      body.num_measures_per_line_score = options.num_measures_per_line_score;
    }
    if (options?.num_measures_per_line_part != null) {
      body.num_measures_per_line_part = options.num_measures_per_line_part;
    }
    if (options?.num_lines_per_page != null) {
      body.num_lines_per_page = options.num_lines_per_page;
    }
    if (options?.staff_spacing_strategy != null) {
      body.staff_spacing_strategy = options.staff_spacing_strategy;
    }
    if (options?.staff_spacing_value != null) {
      body.staff_spacing_value = options.staff_spacing_value;
    }
    if (options?.format_parts != null) {
      body.format_parts = options.format_parts;
    }
    if (options?.formatting_steps != null) {
      body.formatting_steps = options.formatting_steps;
    }

    const response = await fetch(`${API_BASE_URL}/arrangementversions/create_from_commit/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify(body),
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
      throw new Error(
        `Failed to create arrangement version from commit (status: ${response.status}) - ${errorDetails}`
      );
    }

    return response.json();
  },

  async getArrangementCommits(arrangementId: number): Promise<Commit[]> {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${arrangementId}/commits/`, {
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
      throw new Error(`Failed to fetch arrangement commits (status: ${response.status}) - ${errorDetails}`);
    }

    return response.json();
  },

  async checkScoreVersion(arrangementId: number): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/arrangements-by-id/${arrangementId}/check_score_version/`, {
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
      throw new Error(
        `Failed to fetch arrangement score version (status: ${response.status}) - ${errorDetails}`
      );
    }

    const res = await response.json();
    return res.status === "ok";
  },

  async triggerAudioExport(versionId: number) {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/trigger_audio_export/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  },

  async getVersionComments(versionId: number): Promise<{ threads: ArrangementVersionCommentThread[] }> {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/comments/`, {
      credentials: "include",
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to fetch comments (status: ${response.status}) - ${errorText}`);
    }
    return response.json();
  },

  async createVersionCommentThread(
    versionId: number,
    payload: { page_number: number; x: number; y: number; body: string }
  ): Promise<ArrangementVersionCommentThread> {
    const response = await fetch(`${API_BASE_URL}/arrangementversions/${versionId}/comments/threads/`, {
      method: "POST",
      headers: getHeadersWithCsrf(),
      body: JSON.stringify(payload),
      credentials: "include",
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create comment thread (status: ${response.status}) - ${errorText}`);
    }
    return response.json();
  },

  async createVersionCommentMessage(
    versionId: number,
    threadId: number,
    payload: { body: string }
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/arrangementversions/${versionId}/comments/threads/${threadId}/messages/`,
      {
        method: "POST",
        headers: getHeadersWithCsrf(),
        body: JSON.stringify(payload),
        credentials: "include",
      }
    );
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create comment message (status: ${response.status}) - ${errorText}`);
    }
  },

  async resolveVersionCommentThread(
    versionId: number,
    threadId: number
  ): Promise<ArrangementVersionCommentThread> {
    const response = await fetch(
      `${API_BASE_URL}/arrangementversions/${versionId}/comments/threads/${threadId}/resolve/`,
      {
        method: "POST",
        headers: getHeadersWithCsrf(),
        credentials: "include",
      }
    );
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to resolve comment thread (status: ${response.status}) - ${errorText}`);
    }
    return response.json();
  },

  async reopenVersionCommentThread(
    versionId: number,
    threadId: number
  ): Promise<ArrangementVersionCommentThread> {
    const response = await fetch(
      `${API_BASE_URL}/arrangementversions/${versionId}/comments/threads/${threadId}/reopen/`,
      {
        method: "POST",
        headers: getHeadersWithCsrf(),
        credentials: "include",
      }
    );
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to reopen comment thread (status: ${response.status}) - ${errorText}`);
    }
    return response.json();
  },
};
