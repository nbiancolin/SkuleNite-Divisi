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

export interface Commit {
  id: number;
  arrangementId: number;
  message: string;
  timestamp: string;
  has_version: boolean;
  created_by?: UserObj | null;
}

/** MuseScore spatium handling; matches backend ArrangementVersion.staff_spacing_strategy. */
export type StaffSpacingStrategy = "predict" | "preserve" | "override";

export interface ArrangementVersion {
  id: number;
  arrangementId: number;
  versionNum: string;
  timestamp: string;
  audio_state: "none" | "processing" | "complete" | "error";
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
  latest_version: ArrangementVersion | null;
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
  role: "M" | "A";
  date_joined: string;
}

export interface EnsemblePartBook {
  id: number;
  part_name_id: number;
  part_display_name: string;
  revision: number;
  created_at: string | null;
  finalized_at: string | null;
  is_rendered: boolean;
  download_url: string | null;
}

export interface PartName {
  id: number;
  display_name: string;
  order: number | null;
  arrangements?: string[];
}

export interface Ensemble {
  id: number;
  name: string;
  slug: string;
  arrangements?: Arrangement[];
  arrangements_count?: number;
  join_link?: string | null;
  is_admin: boolean;
  part_names?: PartName[];
  part_name?: PartName[];
  userships?: EnsembleUsership[];
  part_books_generating?: boolean;
  latest_part_book_revision?: number;
  part_books?: EnsemblePartBook[];
}

export interface EditableArrangementData {
  ensemble: number;
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
