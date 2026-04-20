import { arrangementApi } from "./arrangements";
import { authApi } from "./auth";
import { ensembleApi } from "./ensembles";

export * from "./types";

export const apiService = {
  ...authApi,
  ...ensembleApi,
  ...arrangementApi,
};
